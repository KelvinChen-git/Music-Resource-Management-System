#!/usr/bin/env python3
"""Create explicitly synthetic media/accounts in an EMPTY isolated development DB."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess

from dev import ROOT, read_env, database_query
from make_discovery_fixture import write_fixture


def prepare(slot, mysql, output, java_home, bcrypt_jar):
    config = read_env(slot)
    query = database_query(slot, mysql)
    if query('SELECT COUNT(*) FROM users;') != '0' or query('SELECT COUNT(*) FROM music_resources;') != '0':
        raise RuntimeError('Synthetic bootstrap only accepts an empty isolated development database')
    output = Path(output).absolute()
    if not output.resolve().is_relative_to((ROOT / '.local' / slot).resolve()) or any(p.is_symlink() for p in (output, *output.parents)):
        raise RuntimeError('Fixture output must be private to the selected slot')
    output.mkdir(mode=0o700)
    home = Path(java_home); jar = Path(bcrypt_jar)
    if not (home / 'bin/java').is_file() or not jar.is_file() or not shutil.which('ffmpeg') or not shutil.which('ffprobe'):
        raise RuntimeError('Existing full JDK, jbcrypt jar and ffmpeg/ffprobe are required; no downloads are performed')
    prior = os.umask(0o077)
    try:
        helper = output / 'HashFixture.java'
        helper.write_text('class HashFixture { public static void main(String[] a) { System.out.print(org.mindrot.jbcrypt.BCrypt.hashpw(System.getenv("FIXTURE_PASSWORD"),org.mindrot.jbcrypt.BCrypt.gensalt())); } }\n')
        password = 'Aa1!' + secrets.token_urlsafe(20)
        result = subprocess.run([str(home / 'bin/java'), '--class-path', str(jar), str(helper)],
                                env={**os.environ, 'FIXTURE_PASSWORD': password}, capture_output=True, text=True, check=True)
        hashed = result.stdout.strip()
        if not hashed.startswith('$2a$'): raise RuntimeError('Synthetic password hash failed')
        accounts = [{'id': 67001, 'email': 'b67-owner@example.invalid', 'role': 'USER'},
                    {'id': 67002, 'email': 'b67-reader@example.invalid', 'role': 'USER'},
                    {'id': 67003, 'email': 'b67-admin@example.invalid', 'role': 'ADMIN'}]
        media = Path(config['MUSIC_UPLOAD_PATH']) / 'mus067'
        media.mkdir(mode=0o700)
        tracks = []
        for i, tone in enumerate((440, 660, 880)):
            path = media / ('tone-' + str(tone) + '.mp3')
            result = subprocess.run(['ffmpeg', '-nostdin', '-n', '-f', 'lavfi', '-i',
                'sine=frequency=%d:sample_rate=48000:duration=25' % tone, '-ac', '2', '-c:a', 'libmp3lame', '-b:a', '128k', str(path)],
                capture_output=True, text=True)
            (output / ('ffmpeg-' + str(tone) + '.log')).write_text(result.stderr)
            result.check_returncode()
            duration = subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', str(path)], text=True)
            raw = path.read_bytes()
            tracks.append({'track_id': str(670101 + i), 'duration_ms': int(float(duration) * 1000),
                           'content_bytes': len(raw), 'content_md5': hashlib.md5(raw).hexdigest(),
                           'content_sha256': hashlib.sha256(raw).hexdigest()})
        statements = []
        for account in accounts:
            statements.append("INSERT INTO users(userid,name,email,password,role,is_locked,verification_status,created_at,updated_at) VALUES(%d,'B67 synthetic %s','%s','%s','%s',0,1,NOW(),NOW());" %
                              (account['id'], account['role'], account['email'], hashed, account['role']))
        statements.extend(["INSERT INTO music_categories(categoryid,category_name) VALUES(67001,'Synthetic tones A'),(67002,'Synthetic tones B');",
                           "INSERT INTO music_tags(tagid,tag_name,userid) VALUES(67011,'Fixture low',67001),(67012,'Fixture generated',67001);"])
        for i, track in enumerate(tracks):
            tid = int(track['track_id']); owner = 67001 if i < 2 else 67002
            category = 67001 if i < 2 else 67002; tone = (440, 660, 880)[i]
            path = 'mus067/tone-%d.mp3' % tone
            statements.append("INSERT INTO file_upload(id,owner_user_id,file_name,file_size,file_md5,file_path,file_type,chunk_size,chunk_count,uploaded_chunks,status,deleted,complete_time) VALUES(%d,%d,'tone-%d.mp3',%d,'%s','%s','mp3',5242880,1,1,1,0,NOW());" %
                              (tid, owner, tone, track['content_bytes'], track['content_md5'], path))
            statements.append("INSERT INTO music_resources(musicid,userid,categoryid,title,artist,file_path,format,file_size,approval_status,is_deleted,upload_time) VALUES(%d,%d,%d,'Synthetic tone %d','Generated signal — test only','%s','mp3',%d,'approved',0,NOW());" %
                              (tid, owner, category, tone, path, track['content_bytes']))
        statements.append('INSERT INTO music_resource_tags(musicid,tagid) VALUES(670101,67011),(670101,67012),(670102,67011);')
        query('START TRANSACTION;\n' + '\n'.join(statements) + '\nCOMMIT;')
        meta = write_fixture(output / 'index', tracks)
        state = {'schema': 'sonora-discovery-smoke-fixture-v1', 'slot': slot, 'tracks': tracks,
                 'accounts': [{**a, 'password': password} for a in accounts],
                 'index_version': meta['index_version'], 'model_version': meta['model_version'],
                 'engine_kind': 'synthetic_fixture'}
        (output / 'state.json').write_text(json.dumps(state, indent=2) + '\n')
        (output / 'catalog.json').write_text(json.dumps(tracks, indent=2) + '\n')
        return {'status': 'synthetic_fixture_created', 'tracks': len(tracks), 'accounts': len(accounts),
                'engine_kind': 'synthetic_fixture', 'state_path': str(output / 'state.json')}
    finally:
        os.umask(prior)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--slot', choices=['a', 'b'], default='b')
    parser.add_argument('--mysql', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--java-home', type=Path, required=True)
    parser.add_argument('--bcrypt-jar', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(**vars(args))))


if __name__ == '__main__':
    main()
