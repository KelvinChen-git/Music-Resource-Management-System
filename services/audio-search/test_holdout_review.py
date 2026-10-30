"""Synthetic complete221/source/HTTP fixtures, never real qrels or test inference."""
from copy import deepcopy
import json
import os
from pathlib import Path
import sys
import subprocess
import shutil
import unittest
from unittest.mock import patch

import holdout_contract as hc
import holdout_review as review
sys.path.insert(0,str(hc.ROOT/'scripts'))
from holdout_test_fixture import HoldoutFixture


class IndependentReviewTest(HoldoutFixture,unittest.TestCase):
    def setUp(self):
        original_root=hc.ROOT;self.real_root=original_root
        self.prepare_fixture();self.run_import()
        subprocess.run(['git','init','-q',str(self.root)],check=True)
        (self.root/'.gitignore').write_text('.local/\n')
        q=json.loads((original_root/hc.QUERY_PATH).read_text())
        q['source_frame_sha256']=self.binding['frame']['sha256'];q['source_corpus_freeze_receipt_sha256']=self.binding['source_freeze']['sha256']
        p=self.root/hc.QUERY_PATH;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(q,ensure_ascii=False))
        config=self.root/hc.CONFIG_PATH
        runtime=json.loads((original_root/hc.CONFIG_PATH).read_text());runtime['query_manifest_sha256']=hc.file_hash(p)
        config.write_text(json.dumps(runtime))
        for module,key,value in [(hc,'ROOT',self.root),(hc,'QUERY_SHA',hc.file_hash(p)),(hc,'CONFIG_SHA',hc.file_hash(config))]:
            item=patch.object(module,key,value);item.start();self.addCleanup(item.stop)
        self.args={'binding':self.binding_path,'binding_sha256':self.binding_sha,'catalog':self.output/'catalog.json',
            'catalog_sha256':hc.file_hash(self.output/'catalog.json'),'audio_root':self.output/'audio'}
        self.data=hc.snapshot(**self.args);self.packs=review.packages(self.data,'a'*64)

    def write(self,name,value):
        p=self.root/'.local/a'/name;p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n');return p

    def seal(self,value):
        p=self.write('base.json',self.packs[0]);q=self.write('judgments.json',value)
        return review.seal(base=p,base_sha256=hc.file_hash(p),judgments=q)

    def complete(self):
        pack=deepcopy(self.packs[0])
        for q in pack['queries']:
            for c in q['candidates']:c.update(relevance=1,annotator='synthetic-only',judged_at='2026-10-29T01:00:00Z')
        return pack

    def test_full221_reconstruction_binds20_and_all480_plus_inputs(self):
        self.assertEqual(len(self.data['tracks']),20);self.assertEqual(len(self.data['queries']),8)
        self.assertGreaterEqual(len(self.data['input_sha256']),400)
        self.assertEqual(self.data['source_dataset_sha256'],self.manifest['dataset_sha256'])

    def test_four_full_grid_packs_no_hints_or_labels_and_distinct_fingerprints(self):
        pairs=set();fingerprints=set();common=set()
        for i,p in enumerate(self.packs,1):
            self.assertEqual(p['provenance']['batch'],i)
            fingerprints.add(p['dataset_sha256']);common.add(p['provenance']['test_dataset_sha256'])
            self.assertEqual(review.rp.validate(p,p)['unjudged'],40)
            self.assertEqual(len({c['track_id'] for q in p['queries'] for c in q['candidates']}),20)
            for q in p['queries']:
                for c in q['candidates']:
                    self.assertEqual(c['model_suggested_intervals_ms'],[])
                    self.assertNotIn((q['query_id'],c['track_id']),pairs);pairs.add((q['query_id'],c['track_id']))
        self.assertEqual((len(pairs),len(fingerprints),len(common)),(160,4,1))

    def test_order_and_bilingual_cues_reproduce_preregistered_sha(self):
        import hashlib
        for p in self.packs:
            for q in p['queries']:
                ranks=[(hashlib.sha256(('MUS-038-phase1-label-order-v1\n'+q['query_id']+'\n'+c['source_provider']+':'+c['source_id']).encode()).hexdigest(),c['source_provider']+':'+c['source_id']) for c in q['candidates']]
                self.assertEqual(ranks,sorted(ranks));self.assertEqual(len(q['audible_required_cues_zh']),3)
                self.assertEqual(set(q['grade_rules_zh']),{'0','1','2','3'})

    def test_changing_frozen_query_config_or_imported_audio_rejected(self):
        for path in [self.root/hc.QUERY_PATH,self.root/hc.CONFIG_PATH,self.output/'audio'/self.data['tracks'][0]['asset_filename']]:
            raw=path.read_bytes();path.write_bytes(raw+b' ')
            with self.assertRaises(ValueError):hc.snapshot(**self.args)
            path.write_bytes(raw)

    def test_receipt_only_exact_payload_hash_no_grade_distribution(self):
        result=self.seal(self.complete())
        self.assertEqual(set(result),{'dataset_sha256','payload_sha256','total_completed_count','validation_status'})
        self.assertEqual(result['payload_sha256'],hc.file_hash(self.root/'.local/a/judgments.json'))
        self.assertEqual(result['total_completed_count'],40)

    def test_unknown_is_not_zero_and_incomplete_receipt_is_rejected(self):
        with self.assertRaises(ValueError):self.seal(self.packs[0])
        complete=self.complete();complete['queries'][0]['candidates'][0].update(relevance=None,annotator=None,judged_at=None)
        with self.assertRaises(ValueError):self.seal(complete)

    def test_immutable_candidate_text_order_provenance_or_hint_changes_rejected(self):
        for change in [lambda p:p['queries'][0].update(text='changed'),lambda p:p['queries'][0]['candidates'].reverse(),
            lambda p:p['provenance'].update(runner_freeze_sha256='b'*64),
            lambda p:p['queries'][0]['candidates'][0].update(model_suggested_intervals_ms=[[0,1000]])]:
            p=self.complete();change(p)
            with self.assertRaises(ValueError):self.seal(p)

    def test_invalid_human_fields_ranges_or_noninteger_relevance_rejected(self):
        for update in [{'relevance':True},{'relevance':1.0},{'judged_at':'2026-02-30T01:00:00Z'},
            {'annotator':'real name'},{'human_intervals_ms':[[0,99999999]]},
            {'relevance':0,'human_intervals_ms':[[0,1000]]}]:
            p=self.complete();p['queries'][0]['candidates'][0].update(update)
            with self.assertRaises(ValueError):self.seal(p)

    def test_valid_optional_intervals_and_zero_grade_are_accepted(self):
        p=self.complete();p['queries'][0]['candidates'][0]['human_intervals_ms']=[[0,1000],[1000,2000]]
        p['queries'][0]['candidates'][1]['relevance']=0
        self.assertEqual(self.seal(p)['total_completed_count'],40)

    def test_duplicate_json_fields_and_wrong_base_pin_rejected(self):
        p=self.write('base.json',self.packs[0]);q=self.write('judgments.json',self.complete())
        with self.assertRaises(ValueError):review.seal(base=p,base_sha256='0'*64,judgments=q)
        q.write_text(q.read_text().replace('"split": "independent_test"','"split": "independent_test", "split": "independent_test"'))
        with self.assertRaises(ValueError):review.seal(base=p,base_sha256=hc.file_hash(p),judgments=q)

    def test_explicit_modes_and_no_overwrite_even_extreme_umask(self):
        out=self.root/'.local/a/modes';mask=os.umask(0o777)
        try:
            target=hc.private_output(out);hc.write_json(target/'value.json',{'ok':True})
        finally:os.umask(mask)
        self.assertEqual(target.stat().st_mode&0o777,0o700)
        self.assertEqual((target/'value.json').stat().st_mode&0o777,0o600)
        with self.assertRaises(FileExistsError):hc.private_output(out)
        with self.assertRaises(FileExistsError):hc.write_json(target/'value.json',{})
        with self.assertRaises(ValueError):hc.private_output(self.root/'escape')

    def test_build_writes_four_blank_private_packages_and_rejects_overwrite(self):
        target=self.root/'.local/a/packages'
        with patch.object(hc,'checked_freeze',return_value=({},self.data)):
            result=review.build(freeze='synthetic',freeze_sha256='a'*64,output=target)
            with self.assertRaises(FileExistsError):review.build(freeze='synthetic',freeze_sha256='a'*64,output=target)
        self.assertEqual(result['counts'],{'unique_recordings':20,'queries':8,'candidate_pairs':160,'judged':0,'model_hints':0})
        self.assertEqual(len(list(target.glob('sonora-independent-batch-*.json'))),4)

    def test_checked_freeze_binds_sources_inputs_both_models_and_environment(self):
        source_name=hc.CONFIG_PATH;pin={'path':'synthetic-checkpoint'}
        f={'schema':'sonora-independent-runner-freeze-v1','status':'frozen_before_test_inference',
           'counts':{'new_test_audio_encoded':0,'new_test_text_encoded':0,'qrels_opened':0},
           'arguments':self.data['arguments'],'input_sha256':self.data['input_sha256'],
           'source_dataset_sha256':self.data['source_dataset_sha256'],
           'source':{'source_sha256':{source_name:hc.file_hash(self.root/source_name)}},
           'models':{m:{'pin':pin,'audio_shape':[1,512],'text_shape':[1,512],
              'strict':{'strict_missing':[],'strict_unexpected':[]},'test_query_token_lengths':[10]*8} for m in ['A','B']},
           'environment':{'synthetic':True}}
        path=self.write('synthetic-freeze.json',f)
        with patch.object(hc,'SOURCE_FILES',[source_name]),patch.object(hc,'checkpoint_pin',return_value=pin),\
             patch.object(hc,'environment',return_value={'synthetic':True}):
            hc.checked_freeze(path,hc.file_hash(path),verify_environment=True)
            for change in [lambda x:x['models']['B'].update(audio_shape=[1,511]),
                lambda x:x['source']['source_sha256'].update({source_name:'0'*64}),
                lambda x:x['environment'].update(changed=True),lambda x:x['input_sha256'].clear()]:
                value=deepcopy(f);change(value);self.write('synthetic-freeze.json',value)
                with self.assertRaises(ValueError):hc.checked_freeze(path,hc.file_hash(path),verify_environment=True)

    def test_python_browser_canonical_fingerprint_and_exact_completion_receipt_agree(self):
        base=self.write('cross-language-base.json',self.packs[0])
        code="""import fs from 'node:fs';
import {loadReviewPack,exportReviewPack,exportCompletionReceipt} from './web/src/utils/reviewPack.js';
const pack=await loadReviewPack(fs.readFileSync(process.argv[1],'utf8'),process.argv[2]);
for(const q of pack.queries)for(const r of q.candidates)Object.assign(r,{relevance:1,annotator:'synthetic-only',judged_at:'2026-10-29T01:00:00Z'});
console.log(JSON.stringify({raw:await exportReviewPack(pack,process.argv[2]),receipt:JSON.parse(await exportCompletionReceipt(pack,process.argv[2]))}));
"""
        node=Path(os.environ.get('SONORA_NODE_BINARY') or shutil.which('node') or str(self.real_root.parent/'.music-tools/node-v22.23.3-darwin-arm64/bin/node'))
        if not node.is_file():self.skipTest('Existing Node runtime unavailable')
        result=subprocess.run([str(node),'--input-type=module','-e',code,str(base),str(self.owner)],cwd=self.real_root,capture_output=True,text=True,check=True)
        value=json.loads(result.stdout);export=self.root/'.local/a/cross-language-judgments.json';export.write_text(value['raw'])
        receipt=review.seal(base=base,base_sha256=hc.file_hash(base),judgments=export)
        self.assertEqual(receipt,value['receipt'])


if __name__=='__main__':unittest.main()
