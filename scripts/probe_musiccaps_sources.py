#!/usr/bin/env python3
"""Bounded metadata-only YouTube source probe; no media downloader or model."""
from pathlib import Path
import argparse
from collections import Counter
import json,os,platform,ssl,subprocess,sys
from urllib.error import HTTPError,URLError
from urllib.request import build_opener,HTTPRedirectHandler,HTTPSHandler,Request
import certifi
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'services/audio-search'))
import holdout_contract as h
import musiccaps_source_probe as probe
SOURCES=('scripts/probe_musiccaps_sources.py','services/audio-search/musiccaps_source_probe.py',
         'services/audio-search/holdout_contract.py','services/audio-search/review_pack.py',
         'scripts/holdout_assets.py','scripts/collect_holdout_music.py')


DOCUMENTS={'videos_api':'https://developers.google.com/youtube/data/reference/rest/v3/videos',
 'api_setup':'https://developers.google.com/youtube/data/getting-started',
 'license_help':'https://support.google.com/youtube/answer/2797468?hl=en',
 'terms':'https://www.youtube.com/static?template=terms'}


def validate(c):
    h.require(c['schema']=='sonora-musiccaps-source-probe-v1'and c['task_directory']=='.local/a/mus066'
        and c['selection_seed']==probe.SEED and c['probe_count']==20 and c['per_probe_bytes']==65536
        and c['per_document_bytes']==1048576 and c['body_budget_bytes']==8388608
        and c['stop_after_consecutive_transport_or_access_errors']==3
        and c['redirects'] is False and c['retries']==c['replacements']==0 and c['call_data_api'] is False
        and c['documents']==DOCUMENTS and c['operations']==dict.fromkeys(('audio_downloads','encodes','fits','project_reserved_test_inputs','new_manual_labels','paid_resources'),0),
        'Fixed no-media source-only protocol required')


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):return None


def write_bytes(path,raw):
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'wb')as f:f.write(raw)


def run(config,config_sha256,output):
    c=h.assets.document(config,config_sha256);validate(c);task=ROOT/c['task_directory']
    h.require(Path(output).absolute().is_relative_to(task.absolute())and not(task/'probe-started.json').exists(),
              'Probe already attempted or invalid output; no new-directory retry')
    h.require(not subprocess.check_output(['git','status','--porcelain'],cwd=ROOT).strip(),'Clean committed source required')
    target=h.private_output(output)
    try:
        bound={str(Path(config).absolute()):config_sha256};docs={}
        for key,pin in c['inputs'].items():
            path=ROOT/pin['path'];h.require(h.file_hash(path)==pin['sha256'],'Pinned original source changed')
            bound[str(path.absolute())]=pin['sha256']
            if path.suffix=='.json':docs[key]=h.assets.document(path,pin['sha256'])
        ca=Path(certifi.where()).resolve();bound[str(ca)]=h.file_hash(ca)
        state={'source_sha':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
               'config_sha256':config_sha256,'source_sha256':{n:h.file_hash(ROOT/n)for n in SOURCES},
               'input_sha256':bound,'created_at_utc':h.now(),'runtime':{'python':platform.python_version(),
                'OpenSSL':ssl.OPENSSL_VERSION,'CA_sha256':bound[str(ca)]},'protocol':c,
               'data_api_called':False,'standard_YOUTUBE_API_KEY_present':bool(os.environ.get('YOUTUBE_API_KEY'))}
        h.write_json(target/'freeze.json',state)
        h.write_json(task/'probe-started.json',{'started_at_utc':h.now(),'source_sha':state['source_sha'],
                     'config_sha256':config_sha256,'maximum_attempts_per_URL':1,'output':str(target)})
        values,flags=probe.project(h.assets.read(ROOT/c['inputs']['musiccaps']['path']),docs['frame'],
                                  docs['prior_verification'],c['inputs']['frame']['sha256'])
        selected=probe.select(values);h.write_json(target/'probe-plan.json',{'seed':probe.SEED,'rows':selected,'source_frame_count':len(values)})
        opener=build_opener(NoRedirect(),HTTPSHandler(context=ssl.create_default_context(cafile=str(ca))))
        ledger=task/'network-ledger.jsonl';reserved=0;captured=0
        def fetch(url,name,maximum):
            nonlocal reserved,captured
            h.require(reserved+maximum+1<=c['body_budget_bytes'],'Task body reservation budget exceeded')
            reserved+=maximum+1
            fd=os.open(ledger,os.O_WRONLY|os.O_CREAT|os.O_APPEND|os.O_NOFOLLOW,0o600)
            with os.fdopen(fd,'a')as f:
                f.write(json.dumps({'time':h.now(),'name':name,'url':url,'reserved_before_request':maximum+1})+'\n');f.flush();os.fsync(f.fileno())
            raw=b'';status=None;kind='';error=None
            try:
                try:r=opener.open(Request(url,headers={'User-Agent':'Music-Sonora-source-metadata/1.0'}),timeout=15)
                except HTTPError as e:r=e
                with r:
                    status=r.code;kind=r.headers.get('Content-Type','');raw=r.read(maximum+1)
            except (URLError,TimeoutError,OSError)as e:error={'type':type(e).__name__,'message':str(e)}
            captured+=len(raw);write_bytes(target/(name+'.body'),raw)
            receipt={'url':url,'status':status,'content_type':kind,'bytes':len(raw),'body_sha256':h.digest(raw),
                     'oversize':len(raw)>maximum,'transport_error':error,'normal_TLS':True,'attempts':1}
            h.write_json(target/(name+'.receipt.json'),receipt)
            return receipt,raw
        document_results={}
        for key,url in c['documents'].items():
            receipt,raw=fetch(url,'document-'+key,c['per_document_bytes'])
            document_results[key]={k:receipt[k]for k in ('status','bytes','body_sha256','oversize','transport_error')}
        results=[];consecutive=0;stopped=False
        for i,row in enumerate(selected):
            if stopped:
                results.append({**row,'outcome':'not_attempted_after_access_stop','oembed_metadata_available':False,
                    'media_accessibility':'unmeasured','media_license':'unknown','music_artist_work_identity':'unverified',
                    'audio_ready':False,'training_ready':False});continue
            receipt,raw=fetch(probe.url(row['source_video_id']),f'probe-{i+1:02}',c['per_probe_bytes'])
            result=probe.classify(row['source_video_id'],receipt['status'],receipt['content_type'],raw,receipt['transport_error'])
            if receipt['oversize']:result.update(outcome='oversize_response',oembed_metadata_available=False)
            results.append({**row,**result})
            consecutive=consecutive+1 if probe.stop_error(receipt['status'],receipt['transport_error'])else 0
            stopped=consecutive>=3
        for path,pin in bound.items():h.require(h.file_hash(path)==pin,'Input changed during probe')
        for path,pin in state['source_sha256'].items():h.require(h.file_hash(ROOT/path)==pin,'Probe source changed')
        h.require('torch'not in sys.modules and 'laion_clap'not in sys.modules,'No model imports allowed')
        result={'status':'bounded_source_metadata_probe_complete_not_training_ready','source_sha':state['source_sha'],
            'config_sha256':config_sha256,'source_counts':{'MusicCaps':5521,**flags,'provisional_non_eval_unaugmented':2448},
            'selected_probes':20,'attempted_probes':sum(r['outcome']!='not_attempted_after_access_stop'for r in results),
            'outcomes':dict(Counter(r['outcome']for r in results)),
            'oembed_metadata_available':sum(r['oembed_metadata_available']for r in results),
            'music_artist_work_verified':0,'media_license_verified':0,'actual_audio_verified':0,
            'audio_ready':0,'training_ready':0,'data_api_license_investigation':'blocked_no_authenticated_API_record_in_this_run',
            'data_api_called':False,'documents':document_results,'reserved_body_bytes':reserved,'captured_body_bytes':captured,
            'stopped_after_consecutive_access_errors':stopped,'operations':c['operations'],
            'decision':'do_not_download_MusicCaps_media_or_expand_training_from_unverified_sources',
            'limits':['oEmbed metadata success is not proof of playable or downloadable media, license or artist/work identity.',
                'author_id is caption writer; uploader/channel is not necessarily music creator.',
                'AudioSet split flag is not project train/development/test isolation.',
                '20 fixed candidate probes are not a full5521 availability or rights estimate; no failed-slot replacement.',
                'No MusicCaps caption/body used as a model input, no final test or model-quality claim.']}
        h.write_json(target/'source-evidence-private.json',{'result':result,'rows':results})
        result['source_evidence_sha256']=h.file_hash(target/'source-evidence-private.json')
        h.write_json(target/'result-public.json',result);return result
    except Exception as e:
        h.write_json(target/'failure.json',{'error_type':type(e).__name__,'error':str(e)});raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--config',type=Path,required=True);p.add_argument('--config-sha256',required=True);p.add_argument('--output',type=Path,required=True)
    print(json.dumps(run(**vars(p.parse_args()))))
