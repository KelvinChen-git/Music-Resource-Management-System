"""Source-only expansion policies. Provisional times never certify actual audio EOF."""
from collections import Counter, defaultdict
from datetime import date, timedelta
import hashlib

from caption_coverage import Coverage
from caption_pair_preflight import require


def isolate(records, existing, blocked_ids, blocked_groups, blocked_works, blocked_sha):
    """Quarantine both sides of cross-split credit/work/content relations, then cap credits."""
    all_rows = existing + records
    relations = {key: defaultdict(set) for key in ('creator_component', 'work', 'audio_sha256')}
    for r in all_rows:
        for key in relations:
            relations[key][r[key]].add(r['split'])
    old_ids = {r['id'] for r in existing}
    old_hashes = {r['audio_sha256'] for r in existing}
    old_works = {r['work'] for r in existing}
    counts = Counter(r['creator_component'] for r in existing)
    result, rejected = [], Counter()
    seen_ids, seen_hashes, seen_works = set(), set(), set()
    for r in sorted(records, key=lambda x: (x['priority_sha256'], int(x['id']))):
        reasons = []
        if r['id'] in blocked_ids or r['id'] in old_ids: reasons.append('reserved_prior_or_existing_ID')
        if r['creator_component'] in blocked_groups: reasons.append('reserved_or_prior_creator')
        if r['work'] in blocked_works or r['work'] in old_works: reasons.append('reserved_prior_or_existing_work')
        if r['audio_sha256'] in blocked_sha or r['audio_sha256'] in old_hashes: reasons.append('reserved_prior_or_existing_content')
        if any(len(relations[k][r[k]]) > 1 for k in relations): reasons.append('cross_split_relation')
        if r['id'] in seen_ids or r['audio_sha256'] in seen_hashes or r['work'] in seen_works:
            reasons.append('duplicate_new_identity_work_or_content')
        if counts[r['creator_component']] >= 4: reasons.append('four_recordings_per_creator_cap')
        if r['original_audio_license_family'] not in ('by', 'by-sa'): reasons.append('original_audio_license')
        if reasons:
            rejected.update(reasons)
            continue
        result.append(r)
        seen_ids.add(r['id']); seen_hashes.add(r['audio_sha256']); seen_works.add(r['work'])
        counts[r['creator_component']] += 1
    require(result, 'No isolated expansion frame')
    return result, dict(rejected)


def provisional_scanner(records):
    # 600 is a decode-policy upper bound, never a claimed measured duration.
    return Coverage([{**r, 'duration_seconds': 600} for r in records])


def choose_candidates(records, captions, counts, seed):
    covered = {r['id'] for r in captions}
    chosen = []
    for split in ('train', 'validation'):
        rows = [r for r in records if r['split'] == split and r['id'] in covered]
        rows.sort(key=lambda r: (hashlib.sha256((seed+'\n'+r['id']).encode()).hexdigest(), int(r['id'])))
        chosen.extend(rows[:counts[split]])
    return chosen


def metadata_file(release_date):
    anchor = date(2008, 1, 1)
    current = date.fromisoformat(release_date)
    require(current >= anchor, 'Date before pinned metadata anchor')
    return (anchor + timedelta(days=((current-anchor).days//5)*5)).isoformat()+'.jsonl'


def actual_intervals(original, raw_lines):
    scanner = Coverage([original])
    for raw in raw_lines: scanner.add(raw)
    result = scanner.finish()
    require(result['summary']['overlapping_interval_pairs'] == 0, 'Overlapping captions require explicit policy')
    return result
