import json
from pathlib import Path
import tempfile
import unittest

import numpy as np
import soundfile as sf

from corpus import checked_assets, canonical_license, decode_mono, file_hash, window_bounds, unit_vectors, rank_segments


class CorpusTest(unittest.TestCase):
    def test_exact_short_and_tail_boundaries(self):
        for seconds, expected in [(4, [(0,4)]), (10, [(0,10)]),
                (12, [(0,10),(5,12)]), (15, [(0,10),(5,15)]),
                (16, [(0,10),(5,15),(10,16)])]:
            with self.subTest(seconds=seconds):
                self.assertEqual(window_bounds(seconds*48000), [(a*48000,b*48000) for a,b in expected])
        self.assertEqual(len(window_bounds(180*48000)),35)

    def test_fractional_end_is_covered_once_without_empty_tail(self):
        for count in [1, 480001, 720001, 8640017]:
            bounds=window_bounds(count)
            self.assertEqual(bounds[-1][1],count)
            self.assertTrue(all(0<=a<b<=count and b-a<=480000 for a,b in bounds))
            self.assertEqual(len(bounds),len(set(bounds)))
            self.assertTrue(all(bounds[i][0]-bounds[i-1][0]==240000 for i in range(1,len(bounds))))

    def test_invalid_sample_counts(self):
        for count in [0,-1,1.1,True]:
            with self.subTest(count=count),self.assertRaises(ValueError):window_bounds(count)

    def test_actual_wav_decode_downmix_resample_and_repeat(self):
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary)/'stereo.wav'
            sf.write(path,np.column_stack((np.full(44100,.2),np.full(44100,.6))),44100,subtype='FLOAT')
            samples,info=decode_mono(path)
            repeat,again=decode_mono(path)
            self.assertEqual(info['source_channels'],2)
            self.assertEqual(info['decoded_samples'],48000)
            self.assertEqual(info['duration_ms'],1000)
            self.assertEqual(samples.dtype,np.float32)
            np.testing.assert_allclose(samples[100:-100],.4,atol=1e-5)
            np.testing.assert_array_equal(samples,repeat)
            self.assertEqual(info,again)

    def test_fractional_wav_and_short_tail(self):
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary)/'short.wav'
            sf.write(path,np.zeros(44101,dtype=np.float32),44100,subtype='FLOAT')
            samples,info=decode_mono(path)
            self.assertEqual(len(samples),48002)
            self.assertEqual(window_bounds(len(samples)),[(0,48002)])

    def test_invalid_empty_nonfinite_multichannel_and_corrupt_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary)/'bad.wav'
            for samples in [np.zeros(0),np.full(100,np.nan),np.zeros((100,3)),np.zeros(1)]:
                sf.write(path,samples,48000,subtype='FLOAT')
                with self.assertRaises((ValueError,RuntimeError)):decode_mono(path)
            path.write_bytes(b'not an audio file')
            with self.assertRaises((ValueError,RuntimeError)):decode_mono(path)

    def test_vector_validation_and_normalization(self):
        np.testing.assert_allclose(unit_vectors([[3,4],[0,2]]),[[.6,.8],[0,1]],atol=1e-6)
        for value in [[],[1,2],[[0,0]],[[float('nan'),1]],[[float('inf'),1]]]:
            with self.subTest(value=value),self.assertRaises(ValueError):unit_vectors(value)

    def test_track_max_score_overlap_suppression_and_stable_ties(self):
        segments=[{'track_id':'2','start_sample':0,'end_sample':100},
                  {'track_id':'1','start_sample':0,'end_sample':100},
                  {'track_id':'1','start_sample':10,'end_sample':100},
                  {'track_id':'1','start_sample':100,'end_sample':200}]
        ranked=rank_segments([.8,.8,.7,.6],segments)
        self.assertEqual([r['track_id'] for r in ranked],['1','2'])
        self.assertEqual([s['start_sample'] for s in ranked[0]['segments']],[0,100])
        with self.assertRaises(ValueError):rank_segments([1],segments)

    def test_at_most_three_segments_per_track_and_top_k_tracks(self):
        segments=[{'track_id':str(i//5+1),'start_sample':(i%5)*100,'end_sample':(i%5+1)*100} for i in range(20)]
        results=rank_segments(np.arange(20),segments,top_k=2)
        self.assertEqual(len(results),2)
        self.assertTrue(all(len(r['segments'])==3 for r in results))

    def fixture(self, root):
        audio=root/'12.mp3';audio.write_bytes(b'controlled fixture bytes')
        track={'sourceId':'12','musicId':42,'sha256':file_hash(audio),'sourceUrl':'https://www.jamendo.com/track/12',
               'licenseUrl':'https://creativecommons.org/licenses/by/3.0/','title':'Fixture','artist':'Synthetic','durationSeconds':90}
        proof={'source':track['sourceUrl'],'license':'http://creativecommons.org/licenses/by/3.0/',
               'sha256':track['sha256'],'size':audio.stat().st_size}
        (root/'12.download.json').write_text(json.dumps(proof))
        catalog=root/'catalog.json';catalog.write_text(json.dumps({'audioTracks':[track]}))
        return catalog,track,proof

    def test_recorded_manifest_hashes_and_license_proof_match(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);catalog,_,_=self.fixture(root)
            assets=checked_assets(catalog,root)
            self.assertEqual(assets[0]['track_id'],'42')
            self.assertEqual(assets[0]['license_url'],'https://creativecommons.org/licenses/by/3.0/')
            self.assertNotIn(str(root),json.dumps(assets))

    def test_changed_audio_or_download_proof_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);catalog,_,proof=self.fixture(root)
            (root/'12.mp3').write_bytes(b'changed')
            with self.assertRaises(ValueError):checked_assets(catalog,root)
            catalog,_,proof=self.fixture(root);proof['size']+=1
            (root/'12.download.json').write_text(json.dumps(proof))
            with self.assertRaises(ValueError):checked_assets(catalog,root)

    def test_duplicate_identity_and_path_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);catalog,track,_=self.fixture(root)
            catalog.write_text(json.dumps({'audioTracks':[track,track]}))
            with self.assertRaises(ValueError):checked_assets(catalog,root)
            track['sourceId']='../12';catalog.write_text(json.dumps({'audioTracks':[track]}))
            with self.assertRaises(ValueError):checked_assets(catalog,root)

    def test_symlink_escape_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);catalog,_,_=self.fixture(root)
            outside=root.parent/(root.name+'-outside')
            try:
                outside.write_bytes(b'outside');(root/'12.mp3').unlink();(root/'12.mp3').symlink_to(outside)
                with self.assertRaises(ValueError):checked_assets(catalog,root)
            finally:outside.unlink(missing_ok=True)

    def test_recorded_license_url_must_be_exact_cc_by(self):
        for value in ['https://creativecommons.org.evil.test/licenses/by/3.0/',
                'https://creativecommons.org/licenses/by-nc/3.0/','https://user@creativecommons.org/licenses/by/3.0/',
                'https://creativecommons.org/licenses/by/3.0/?token=fixture']:
            with self.subTest(value=value),self.assertRaises(ValueError):canonical_license(value)


if __name__=='__main__':unittest.main()
