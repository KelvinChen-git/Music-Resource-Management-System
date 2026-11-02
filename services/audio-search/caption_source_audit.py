"""Source-only projections and grouped supplemental-development planning."""
from collections import Counter, defaultdict
import csv
from decimal import Decimal, InvalidOperation
import hashlib
import io
import re
from urllib.parse import urlsplit

from review_pack import require


def wiki_frame(raw):
    reader = csv.DictReader(io.StringIO(raw.decode('utf8')))
    require(reader.fieldnames == ['file', 'pageid', 'aspects', 'sentences', 'audio_url', 'page_url'],
            'Pinned WikiMuTe source schema required')
    projected, invalid = [], Counter()
    for row in reader:
        # Neither sentences nor aspects are inspected or parsed as text lists.
        filename, pageid, audio, article = (row[k] for k in ('file', 'pageid', 'audio_url', 'page_url'))
        if not filename or not pageid.isascii() or not pageid.isdigit():
            invalid['invalid_file_or_page_id'] += 1
            continue
        parsed = urlsplit(audio)
        if (parsed.scheme != 'https' or parsed.netloc != 'upload.wikimedia.org'
                or not parsed.path.startswith('/wikipedia/') or parsed.query or parsed.fragment):
            invalid['unsupported_audio_url'] += 1
            continue
        page = urlsplit(article)
        if page.scheme not in ('http', 'https') or page.netloc != 'en.wikipedia.org':
            invalid['unsupported_article_url'] += 1
            continue
        projected.append({'file': filename, 'pageid': pageid, 'audio_url': audio, 'page_url': article})
    files, urls, pages = defaultdict(set), defaultdict(set), defaultdict(set)
    for row in projected:
        files[row['file']].add(row['audio_url'])
        urls[row['audio_url']].add(row['file'])
        pages[row['pageid']].add(row['file'])
    return {'rows': projected, 'summary': {
        'source_rows': len(projected) + sum(invalid.values()), 'projected_rows': len(projected),
        'unique_files': len(files), 'unique_audio_urls': len(urls), 'unique_article_ids': len(pages),
        'duplicate_file_article_url_rows': len(projected) - len({tuple(r.values()) for r in projected}),
        'files_with_conflicting_audio_urls': sum(len(v) > 1 for v in files.values()),
        'urls_shared_by_multiple_filenames': sum(len(v) > 1 for v in urls.values()),
        'articles_containing_multiple_files': sum(len(v) > 1 for v in pages.values()),
        'audio_url_wiki_namespaces': dict(sorted(Counter(urlsplit(u).path.split('/')[2] for u in urls).items())),
        'quarantined_rows_by_reason': dict(invalid), 'caption_bodies_used': False,
        'clip_human_verification_established': False, 'artist_work_fields_present': False,
        'per_audio_rights_established': False, 'audio_ready': 0,
    }}


def youtube_frame(raw, musiccaps_rows, musicbench_train_ids):
    reader = csv.DictReader(io.StringIO(raw.decode('utf8')))
    require(reader.fieldnames == ['video_id', 'start', 'end', 'text'], 'Pinned YouTube8M schema required')
    projected = []
    for row in reader:
        require(re.fullmatch(r'[A-Za-z0-9_-]{11}', row['video_id']) is not None, 'Invalid YouTube source ID')
        try:
            start, end = Decimal(row['start']), Decimal(row['end'])
        except InvalidOperation as error:
            raise ValueError('Invalid clip times') from error
        require(start.is_finite() and end.is_finite() and start >= 0 and end - start == 10,
                'Exactly10 finite seconds required')
        projected.append({'video_id': row['video_id'], 'start': str(start), 'end': str(end)})
    ids = {r['video_id'] for r in projected}
    canonical = {r['ytid']: r for r in musiccaps_rows}
    overlap = ids & set(canonical)
    clips = {(r['video_id'], Decimal(r['start']), Decimal(r['end'])) for r in projected}
    mcclips = {(t, Decimal(canonical[t]['start_s']), Decimal(canonical[t]['end_s'])) for t in overlap}
    return {'rows': projected, 'summary': {
        'source_train_rows': len(projected), 'source_train_video_ids': len(ids),
        'unique_clips': len(clips), 'duplicate_clip_rows': len(projected) - len(clips),
        'musiccaps_video_id_overlap': len(overlap), 'musiccaps_exact_clip_overlap': len(clips & mcclips),
        'musicbench_training_video_id_overlap': len(ids & set(musicbench_train_ids)),
        'artist_work_fields_present': False, 'original_audio_distributed_with_csv': False,
        'per_audio_rights_established': False, 'caption_bodies_used': False, 'audio_ready': 0,
    }}


def supplement_plan(eligible, sdd_rows, seed):
    require(seed == 'MUS-062-unused-SDD-six-components-v1', 'Fixed source-only seed required')
    require(len(eligible) == 8 and len({r['source_track_id'] for r in eligible}) == 8,
            'Exactly8 original unused candidates required')
    groups = defaultdict(list)
    validated = Counter(r['track_id'] for r in sdd_rows if r['validated'])
    for row in eligible:
        require(row['validated_caption_count'] == validated[row['source_track_id']] > 0,
                'Original valid-caption count changed')
        key = hashlib.sha256((seed + '\n' + row['source_track_id']).encode()).hexdigest()
        groups[row['creator_component']].append({**row, 'priority_sha256': key})
    require(len(groups) == 6, 'Exactly6 independent source components required')
    selected, omitted = [], []
    for component in sorted(groups):
        ordered = sorted(groups[component], key=lambda r: (r['priority_sha256'], r['source_track_id']))
        selected.append(ordered[0]); omitted.extend(ordered[1:])
    require(len({r['work_key'] for r in selected}) == 6 and len({r['audio_sha256'] for r in selected}) == 6,
            'Work or official content conflict; no automatic replacement')
    return {'schema': 'sonora-six-source-development-supplement-v1', 'role': 'development_metadata_only',
            'selected': selected, 'omitted_same_component_not_fallback': omitted,
            'summary': {'selected_recordings': 6, 'creator_components': 6,
                        'validated_caption_queries': sum(r['validated_caption_count'] for r in selected),
                        'same_component_omitted_recordings': len(omitted), 'audio_ready': 0,
                        'caption_bodies_extracted': False, 'sealed_test_used': False,
                        'selection_uses_scores_or_text_semantics': False}}
