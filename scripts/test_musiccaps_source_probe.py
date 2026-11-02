"""Synthetic identity, provenance, access and unknown-rights boundaries; no live network."""
from pathlib import Path
import csv,io,json,tempfile,unittest,hashlib
from unittest.mock import patch
import musiccaps_source_probe as s
import probe_musiccaps_sources as r

class MusicCapsSourceTests(unittest.TestCase):
    def body(self,tid='abcdefghijk',**kw):
        v={'type':'video','provider_name':'YouTube','provider_url':'https://www.youtube.com/',
           'title':'Some music','author_name':'Uploader','author_url':'https://www.youtube.com/@uploader',
           'html':f'<iframe src="https://www.youtube.com/embed/{tid}?feature=oembed"></iframe>'};v.update(kw);return json.dumps(v).encode()
    def fixture(self):
        out=io.StringIO();writer=csv.writer(out)
        writer.writerow(['ytid','start_s','end_s','audioset_positive_labels','aspect_list','caption','author_id','is_balanced_subset','is_audioset_eval'])
        frame=[]
        for i in range(5521):
            tid=f'v{i:010}';writer.writerow([tid,10,20,'unused','UNINSPECTED','DO NOT READ CAPTION',0,False,i>=2663])
            if i<2448:frame.append({'source_video_id':tid,'start_s':10,'end_s':20,'unaugmented_location':f'data/{tid}.wav'})
        f={'count':2448,'rows':frame,'audio_ready':0,'artist_work_isolation_verified':False};e={'private_evidence_sha256':{'musiccaps-provisional-frame.json':'a'*64}}
        return out.getvalue().encode(),f,e
    def test_original5521_2448_metadata_binding_never_exports_captions_or_writer_ids(self):
        a,b,c=self.fixture();values,flags=s.project(a,b,c,'a'*64)
        self.assertEqual(flags,{'AudioSet_train':2663,'AudioSet_eval':2858});self.assertEqual(len(values),2448)
        self.assertNotIn('CAPTION',str(values));self.assertNotIn('author_id',str(values))
    def test_wrong_frame_pin_eval_flag_or_augmented_path_rejected(self):
        for case in ['pin','eval','aug','time']:
            a,b,c=self.fixture()
            if case=='pin':c['private_evidence_sha256']['musiccaps-provisional-frame.json']='b'*64
            elif case=='eval':b['rows'][0]['source_video_id']='v0000003000'
            elif case=='aug':b['rows'][0]['unaugmented_location']='data/v0000000000_1.wav'
            else:b['rows'][0]['end_s']=21
            with self.assertRaises(ValueError):s.project(a,b,c,'a'*64)
    def test_fixed_hash_selection_is_deterministic_and_order_independent(self):
        a,b,c=self.fixture();values,_=s.project(a,b,c,'a'*64);picked=s.select(values)
        self.assertEqual(picked,s.select(list(reversed(values))));self.assertEqual(len(picked),20)
        self.assertEqual(picked,sorted(values,key=lambda v:hashlib.sha256((s.SEED+'\n'+v['source_video_id']).encode()).hexdigest())[:20])
        with self.assertRaises(ValueError):s.select(values,seed='different')
    def test_oembed_video_binding_and_uploader_are_only_metadata(self):
        value=s.classify('abcdefghijk',200,'application/json; charset=utf-8',self.body())
        self.assertTrue(value['oembed_metadata_available']);self.assertEqual(value['media_license'],'unknown')
        self.assertFalse(value['audio_ready']or value['training_ready']);self.assertEqual(value['music_artist_work_identity'],'unverified')
    def test_CC_title_arbitrary_license_and_licensedContent_do_not_grant_rights(self):
        for kw in [{'title':'CC BY royalty free'},{'license':'creativeCommon'},{'licensedContent':False},{'embeddable':True}]:
            value=s.classify('abcdefghijk',200,'application/json',self.body(**kw));self.assertEqual(value['media_license'],'unknown');self.assertFalse(value['training_ready'])
    def test_wrong_video_or_provider_is_not_available_metadata(self):
        for raw in [self.body('differentid'),self.body(provider_name='Fake'),self.body(author_url='https://evil.example/a'),self.body(html='<script>bad()</script>')]:
            self.assertFalse(s.classify('abcdefghijk',200,'application/json',raw)['oembed_metadata_available'])
    def test_HTML_consent_or_invalid_JSON_not_marked_available(self):
        for kind,raw in [('text/html',b'consent'),('application/json',b'bad json'),('application/json',b'[]')]:
            self.assertFalse(s.classify('abcdefghijk',200,kind,raw)['oembed_metadata_available'])
    def test_HTTP404_does_not_mean_media_is_proven_unavailable(self):
        v=s.classify('abcdefghijk',404,'text/plain',b'Not found');self.assertEqual(v['outcome'],'http_404');self.assertEqual(v['media_accessibility'],'unmeasured')
    def test_network_error_not_recording_unavailability(self):
        v=s.classify('abcdefghijk',None,'',b'',{'type':'TimeoutError'});self.assertEqual(v['outcome'],'transport_error');self.assertEqual(v['media_license'],'unknown')
    def test_access_stop_conditions_differ_from_ordinary404(self):
        for code in [401,403,429,500,503]:self.assertTrue(s.stop_error(code,None))
        for code in [200,400,404]:self.assertFalse(s.stop_error(code,None))
        self.assertTrue(s.stop_error(None,{'type':'network'}))
    def test_exact_oembed_URL_has_no_media_download_path_or_key(self):
        url=s.url('abcdefghijk');self.assertTrue(url.startswith('https://www.youtube.com/oembed?'));self.assertNotIn('key=',url)
        with self.assertRaises(ValueError):s.url('../bad')
    def test_redirects_are_never_followed(self):
        self.assertIsNone(r.NoRedirect().redirect_request(None,None,302,'',None,'https://elsewhere.invalid/'))
    def test_task_claim_blocks_before_any_new_output(self):
        cfg=json.loads(Path('docs/evaluation/MUS-066-source-config.json').read_text())
        with tempfile.TemporaryDirectory()as tmp:
            root=Path(tmp).resolve();task=root/cfg['task_directory'];task.mkdir(parents=True);(task/'probe-started.json').write_text('{}')
            with patch.object(r,'ROOT',root),patch.object(r.h.assets,'document',return_value=cfg):
                with self.assertRaisesRegex(ValueError,'already attempted'):r.run(root/'cfg','0'*64,task/'new')
            self.assertFalse((task/'new').exists())
    def test_protocol_forbids_more_probes_data_API_or_audio(self):
        cfg=json.loads(Path('docs/evaluation/MUS-066-source-config.json').read_text())
        for key,value in [('probe_count',40),('call_data_api',True),('redirects',True),('operations',{'audio_downloads':1}),('documents',{'unexpected':'https://elsewhere.invalid/'})]:
            with self.assertRaises(ValueError):r.validate({**cfg,key:value})

if __name__=='__main__':unittest.main()
