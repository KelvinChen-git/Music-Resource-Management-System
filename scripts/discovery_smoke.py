#!/usr/bin/env python3
"""Real HTTP/SQL/Range with self-generated synthetic fixtures; no model quality test."""
import argparse
import json
import re
from pathlib import Path
import urllib.error
import urllib.request

from dev import read_env, database_query


def run(slot, mysql, state, output):
    config = read_env(slot); state = json.loads(Path(state).read_text()); output = Path(output)
    if output.exists(): raise RuntimeError('Prior smoke evidence preserved; choose a new output')
    if state.get('schema') != 'sonora-discovery-smoke-fixture-v1' or state['slot'] != slot or state.get('engine_kind') != 'synthetic_fixture':
        raise RuntimeError('Explicit synthetic state for this slot required')
    sql = database_query(slot, mysql)
    expected = sql("SELECT COUNT(*) FROM music_resources WHERE musicid IN(670101,670102,670103) AND title LIKE 'Synthetic tone %' AND approval_status='approved' AND is_deleted=0;")
    marked_users = sql("SELECT COUNT(*) FROM users WHERE userid IN(67001,67002,67003) AND email IN('b67-owner@example.invalid','b67-reader@example.invalid','b67-admin@example.invalid');")
    if expected != '3' or marked_users != '3' or [t['track_id'] for t in state['tracks']] != ['670101', '670102', '670103'] or not all(re.fullmatch('[a-f0-9]{32}', t['content_md5']) for t in state['tracks']):
        raise RuntimeError('Only untouched marked synthetic rows may be exercised')
    base = 'http://127.0.0.1:' + config['MUSIC_SERVER_PORT'] + '/api'
    checks = []
    def request(path, token=None, body=None, raw=None, headers=None):
        data = raw if raw is not None else json.dumps(body).encode() if body is not None else None
        merged = {'Content-Type': 'application/json', **(headers or {})}
        if token: merged['Authorization'] = 'Bearer ' + token
        req = urllib.request.Request(base + path, data=data, headers=merged)
        try: response = urllib.request.urlopen(req, timeout=15)
        except urllib.error.HTTPError as error: response = error
        with response: return response.status, dict(response.headers.items()), response.read()
    def check(name, passed):
        checks.append({'name': name, 'passed': bool(passed)})
        if not passed: raise AssertionError(name)
    query = {'query': {'kind': 'text', 'text': 'synthetic tone 440'}, 'top_k': 3}
    report = {'scope': 'real_HTTP_SQL_Range_synthetic_media_and_vectors_not_semantic_quality', 'checks': checks, 'status': 'failed'}
    try:
        tokens = []
        for account in state['accounts']:
            status, _, raw = request('/auth/login', body={'email': account['email'], 'password': account['password']})
            value = json.loads(raw); check('real login ' + account['role'] + str(account['id']), status == 200 and value.get('code') == 200)
            tokens.append(value['data']['token'])
        status, _, raw = request('/discovery/search', body=query)
        check('anonymous search401 envelope', status == 401 and json.loads(raw)['data']['error_type'] == 'unauthorized')
        status, headers, raw = request('/discovery/search', tokens[0], body=query)
        result = json.loads(raw)['data']; rows = result['results']
        check('real Java Python search explicitly synthetic', status == 200 and result['engine_kind'] == 'synthetic_fixture'
              and [r['track_id'] for r in rows] == [r['track_id'] for r in state['tracks']])
        preview = rows[0]['preview_url'].removeprefix('/api')
        check('JSON no-store', 'no-store' in headers.get('Cache-Control', ''))
        for row in rows:
            check('valid clips ' + row['track_id'], 1 <= len(row['segments']) <= 3
                  and all(0 <= s['start_ms'] < s['end_ms'] <= row['duration_ms'] for s in row['segments']))
        status, headers, raw = request(preview, tokens[1], headers={'Range': 'bytes=0-31'})
        check('actual authorized Range206 bytes32', status == 206 and len(raw) == 32 and headers.get('Content-Range', '').startswith('bytes 0-31/'))
        check('media no-store', 'no-store' in headers.get('Cache-Control', ''))
        check('anonymous media401', request(preview)[0] == 401)
        check('bad input400', request('/discovery/search', tokens[0], body={'query': {'kind': 'text', 'text': ' '}})[0] == 400)
        check('unsupported mode400', request('/discovery/search', tokens[0], body={**query, 'retrieval_mode': 'hybrid'})[0] == 400)
        check('duplicate JSON400', request('/discovery/search', tokens[0], raw=b'{"query":{},"query":{}}')[0] == 400)
        filtered = {**query, 'filters': {'category_id': '67002'}}
        value = json.loads(request('/discovery/search', tokens[0], body=filtered)[2])['data']
        check('actual category filter', [r['track_id'] for r in value['results']] == ['670103'])
        filtered = {**query, 'filters': {'tag_ids': ['67011', '67012'], 'tag_match': 'all'}}
        value = json.loads(request('/discovery/search', tokens[0], body=filtered)[2])['data']
        check('actual SQL tag ALL', [r['track_id'] for r in value['results']] == ['670101'])
        filtered['filters']['tag_match'] = 'any'
        value = json.loads(request('/discovery/search', tokens[0], body=filtered)[2])['data']
        check('actual SQL tag ANY', [r['track_id'] for r in value['results']] == ['670101', '670102'])
        filtered = {**query, 'filters': {'category_id': '999999'}}
        status, _, raw = request('/discovery/search', tokens[0], body=filtered)
        check('empty results200', status == 200 and json.loads(raw)['data']['results'] == [])
        for state_name in ('pending', 'rejected', 'deleted'):
            if state_name == 'deleted': sql('UPDATE music_resources SET is_deleted=1 WHERE musicid=670101;')
            else: sql("UPDATE music_resources SET approval_status='%s' WHERE musicid=670101;" % state_name)
            try:
                for i, token in enumerate(tokens):
                    status, _, raw = request('/discovery/search', token, body=query)
                    check(state_name + ' excluded for actor' + str(i), status == 200 and all(r['track_id'] != '670101' for r in json.loads(raw)['data']['results']))
                    check(state_name + ' preview404 actor' + str(i), request(preview, token)[0] == 404)
                if state_name == 'pending':
                    check('legacy owner pending access preserved', request('/music-resources/670101/file', tokens[0])[0] == 200)
            finally: sql("UPDATE music_resources SET approval_status='approved',is_deleted=0 WHERE musicid=670101;")
        sql("UPDATE file_upload SET file_md5=REPEAT('0',32) WHERE id=670101;")
        try:
            status, _, raw = request('/discovery/search', tokens[0], body=query)
            check('stale index excluded before topk', status == 200 and all(r['track_id'] != '670101' for r in json.loads(raw)['data']['results']))
            check('stale preview409', request(preview, tokens[0])[0] == 409)
        finally: sql("UPDATE file_upload SET file_md5='%s' WHERE id=670101;" % state['tracks'][0]['content_md5'])
        sql('UPDATE users SET is_locked=1 WHERE userid=67002;')
        try:
            check('locked viewer search403', request('/discovery/search', tokens[1], body=query)[0] == 403)
            check('locked viewer media403', request(preview, tokens[1])[0] == 403)
        finally: sql('UPDATE users SET is_locked=0 WHERE userid=67002;')
        check('preview restored200', request(preview, tokens[0])[0] == 200)
        report['status'] = 'passed'
    except Exception as error:
        report['error_type'] = type(error).__name__  # Do not persist tokens/passwords in shared evidence.
        raise
    finally:
        # Restore only the known synthetic rows, even if an intermediate assertion failed.
        sql("UPDATE music_resources SET approval_status='approved',is_deleted=0 WHERE musicid=670101;UPDATE users SET is_locked=0 WHERE userid=67002;UPDATE file_upload SET file_md5='%s' WHERE id=670101;" % state['tracks'][0]['content_md5'])
        output.write_text(json.dumps(report, indent=2) + '\n'); output.chmod(0o600)
    return {'status': report['status'], 'checks': len(checks), 'semantic_model_runs': 0}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--slot', choices=['a', 'b'], default='b')
    parser.add_argument('--mysql', required=True)
    parser.add_argument('--state', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    print(json.dumps(run(**vars(parser.parse_args()))))


if __name__ == '__main__':
    main()
