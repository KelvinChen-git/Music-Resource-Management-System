#!/usr/bin/env python3
"""One metadata audit; never fetch audio, fit models or consume held-out captions."""
from pathlib import Path
import argparse
import hashlib
import json
import platform
import subprocess
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'services/audio-search'))
import holdout_contract as h
import clotho_source_capacity as source
SOURCES = ('scripts/audit_clotho_capacity.py', 'services/audio-search/clotho_source_capacity.py',
           'services/audio-search/holdout_contract.py', 'scripts/holdout_assets.py',
           'services/audio-search/review_pack.py', 'scripts/collect_holdout_music.py')


def validate(cfg):
    h.require(cfg['schema'] == 'sonora-clotho-source-capacity-v1' and cfg['task_directory'] == '.local/a/mus065'
              and cfg['music_tags'] == source.TAGS and cfg['audio_license_families'] == ['by','by-sa']
              and cfg['closure'] == 'same_sound_id_or_casefolded_uploader_all3splits_exclude_cross_split_both_sides'
              and cfg['encoding'] == 'utf8_sig_then_iso88591_if_decode_error'
              and cfg['role'] == 'metadata_training_candidates_only_no_new_independent_benchmark'
              and cfg['operations'] == dict.fromkeys(('audio_downloads','encodes','fits','quality_scores','reserved_test_inputs','new_manual_labels'),0),
              'Fixed metadata-only capacity recipe required')


def selection_proof(raw):
    lines = raw.decode('utf8').splitlines()
    matches = [line for line in lines if 'highest average mAP score' in line and 'Clotho' in line
               and 'AudioCaps' in line and 'checkpoints' in line]
    h.require(len(matches) == 1 and 'music_audioset_epoch_15_esc_90.14.pt' in raw.decode('utf8'),
              'Pinned current-A checkpoint-selection provenance missing')
    return {'current_A_checkpoint_named': True, 'Clotho_in_checkpoint_selection_metric': True,
            'AudioCaps_in_checkpoint_selection_metric': True, 'exact_training_membership_established': False,
            'selection_line_sha256': hashlib.sha256(matches[0].encode()).hexdigest()}


def run(config, config_sha256, output):
    cfg = h.assets.document(config, config_sha256); validate(cfg); task = ROOT/cfg['task_directory']
    h.require(Path(output).absolute().is_relative_to(task.absolute()) and not (task/'audit-started.json').exists(),
              'Audit already attempted or invalid output; no new-directory retry')
    h.require(not subprocess.check_output(['git','status','--porcelain'],cwd=ROOT).strip(), 'Committed clean source required')
    target = h.private_output(output)
    try:
        bound = {str(Path(config).absolute()): config_sha256}
        for pin in cfg['inputs'].values():
            path = ROOT/pin['path']; h.require(h.file_hash(path) == pin['sha256'], 'Pinned source changed')
            bound[str(path.absolute())] = pin['sha256']
            if 'md5' in pin: h.require(hashlib.md5(h.assets.read(path)).hexdigest() == pin['md5'], 'Official source MD5 mismatch')
        freeze = {'source_sha':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                  'source_sha256':{n:h.file_hash(ROOT/n) for n in SOURCES}, 'input_sha256':bound,
                  'config_sha256':config_sha256,'created_at_utc':h.now(),'python':platform.python_version(),'system':platform.system()}
        h.write_json(target/'freeze.json',freeze)
        h.write_json(task/'audit-started.json',{'started_at_utc':h.now(),'source_sha':freeze['source_sha'],
                     'config_sha256':config_sha256,'output':str(target),'maximum_attempts':1,'fits':0})
        value = source.analyze({split:h.assets.read(ROOT/cfg['inputs'][split]['path']) for split in source.SPLITS},
                               h.assets.read(ROOT/cfg['inputs']['captions_development']['path']))
        value['checkpoint_provenance'] = selection_proof(h.assets.read(ROOT/cfg['inputs']['clap_readme']['path']))
        value['caption_license'] = {'source_sha256': cfg['inputs']['license']['sha256'],
            'experimental_noncommercial_only': True,'original_notice_must_be_retained':True,
            'commercial_services_or_results_not_authorized_by_this_license':True}
        for n,pin in bound.items():h.require(h.file_hash(n) == pin, 'Source changed during audit')
        for n,pin in freeze['source_sha256'].items():h.require(h.file_hash(ROOT/n) == pin, 'Audit code changed')
        h.require('torch' not in sys.modules and 'laion_clap' not in sys.modules,'No encoder imports allowed')
        value.update(status='metadata_capacity_complete_not_audio_or_training_ready',source_sha=freeze['source_sha'],
                     config_sha256=config_sha256,torch_or_CLAP_imported=False)
        h.write_json(target/'result-private.json',value)
        public = {k:v for k,v in value.items() if k not in ('training_candidates','metadata_components')}
        public['training_candidate_clips'] = len(value['training_candidates'])
        public['private_result_sha256'] = h.file_hash(target/'result-private.json')
        h.write_json(target/'result-public.json',public)
        return public
    except Exception as error:
        h.write_json(target/'failure.json',{'error_type':type(error).__name__,'error':str(error)});raise


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--config',type=Path,required=True)
    parser.add_argument('--config-sha256',required=True);parser.add_argument('--output',type=Path,required=True)
    print(json.dumps(run(**vars(parser.parse_args()))))


if __name__ == '__main__':main()
