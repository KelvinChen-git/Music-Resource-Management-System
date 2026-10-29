#!/usr/bin/env python3
"""Collect an independent source-only development batch; never write local music APIs."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import ssl
from urllib.parse import quote, unquote, urlparse
from urllib.request import HTTPRedirectHandler, HTTPSHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = 'sonora-source-selection-v1'
SPLIT = 'development_source_candidates_not_held_out'
BUCKETS = ['exp-02', 'exp-03', 'exp-04', 'exp-07', 'exp-08']
BASE = 'https://incompetech.com/music/royalty-free/'
MAX_AUDIO = 30 * 1024 * 1024
MAX_METADATA = 2 * 1024 * 1024
ISRC = re.compile(r'[A-Z]{2}[A-Z0-9]{3}[0-9]{7}')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()


def strict_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'Duplicate JSON key')
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=pairs)


def pinned_json(path, expected):
    require(isinstance(expected, str) and re.fullmatch(r'[a-f0-9]{64}', expected), 'Explicit SHA256 required')
    raw = Path(path).read_bytes()
    require(0 < len(raw) <= MAX_METADATA and digest(raw) == expected, 'Input bytes/SHA256 mismatch')
    return strict_json(raw)


def filename_ok(value):
    return (isinstance(value, str) and 5 <= len(value) <= 180 and value.endswith('.mp3')
            and '..' not in value and not any(c in value for c in '/\\?#%')
            and all(ord(c) >= 32 and ord(c) != 127 for c in value))


def safe_url(value):
    url = urlparse(value)
    require(url.scheme == 'https' and url.hostname in ('incompetech.com', 'www.incompetech.com')
            and url.username is None and url.password is None and url.port in (None, 443)
            and not url.fragment, 'Unexpected official source origin')
    prefix = '/music/royalty-free/'
    path = unquote(url.path)
    require(path.startswith(prefix), 'Unexpected source path')
    tail = path[len(prefix):]
    allowed = tail in ('pieces.json', 'licenses/')
    if tail == 'index.html':
        allowed = bool(re.fullmatch(r'isrc=[A-Z]{2}[A-Z0-9]{3}[0-9]{7}', url.query))
    elif tail.startswith('mp3-royaltyfree/'):
        allowed = filename_ok(tail[len('mp3-royaltyfree/'):])
    require(allowed and (not url.query or tail == 'index.html'), 'Unexpected source URL/path parameters')
    return value


class OfficialRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        safe_url(newurl)
        old, new = urlparse(req.full_url), urlparse(newurl)
        require((old.path, old.query) == (new.path, new.query), 'Redirect changed source identity')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch_bytes(url, limit):
    safe_url(url)
    ca = '/etc/ssl/cert.pem' if Path('/etc/ssl/cert.pem').is_file() else None
    opener = build_opener(OfficialRedirects(), HTTPSHandler(context=ssl.create_default_context(cafile=ca)))
    request = Request(url, headers={'User-Agent': 'SonoraResearch/1.0 (bounded development collection)'})
    with opener.open(request, timeout=45) as response:
        safe_url(response.url)
        before, after = urlparse(url), urlparse(response.url)
        require((before.path, before.query) == (after.path, after.query), 'Response changed source identity')
        raw = response.read(limit + 1)
    require(0 < len(raw) <= limit, 'Empty or oversized source response')
    return raw


def validate_plan(plan):
    require(isinstance(plan, dict) and set(plan) == {'schema', 'split', 'tracks'}
            and plan['schema'] == SCHEMA and plan['split'] == SPLIT, 'Wrong selection schema/split')
    rows = plan['tracks']
    require(isinstance(rows, list) and len(rows) == 20, 'Expected twenty selections')
    counts, seen = Counter(), set()
    for row in rows:
        require(isinstance(row, dict) and set(row) == {'bucket_id', 'isrc', 'title'}, 'Unexpected selection fields')
        sid, bucket = row['isrc'], row['bucket_id']
        require(isinstance(sid, str) and ISRC.fullmatch(sid) and sid not in seen, 'Invalid or duplicate ISRC')
        require(bucket in BUCKETS, 'Unknown development bucket')
        require(isinstance(row['title'], str) and 0 < len(row['title']) <= 160
                and all(ord(c) >= 32 for c in row['title']), 'Invalid selected title')
        seen.add(sid)
        counts[bucket] += 1
    require(dict(counts) == dict.fromkeys(BUCKETS, 4), 'Expected four different candidates per bucket')
    return rows


def select_tracks(catalog, plan):
    rows = validate_plan(plan)
    require(isinstance(catalog, list), 'Expected official catalog list')
    selected = []
    for row in rows:
        sid, bucket = row['isrc'], row['bucket_id']
        matches = [p for p in catalog if isinstance(p, dict) and p.get('isrc') == sid]
        require(len(matches) == 1, 'Missing or ambiguous official recording')
        piece = matches[0]
        title, filename = piece.get('title'), piece.get('filename')
        require(isinstance(title, str) and title == row['title'] and 0 < len(title) <= 160
                and all(ord(c) >= 32 for c in title), 'Selection title changed')
        require(filename_ok(filename), 'Unsafe audio filename')
        length = piece.get('length')
        require(isinstance(length, str) and re.fullmatch(r'[0-9]{2}:[0-5][0-9]:[0-5][0-9]', length), 'Invalid duration')
        h, m, s = map(int, length.split(':'))
        seconds = h * 3600 + m * 60 + s
        require(30 <= seconds <= 600, 'Recording duration outside collection bounds')
        selected.append({'provider': 'incompetech', 'source_id': sid, 'bucket_id': bucket,
            'title': title, 'artist': 'Kevin MacLeod', 'duration_seconds': seconds,
            'source_url': BASE + 'index.html?isrc=' + sid,
            'license_url': 'https://creativecommons.org/licenses/by/4.0/',
            'download_url': safe_url(BASE + 'mp3-royaltyfree/' + quote(filename, safe='')),
            'audio_filename': sid + '.mp3', 'metadata_record_sha256': digest(canonical(piece)),
            'provider_instruments': str(piece.get('instruments') or '')[:1000],
            'provider_feel': str(piece.get('feel') or '')[:1000], 'provider_bpm': str(piece.get('bpm') or '')[:100],
            'attribution': title + ' — Kevin MacLeod (incompetech.com), CC BY 4.0',
            'changes': 'Audio file unchanged', 'human_relevance': None})
    return selected


def write_new(path, raw):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as output:
        output.write(raw)


def run(output, selection, selection_sha256, baseline_catalog, baseline_sha256, fetch=None):
    plan = pinned_json(selection, selection_sha256)
    validate_plan(plan)
    prior = pinned_json(baseline_catalog, baseline_sha256)
    require(isinstance(prior, dict) and isinstance(prior.get('audioTracks'), list), 'Invalid original catalog')
    old_hashes = {track['sha256'] for track in prior['audioTracks']}
    require(bool(old_hashes) and all(isinstance(v, str) and re.fullmatch(r'[a-f0-9]{64}', v) for v in old_hashes), 'Invalid original content hashes')
    # Bind exact titles against the live official snapshot before downloading any audio.
    first = plan['tracks'][0]['isrc']
    target = Path(output)
    local = ROOT / '.local'
    require(local.is_dir() and not local.is_symlink(), 'Expected checkout private root')
    resolved = target.resolve()
    require(resolved.is_relative_to(local.resolve()) and resolved != local.resolve(), 'Output must be below checkout .local')
    require(not any(p.is_symlink() for p in (target, *target.parents)), 'Output cannot traverse symlinks')
    require(target.parent.is_dir(), 'Create the private parent directory first')
    target.mkdir(mode=0o700)  # Existing successful or partial batches are never overwritten.
    get = fetch or fetch_bytes
    snapshots = {}
    urls = {'official-catalog.json': BASE + 'pieces.json',
            'official-track-template.html': BASE + 'index.html?isrc=' + first,
            'official-license.html': BASE + 'licenses/'}
    for name, url in urls.items():
        raw = get(safe_url(url), MAX_METADATA)
        require(isinstance(raw, bytes) and 0 < len(raw) <= MAX_METADATA, 'Invalid metadata response')
        write_new(target / name, raw)
        snapshots[name] = {'url': url, 'sha256': digest(raw)}
    template = (target / 'official-track-template.html').read_text()
    license_page = (target / 'official-license.html').read_text()
    require('Licensed under Creative Commons: By Attribution 4.0 License' in template
            and 'creativecommons.org/licenses/by/4.0/' in template
            and 'encodeURIComponent(p.filename)' in template, 'Official attribution/download template changed')
    require('Creative Commons' in license_page and 'Requires that you credit' in license_page, 'Official license description changed')
    tracks = select_tracks(strict_json((target / 'official-catalog.json').read_bytes()), plan)
    seen_hashes = set(old_hashes)
    for track in tracks:
        audio = get(track['download_url'], MAX_AUDIO)
        require(isinstance(audio, bytes) and 0 < len(audio) <= MAX_AUDIO
                and not audio.lstrip().startswith(b'<'), 'Invalid or oversized audio bytes')
        sha = digest(audio)
        require(sha not in seen_hashes, 'Duplicate new or original audio content')
        seen_hashes.add(sha)
        write_new(target / track['audio_filename'], audio)
        track.update(sha256=sha, bytes=len(audio))
        write_new(target / (track['source_id'] + '.download.json'), canonical({
            'sha256': sha, 'size': len(audio), 'source': track['source_url'],
            'license': track['license_url'], 'download_url': track['download_url'],
            'metadata_record_sha256': track['metadata_record_sha256'], 'snapshots': snapshots}))
    # Refuse an input change during acquisition; no final manifest signals an incomplete batch.
    require(digest(Path(selection).read_bytes()) == selection_sha256
            and digest(Path(baseline_catalog).read_bytes()) == baseline_sha256, 'Collection inputs changed during run')
    manifest = {'schema': 'sonora-source-candidates-v1', 'split': SPLIT,
        'created_at': datetime.now(timezone.utc).isoformat(), 'selection_sha256': selection_sha256,
        'baseline_catalog_sha256': baseline_sha256, 'collector_sha256': digest(Path(__file__).read_bytes()),
        'snapshots': snapshots, 'tracks': tracks,
        'limits': ['Source candidates, not authenticated human relevance or Java-imported music.',
                   'One additional composer; known-query selection bias; no independent test claim.',
                   'Original recording bytes preserved; actual decode verification is a separate required check.']}
    write_new(target / 'manifest.json', json.dumps(manifest, ensure_ascii=False, indent=2).encode() + b'\n')
    return {'status': 'collected_source_candidates', 'tracks': len(tracks), 'buckets': dict(Counter(t['bucket_id'] for t in tracks)),
            'manifest_sha256': digest((target / 'manifest.json').read_bytes()), 'bytes': sum(t['bytes'] for t in tracks),
            'human_judged': 0, 'java_imported': 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--selection', type=Path, required=True)
    parser.add_argument('--selection-sha256', required=True)
    parser.add_argument('--baseline-catalog', type=Path, required=True)
    parser.add_argument('--baseline-sha256', required=True)
    args = parser.parse_args()
    try:
        result = run(args.output, args.selection, args.selection_sha256, args.baseline_catalog, args.baseline_sha256)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.exit(1, type(exc).__name__ + ': ' + str(exc) + '\n')


if __name__ == '__main__':
    main()
