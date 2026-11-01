#!/usr/bin/env python3
"""Reconcile captured metadata and check three same-ID reference snapshots; never fit."""
import argparse
from collections import Counter, defaultdict
import fcntl
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
import holdout_contract as h
import caption_pair_preflight as pair
from acquire_caption_gate import JournalBudget

SOURCES = ('scripts/preflight_caption_pairs.py', 'services/audio-search/caption_pair_preflight.py',
           'services/audio-search/research_corpus.py', 'services/audio-search/preprocess.py',
           'scripts/acquire_caption_gate.py')


def pinned(entry):
    p = ROOT/entry['path']; h.require(h.file_hash(p) == entry['sha256'], 'Pinned input changed')
    return json.loads(p.read_text())


class Redirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        p = urlsplit(newurl)
        h.require(p.scheme == 'https' and p.hostname and p.hostname.endswith('.jamendo.com'),
                  'Reference redirect must stay on HTTPS Jamendo')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def reserve(budget, count):
    with budget.lock:
        h.require(count <= budget.maximum-budget.used, 'Task body budget exhausted')
        budget.append({'event': 'charge', 'bytes': count}); budget.used += count


def decode(path):
    import soundfile as sf
    from research_corpus import decode_source_mono
    with sf.SoundFile(path) as x:
        header = {'frames': x.frames, 'sample_rate_hz': x.samplerate, 'channels': x.channels,
                  'format': x.format, 'duration_ms': x.frames*1000//x.samplerate}
    return decode_source_mono(path, header)


def save_npz(path, values):
    import numpy as np
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    os.fchmod(fd, 0o600)
    with os.fdopen(fd, 'wb') as f: np.savez(f, **values)


def run(config, config_sha256, output, ca_file=None):
    cfg = h.assets.document(config, config_sha256)
    h.require(cfg['schema'] == 'sonora-caption-pair-preflight-v1' and cfg['reference_count'] == 3
              and cfg['fits'] == 0 and cfg['alignment']['min_normalized_correlation'] == .95,
              'Fixed no-training pair preflight required')
    h.require(not subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT).strip(), 'Clean committed source required')
    target = h.private_output(output)
    try:
        source_sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
        hashes = {name: h.file_hash(ROOT/name) for name in SOURCES}
        inputs = {k: pinned(cfg[k]) for k in ('metadata_plan', 'metadata_manifest', 'candidates', 'allowlist', 'dataset', 'corpus')}
        manifest = inputs['metadata_manifest']; h.require(manifest['all_complete'], 'Complete fixed metadata required')
        wanted = {r['id'] for r in inputs['candidates']['candidates']}; raw_rows = defaultdict(list)
        for entry in manifest['files']:
            path = ROOT/cfg['metadata_directory']/entry['file']
            h.require(entry['status'] == 'passed' and h.file_hash(path) == entry['sha256']
                      and path.stat().st_size == entry['bytes'], 'Captured source metadata changed')
            for line in path.read_bytes().splitlines():
                row = json.loads(line)
                if str(row.get('id')) in wanted: raw_rows[str(row['id'])].append(row)
        originals = {}; catalog = {(r['split'], r['source_track_id']): r for r in inputs['corpus']['tracks']}
        allowed = {r['id']: r for r in inputs['allowlist']['records']}
        for split in ('train', 'validation'):
            for r in inputs['dataset']['selected'][split]:
                tid = str(int(r['source_track_id'].split('_')[-1]))
                if tid not in wanted: continue
                item = catalog[(split, r['source_track_id'])]
                receipt = Path(item['receipt_path']); audio = receipt.parent/'audio.mp3'
                h.require(h.file_hash(receipt) == item['receipt_sha256'] and h.file_hash(audio) == r['audio_sha256']
                          == allowed[tid]['audio_sha256'], 'Original audio provenance changed')
                originals[tid] = {**allowed[tid], 'artist_id': str(int(r['artist_id'].split('_')[-1])),
                                  'title': r['title'], 'audio_path': str(audio), 'decode': item['decode']}
        h.require(len(originals) == len(wanted) == 57, 'Original57 candidate sources required')
        verdicts = [pair.reconcile(originals[tid], raw_rows[tid], duration_tolerance=cfg['metadata_duration_tolerance_seconds'])
                    for tid in sorted(originals, key=int)]
        references = pair.choose_references(list(originals.values()), verdicts, inputs['candidates']['candidates'],
                                            cfg['reference_count'], cfg['reference_seed'])
        h.write_json(target/'metadata-verdicts.json', verdicts)
        h.write_json(target/'freeze.json', {'created_at_utc': h.now(), 'source_sha': source_sha, 'source_sha256': hashes,
                     'config_sha256': config_sha256, 'input_pins': {k: cfg[k] for k in inputs},
                     'reference_ids_in_fixed_order': references, 'alignment_thresholds': cfg['alignment']})
        # Hold a task-wide lock. A new output cannot silently repeat an already started reference run.
        lockpath = ROOT/cfg['task_directory']/'reference.lock'
        fd = os.open(lockpath, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600); os.fchmod(fd, 0o600)
        with os.fdopen(fd, 'w') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            budget = JournalBudget(ROOT/cfg['task_directory']/'network-budget.jsonl', cfg['max_total_body_bytes'])
            h.require(not budget.events, 'Reference preflight already attempted; no implicit restart')
            budget.append({'event': 'run_started', 'config_sha256': config_sha256})
            reserve(budget, manifest['reserved_bytes'])
            opener = build_opener(Redirects(), HTTPSHandler(context=ssl.create_default_context(cafile=ca_file)))
            output_refs = []; by_id = {v['id']: v for v in verdicts}
            refsdir = target/'references'; refsdir.mkdir(mode=0o700); refsdir.chmod(0o700)
            for tid in references:
                folder = refsdir/tid; folder.mkdir(mode=0o700); folder.chmod(0o700)
                phase = 'reference_http'; transport = None
                try:
                    limit = cfg['max_reference_audio_bytes']; reserve(budget, limit+1)
                    with opener.open(Request(by_id[tid]['reference_url'], headers={'Accept-Encoding': 'identity',
                                     'User-Agent': 'Sonora-caption-pair-reference/1'}), timeout=30) as response:
                        length = int(response.headers.get('Content-Length', '-1'))
                        h.require(response.status == 200 and 0 < length <= limit
                                  and response.headers.get('Content-Encoding', 'identity') == 'identity',
                                  'Bounded complete reference representation required')
                        raw = response.read(limit+1)
                        h.require(len(raw) == length, 'Incomplete reference body')
                        transport = {'bytes': len(raw), 'sha256': h.digest(raw), 'status': response.status,
                                     'ETag': response.headers.get('ETag'), 'Last-Modified': response.headers.get('Last-Modified')}
                    audio = folder/'reference.mp3'
                    outfd = os.open(audio, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600); os.fchmod(outfd, 0o600)
                    with os.fdopen(outfd, 'wb') as f: f.write(raw)
                    h.write_json(folder/'transport.json', transport); phase = 'actual_EOF_and_alignment'
                    a, info = decode(originals[tid]['audio_path']); b, reference_info = decode(audio)
                    h.require(h.digest(a.astype('<f4', copy=False).tobytes()) == originals[tid]['pcm_sha256'], 'Original PCM pin differs')
                    report, probes = pair.align(a, b, [r for r in inputs['candidates']['candidates'] if r['id'] == tid], cfg['alignment'])
                    save_npz(folder/'anchor-probes.npz', probes)
                    value = {'id': tid, 'status': 'passed' if report['passed'] else 'alignment_failed',
                             'transport': transport, 'original_decode': info, 'reference_decode': reference_info, 'alignment': report}
                    h.write_json(folder/'result.json', value); output_refs.append(value)
                except Exception as exc:
                    value = {'id': tid, 'status': 'blocked', 'phase': phase, 'error_type': type(exc).__name__,
                             'detail': str(exc)[:2000], 'transport': transport or {},
                             'http_status': getattr(exc, 'code', None), 'budget_reservation_retained': True}
                    h.write_json(folder/'failure.json', value); output_refs.append(value)
        for name, pin in hashes.items(): h.require(h.file_hash(ROOT/name) == pin, 'Source changed during preflight')
        for key in inputs: pinned(cfg[key])
        h.require(h.file_hash(config) == config_sha256 and not any(n in sys.modules for n in ('torch', 'laion_clap')),
                  'Config changed or unexpected model import')
        good = {v['id'] for v in verdicts if v['eligible']}
        candidates = [r for r in inputs['candidates']['candidates'] if r['id'] in good]
        h.write_json(target/'eligible-candidates.json', {'training_ready': False, 'label_source': 'model_generated', 'candidates': candidates})
        summary = {'schema': 'sonora-caption-pair-preflight-result-v1', 'source_sha': source_sha,
                   'metadata_files': len(manifest['files']), 'metadata_bytes': sum(r['bytes'] for r in manifest['files']),
                   'metadata_matched_rows': sum(len(v) for v in raw_rows.values()),
                   'eligible_recordings': len(good), 'eligible_intervals': len(candidates),
                   'excluded_reasons_nonexclusive': dict(Counter(reason for v in verdicts for reason in v['reasons'])),
                   'splits': {s: {'eligible_recordings': sum(originals[t]['split'] == s for t in good),
                             'eligible_intervals': sum(originals[r['id']]['split'] == s for r in candidates)}
                              for s in ('train', 'validation')},
                   'reference_selected': len(references), 'reference_statuses': dict(Counter(r['status'] for r in output_refs)),
                   'reference_body_bytes_received': sum(r.get('transport', {}).get('bytes', 0) for r in output_refs),
                   'budget_reserved_bytes': budget.used, 'metadata_complete': True,
                   'reference_preflight_passed': len(references) == 3 and all(r['status'] == 'passed' for r in output_refs),
                   'training_ready': False, 'new_recording_IDs': 0, 'fits': 0,
                   'exact_teacher_audio_artifact_verified': False, 'all57_waveforms_verified': False}
        h.write_json(target/'result.json', summary); return summary
    except Exception as exc:
        h.write_json(target/'failure.json', {'status': 'incomplete', 'error_type': type(exc).__name__}); raise


def main():
    p = argparse.ArgumentParser()
    for n in ('config', 'output'): p.add_argument('--'+n, type=Path, required=True)
    p.add_argument('--config-sha256', required=True); p.add_argument('--ca-file')
    print(json.dumps(run(**vars(p.parse_args()))))


if __name__ == '__main__': main()
