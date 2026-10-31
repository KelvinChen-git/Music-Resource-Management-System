"""Synthetic tagged-library isolation and weak-label semantics, no real music or labels."""
from copy import deepcopy
import hashlib,json,unittest
import mtg_dataset as m


class MetadataTest(unittest.TestCase):
    def fixture(self):
        header='TRACK_ID\tARTIST_ID\tALBUM_ID\tPATH\tDURATION\tTAGS\n'
        rows={i:f'track_{i}\tartist_{i}\talbum_{i}\t{i%100:02}/{i}.mp3\t60.0\tgenre---ambient\tinstrument---piano\n' for i in range(1,29)}
        raw={'base':(header+''.join(rows.values())).encode()}
        for name,ids in [('train',range(1,25)),('validation',range(25,27)),('test',range(27,29))]:raw[name]=(header+''.join(rows[i]for i in ids)).encode()
        raw['names']=('TRACK_ID\tARTIST_ID\tALBUM_ID\tTRACK_NAME\tARTIST_NAME\tALBUM_NAME\tRELEASEDATE\tURL\n'+''.join(f'track_{i}\tartist_{i}\talbum_{i}\tTrack {i}\tCreator{i}\tAlbum{i}\t2020\thttps://example.org\n'for i in rows)).encode()
        raw['licenses']='\n\n'.join(f'{i%100:02}/{i}.mp3\nCredit{i}\nLicense: https://creativecommons.org/licenses/by/4.0/'for i in rows).encode()
        raw['audio_sha256']='\n'.join(hashlib.sha256(str(i).encode()).hexdigest()+f' {i%100:02}/{i}.low.mp3'for i in rows).encode()
        old=[{'sourceId':str(9000+i),'sourceProvider':'jamendo','artist':f'OldCreator{i}','title':f'OldTitle{i}','sha256':hashlib.sha256(f'old{i}'.encode()).hexdigest()}for i in range(40)]
        new=[{'contributors':[f'HoldCreator{i}'],'imported_metadata':{'artist':f'HoldCreator{i}'},'title':f'HoldTitle{i}','content_sha256':hashlib.sha256(f'hold{i}'.encode()).hexdigest()}for i in range(20)]
        raw['prior40']=json.dumps({'audioTracks':old}).encode();raw['prior20']=json.dumps({'tracks':new}).encode()
        raw['sdd']=b'track_id,artist_id,caption\n9999,9999,This text must not enter model input\n'
        policy={'revision':m.REVISION,'seed':m.SEED,'preflight_tracks':20,'per_artist_cap':1,'allowed_audio_license_families':['by','by-sa'],'expected_split_counts':{'train':24,'validation':2,'test':2},'expected_tag_count':2}
        return raw,policy

    def test_deterministic_twenty_distinct_artists_train_only(self):
        raw,p=self.fixture();a=m.build(raw,p);b=m.build(raw,p)
        self.assertEqual(a,b);self.assertEqual(a['summary']['selected_artist_ids'],20)
        self.assertTrue(all(r['official_split']=='train' and int(r['source_track_id'].split('_')[-1])<=24 for r in a['selected']))
        self.assertEqual([r['priority_sha256']for r in a['selected']],sorted(r['priority_sha256']for r in a['selected']))

    def test_missing_tags_are_unknown_and_text_only_repeats_present_tags(self):
        raw,p=self.fixture();a=m.build(raw,p)
        for r in a['selected']:
            self.assertEqual(r['unobserved_tags'],'unknown_not_confirmed_negative')
            self.assertEqual(r['text_en'],'Music tagged with genre: ambient; instrument: piano.')
            self.assertNotIn('caption',r)

    def test_label_or_identity_drift_in_split_rejected(self):
        for before,after in [(b'genre---ambient',b'genre---jazz'),(b'artist_1\t',b'artist_99\t')]:
            raw,p=self.fixture();raw['train']=raw['train'].replace(before,after,1)
            with self.assertRaises(ValueError):m.build(raw,p)

    def test_artist_leakage_between_splits_rejected(self):
        raw,p=self.fixture()
        for key in ('base','validation'):raw[key]=raw[key].replace(b'artist_25\t',b'artist_1\t')
        with self.assertRaisesRegex(ValueError,'leakage'):m.build(raw,p)

    def test_prior_source_id_blocks_known_creator_group(self):
        raw,p=self.fixture();old=json.loads(raw['prior40']);old['audioTracks'][0]['sourceId']='1';raw['prior40']=json.dumps(old).encode()
        a=m.build(raw,p);self.assertTrue(all(r['artist_id']!='artist_1'for r in a['selected']))
        self.assertEqual(a['summary']['known_prior_source_matches'],1)

    def test_normalized_creator_and_work_names_excluded(self):
        raw,p=self.fixture();old=json.loads(raw['prior40']);old['audioTracks'][0].update(artist='ＣＲＥＡＴＯＲ１',title='Track-2');raw['prior40']=json.dumps(old).encode()
        a=m.build(raw,p);self.assertTrue(all(r['source_track_id'] not in ('track_1','track_2')for r in a['selected']))

    def test_reserved_sdd_author_not_just_recording_excluded(self):
        raw,p=self.fixture();raw['sdd']=b'track_id,artist_id,caption\n9999,1,ignored\n';a=m.build(raw,p)
        self.assertTrue(all(r['artist_id']!='artist_1'for r in a['selected']))

    def test_unknown_nc_nd_and_artlibre_licenses_never_rewritten_to_by(self):
        for uri in [b'https://creativecommons.org/licenses/by-nc/4.0/',b'https://creativecommons.org/licenses/by-nd/4.0/',b'http://artlibre.org/licence/lal/',b'https://example.org/unknown']:
            raw,p=self.fixture();raw['licenses']=raw['licenses'].replace(b'https://creativecommons.org/licenses/by/4.0/',uri,1)
            a=m.build(raw,p);self.assertTrue(all(r['source_track_id']!='track_1'for r in a['selected']))
            self.assertEqual(a['summary']['exclusion_reasons_nonexclusive']['audio_license_outside_policy'],1)

    def test_literal_quotes_preserved_and_bad_tab_rows_quarantined(self):
        raw,p=self.fixture();raw['names']=raw['names'].replace(b'Track 1\t',b'"Quoted track 1"\t',1).replace(b'Track 2\t',b'Bad\tTab\t',1)
        meta,bad=m.names(raw['names']);self.assertEqual(meta['track_1']['title'],'"Quoted track 1"');self.assertEqual(bad,['track_2'])
        a=m.build(raw,p);self.assertEqual(a['summary']['raw_name_records_quarantined'],1)

    def test_bad_path_duplicate_or_nonfinite_duration_rejected(self):
        for before,after in [(b'01/1.mp3',b'../1.mp3'),(b'60.0',b'nan'),(b'track_2\t',b'track_1\t')]:
            raw,p=self.fixture();raw['base']=raw['base'].replace(before,after,1)
            with self.assertRaises(ValueError):m.build(raw,p)

    def test_insufficient_eligible_distinct_artists_fails_closed(self):
        raw,p=self.fixture();raw['licenses']=raw['licenses'].replace(b'https://creativecommons.org/licenses/by/4.0/',b'https://creativecommons.org/licenses/by-nd/4.0/',5)
        with self.assertRaisesRegex(ValueError,'Insufficient'):m.build(raw,p)

    def test_metadata_duration_filter_does_not_relabel_or_substitute_audio(self):
        raw,p=self.fixture()
        for k in ('base','train'):raw[k]=raw[k].replace(b'60.0',b'700.0',1)
        a=m.build(raw,p);self.assertEqual(a['summary']['exclusion_reasons_nonexclusive']['metadata_duration_outside_bounds'],1)
        self.assertTrue(all(r['source_track_id']!='track_1'for r in a['selected']))

    def test_audio_hash_duplicate_prior_content_excluded(self):
        raw,p=self.fixture();old=json.loads(raw['prior40']);old['audioTracks'][0]['sha256']=hashlib.sha256(b'1').hexdigest();raw['prior40']=json.dumps(old).encode()
        a=m.build(raw,p);self.assertTrue(all(r['source_track_id']!='track_1'for r in a['selected']))


if __name__=='__main__':unittest.main()
