"""Separate source metadata accessibility from music rights and actual audio readiness."""
import csv
import hashlib
from html.parser import HTMLParser
import io
import json
import re
from urllib.parse import urlencode, urlsplit
from review_pack import require

SEED = 'MUS-066-MusicCaps-source-probe-v1'


def project(raw, frame, evidence, frame_sha256):
    require(evidence['private_evidence_sha256']['musiccaps-provisional-frame.json'] == frame_sha256
            and frame['count'] == len(frame['rows']) == 2448 and frame['audio_ready'] == 0
            and frame['artist_work_isolation_verified'] is False, 'Original050 provisional frame required')
    reader = csv.DictReader(io.StringIO(raw.decode('utf8')))
    require(reader.fieldnames == ['ytid','start_s','end_s','audioset_positive_labels','aspect_list','caption',
                                  'author_id','is_balanced_subset','is_audioset_eval'], 'Pinned original MusicCaps schema required')
    rows = {}
    flags = {'AudioSet_train':0, 'AudioSet_eval':0}
    for r in reader:
        # Never use caption, aspect_list, labels or author_id for selection/grouping.
        tid = r['ytid']; require(re.fullmatch(r'[A-Za-z0-9_-]{11}', tid) is not None and tid not in rows, 'Unique video IDs required')
        lo, hi = int(r['start_s']), int(r['end_s'])
        require(0 <= lo and hi-lo == 10 and r['is_audioset_eval'] in ('True','False'), 'Original10s AudioSet flag required')
        rows[tid] = {'source_video_id':tid,'start_s':lo,'end_s':hi,'audioset_eval':r['is_audioset_eval']=='True'}
        flags['AudioSet_eval' if rows[tid]['audioset_eval'] else 'AudioSet_train'] += 1
    require(len(rows) == 5521 and flags == {'AudioSet_train':2663,'AudioSet_eval':2858}, 'Original fixed source frame changed')
    candidates = []
    for r in frame['rows']:
        tid = r['source_video_id']; require(tid in rows and not rows[tid]['audioset_eval'], 'No AudioSet-eval probe permitted')
        require(int(r['start_s']) == rows[tid]['start_s'] and int(r['end_s']) == rows[tid]['end_s']
                and r['unaugmented_location'].split('/')[-1] == tid+'.wav', 'Original unaugmented source binding differs')
        candidates.append(rows[tid])
    require(len({r['source_video_id'] for r in candidates}) == 2448, 'Unique2448 candidates required')
    return candidates, flags


def select(rows, seed=SEED, count=20):
    require(seed == SEED and count == 20 and len(rows) == 2448, 'Fixed source-only20 probe required')
    return sorted(rows, key=lambda r: hashlib.sha256((seed+'\n'+r['source_video_id']).encode()).hexdigest())[:count]


def url(tid):
    require(re.fullmatch(r'[A-Za-z0-9_-]{11}',tid) is not None, 'Valid video ID required')
    return 'https://www.youtube.com/oembed?'+urlencode({'url':'https://www.youtube.com/watch?v='+tid,'format':'json'})


class Frames(HTMLParser):
    def __init__(self):super().__init__();self.sources=[]
    def handle_starttag(self,tag,attrs):
        if tag.lower() == 'iframe': self.sources.extend(v for k,v in attrs if k.lower()=='src')


def classify(tid, status, content_type, raw, transport_error=None):
    result = {'source_video_id':tid,'oembed_metadata_available':False,'media_accessibility':'unmeasured',
              'media_license':'unknown','music_artist_work_identity':'unverified',
              'audio_ready':False,'training_ready':False,'status':status}
    if transport_error:result['outcome']='transport_error';return result
    if status != 200:result['outcome']='http_'+str(status);return result
    if content_type.split(';')[0].strip().lower() != 'application/json':
        result['outcome']='unexpected_content_type';return result
    try:
        value = json.loads(raw)
        require(isinstance(value,dict) and value.get('type')=='video' and value.get('provider_name')=='YouTube'
                and value.get('provider_url','').rstrip('/')=='https://www.youtube.com'
                and all(isinstance(value.get(k),str) and value[k] for k in ('title','author_name','author_url','html')),
                'YouTube oEmbed fields required')
        author=urlsplit(value['author_url']);require(author.scheme=='https' and author.netloc in ('youtube.com','www.youtube.com')
            and author.path not in ('','/'), 'YouTube uploader URL required')
        parser=Frames();parser.feed(value['html']);require(len(parser.sources)==1,'One iframe source required')
        video=urlsplit(parser.sources[0]);require(video.scheme=='https' and video.netloc in ('youtube.com','www.youtube.com')
            and video.path=='/embed/'+tid,'Returned video binding differs')
    except (ValueError,TypeError,AttributeError):result['outcome']='invalid_oembed_schema';return result
    result.update(oembed_metadata_available=True,outcome='metadata_available',uploader_url=value['author_url'],
                  uploader_display_name=value['author_name'],title=value['title'],response_video_binding_verified=True)
    # Extra license/embeddable/licensedContent/CC-title fields are deliberately not approval evidence.
    return result


def stop_error(status, error):return bool(error) or status in (401,403,429) or (isinstance(status,int) and status>=500)
