#!/usr/bin/env python3
"""One bounded, source-only expansion of paired audio. No model import, fit or test scoring."""
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
from urllib.request import Request, HTTPSHandler, build_opener

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'services/audio-search'))
import holdout_contract as h
import caption_expansion as policy
import caption_pair_preflight as pair
import mtg_dataset as mtg
from mtg_plan import Groups
from audit_caption_coverage import Redirects as CaptionRedirects, pinned
from preflight_caption_pairs import Redirects as ReferenceRedirects, reserve, decode, save_npz
from preflight_mtg import Redirects as AudioRedirects, fetch_one, write_raw
from acquire_caption_gate import JournalBudget

SOURCES = ('scripts/expand_caption_corpus.py', 'services/audio-search/caption_expansion.py',
           'scripts/audit_caption_coverage.py', 'scripts/preflight_caption_pairs.py',
           'scripts/preflight_mtg.py', 'scripts/acquire_caption_gate.py',
           'services/audio-search/caption_coverage.py', 'services/audio-search/caption_pair_preflight.py',
           'services/audio-search/mtg_dataset.py', 'services/audio-search/mtg_plan.py',
           'services/audio-search/research_corpus.py', 'services/audio-search/preprocess.py')


def frame(cfg):
    manifest, plan, data, corpus, prior = [pinned(cfg[k]) for k in ('inputs', 'plan', 'dataset', 'corpus', 'prior_pcm')]
    raw = {k: h.assets.read(v['path'], 40*1024*1024) for k, v in manifest['files'].items()}
    h.require(all(h.digest(v) == manifest['files'][k]['sha256'] for k, v in raw.items()), 'Metadata drift')
    names, _ = mtg.names(raw['names']); base = mtg.table(raw['base']); hashes = mtg.checksums(raw['audio_sha256'])
    old = json.loads(raw['prior40'])['audioTracks']; newer = json.loads(raw['prior20'])['tracks']
    sdd = list(csv.DictReader(io.StringIO(raw['sdd'].decode())))
    blocked_ids = {str(int(r['track_id'].removeprefix('track_'))) for r in sdd}
    artists = {str(int(r['artist_id'].removeprefix('artist_'))) for r in sdd}
    blocked_artists = {r['artist_id'] for r in names.values() if mtg.source_id(r['artist_id'], 'artist') in artists}
    blocked_ids |= {str(int(r['sourceId'])) for r in old if r['sourceProvider'] == 'jamendo'}
    reserved = data['selected']['caption_dev'] + data['caption_test_reserved'] + plan['selected']['test']
    blocked_ids |= {mtg.source_id(r['source_track_id'], 'track') for r in reserved}
    blocked_artists |= {r['artist_id'] for r in reserved}
    aliases = set().union(*(mtg.aliases(r['artist']) for r in old),
                          *(mtg.aliases(r['imported_metadata']['artist']) for r in newer),
                          *(mtg.aliases(v) for r in newer for v in r['contributors']))
    works = {mtg.norm(r['title']) for r in old+newer+reserved}
    sha = {r['sha256'] for r in old} | {r['content_sha256'] for r in newer} | {r['audio_sha256'] for r in reserved}
    for tid, r in names.items():
        if mtg.source_id(tid, 'track') in blocked_ids:
            blocked_artists.add(r['artist_id']); works.add(mtg.norm(r['title']))
            low = base.get(tid, {}).get('path', '').removesuffix('.mp3')+'.low.mp3'
            if low in hashes: sha.add(hashes[low])
    groups = Groups(); owner = {}
    for r in names.values():
        for alias in mtg.aliases(r['artist']):
            if alias in owner: groups.union(r['artist_id'], owner[alias])
            else: owner[alias] = r['artist_id']
    blocked_groups = {groups.root(a) for a in blocked_artists}
    blocked_groups |= {groups.root(r['artist_id']) for r in names.values() if mtg.aliases(r['artist']) & aliases}
    dates = {}
    for row in csv.reader(io.StringIO(raw['names'].decode()), delimiter='\t', quoting=csv.QUOTE_NONE):
        if len(row) == 8 and row[0] in names: dates[row[0]] = row[6]
    def convert(r, split):
        return {**r, 'id': mtg.source_id(r['source_track_id'], 'track'), 'split': split,
                'creator_component': groups.root(r['artist_id']), 'work': mtg.norm(r['title']),
                'artist_id_numeric': mtg.source_id(r['artist_id'], 'artist'),
                'release_date': dates[r['source_track_id']], 'original_audio_license_family': r['audio_license']['family']}
    existing = [convert(r, s) for s in ('train', 'validation') for r in data['selected'][s]]
    records = [convert(r, s) for s in ('train', 'validation') for r in plan['selected'][s]]
    clean, rejected = policy.isolate(records, existing, blocked_ids, blocked_groups, works, sha)
    tree_files = {r['path'] for r in pinned(cfg['tree']) if r['type'] == 'file'}
    dated = []
    for r in clean:
        try:
            available = policy.metadata_file(r['release_date']) in tree_files
        except ValueError:
            available = False
        if available: dated.append(r)
        else: rejected['release_metadata_mapping_unavailable'] = rejected.get('release_metadata_mapping_unavailable', 0)+1
    clean = dated
    pcm = {r['pcm_sha256'] for r in prior['tracks']} | {r['decode']['pcm_sha256'] for r in corpus['tracks']}
    return {'records': clean, 'excluded_reasons_nonexclusive': rejected,
            'counts': dict(Counter(r['split'] for r in clean)),
            'exclusion_pins': {k: h.digest(h.canonical(sorted(v))) for k, v in
                {'ids': blocked_ids, 'groups': blocked_groups, 'works': works, 'sha256': sha, 'pcm': pcm}.items()}}, pcm


def fetch_metadata(cfg, selected, target, opener, budget):
    tree = {r['path']: r for r in pinned(cfg['tree']) if r['type'] == 'file'}
    cached_plan = {r['path']: r for r in pinned(cfg['cached_metadata_plan'])['files']}
    cached = {r['file']: r for r in pinned(cfg['cached_metadata_manifest'])['files']}
    mapping = [{'id': r['id'], 'file': policy.metadata_file(r['release_date'])} for r in selected]
    names = sorted({r['file'] for r in mapping}); entries = []
    for name in names:
        h.require(name in tree, 'Fixed release metadata file missing from pinned tree')
        entry = tree[name]; reuse = name in cached and cached[name]['status'] == 'passed'
        if reuse:
            h.require(cached_plan[name] == entry, 'Cached tree entry drift')
            path = ROOT/cfg['cached_metadata_directory']/name
            h.require(h.file_hash(path) == cached[name]['sha256'] and path.stat().st_size == entry['size'], 'Cached metadata drift')
        entries.append({**entry, 'reuse': reuse})
    size = sum(r['size']+1 for r in entries if not r['reuse'])
    h.require(size <= cfg['max_metadata_body_bytes'], 'Fixed candidate prefix exceeds metadata budget; no adaptive shrink')
    h.write_json(target/'metadata-plan.json', {'revision': cfg['source']['revision'], 'files': entries,
                 'mapping': mapping, 'new_body_reservation': size})
    directory = target/'metadata'; directory.mkdir(mode=0o700)
    manifest = []
    for i, entry in enumerate(entries):
        name = entry['path']
        if entry['reuse']:
            path = ROOT/cfg['cached_metadata_directory']/name
            raw = path.read_bytes()
        else:
            reserve(budget, entry['size']+1)
            url = 'https://huggingface.co/datasets/amaai-lab/JamendoMaxCaps/resolve/'+cfg['source']['revision']+'/'+name
            with opener.open(Request(url, headers={'Accept-Encoding': 'identity'}), timeout=35) as response:
                h.require(response.status == 200 and response.headers.get('Content-Encoding', 'identity') == 'identity', 'Metadata HTTP response')
                raw = response.read(entry['size']+1)
            path = directory/name
            write_raw(path, raw)
        h.require(len(raw) == entry['size'] and hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest() == entry['oid'], 'Metadata Git blob mismatch')
        manifest.append({'path': str(path), 'sha256': h.digest(raw), 'bytes': len(raw), 'reused': entry['reuse'], 'git_blob_oid': entry['oid']})
        if (i+1) % 10 == 0: print(json.dumps({'phase': 'metadata', 'ready': i+1, 'total': len(entries)}), flush=True)
    h.write_json(target/'metadata-manifest.json', {'files': manifest, 'new_body_reserved': size})
    wanted = {r['id'] for r in selected}; rows = defaultdict(list)
    for r in manifest:
        for line in Path(r['path']).read_bytes().splitlines():
            item = json.loads(line)
            if str(item.get('id')) in wanted: rows[str(item['id'])].append(item)
    return rows, manifest


def original(row, duration):
    return {**row, 'artist_id': row['artist_id_numeric'], 'duration_seconds': duration}


def run(config, config_sha256, output, ca_file=None):
    cfg = h.assets.document(config, config_sha256)
    h.require(cfg['schema'] == 'sonora-caption-expansion-v1' and cfg['fits'] == cfg['encoder_loads'] == 0
              and cfg['max_total_body_bytes'] == 2*1024**3 and cfg['max_audio_attempts'] == 76,
              'Fixed expansion-only protocol required')
    h.require(not subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT).strip(), 'Clean committed source required')
    task = ROOT/cfg['task_directory']
    h.require(task.resolve() == (ROOT/'.local/a/mus057').resolve(), 'Task-local ledger required')
    fd = os.open(task/'run.lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600); os.fchmod(fd, 0o600)
    with os.fdopen(fd, 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        budget = JournalBudget(ROOT/cfg['budget_ledger'], cfg['max_total_body_bytes'])
        h.require(not budget.events, 'Expansion already attempted; changing output cannot retry')
        target = h.private_output(output)
        budget.append({'event': 'started', 'config_sha256': config_sha256})
        try:
            sources = {p: h.file_hash(ROOT/p) for p in SOURCES}
            source_sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
            old_candidates = pinned(cfg['old_eligible'])['candidates']
            old_allow = {r['id']: r for r in pinned(cfg['old_allowlist'])['records']}
            old_counts = Counter(old_allow[tid]['split'] for tid in {r['id'] for r in old_candidates})
            h.require(dict(old_counts) == {'train': 37, 'validation': 7}, 'Existing effective pair counts changed')
            frozen, known_pcm = frame(cfg); h.write_json(target/'frame.json', frozen)
            h.write_json(target/'freeze.json', {'source_sha': source_sha, 'source_sha256': sources,
                         'config_sha256': config_sha256, 'frame_sha256': h.file_hash(target/'frame.json'),
                         'created_at_utc': h.now(), 'encoder_loads': 0, 'fits': 0})
            opener = build_opener(CaptionRedirects(), HTTPSHandler(context=ssl.create_default_context(cafile=ca_file)))
            scanner = policy.provisional_scanner(frozen['records']); digest = hashlib.sha256(); received = 0
            reserve(budget, cfg['source']['bytes'])
            with opener.open(Request(cfg['source']['url'], headers={'Accept-Encoding': 'identity'}), timeout=35) as response:
                h.require(response.status == 200 and response.headers.get('Content-Encoding', 'identity') == 'identity'
                          and int(response.headers.get('Content-Length', '-1')) == cfg['source']['bytes'], 'Pinned caption length required')
                outfd = os.open(target/'matched-source.jsonl', os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
                with os.fdopen(outfd, 'wb') as matched:
                    while True:
                        raw = response.readline(cfg['max_line_bytes']+1)
                        if not raw: break
                        received += len(raw); h.require(received <= cfg['source']['bytes'], 'Caption body exceeds bound'); digest.update(raw)
                        if scanner.add(raw): matched.write(raw)
                        if scanner.lines % 200000 == 0:
                            print(json.dumps({'phase': 'caption_scan', 'rows': scanner.lines, 'bytes': received}), flush=True)
            h.require(received == cfg['source']['bytes'] and digest.hexdigest() == cfg['source']['sha256'], 'Complete caption SHA mismatch')
            provisional = scanner.finish()
            selected = policy.choose_candidates(frozen['records'], provisional['candidates'], cfg['candidate_counts'], cfg['selection_seed'])
            h.write_json(target/'selection.json', {'records': selected, 'actual_EOF_verified': False,
                         'selection': 'fixed hash prefix, no model scores', 'caption_source_fully_verified': True})
            h.write_json(target/'provisional-candidates.json', {'candidates': provisional['candidates'], 'actual_EOF_verified': False})
            metadata, manifest = fetch_metadata(cfg, selected, target, opener, budget)
            preliminary = [pair.reconcile(original(r, r['duration']), metadata[r['id']]) for r in selected]
            h.write_json(target/'preliminary-verdicts.json', {'verdicts': preliminary, 'duration_is_source_metadata_not_actual_EOF': True})
            pre_good = {r['id'] for r in preliminary if r['eligible']}
            raw_by_id = defaultdict(list)
            for raw in (target/'matched-source.jsonl').read_bytes().splitlines(keepends=True):
                raw_by_id[str(int(json.loads(raw)['id']))].append(raw)
            audio_opener = build_opener(AudioRedirects(), HTTPSHandler(context=ssl.create_default_context(cafile=ca_file)))
            audio_dir = target/'audio'; audio_dir.mkdir(mode=0o700)
            counts = Counter(); attempts = 0; ready = []; candidates = []; failures = []
            for r in selected:
                if r['id'] not in pre_good or counts[r['split']] >= cfg['new_audio_targets'][r['split']]: continue
                if attempts == cfg['max_audio_attempts']: break
                attempts += 1; folder = audio_dir/f'slot-{attempts:03}'; folder.mkdir(mode=0o700)
                try:
                    raw, transport = fetch_one(audio_opener, r, cfg, budget)
                    path = folder/'audio.mp3'; write_raw(path, raw)
                    audio, info = decode(path); pcm = h.digest(audio.astype('<f4', copy=False).tobytes())
                    h.require(pcm not in known_pcm, 'Prior or new PCM collision')
                    measured = original(r, len(audio)/48000)
                    verdict = pair.reconcile(measured, metadata[r['id']])
                    h.require(verdict['eligible'], 'Metadata disagrees with verified audio EOF')
                    intervals = policy.actual_intervals(measured, raw_by_id[r['id']])
                    h.require(intervals['candidates'], 'No valid actual-EOF caption interval')
                    record = {**measured, 'audio_path': str(path), 'pcm_sha256': pcm, 'decode': info,
                              'transport': transport, 'metadata_verdict': verdict,
                              'interval_summary': intervals['summary']}
                    h.write_json(folder/'receipt.json', record)
                    record['receipt_path'] = str(folder/'receipt.json'); record['receipt_sha256'] = h.file_hash(folder/'receipt.json')
                    ready.append(record); candidates.extend(intervals['candidates']); known_pcm.add(pcm); counts[r['split']] += 1
                except Exception as exc:
                    failure = {'slot': attempts, 'id': r['id'], 'error_type': type(exc).__name__, 'detail': str(exc)[:1000]}
                    h.write_json(folder/'failure.json', failure); failures.append(failure)
                print(json.dumps({'phase': 'audio', 'attempts': attempts, 'ready': dict(counts), 'budget_reserved': budget.used}), flush=True)
            h.write_json(target/'recordings.json', {'records': ready, 'failures': failures})
            h.write_json(target/'eligible-candidates.json', {'candidates': candidates, 'label_source': 'model_generated', 'training_ready': False})
            refs = pair.choose_references(ready, [r['metadata_verdict'] for r in ready], candidates, cfg['reference_count'], cfg['selection_seed'])
            h.write_json(target/'reference-plan.json', {'ids_in_fixed_order': refs, 'alignment': cfg['alignment']})
            ref_dir = target/'references'; ref_dir.mkdir(mode=0o700)
            reference_opener = build_opener(ReferenceRedirects(), HTTPSHandler(context=ssl.create_default_context(cafile=ca_file)))
            references = []; by_id = {r['id']: r for r in ready}
            for i, tid in enumerate(refs):
                folder = ref_dir/f'slot-{i+1:02}'; folder.mkdir(mode=0o700); r = by_id[tid]
                try:
                    limit = cfg['max_reference_audio_bytes']; reserve(budget, limit+1)
                    with reference_opener.open(Request(r['metadata_verdict']['reference_url'], headers={'Accept-Encoding': 'identity'}), timeout=35) as response:
                        length = int(response.headers.get('Content-Length', '-1'))
                        h.require(response.status == 200 and 0 < length <= limit and response.headers.get('Content-Encoding', 'identity') == 'identity', 'Bounded reference required')
                        raw = response.read(limit+1)
                        h.require(len(raw) == length, 'Truncated reference')
                    write_raw(folder/'reference.mp3', raw)
                    a, _ = decode(r['audio_path']); b, info = decode(folder/'reference.mp3')
                    report, probes = pair.align(a, b, [v for v in candidates if v['id'] == tid], cfg['alignment'])
                    save_npz(folder/'anchor-probes.npz', probes)
                    result = {'status': 'passed' if report['passed'] else 'failed', 'alignment': report,
                              'reference_sha256': h.digest(raw), 'bytes': len(raw), 'decode': info}
                    h.write_json(folder/'result.json', result); references.append(result)
                except Exception as exc:
                    result = {'status': 'blocked', 'error_type': type(exc).__name__}
                    h.write_json(folder/'failure.json', result); references.append(result)
            for p, pin in sources.items(): h.require(h.file_hash(ROOT/p) == pin, 'Source changed during run')
            h.require(h.file_hash(config) == config_sha256 and frame(cfg)[0] == frozen, 'Inputs or frame changed')
            pinned(cfg['old_eligible']); pinned(cfg['old_allowlist'])
            for r in manifest: h.require(h.file_hash(r['path']) == r['sha256'], 'Metadata changed')
            h.require(not any(n in sys.modules for n in ('torch', 'laion_clap')), 'No encoder permitted')
            summary = {'schema': 'sonora-caption-expansion-result-v1', 'source_sha': source_sha,
                       'source_fully_verified': True, 'frame_counts': frozen['counts'],
                       'selected_counts': dict(Counter(r['split'] for r in selected)),
                       'preliminary_metadata_eligible': len(pre_good), 'audio_attempts': attempts,
                       'new_counts': dict(counts), 'new_intervals': len(candidates),
                       'combined_recording_counts': {s: old_counts[s]+counts[s] for s in ('train', 'validation')},
                       'combined_interval_counts': {s: sum(old_allow[r['id']]['split'] == s for r in old_candidates)
                           +sum(by_id[r['id']]['split'] == s for r in candidates) for s in ('train', 'validation')},
                       'new_intervals_by_split': {s: sum(1 for v in candidates if by_id[v['id']]['split'] == s) for s in ('train', 'validation')},
                       'new_creator_components': {s: len({r['creator_component'] for r in ready if r['split'] == s}) for s in ('train', 'validation')},
                       'audio_failures': len(failures), 'metadata_files': len(manifest),
                       'metadata_reused': sum(r['reused'] for r in manifest),
                       'reference_statuses': dict(Counter(r['status'] for r in references)),
                       'reference_preflight_passed': len(references) == 3 and all(r['status'] == 'passed' for r in references),
                       'budget_reserved_bytes': budget.used, 'max_total_body_bytes': budget.maximum,
                       'encoder_loads': 0, 'fits': 0, 'reserved_test_inputs': 0, 'raw_full_corpus_saved': False,
                       'training_ready': False, 'label_source': 'model_generated', 'exact_teacher_artifact_verified': False}
            h.write_json(target/'result.json', summary); return summary
        except Exception as exc:
            h.write_json(target/'failure.json', {'status': 'incomplete', 'error_type': type(exc).__name__,
                         'detail': str(exc)[:1000], 'budget_reservation_retained': True}); raise


def main():
    p = argparse.ArgumentParser()
    for k in ('config', 'output'): p.add_argument('--'+k, required=True, type=Path)
    p.add_argument('--config-sha256', required=True); p.add_argument('--ca-file')
    print(json.dumps(run(**vars(p.parse_args()))))


if __name__ == '__main__': main()
