#!/usr/bin/env python3
"""Once-only pinned metadata audit; never download/encode/fit/score or read caption fields."""
from pathlib import Path
import argparse
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'services/audio-search'))
import holdout_contract as h
import human_caption_capacity as capacity
import mtg_dataset as m

SOURCES = ('scripts/audit_human_caption_capacity.py', 'services/audio-search/human_caption_capacity.py',
           'services/audio-search/mtg_dataset.py', 'services/audio-search/mtg_plan.py',
           'services/audio-search/holdout_contract.py', 'services/audio-search/review_pack.py',
           'scripts/holdout_assets.py')


def attempt_file(cfg, task):
    if 'repair_of' not in cfg: return 'audit-started.json'
    pins = cfg['repair_of']
    h.require(set(pins) == {'original_config', 'claim', 'freeze', 'failure'}
              and cfg.get('repair_reason') == 'numeric_source_ids_and_blank_nonvalidated_flags', 'Only pinned source-format repair allowed')
    old = {k: h.assets.document(ROOT/v['path'], v['sha256']) for k, v in pins.items()}
    h.require({k: v for k, v in cfg.items() if k not in ('repair_of', 'repair_reason')} == old['original_config']
              and ROOT/pins['claim']['path'] == task/'audit-started.json'
              and old['claim']['source_sha'] == old['freeze']['source_sha']
              and old['freeze']['config_sha256'] == pins['original_config']['sha256']
              and old['failure'] == {'error_type': 'ValueError', 'error': 'Invalid source identifier'}
              and (ROOT/pins['failure']['path']).parent == (ROOT/pins['freeze']['path']).parent
              and not ((ROOT/pins['freeze']['path']).parent/'result-private.json').exists(), 'Exact failed source-format audit required')
    for path, pin in old['freeze']['input_sha256'].items(): h.require(h.file_hash(path) == pin, 'Original failed input mutated')
    return 'audit-repair-started.json'


def run(config, config_sha256, output):
    cfg = h.assets.document(config, config_sha256)
    h.require(cfg['schema'] == 'sonora-human-caption-capacity-v1'
              and cfg['task_directory'] == '.local/a/mus061'
              and cfg['policy'] == {'validated_only': True, 'allowed_license_families': ['by', 'by-sa'],
                  'duration_bounds_seconds': [30, 600], 'one_recording_per_creator_component': True,
                  'unseen_caption_body_used': False, 'new_partition_selected': False}
              and cfg['operations'] == dict.fromkeys(('downloads', 'encodes', 'fits', 'scored_queries', 'test_caption_inputs'), 0),
              'Fixed source-only audit policy required')
    task = ROOT/cfg['task_directory']
    attempt = attempt_file(cfg, task)
    h.require(Path(output).absolute().is_relative_to(task.absolute()) and not (task/attempt).exists(),
              'Task metadata audit already attempted or invalid output')
    h.require(not subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT).strip(), 'Clean committed audit required')
    target = h.private_output(output)
    try:
        docs = {k: h.assets.document(ROOT/v['path'], v['sha256']) for k, v in cfg['inputs'].items()}
        pins = {str((ROOT/v['path']).absolute()): v['sha256'] for v in cfg['inputs'].values()}
        pins[str(Path(config).absolute())] = config_sha256
        if 'repair_of' in cfg:
            pins.update({str((ROOT/v['path']).absolute()): v['sha256'] for v in cfg['repair_of'].values()})
        raw = {}
        for k, v in docs['inputs']['files'].items():
            raw[k] = h.assets.read(ROOT/v['path'], 40*1024*1024)
            h.require(h.digest(raw[k]) == v['sha256'], 'Pinned source metadata changed')
            pins[str((ROOT/v['path']).absolute())] = v['sha256']
        source = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
        freeze = {'created_at_utc': h.now(), 'source_sha': source, 'config_sha256': config_sha256,
                  'source_sha256': {n: h.file_hash(ROOT/n) for n in SOURCES}, 'input_sha256': pins,
                  'runtime': {'python': sys.version}, 'operations': cfg['operations']}
        h.write_json(target/'freeze.json', freeze)
        h.write_json(task/attempt, {'started_at_utc': h.now(), 'source_sha': source, 'maximum_attempts': 1})
        # No caption/familiarity content is retained, compared, printed or passed to models.
        rows = capacity.sdd_metadata(raw['sdd'])
        names, malformed = m.names(raw['names'])
        splits = {tid: split for split in ('train', 'validation', 'test') for tid in m.table(raw[split])}
        result = capacity.measure(rows, m.table(raw['base']), names, m.licenses(raw['licenses']),
                                  m.checksums(raw['audio_sha256']), splits, capacity.blockers_from_documents(docs, raw))
        result['summary']['malformed_name_rows_quarantined'] = len(malformed)
        result['source_sha'] = source
        result['operations'] = cfg['operations']
        for path, pin in pins.items(): h.require(h.file_hash(path) == pin, 'Input mutated during audit')
        for path, pin in freeze['source_sha256'].items(): h.require(h.file_hash(ROOT/path) == pin, 'Audit source mutated')
        h.write_json(target/'result-private.json', result)
        public = {k: result[k] for k in ('summary', 'source_sha', 'operations')}
        public['private_result_sha256'] = h.file_hash(target/'result-private.json')
        h.write_json(target/'result-public.json', public)
        return public
    except Exception as error:
        h.write_json(target/'failure.json', {'error_type': type(error).__name__, 'error': str(error)})
        raise


def main():
    p = argparse.ArgumentParser()
    for name in ('config', 'output'): p.add_argument('--'+name, type=Path, required=True)
    p.add_argument('--config-sha256', required=True)
    print(json.dumps(run(**vars(p.parse_args()))))


if __name__ == '__main__': main()
