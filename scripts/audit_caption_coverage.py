#!/usr/bin/env python3
"""Freeze existing audio identities, then stream one pinned caption file; never train."""
import argparse
from collections import Counter, defaultdict
import csv
import fcntl
import hashlib
import io
import json
import os
from pathlib import Path
import ssl
import subprocess
import sys
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, HTTPSHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'services/audio-search'))
import caption_coverage as coverage
import holdout_contract as h
import mtg_dataset as mtg
from mtg_plan import Groups

SOURCES = ('scripts/audit_caption_coverage.py', 'services/audio-search/caption_coverage.py',
           'services/audio-search/mtg_dataset.py', 'services/audio-search/mtg_plan.py')


def pinned(entry):
    path = ROOT/entry['path']
    h.require(h.file_hash(path) == entry['sha256'], 'Pinned metadata changed')
    return json.loads(path.read_text())


def make_allowlist(cfg):
    manifest = pinned(cfg['inputs']); future = pinned(cfg['plan'])
    data = pinned(cfg['dataset']); corpus = pinned(cfg['corpus']); prior_pcm = pinned(cfg['prior_pcm'])
    raw = {k: h.assets.read(r['path'], 40*1024*1024) for k, r in manifest['files'].items()}
    h.require(all(h.digest(v) == manifest['files'][k]['sha256'] for k, v in raw.items()), 'Original metadata drift')
    names, _ = mtg.names(raw['names']); base = mtg.table(raw['base']); hashes = mtg.checksums(raw['audio_sha256'])
    old = json.loads(raw['prior40'])['audioTracks']; newer = json.loads(raw['prior20'])['tracks']
    # SDD identities only: never copy, display, or pass its caption column to a model.
    sdd = list(csv.DictReader(io.StringIO(raw['sdd'].decode())))
    blocked_ids = {str(int(r['track_id'].removeprefix('track_'))) for r in sdd}
    sdd_artists = {str(int(r['artist_id'].removeprefix('artist_'))) for r in sdd}
    blocked_artists = {r['artist_id'] for r in names.values()
                       if mtg.source_id(r['artist_id'], 'artist') in sdd_artists}
    blocked_ids |= {str(int(r['sourceId'])) for r in old if r['sourceProvider'] == 'jamendo'}
    reserved = data['selected']['caption_dev'] + data['caption_test_reserved'] + future['selected']['test']
    blocked_ids |= {mtg.source_id(r['source_track_id'], 'track') for r in reserved}
    blocked_artists |= {r['artist_id'] for r in reserved}
    aliases = set().union(*(mtg.aliases(r['artist']) for r in old),
                          *(mtg.aliases(r['imported_metadata']['artist']) for r in newer),
                          *(mtg.aliases(v) for r in newer for v in r['contributors']))
    works = {mtg.norm(r['title']) for r in old + newer + reserved}
    blocked_sha = {r['sha256'] for r in old} | {r['content_sha256'] for r in newer}
    blocked_sha |= {r['audio_sha256'] for r in reserved}
    for tid, record in names.items():
        if mtg.source_id(tid, 'track') in blocked_ids:
            blocked_artists.add(record['artist_id']); works.add(mtg.norm(record['title']))
            low = base.get(tid, {}).get('path', '').removesuffix('.mp3') + '.low.mp3'
            if low in hashes:
                blocked_sha.add(hashes[low])
    groups = Groups(); owner = {}
    for r in names.values():
        for alias in mtg.aliases(r['artist']):
            if alias in owner:
                groups.union(r['artist_id'], owner[alias])
            else:
                owner[alias] = r['artist_id']
    blocked_groups = {groups.root(a) for a in blocked_artists}
    for r in names.values():
        if mtg.aliases(r['artist']) & aliases:
            blocked_groups.add(groups.root(r['artist_id']))
    catalog = {(r['split'], r['source_track_id']): r for r in corpus['tracks']}
    pcm_exclusion = {r['pcm_sha256'] for r in prior_pcm['tracks']}
    allowed, rejected = [], Counter()
    for split in ('train', 'validation'):
        h.require(len(data['selected'][split]) == cfg['expected_counts'][split], 'Existing split size changed')
        for r in data['selected'][split]:
            tid = mtg.source_id(r['source_track_id'], 'track'); component = groups.root(r['artist_id'])
            item = catalog[(split, r['source_track_id'])]
            receipt = Path(item['receipt_path']); audio = receipt.parent/'audio.mp3'
            h.require(h.file_hash(receipt) == item['receipt_sha256'] and h.file_hash(audio) == r['audio_sha256']
                      == item['audio_sha256'], 'Existing verified audio/receipt changed')
            reasons = []
            if tid in blocked_ids: reasons.append('reserved_or_prior_ID')
            if component in blocked_groups: reasons.append('reserved_or_prior_creator_component')
            if mtg.norm(r['title']) in works: reasons.append('reserved_or_prior_work')
            if r['audio_sha256'] in blocked_sha or item['decode']['pcm_sha256'] in pcm_exclusion:
                reasons.append('prior_or_reserved_content')
            if r['audio_license']['family'] not in ('by', 'by-sa'): reasons.append('source_audio_license')
            if reasons:
                rejected.update(split+':'+x for x in reasons); continue
            allowed.append({'id': tid, 'split': split, 'creator_component': component,
                            'duration_seconds': item['decode']['decoded_samples']/item['decode']['sample_rate_hz'],
                            'audio_sha256': r['audio_sha256'], 'pcm_sha256': item['decode']['pcm_sha256'],
                            'original_audio_license': r['audio_license']['uri']})
    # Quarantine both sides if expanded full-metadata credit closure finds a new cross-split relation.
    splits = defaultdict(set)
    for r in allowed: splits[r['creator_component']].add(r['split'])
    clean = []
    for r in allowed:
        if len(splits[r['creator_component']]) > 1:
            rejected[r['split']+':new_cross_split_creator_component'] += 1
        else: clean.append(r)
    h.require(clean, 'No eligible existing recordings after exclusions')
    return {'schema': 'sonora-caption-coverage-allowlist-v1', 'records': clean,
            'summary': {'input_counts': cfg['expected_counts'], 'eligible_counts': dict(Counter(r['split'] for r in clean)),
                        'excluded_reasons_nonexclusive': dict(rejected), 'all_SDD_and_prior_and_reserved_groups_excluded': True,
                        'teacher_metadata_rights_and_waveform_alignment_verified': False,
                        'training_ready': False}, 'exclusion_id_sha256': h.digest(h.canonical(sorted(blocked_ids))),
            'exclusion_groups_sha256': h.digest(h.canonical(sorted(blocked_groups))),
            'exclusion_work_sha256': h.digest(h.canonical(sorted(works)))}


def charge(path, cfg, cfg_sha):
    fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_APPEND | os.O_NOFOLLOW, 0o600)
    os.fchmod(fd, 0o600)
    with os.fdopen(fd, 'a+') as f:
        fcntl.flock(f, fcntl.LOCK_EX); f.seek(0)
        prior = [json.loads(line) for line in f if line.strip()]
        h.require(all(r['config_sha256'] == cfg_sha for r in prior), 'Budget belongs to a different protocol')
        charged = sum(r['reserved_bytes'] for r in prior) + cfg['source']['bytes']
        h.require(charged <= cfg['max_total_body_bytes'], 'Task-wide body budget exhausted; no repeated full GET')
        event = {'created_at_utc': h.now(), 'config_sha256': cfg_sha, 'reserved_bytes': cfg['source']['bytes'],
                 'total_reserved_bytes': charged, 'source_sha256': cfg['source']['sha256']}
        f.write(json.dumps(event)+'\n'); f.flush(); os.fsync(f.fileno())
    return event


class Redirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        p = urlsplit(newurl)
        h.require(p.scheme == 'https' and p.hostname and (p.hostname == 'huggingface.co'
                  or p.hostname.endswith('.hf.co')), 'Unexpected source redirect host')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def run(config, config_sha256, output, ca_file=None):
    cfg = h.assets.document(config, config_sha256)
    h.require(cfg['schema'] == 'sonora-caption-coverage-v1' and cfg['new_audio'] == cfg['fits'] == 0
              and cfg['source']['revision'] == '13090d785d071dcd617636deaa4a9775936ac995', 'Fixed metadata-only protocol required')
    h.require(cfg['source']['url'] == 'https://huggingface.co/datasets/amaai-lab/JamendoMaxCaps/resolve/'
              + cfg['source']['revision'] + '/final_caption30sec.jsonl', 'Pinned official metadata URL required')
    h.require(not subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT).strip(), 'Clean committed source required')
    target = h.private_output(output); received = 0
    try:
        hashes = {p: h.file_hash(ROOT/p) for p in SOURCES}
        allow = make_allowlist(cfg)
        h.write_json(target/'allowlist.json', allow)
        h.write_json(target/'freeze.json', {'created_at_utc': h.now(), 'source_sha': subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(), 'source_sha256': hashes,
            'config_sha256': config_sha256, 'allowlist_sha256': h.file_hash(target/'allowlist.json'),
            'inputs': {k: cfg[k] for k in ('inputs', 'plan', 'dataset', 'corpus', 'prior_pcm')},
            'caption_source': cfg['source'], 'model_loads': 0, 'fits': 0})
        ledger = ROOT/cfg['budget_ledger']
        h.require(ledger.parent.resolve() == (ROOT/'.local/a/mus051').resolve(), 'Task-local budget ledger required')
        charge(ledger, cfg, config_sha256)  # Reservation is retained on any HTTP/read/hash failure.
        scanner = coverage.Coverage(allow['records'], max_line_bytes=cfg['max_line_bytes'],
                                   min_seconds=cfg['min_interval_seconds'], max_seconds=cfg['max_interval_seconds'])
        context = ssl.create_default_context(cafile=ca_file)
        opener = build_opener(Redirects(), HTTPSHandler(context=context))
        digest = hashlib.sha256(); physical_lines = 0
        fd = os.open(target/'matched-source.jsonl', os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, 'wb') as matched:
            with opener.open(Request(cfg['source']['url'], headers={'Accept-Encoding': 'identity',
                             'User-Agent': 'Sonora-caption-coverage/1'}), timeout=30) as response:
                h.require(response.status == 200 and response.headers.get('Content-Encoding', 'identity') == 'identity'
                          and int(response.headers.get('Content-Length', '-1')) == cfg['source']['bytes'],
                          'Exact complete source length and identity encoding required')
                while True:
                    line = response.readline(cfg['max_line_bytes']+1)
                    if not line: break
                    received += len(line); physical_lines += 1
                    h.require(received <= cfg['source']['bytes'], 'Body exceeds pinned length')
                    digest.update(line)
                    if scanner.add(line): matched.write(line)
        h.require(received == cfg['source']['bytes'] and digest.hexdigest() == cfg['source']['sha256'],
                  'Complete source SHA/length mismatch; no completed coverage')
        for name, pin in hashes.items(): h.require(h.file_hash(ROOT/name) == pin, 'Source changed during scan')
        for key in ('inputs', 'plan', 'dataset', 'corpus', 'prior_pcm'): pinned(cfg[key])
        h.require(h.file_hash(config) == config_sha256 and make_allowlist(cfg) == allow,
                  'Config, source metadata, audio or exclusions changed during scan')
        result = scanner.finish()
        h.require(not any(n in sys.modules for n in ('torch', 'numpy', 'laion_clap')), 'Unexpected model dependency import')
        h.write_json(target/'candidates.json', {'schema': 'sonora-generated-caption-candidates-v1',
                     'training_ready': False, 'permission_and_waveform_alignment_pending': True,
                     'candidates': result['candidates']})
        public = {'schema': 'sonora-caption-coverage-result-v1', 'status': 'coverage_completed_not_training_ready',
                  'summary': result['summary'], 'allowlist_summary': allow['summary'], 'bytes': received,
                  'source_sha256': digest.hexdigest(), 'physical_lines': physical_lines,
                  'source_fully_verified': True, 'raw_full_corpus_saved': False, 'new_audio': 0, 'fits': 0,
                  'matched_source_sha256': h.file_hash(target/'matched-source.jsonl'),
                  'candidates_sha256': h.file_hash(target/'candidates.json'), 'completed_at_utc': h.now()}
        h.write_json(target/'result.json', public)
        return public
    except Exception as exc:
        h.write_json(target/'failure.json', {'status': 'incomplete_no_ready_output', 'error_type': type(exc).__name__,
                     'received_bytes': received, 'budget_reservation_retained': True})
        raise


def main():
    p = argparse.ArgumentParser()
    for name in ('config', 'output'): p.add_argument('--'+name, type=Path, required=True)
    p.add_argument('--config-sha256', required=True); p.add_argument('--ca-file')
    print(json.dumps(run(**vars(p.parse_args()))))


if __name__ == '__main__': main()
