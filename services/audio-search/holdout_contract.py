"""Read-only independent-test inputs, source commitments and private outputs (stdlib only)."""
from datetime import datetime, timezone
import hashlib
from importlib.metadata import distribution, version
import json
import os
from pathlib import Path
import platform
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import holdout_assets as assets
import review_pack as rp

require, canonical, digest = rp.require, rp.canonical, rp.digest
PROTOCOL_SHA = '83bc7bf3f00a91634a56fd269daaf6720192c19507860ddff9df33c3063de63b'
QUERY_SHA = '6b3af0cc99ab0bde1d1d27b88e5f477e44f627948ffd69183ec421bad185cbfb'
CONFIG_SHA = '8c91b0da29aea117d0ab174397f61adf727e70e46c4cc54b91689e8a8d45db38'
CONFIG_PATH = 'docs/evaluation/MUS-040-runtime-config.json'
QUERY_PATH = 'docs/evaluation/MUS-039-queries-v2.json'
SCHEMA = 'sonora-independent-review-pack-v1'
PINS = {
    'A': ('music_audioset_epoch_15_esc_90.14.pt', 2352471003,
          'fae3e9c087f2909c28a09dc31c8dfcdacbc42ba44c70e972b58c1bd1caf6dedd'),
    'B': ('music_speech_audioset_epoch_15_esc_89.98.pt', 2352471003,
          '51c68f12f9d7ea25fdaaccf741ec7f81e93ee594455410f3bca4f47f88d8e006')}
SOURCE_FILES = [*(f'services/audio-search/{n}.py' for n in [
    'holdout_contract','holdout_runner','holdout_review','checkpoint_model','probe','corpus',
    'preprocess','research_corpus','research_probe','review_pack','source_review_pack']),
    'scripts/holdout_assets.py','scripts/collect_holdout_music.py','scripts/import_demo_music.py',
    'scripts/baseline.py','scripts/dev.py',
    'web/src/utils/reviewPack.js','web/src/utils/reviewAudio.js','web/src/views/ReviewWorkspace.vue',
    'web/package-lock.json',CONFIG_PATH,QUERY_PATH,'docs/evaluation/MUS-039-protocol-v2.json']
PACKAGES = ['laion-clap','torch','numpy','librosa','soundfile','soxr','transformers','numba','tokenizers']


def file_hash(path):
    h = hashlib.sha256()
    with assets.regular(path).open('rb') as f:
        for block in iter(lambda:f.read(8*1024*1024),b''):h.update(block)
    return h.hexdigest()


def now():return datetime.now(timezone.utc).isoformat()


def private_output(path):
    path=Path(path).absolute();local=ROOT/'.local'
    require(local.is_dir() and not any(p.is_symlink() for p in (path,*path.parents))
        and path.resolve().is_relative_to(local.resolve()) and path.resolve()!=local.resolve()
        and path.parent.is_dir(),'Private output must remain below existing ignored .local')
    require(subprocess.run(['git','check-ignore','--quiet','--no-index',str(path)],cwd=ROOT).returncode==0,
        'Output must be ignored')
    path.mkdir(mode=0o700);path.chmod(0o700)
    return path


def write_json(path,value):
    raw=(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode()
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    os.fchmod(fd,0o600)
    with os.fdopen(fd,'wb') as f:f.write(raw)


def source_state(clean=True):
    sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    if clean:require(not subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip(),
                     'Committed clean source required')
    hashes={name:file_hash(ROOT/name) for name in SOURCE_FILES}
    for name,h in hashes.items():
        require(digest(subprocess.check_output(['git','show',sha+':'+name],cwd=ROOT))==h,
                'Source differs from committed tree')
    return {'code_sha':sha,'source_sha256':hashes}


def environment():
    """Bind installed ML packages' code/config bytes without importing the SDK."""
    entries={}
    for name in PACKAGES:
        d=distribution(name)
        for item in d.files or []:
            if item.suffix in ('.py','.json','.so','.dylib','.pyd') and '..' not in item.parts:
                p=d.locate_file(item)
                if p.is_file() and not p.is_symlink():entries[name+':'+str(item)]=file_hash(p)
    cache=Path(os.environ.get('HF_HUB_CACHE', Path(os.environ.get('HF_HOME', Path.home()/'.cache/huggingface'))/'hub'))
    cached={str(p.absolute()):file_hash(p) for p in cache.rglob('*') if p.is_file() and not p.is_symlink()}
    require(cached,'Offline model cache must already exist')
    return {'offline_cache_sha256':cached,'python':platform.python_version(),'system':platform.system(),'machine':platform.machine(),
        'device':'cpu','threads':2,'packages':{n:version(n) for n in PACKAGES},
        'installed_code_config_sha256':digest(canonical(entries)),'installed_files':len(entries)}


def checkpoint_pin(path,model):
    path=assets.regular(path);name,size,h=PINS[model]
    require(path.name==name and path.stat().st_size==size and file_hash(path)==h,
            'Checkpoint differs from preregistered bytes')
    return {'path':str(path),'filename':name,'bytes':size,'sha256':h}


def snapshot(*,binding,binding_sha256,catalog,catalog_sha256,audio_root):
    context=assets.checked_source(binding,binding_sha256)
    cat=assets.document(catalog,catalog_sha256)
    tracks=assets.validate_catalog(cat,context,audio_root)
    config=assets.document(ROOT/CONFIG_PATH,CONFIG_SHA)
    queries=assets.document(ROOT/QUERY_PATH,QUERY_SHA)
    require(config['schema']=='sonora-independent-runtime-config-v1' and config['protocol_sha256']==PROTOCOL_SHA
        and config['query_manifest_sha256']==QUERY_SHA and config['tracks']==20 and config['queries']==8
        and config['pairs']==160 and config['dimension']==512,'Unexpected fixed runtime config')
    require(queries['protocol_sha256']==PROTOCOL_SHA and queries['source_frame_sha256']==context['binding']['frame']['sha256']
        and queries['source_corpus_freeze_receipt_sha256']==context['binding']['source_freeze']['sha256']
        and [q['query_key'] for q in queries['queries']]==[f'holdout-{i:02}' for i in range(1,9)],
        'Query manifest differs from G1 freeze')
    hashes={str(p.absolute()):h for p,h in context['hashes'].items()}
    for p in [Path(catalog),ROOT/CONFIG_PATH,ROOT/QUERY_PATH]:hashes[str(p.absolute())]=file_hash(p)
    for t in tracks:
        for name in ['asset_filename','proof_filename']:
            p=Path(audio_root)/t[name];hashes[str(p.absolute())]=file_hash(p)
    assets.recheck({Path(p):h for p,h in hashes.items()})
    args={'binding':str(Path(binding).absolute()),'binding_sha256':binding_sha256,
        'catalog':str(Path(catalog).absolute()),'catalog_sha256':catalog_sha256,
        'audio_root':str(Path(audio_root).absolute())}
    return {'arguments':args,'catalog':cat,'tracks':tracks,'queries':queries['queries'],
        'config':config,'input_sha256':hashes,'source_dataset_sha256':context['manifest']['dataset_sha256']}


def checked_freeze(path,sha256,verify_environment=False):
    f=assets.document(path,sha256)
    require(f.get('schema')=='sonora-independent-runner-freeze-v1' and f.get('status')=='frozen_before_test_inference'
        and f.get('counts')=={'new_test_audio_encoded':0,'new_test_text_encoded':0,'qrels_opened':0},
        'Completed G2 receipt required')
    data=snapshot(**f['arguments'])
    require(data['input_sha256']==f['input_sha256'] and data['source_dataset_sha256']==f['source_dataset_sha256'],
        'Frozen input set changed')
    require(set(f['source']['source_sha256'])==set(SOURCE_FILES),'Incomplete frozen source set')
    for name,h in f['source']['source_sha256'].items():require(file_hash(ROOT/name)==h,'Frozen source changed')
    require(set(f['models'])=={'A','B'},'Both frozen models required')
    for key,model in f['models'].items():
        require(checkpoint_pin(model['pin']['path'],key)==model['pin']
            and model['audio_shape']==[1,512] and model['text_shape']==[1,512]
            and model['strict']['strict_missing']==[] and model['strict']['strict_unexpected']==[]
            and len(model['test_query_token_lengths'])==8
            and all(type(n) is int and 0<n<=77 for n in model['test_query_token_lengths']), 'Incomplete strict model preflight')
    if verify_environment:require(environment()==f['environment'],'Frozen environment changed')
    require(file_hash(path)==sha256,'G2 receipt changed')
    return f,data
