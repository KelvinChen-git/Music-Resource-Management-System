"""Synthetic LOC frame/transport/decoder tests; no new queries, labels or network."""
from collections import Counter
from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.request import Request

import collect_holdout_music as c


def put(path, value):
    path.write_bytes(c.canonical(value))
    path.chmod(0o600)
    return c.digest(path.read_bytes())


class HoldoutCollectionTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        protocol = (c.ROOT / 'docs/evaluation/MUS-038-protocol.json').read_bytes()
        self.root = Path(temporary.name).resolve()
        self.state = self.root / '.local/a/mus039'
        self.state.mkdir(parents=True, mode=0o700)
        self.output = self.state / 'batch'
        p = self.root / 'docs/evaluation/MUS-038-protocol.json'
        p.parent.mkdir(parents=True)
        p.write_bytes(protocol)
        self.root_patch = patch.object(c, 'ROOT', self.root)
        self.root_patch.start(); self.addCleanup(self.root_patch.stop)
        self.frame_path = self.state / 'source-frame.json'
        self.groups_path = self.state / 'group-review.json'
        self.old_path = self.state / 'old-group-review.json'
        self.rows, snapshots, items, data_items = [], {}, [], []
        (self.state / 'item-rights').mkdir(mode=0o700)
        def snapshot(name, body):
            path = self.state / name
            path.write_bytes(body); path.chmod(0o600)
            snapshots[name] = c.digest(body)
        names = ['Synthetic new creator ' + str(i) for i in range(8)]
        for i in range(132):
            sid = 'fma-' + str(1000 + i)
            title = 2670 if i == 0 else 'Synthetic official recording ' + str(i)
            page = '/items/loc-fma/' + sid + '/'
            stream = '/audio/items/loc-fma/' + sid + '.mp3'
            rights = 'item-rights/' + sid + '.md'
            fields = {'uid': sid, 'title': title, 'permalink': page, 'stream_url': stream,
                'contributors': names[i % 8], 'rights': c.RIGHTS, 'source_url': 'https://freemusicarchive.org/music/synthetic/' + sid}
            body = ('---\n' + ''.join(k + ': ' + json.dumps(v) + '\n' for k, v in fields.items()) + '---\nSynthetic recording evidence.').encode()
            snapshot(rights, body)
            items.append([title, sid + '.mp3', [i % 8], [], page, stream])
            data_items.append({'id': sid, 'title': str(title), 'url': page, 'clips': []})
            rows = {'source_provider': c.PROVIDER, 'source_id': sid, 'title': str(title),
                'contributors': [names[i % 8]], 'source_url': c.SITE + page,
                'upstream_source_url': fields['source_url'], 'download_url': c.BUCKET + stream,
                'rights_id': 'public-domain-dedication', 'rights_snapshot': rights,
                'rights_snapshot_sha256': snapshots[rights], 'priority_sha256': c.priority(sid)}
            self.rows.append(rows)
        snapshot('loc-fma-metadata.json', c.canonical({'itemHeadings': ['title','filename','contributors','subjects','url','stream_url'],
            'items': items, 'groups': {'contributors': names, 'subjects': []}, 'lists': ['contributors','subjects']}))
        snapshot('loc-fma-collection.md', ('---\nuid: "loc-fma"\nitem_rights: ' + json.dumps(c.RIGHTS) + '\n---\n').encode())
        snapshot('loc-fma-data.json', c.canonical({'items': data_items, 'packages': [], 'clips': []}))
        snapshot('loc-config.yml', ('asset_url: ' + json.dumps(c.BUCKET) + '\n').encode())
        snapshot('loc-item-layout.html', b'{{ site.asset_url }}{{ page.stream_url }} {{ page.rights }}')
        self.rows.sort(key=lambda r: (r['priority_sha256'], c.PROVIDER, r['source_id']))
        self.frame = {'schema': 'sonora-holdout-source-frame-v1', 'status': 'source_frame_frozen_not_final_dataset',
            'protocol_sha256': c.PROTOCOL_SHA, 'source_revision': c.REVISION, 'provider': c.PROVIDER,
            'enumeration': 'all132items_in_pinned_official_metadata_no_genre_or_query_filter', 'expected_item_count': 132,
            'priority_seed': c.SEED, 'selection_uses_query_or_model_or_human_relevance': False,
            'rights_statement': c.RIGHTS, 'license_uri_not_inferred': 'No exact CC0 URI inferred',
            'metadata_file': 'loc-fma-metadata.json', 'snapshots': snapshots, 'tracks': self.rows}
        old_evidence = self.root / 'old-evidence.json'
        old_sha = put(old_evidence, {'note': 'Synthetic old metadata only'})
        self.old = {'schema': 'sonora-old-creator-work-exclusion-review-v1',
            'evidence': [{'path': old_evidence.name, 'sha256': old_sha}], 'creator_groups': []}
        for i in range(40):
            self.old['creator_groups'].append({'canonical_creator_name': 'Old creator ' + str(i),
                'creator_comparison_key': 'old creator ' + str(i), 'observed_creator_names': ['Old creator ' + str(i)],
                'proven_aliases': [], 'proven_collaborators': [], 'works': [{'title': 'Old work ' + str(i),
                    'title_comparison_key': 'old work ' + str(i), 'provider': 'old-synthetic', 'source_id': str(i),
                    'content_sha256': c.digest(('old body ' + str(i)).encode()), 'evidence_paths': [old_evidence.name]}]})
        evidence = self.state / 'creator-evidence.txt'
        evidence.write_bytes(b'Synthetic creator identity/work review, no acoustic fingerprinting.'); evidence.chmod(0o600)
        self.groups = {'schema': 'sonora-holdout-group-review-v1', 'source_frame_sha256': '',
            'old_group_review_sha256': '', 'method_version': 'synthetic-metadata-group-test-v1',
            'acoustic_fingerprinting_performed': False, 'evidence': {evidence.name: c.digest(evidence.read_bytes())},
            'records': [{'source_id': row['source_id'], 'decision': 'eligible',
                'creator_group': row['contributors'][0], 'work_group': 'work-' + row['source_id'],
                'reason': 'Synthetic independently reviewed metadata case', 'evidence_paths': [evidence.name]}
                for row in self.rows]}
        self.calls = []
        self.save()

    def save(self):
        self.frame_sha = put(self.frame_path, self.frame)
        self.old_sha = put(self.old_path, self.old)
        self.groups.update(source_frame_sha256=self.frame_sha, old_group_review_sha256=self.old_sha)
        self.groups_sha = put(self.groups_path, self.groups)

    def fetch(self, url, limit):
        self.calls.append(url)
        return b'ID3 synthetic full recording ' + url.encode(), url

    def decode(self, path):
        frames, declared, rate = 48000 * 60, 48000 * 60 + 1024, 48000
        return {'recorded_decode': {'frames': declared, 'sample_rate_hz': rate, 'channels': 2,
            'format': 'MP3', 'duration_ms': declared * 1000 // rate}, 'format': 'MP3', 'source_frames': frames,
            'declared_source_frames': declared, 'source_sample_rate_hz': rate, 'source_channels': 2,
            'sample_rate_hz': 48000, 'decoded_samples': frames, 'duration_ms': 60000,
            'pcm_sha256': c.digest(b'Synthetic PCM ' + path.name.encode()), 'pcm_dtype': 'float32_le',
            'source_decoder_version': c.DECODER}

    def arguments(self):
        return dict(frame=self.frame_path, frame_sha256=self.frame_sha, group_review=self.groups_path,
            group_review_sha256=self.groups_sha, old_group_review=self.old_path, old_group_review_sha256=self.old_sha,
            output=self.output, fetch=self.fetch, decode=self.decode)

    def run_batch(self, **changes):
        args = self.arguments(); args.update(changes)
        return c.run(**args)

    def test_priority_full_source_capture_caps_private_files_and_no_label_fields(self):
        before = {p: p.read_bytes() for p in self.state.rglob('*') if p.is_file()}
        result = self.run_batch()
        manifest = json.loads((self.output / 'manifest.json').read_text())
        self.assertEqual(result['tracks'], 20)
        self.assertEqual((manifest['schema'], manifest['split']), ('sonora-holdout-corpus-v1','independent_test_source_only'))
        tracks = manifest['tracks']
        keys = [hashlib.sha256((c.SEED+'\n'+c.PROVIDER+'\n'+r['source_id']).encode()).hexdigest() for r in tracks]
        self.assertEqual(keys, sorted(keys))
        counts = Counter(r['creator_group'] for r in tracks)
        self.assertGreaterEqual(len(counts),5); self.assertLessEqual(max(counts.values()),4)
        self.assertEqual(len({r['work_group'] for r in tracks}),20)
        for row in tracks:
            self.assertGreater(row['declared_source_frames'],row['source_frames'])
            self.assertEqual(c.digest((self.output/row['audio_filename']).read_bytes()),row['content_sha256'])
            self.assertEqual(c.digest((self.output/row['download_proof_filename']).read_bytes()),row['download_proof_sha256'])
            self.assertFalse({'relevance','annotator','ownerId','musicId','model_score'} & set(row))
        self.assertEqual(manifest['dataset_sha256'],c.digest(c.canonical({k:v for k,v in manifest.items() if k!='dataset_sha256'})))
        self.assertEqual(self.output.stat().st_mode&0o777,0o700)
        self.assertTrue(all(p.stat().st_mode&0o777==0o600 for p in self.output.rglob('*') if p.is_file()))
        self.assertEqual(before,{p:p.read_bytes() for p in before})

    def test_creator_cap_work_versions_and_quarantine_follow_same_queue(self):
        for row in self.groups['records'][:6]: row['creator_group']='shared-cap-group'
        self.groups['records'][6]['work_group']=self.groups['records'][7]['work_group']='shared-work'
        self.groups['records'][8].update(decision='quarantined',creator_group=None,work_group=None)
        self.save(); self.run_batch()
        manifest=json.loads((self.output/'manifest.json').read_text())
        exclusions=json.loads((self.output/'exclusions.json').read_text())
        self.assertEqual(sum(t['creator_group']=='shared-cap-group' for t in manifest['tracks']),4)
        self.assertEqual(sum(t['work_group']=='shared-work' for t in manifest['tracks']),1)
        self.assertTrue({'creator_group_cap4','work_or_version_already_selected','group_quarantined'} <= {r['reason'] for r in exclusions})

    def test_old_creator_overlap_and_old_exact_content_are_excluded(self):
        self.groups['records'][0]['creator_group']='Old creator 0'
        second_url=self.rows[1]['download_url']
        self.old['creator_groups'][0]['works'][0]['content_sha256']=c.digest(self.fetch(second_url,0)[0])
        self.calls.clear(); self.save(); self.run_batch()
        exclusions=json.loads((self.output/'exclusions.json').read_text())
        self.assertTrue({'old_creator_or_work_overlap','old_or_new_exact_content_duplicate'} <= {r['reason'] for r in exclusions})
        self.assertNotIn(self.rows[0]['download_url'],self.calls)

    def test_invalid_first_audio_replaced_by_next_fixed_candidate(self):
        count=[0]
        def decoder(path):
            count[0]+=1
            if count[0]==1:raise ValueError('Synthetic invalid MP3')
            return self.decode(path)
        self.run_batch(decode=decoder)
        self.assertEqual(json.loads((self.output/'exclusions.json').read_text())[0]['reason'],'unsupported_invalid_or_out_of_bounds_actual_audio')
        self.assertTrue((self.output/'audio'/(self.rows[0]['source_id']+'.mp3')).exists())

    def test_network_or_changed_final_identity_aborts_without_replacement(self):
        def broken(url,limit):raise OSError('Synthetic transport failure')
        with self.assertRaises(OSError):self.run_batch(fetch=broken)
        self.assertTrue((self.output/'failure.json').exists());self.assertFalse((self.output/'manifest.json').exists())

    def test_same_source_identity_only_no_alternate_or_samplepack_urls(self):
        url=self.rows[0]['download_url'];sid=self.rows[0]['source_id']
        for changed in (url.replace('https:','http:'),url+'?token=anything',url.replace('/audio/items/','/samplepacks/'),url.replace('s3.amazonaws.com','example.invalid')):
            with self.subTest(url=changed),self.assertRaises(ValueError):c.audio_url(changed,sid)
        with self.assertRaises(ValueError):c.ExactRedirects().redirect_request(Request(url),None,302,'redirect',{},self.rows[1]['download_url'])

    def test_complete_metadata_and_rights_are_rebuilt_not_trusted(self):
        self.frame['tracks'][0]['title']='Changed frozen metadata';self.save()
        with self.assertRaisesRegex(ValueError,'complete reconstructed'):self.run_batch()
        self.assertEqual(self.calls,[]);self.assertFalse(self.output.exists())

    def test_unknown_frame_and_forged_priority_are_rejected_before_fetch(self):
        self.frame['provider']='unknown-provider';self.save()
        with self.assertRaises(ValueError):self.run_batch()
        self.assertEqual(self.calls,[])
        self.frame['provider']=c.PROVIDER;self.frame['tracks'][0]['priority_sha256']='0'*64;self.save()
        with self.assertRaises(ValueError):self.run_batch()

    def test_all_three_explicit_pins_and_source_snapshots_are_required(self):
        for pin in ('frame_sha256','group_review_sha256','old_group_review_sha256'):
            with self.subTest(pin=pin),self.assertRaises(ValueError):self.run_batch(**{pin:None})
        path=self.state/self.rows[0]['rights_snapshot'];path.write_bytes(path.read_bytes()+b'changed')
        with self.assertRaisesRegex(ValueError,'SHA/size'):self.run_batch()
        self.assertEqual(self.calls,[])

    def test_group_review_cannot_omit_identity_or_pinned_evidence(self):
        for field,value in (('creator_group',None),('evidence_paths',[]),('source_id','fma-999999999')):
            original=deepcopy(self.groups['records'][0]);self.groups['records'][0][field]=value;self.save()
            with self.subTest(field=field),self.assertRaises(ValueError):self.run_batch()
            self.groups['records'][0]=original
        self.assertEqual(self.calls,[])

    def test_changed_input_during_failed_decode_aborts_instead_of_skipping(self):
        def corrupt(path):
            self.groups_path.write_bytes(self.groups_path.read_bytes()+b'changed')
            raise ValueError('Synthetic audio failure')
        with self.assertRaisesRegex(ValueError,'evidence changed'):self.run_batch(decode=corrupt)
        self.assertEqual(len(self.calls),1);self.assertFalse((self.output/'manifest.json').exists())

    def test_later_decoder_cannot_change_previously_accepted_audio_or_proof(self):
        for kind in ('audio','proof'):
            calls=[0]
            first=self.rows[0]['source_id']
            output=self.state/('tampered-'+kind)
            def corrupt(path):
                calls[0]+=1
                if calls[0]==2:
                    prior=output/'audio'/(first+('.mp3' if kind=='audio' else '.download.json'))
                    prior.write_bytes(prior.read_bytes()+b'changed')
                return self.decode(path)
            with self.subTest(kind=kind),self.assertRaisesRegex(ValueError,'Previously downloaded'):
                self.run_batch(output=output,decode=corrupt)
            self.assertEqual(calls[0],2)
            self.assertFalse((output/'manifest.json').exists())
            self.assertTrue((output/'failure.json').exists())

    def test_rejected_download_also_remains_bound_against_later_changes(self):
        calls=[0]
        first=self.rows[0]['source_id']
        def corrupt(path):
            calls[0]+=1
            if calls[0]==1:raise ValueError('Synthetic first recording invalid')
            prior=self.output/'audio'/(first+'.mp3')
            prior.write_bytes(prior.read_bytes()+b'changed')
            return self.decode(path)
        with self.assertRaisesRegex(ValueError,'Previously downloaded'):self.run_batch(decode=corrupt)
        self.assertEqual(calls[0],2);self.assertFalse((self.output/'manifest.json').exists())

    def test_actual_decode_numeric_bounds_and_declared_metadata_types(self):
        valid=self.decode(Path('synthetic.mp3'))
        for field,value in (('source_sample_rate_hz',0),('source_frames',48000*29),('source_frames',48000*601),
                             ('decoded_samples',valid['decoded_samples']+1),('format','WAV'),('source_channels',3)):
            info={**valid,field:value}
            with self.subTest(field=field,value=value),self.assertRaises(ValueError):c.validate_decode(info)

    def test_oversized_download_is_retained_as_rejected_and_never_decoded(self):
        for row in self.groups['records'][1:]:row.update(decision='quarantined',creator_group=None,work_group=None)
        self.save()
        with patch.object(c,'MAX_AUDIO',10),patch.object(c,'decode_actual') as decode,self.assertRaises(ValueError):
            self.run_batch(decode=decode)
        decode.assert_not_called()
        proof=json.loads(next((self.output/'audio').glob('*.download.json')).read_text())
        self.assertFalse(proof['download_within_complete_size_bound'])
        self.assertFalse((self.output/'manifest.json').exists())

    def test_insufficient_groups_preserves_partial_and_failure_never_success_manifest(self):
        for row in self.groups['records']:row['creator_group']='one-group'
        self.save()
        with self.assertRaisesRegex(ValueError,'at least five'):self.run_batch()
        partial=json.loads((self.output/'partial.json').read_text())
        self.assertEqual(len(partial['tracks']),4)
        self.assertTrue((self.output/'failure.json').exists());self.assertFalse((self.output/'manifest.json').exists())

    def test_output_reuse_symlink_escape_and_hardlinked_input_are_rejected(self):
        self.output.mkdir(mode=0o700);sentinel=self.output/'sentinel';sentinel.write_bytes(b'keep')
        with self.assertRaises(FileExistsError):self.run_batch()
        self.assertEqual(sentinel.read_bytes(),b'keep');self.assertEqual(self.calls,[])
        with self.assertRaises(ValueError):self.run_batch(output=self.root/'outside')
        link=self.state/'linked';link.symlink_to(self.state,target_is_directory=True)
        with self.assertRaises(ValueError):self.run_batch(output=link/'child')
        os.link(self.frame_path,self.state/'hardlinked-frame.json')
        with self.assertRaisesRegex(ValueError,'hard link'):self.run_batch(output=self.state/'other-run')

    def test_extreme_umask_still_produces_private_files(self):
        previous=os.umask(0o777)
        try:self.run_batch()
        finally:os.umask(previous)
        self.assertEqual(self.output.stat().st_mode&0o777,0o700)
        self.assertTrue(all(p.stat().st_mode&0o777==0o600 for p in self.output.rglob('*') if p.is_file()))

    def test_cli_outputs_aggregate_only_and_takes_no_query_input(self):
        args=self.arguments();args.pop('fetch');args.pop('decode')
        argv=['collect_holdout_music.py']
        for k,v in args.items():argv.extend(['--'+k.replace('_','-'),str(v)])
        out,err=io.StringIO(),io.StringIO()
        with patch.object(sys,'argv',argv),patch.object(c,'fetch_audio',side_effect=self.fetch),patch.object(c,'decode_actual',side_effect=self.decode),redirect_stdout(out),redirect_stderr(err):
            c.main()
        self.assertEqual(err.getvalue(),'');self.assertEqual(json.loads(out.getvalue())['tracks'],20)
        self.assertNotIn('source_id',out.getvalue());self.assertNotIn('title',out.getvalue())


if __name__=='__main__':unittest.main()
