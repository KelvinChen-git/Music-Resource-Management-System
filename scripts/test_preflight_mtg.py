"""Synthetic bounded transport responses; never network or real audio."""
import io,unittest,hashlib
import preflight_mtg as p


class Response(io.BytesIO):
    def __init__(self,raw,start,end,total,validator='"stable"',status=206):
        super().__init__(raw);self.status=status;self.url='https://cdn.freesound.org/mtg-jamendo/raw_30s/audio-low/01/1.low.mp3'
        self.headers={'Content-Range':f'bytes {start}-{end}/{total}','Content-Length':str(end-start+1),'ETag':validator}
    def __enter__(self):return self
    def __exit__(self,*args):self.close()


class Opener:
    def __init__(self, responses): self.responses=iter(responses);self.requests=[]
    def open(self,req,timeout):self.requests.append(req);return next(self.responses)


class TransportTest(unittest.TestCase):
    def fixture(self,second_validator='"stable"',bad_hash=False):
        raw=b'fake-bounded-audio-bytes';n=len(raw)
        opener=Opener([Response(raw[:1],0,0,n),Response(raw,0,n-1,n,second_validator)])
        track={'low_path':'01/1.low.mp3','audio_sha256':hashlib.sha256(raw).hexdigest() if not bad_hash else '0'*64}
        policy={'audio_base_url':'https://cdn.freesound.org/mtg-jamendo/raw_30s/audio-low/','max_track_bytes':100}
        return raw,opener,track,policy

    def test_two_bounded_ranges_match_official_SHA_and_stable_validator(self):
        raw,o,t,c=self.fixture();budget=p.Budget(200,10);got,proof=p.fetch_one(o,t,c,budget)
        self.assertEqual(got,raw);self.assertEqual(budget.used,10+1+len(raw));self.assertTrue(proof['official_sha_matched'])
        self.assertEqual(o.requests[0].headers['Range'],'bytes=0-0');self.assertEqual(o.requests[1].headers['If-range'],'"stable"')

    def test_wrong_official_hash_rejected(self):
        raw,o,t,c=self.fixture(bad_hash=True)
        with self.assertRaisesRegex(ValueError,'SHA'):p.fetch_one(o,t,c,p.Budget(200))

    def test_changed_validator_rejected_before_audio_body(self):
        raw,o,t,c=self.fixture(second_validator='"changed"');b=p.Budget(200)
        with self.assertRaisesRegex(ValueError,'representation'):p.fetch_one(o,t,c,b)
        self.assertEqual(b.used,1)

    def test_whole_response_or_wrong_range_or_gzip_rejected(self):
        good={'Content-Range':'bytes 0-0/100','Content-Length':'1'}
        for status,h in [(200,good),(206,dict(good,**{'Content-Range':'bytes 1-1/100'})),(206,dict(good,**{'Content-Encoding':'gzip'})),(206,dict(good,**{'Content-Length':'2'}))]:
            with self.assertRaises(ValueError):p.range_total(status,h,0,0)

    def test_global_budget_prevents_read_instead_of_partial_acceptance(self):
        stream=io.BytesIO(b'abcdef');b=p.Budget(3)
        with self.assertRaises(ValueError):b.read(stream,4)
        self.assertEqual(stream.tell(),0);self.assertEqual(b.used,0)

    def test_url_blocks_archive_unauthorized_host_escape_and_query(self):
        for url in ['http://cdn.freesound.org/mtg-jamendo/raw_30s/audio-low/01/1.low.mp3','https://example.org/01/1.low.mp3','https://cdn.freesound.org/mtg-jamendo/raw_30s/audio-low/raw_30s_audio-low-00.tar','https://cdn.freesound.org/mtg-jamendo/raw_30s/audio-low/../1.low.mp3','https://cdn.freesound.org/mtg-jamendo/raw_30s/audio-low/01/1.low.mp3?x=1']:
            with self.assertRaises(ValueError):p.official_url(url)

    def test_oversized_track_refused_before_full_body_request(self):
        raw,o,t,c=self.fixture();c['max_track_bytes']=2;b=p.Budget(200)
        with self.assertRaisesRegex(ValueError,'size'):p.fetch_one(o,t,c,b)
        self.assertEqual(len(o.requests),1);self.assertEqual(b.used,0)

    def test_truncated_body_not_saved_as_success(self):
        raw,o,t,c=self.fixture();n=len(raw);o=Opener([Response(raw[:1],0,0,n),Response(raw[:-1],0,n-1,n)])
        with self.assertRaises(ValueError):p.fetch_one(o,t,c,p.Budget(200))


if __name__=='__main__':unittest.main()
