#!/usr/bin/env python3
"""Offline pinned source audit and one six-component metadata plan, no model/network."""
from pathlib import Path
import argparse
import csv
import io
import json
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'services/audio-search'))
import holdout_contract as h
import caption_source_audit as audit
import human_caption_capacity as capacity
import mtg_dataset as mtg

SOURCES = ('scripts/audit_caption_sources.py', 'services/audio-search/caption_source_audit.py',
           'services/audio-search/human_caption_capacity.py', 'services/audio-search/mtg_dataset.py',
           'services/audio-search/mtg_plan.py', 'services/audio-search/review_pack.py',
           'services/audio-search/holdout_contract.py', 'scripts/holdout_assets.py')


def run(config, config_sha256, output):
    cfg = h.assets.document(config, config_sha256)
    h.require(cfg['schema'] == 'sonora-human-source-audit-and-six-dev-plan-v1'
              and cfg['task_directory'] == '.local/a/mus062' and cfg['supplement_recordings'] == 6
              and cfg['selection_seed'] == 'MUS-062-unused-SDD-six-components-v1'
              and cfg['allow_original_rule_relaxation'] is False
              and cfg['future_comparison']['models'] == ['identity', 'saved100-fulltext-ridge']
              and cfg['future_comparison']['status'] == 'plan_only_no_model_inputs_or_scores'
              and cfg['future_comparison']['candidate_pool'] == 'existing140_plus_new6_same_first120_view'
              and cfg['future_comparison']['new_fit_runs'] == 0
              and cfg['future_comparison']['formal_quality_acceptance'] is False
              and cfg['operations'] == dict.fromkeys(('audio_downloads', 'encodes', 'fits', 'scores',
                                                     'project_reserved_test_inputs', 'new_manual_labels'), 0),
              'Fixed source-only six-development plan required')
    task = ROOT/cfg['task_directory']
    h.require(Path(output).absolute().is_relative_to(task.absolute()) and not (task/'audit-started.json').exists(),
              'Task already attempted or invalid output; no new-directory restart')
    h.require(not subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT).strip(), 'Clean committed source audit required')
    target = h.private_output(output)
    try:
        pins = {str((ROOT/v['path']).absolute()): v['sha256'] for v in cfg['inputs'].values()}
        pins[str(Path(config).absolute())] = config_sha256
        for path, pin in pins.items(): h.require(h.file_hash(path) == pin, 'Fixed input changed')
        def document(key):
            pin = cfg['inputs'][key]
            return h.assets.document(ROOT/pin['path'], pin['sha256'])
        capture = document('capture_manifest')
        h.require(capture['reserved_body_bytes'] <= capture['body_budget_bytes'] == 32*1024*1024,
                  'Fixed source-only body budget exceeded')
        for row in capture['entries']:
            h.require(row['result'] == 'captured', 'Source capture incomplete; no silent omission')
            path = task/row['name']; h.require(h.file_hash(path) == row['sha256'], 'Captured source mutated')
            pins[str(path.absolute())] = row['sha256']
        original = document('source_inputs'); raw = {}
        for key, pin in original['files'].items():
            raw[key] = h.assets.read(ROOT/pin['path'], 40*1024*1024)
            h.require(h.digest(raw[key]) == pin['sha256'], 'Pinned original source changed')
            pins[str((ROOT/pin['path']).absolute())] = pin['sha256']
        source = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
        source_pins = {n: h.file_hash(ROOT/n) for n in SOURCES}
        h.write_json(target/'freeze.json', {'created_at_utc': h.now(), 'source_sha': source,
            'input_sha256': pins, 'source_sha256': source_pins,
            'python': sys.version, 'operations': cfg['operations']})
        h.write_json(task/'audit-started.json', {'started_at_utc': h.now(), 'source_sha': source, 'maximum_attempts': 1})
        wiki = audit.wiki_frame(h.assets.read(ROOT/cfg['inputs']['wikimute']['path']))
        mc = list(csv.DictReader(io.StringIO(h.assets.read(ROOT/cfg['inputs']['musiccaps']['path']).decode('utf8'))))
        mb = set()
        with (ROOT/cfg['inputs']['musicbench_train']['path']).open() as stream:
            for line in stream:
                location = json.loads(line)['location']
                match = re.fullmatch(r'([A-Za-z0-9_-]{11})(?:_\d+)?\.wav', Path(location).name)
                h.require(match is not None, 'Pinned MusicBench location malformed')
                mb.add(match[1])
        yt = audit.youtube_frame(h.assets.read(ROOT/cfg['inputs']['yt8m_train']['path']), mc, mb)
        prior = document('capacity'); verified = document('capacity_verification')
        h.require(verified['private_result_sha256'] == cfg['inputs']['capacity']['sha256']
                  and prior['summary']['eligible_recordings'] == 8
                  and prior['summary']['independent_credit_components_upper_bound'] == 6,
                  'Published unused-capacity evidence required')
        plan = audit.supplement_plan(prior['eligible'], capacity.sdd_metadata(raw['sdd']), cfg['selection_seed'])
        oldpool = {r['source_track_id'] for r in document('retrieval_cache')['rows']}
        h.require(len(oldpool) == 140 and not oldpool & {r['source_track_id'] for r in plan['selected']},
                  'Supplement cannot reuse existing140 candidate recording')
        names, _ = mtg.names(raw['names']); base = mtg.table(raw['base']); licenses = mtg.licenses(raw['licenses'])
        for row in plan['selected']:
            tid = row['source_track_id']; b = base[tid]; n = names[tid]
            row.update(artist_id=b['artist_id'], artist_name=n['artist'], title=n['title'], path=b['path'],
                       duration_metadata_seconds=b['duration'], audio_license=licenses[b['path']],
                       official_low_path=b['path'].removesuffix('.mp3')+'.low.mp3')
        plan['source_sha'] = source; plan['future_comparison'] = cfg['future_comparison']
        plan['sdd_source_sha256'] = original['files']['sdd']['sha256']
        h.write_json(target/'supplement-plan.json', plan)
        result = {'source_sha': source, 'wikimute': wiki['summary'], 'yt8m_train': yt['summary'],
                  'supplement': plan['summary'], 'supplement_plan_sha256': h.file_hash(target/'supplement-plan.json'),
                  'operations': cfg['operations'], 'capture': {k: capture[k] for k in
                      ('body_budget_bytes', 'reserved_body_bytes', 'actual_captured_bytes', 'audio_downloads')}}
        h.write_json(target/'source-projections.json', {'wikimute': wiki['rows'], 'yt8m_train': yt['rows']})
        for path, pin in pins.items(): h.require(h.file_hash(path) == pin, 'Input mutated during source audit')
        for path, pin in source_pins.items(): h.require(h.file_hash(ROOT/path) == pin, 'Audit source mutated')
        h.write_json(target/'result-public.json', result)
        return result
    except Exception as error:
        h.write_json(target/'failure.json', {'error_type': type(error).__name__, 'error': str(error)})
        raise


def main():
    parser = argparse.ArgumentParser()
    for name in ('config', 'output'): parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--config-sha256', required=True)
    print(json.dumps(run(**vars(parser.parse_args()))))


if __name__ == '__main__': main()
