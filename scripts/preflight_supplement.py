#!/usr/bin/env python3
"""One bounded six-development-source acquisition and actual-EOF preflight."""
from pathlib import Path
import argparse
from importlib.metadata import distribution
import json
import os
import platform
import ssl
import subprocess
import sys
from urllib.request import HTTPSHandler, build_opener

for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[key] = '2'
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'services/audio-search'))
import holdout_contract as h
import human_caption_capacity as capacity
import mtg_dataset as mtg
import supplement_preflight as checks
from acquire_caption_gate import JournalBudget
from preflight_mtg import fetch_one, Redirects, write_raw

SOURCES = ('scripts/preflight_supplement.py', 'services/audio-search/supplement_preflight.py',
           'scripts/acquire_caption_gate.py', 'scripts/preflight_mtg.py',
           'services/audio-search/research_corpus.py', 'services/audio-search/preprocess.py',
           'services/audio-search/source_review_pack.py',
           'services/audio-search/corpus.py', 'services/audio-search/human_caption_capacity.py',
           'services/audio-search/mtg_dataset.py', 'services/audio-search/mtg_plan.py',
           'services/audio-search/holdout_contract.py', 'services/audio-search/review_pack.py',
           'scripts/holdout_assets.py')


def runtime():
    import soundfile as sf
    import certifi
    packages = {}; files = {}
    for name in ('numpy', 'soundfile', 'librosa', 'soxr', 'scipy', 'numba', 'llvmlite', 'certifi'):
        dist = distribution(name); packages[name] = dist.version
        for entry in dist.files or []:
            if str(entry).endswith(('.py', '.so', '.dylib')):
                path = Path(dist.locate_file(entry)).resolve()
                if path.is_file(): files[str(path)] = h.file_hash(path)
    return {'python': sys.version, 'platform': platform.platform(), 'package_versions': packages,
            'libsndfile_version': sf.__libsndfile_version__, 'openssl': ssl.OPENSSL_VERSION,
            'ca_bundle_sha256': h.file_hash(certifi.where()),
            'installed_decoder_code_sha256': files}


def decode(path):
    import soundfile as sf
    from research_corpus import decode_source_mono
    with sf.SoundFile(path) as source:
        header = {'frames': source.frames, 'sample_rate_hz': source.samplerate,
                  'channels': source.channels, 'format': source.format,
                  'duration_ms': source.frames*1000//source.samplerate}
    return decode_source_mono(path, header)


def run(config, config_sha256, output):
    cfg = h.assets.document(config, config_sha256); checks.validate_config(cfg)
    task = ROOT/cfg['task_directory']
    h.require(Path(output).absolute().is_relative_to(task.absolute()) and not (task/'preflight-started.json').exists(),
              'Task preflight already attempted or invalid output; no new-directory retry')
    h.require(not subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT).strip(), 'Clean committed preflight required')
    target = h.private_output(output)
    try:
        documents = {k: h.assets.document(ROOT/v['path'], v['sha256']) for k, v in cfg['inputs'].items()}
        pins = {str((ROOT/v['path']).absolute()): v['sha256'] for v in cfg['inputs'].values()}
        pins[str(Path(config).absolute())] = config_sha256
        raw = {}
        for key, pin in documents['source_inputs']['files'].items():
            raw[key] = h.assets.read(ROOT/pin['path'], 40*1024*1024)
            h.require(h.digest(raw[key]) == pin['sha256'], 'Pinned metadata changed')
            pins[str((ROOT/pin['path']).absolute())] = pin['sha256']
        h.require(documents['plan_verification']['supplement_plan_sha256'] == cfg['inputs']['plan']['sha256'],
                  'Exact published six-source plan required')
        # Recompute all8 unused sources on the full global-credit graph, without caption text.
        names, _ = mtg.names(raw['names']); base = mtg.table(raw['base'])
        rights = mtg.licenses(raw['licenses']); hashes = mtg.checksums(raw['audio_sha256'])
        split = {tid: key for key in ('train', 'validation', 'test') for tid in mtg.table(raw[key])}
        group_docs = {'dataset': documents['dataset'], 'plan': documents['future_plan'],
                      'pilot': documents['pilot'], 'expanded': documents['prior76']}
        frame = capacity.measure(capacity.sdd_metadata(raw['sdd']), base, names, rights, hashes,
                                 split, capacity.blockers_from_documents(group_docs, raw))
        h.require(frame['eligible'] == documents['capacity']['eligible'], 'Unused full-credit isolation changed')
        selected = checks.validate_selection(documents['plan'], frame['eligible'], base, names, rights, hashes,
                                             {tid for tid, value in split.items() if value == 'test'})
        prior = checks.prior_content(documents)
        h.require(prior['summary']['record_references'] == 296, 'All old60/pilot20/140/76 exact-content evidence required')
        source = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
        code_pins = {name: h.file_hash(ROOT/name) for name in SOURCES}
        environment = runtime()
        h.write_json(target/'freeze.json', {'created_at_utc': h.now(), 'source_sha': source,
            'config_sha256': config_sha256, 'source_sha256': code_pins, 'input_sha256': pins,
            'runtime': environment, 'prior_content_summary': prior['summary']})
        h.write_json(task/'preflight-started.json', {'started_at_utc': h.now(), 'source_sha': source,
                                                   'maximum_attempts_per_selected_track': 1, 'automatic_replacements': False})
        budget = JournalBudget(task/'network-ledger.jsonl', cfg['max_total_body_bytes'])
        import certifi
        opener = build_opener(Redirects(), HTTPSHandler(context=ssl.create_default_context(cafile=certifi.where())))
        rows, failures, seen_bytes, seen_pcm = [], [], set(), set()
        for index, row in enumerate(selected, 1):
            directory = target/row['source_track_id']; directory.mkdir(mode=0o700)
            try:
                h.require(row['audio_sha256'] not in prior['bytes'], 'Old official byte duplicate before GET')
                # The only allowed network path is the fixed official per-track low MP3.
                blob, transport = fetch_one(opener, {'low_path': row['official_low_path'],
                                                    'audio_sha256': row['audio_sha256']}, cfg, budget)
                path = directory/'audio.mp3'; write_raw(path, blob)
                h.write_json(directory/'transport.json', transport)
                audio, info = decode(path)
                proof = checks.inspect_audio(audio, row['duration_metadata_seconds'])
                checks.check_duplicate(row['audio_sha256'], proof['pcm_sha256'], prior, seen_bytes, seen_pcm)
                receipt = {'source_track_id': row['source_track_id'], 'creator_component': row['creator_component'],
                    'audio_sha256': row['audio_sha256'], 'validated_caption_count': row['validated_caption_count'],
                    'audio_path': str(path), 'bytes': len(blob), 'transport': transport, 'decode': info,
                    'audio_preflight': proof, 'audio_license': row['audio_license']}
                h.write_json(directory/'receipt.json', receipt)
                rows.append({**receipt, 'receipt_path': str(directory/'receipt.json'),
                             'receipt_sha256': h.file_hash(directory/'receipt.json')})
                seen_bytes.add(row['audio_sha256']); seen_pcm.add(proof['pcm_sha256'])
            except Exception as error:
                failure = {'source_track_id': row['source_track_id'], 'error_type': type(error).__name__, 'error': str(error)}
                h.write_json(directory/'failure.json', failure); failures.append(failure)
            print(json.dumps({'completed_slots': index, 'required': 6, 'ready': len(rows),
                              'failed': len(failures), 'body_reserved_bytes': budget.used}), flush=True)
        h.write_json(target/'attempts.json', {'ready': rows, 'failures': failures, 'body_reserved_bytes': budget.used})
        h.require(not failures and len(rows) == 6, 'Fixed six-source preflight incomplete; no retry or replacement')
        for path, pin in pins.items(): h.require(h.file_hash(path) == pin, 'Source input mutated')
        for path, pin in code_pins.items(): h.require(h.file_hash(ROOT/path) == pin, 'Preflight code mutated')
        h.require(runtime() == environment, 'Installed decoder runtime changed')
        h.require(not any(k == 'torch' or k.startswith(('torch.', 'laion_clap')) for k in sys.modules),
                  'Audio preflight must not load encoder libraries')
        summary = {'recordings': 6, 'creator_components': 6, 'validated_caption_queries': 7,
            'official_audio_sha_matches': 6, 'actual_EOF_decodes': 6,
            'first_tail_windows_checked': 12, 'whole_song_windows': sum(r['audio_preflight']['whole_song_window_count'] for r in rows),
            'prior_and_new_exact_byte_duplicates': 0, 'prior_and_new_normalized_PCM_duplicates': 0,
            'body_reserved_bytes': budget.used, 'audio_bytes': sum(r['bytes'] for r in rows),
            'prior_content': prior['summary'], 'audio_ready_for_feature_build': True,
            'semantic_caption_audio_match_verified': False, 'operations': cfg['operations']}
        private = {'schema': 'sonora-six-development-audio-preflight-result-v1', 'source_sha': source,
                   'summary': summary, 'tracks': rows}
        h.write_json(target/'catalog.json', private)
        public = {'source_sha': source, 'summary': summary, 'catalog_sha256': h.file_hash(target/'catalog.json')}
        h.write_json(target/'result-public.json', public)
        return public
    except Exception as error:
        h.write_json(target/'failure.json', {'error_type': type(error).__name__, 'error': str(error)})
        raise


def main():
    parser = argparse.ArgumentParser()
    for name in ('config', 'output'): parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--config-sha256', required=True)
    print(json.dumps(run(**vars(parser.parse_args()))))


if __name__ == '__main__': main()
