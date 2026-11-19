#!/usr/bin/env python3
"""Fixed real CLAP/MP3/loopback HTTP verification; no quality labels or downloads."""
import argparse
import http.client
import json
from pathlib import Path
import secrets
import sys
import threading

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'services/audio-search'))
import numpy as np
from discovery_build import checked_catalog, decode_audio, new_output, private_path, runtime_identity, write_json
from discovery_index import (ClapTextEncoder, DiscoveryIndex, MODEL_VERSION, SAMPLE_RATE,
                             file_hash, matrix, regular, require)
from discovery_server import make_server

TEXTS = ['Calm acoustic guitar music.', 'Energetic instrumental rock music.',
         ('A calm instrumental melody played on acoustic guitar with a steady gentle rhythm. ' * 7).strip()]
SCORE_TOLERANCE = 1e-6


def verify(slot, index, catalog, audio_root, checkpoint, offline_cache, output):
    output = new_output(output, slot)
    report = {'status': 'failed', 'scope': 'real_CLAP_audio_index_text_HTTP_only_not_semantic_quality',
              'semantic_quality_evaluation': False, 'checks': [], 'text_token_proofs': [],
              'model_loads_completed': 0, 'worker_stopped': False, 'runtime': runtime_identity()}
    server = None; thread = None

    def check(name, condition):
        report['checks'].append({'name': name, 'passed': bool(condition)})
        require(condition, name)

    try:
        manifest_path = regular(private_path(index, slot))
        index = DiscoveryIndex(manifest_path)
        require(index.meta['engine_kind'] == 'clap_identity', 'Real model index required; fixture refused')
        rows, pins, catalog_sha = checked_catalog(regular(private_path(catalog, slot)),
                                                 private_path(audio_root, slot, directory=True))
        check('catalog matches independently opened index proof', catalog_sha == index.proof['catalog_sha256'])
        by_id = {r['track_id']: r for r in rows}
        check('index and input content identities match', len(by_id) == len(index.tracks) and all(
            tid in by_id and all(row[k] == by_id[tid][k] for k in ('content_bytes', 'content_md5', 'content_sha256'))
            for tid, row in index.tracks.items()))
        for row in index.proof['tracks']:
            samples, info = decode_audio(by_id[row['track_id']]['path'])
            check('actual MP3 EOF and resampled PCM ' + row['track_id'],
                  all(row[k] == v for k, v in info.items()) and row['duration_ms'] == len(samples) * 1000 // SAMPLE_RATE)
        encoder = ClapTextEncoder(regular(private_path(checkpoint, slot)),
                                  private_path(offline_cache, slot, directory=True))
        report['model_loads_completed'] = 1
        encoder.verify_index(index)
        check('strict real CPU FP32 identity model and matching cache',
              encoder.checkpoint_meta['id'] == 'A' and not encoder.checkpoint_meta['strict_missing']
              and not encoder.checkpoint_meta['strict_unexpected'] and index.meta['model_version'] == MODEL_VERSION)
        vectors = []
        for text in TEXTS:
            vectors.append(matrix(encoder.encode(text), (1, 512))[0])
            report['text_token_proofs'].append(dict(encoder.last_tokenization))
        check('complete long text exceeds77 and fits256 without truncation',
              77 < report['text_token_proofs'][-1]['untruncated_tokens'] <= 256
              and all(p['untruncated_tokens'] == p['encoded_nonpad_tokens'] for p in report['text_token_proofs']))
        secret = secrets.token_hex(32)
        server = make_server(index, encoder, secret, port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        port = server.server_address[1]

        def post(body, authenticated=True):
            client = http.client.HTTPConnection('127.0.0.1', port, timeout=30)
            headers = {'Content-Type': 'application/json'}
            if authenticated: headers['Authorization'] = 'Bearer ' + secret
            try:
                client.request('POST', '/internal/search', json.dumps(body).encode(), headers)
                response = client.getresponse(); raw = response.read(65537)
                check('bounded HTTP response', len(raw) <= 65536)
                check('HTTP response is no-store', response.getheader('Cache-Control') == 'no-store')
                return response.status, json.loads(raw)
            finally:
                client.close()

        allowed = [{k: r[k] for k in ('track_id', 'content_md5', 'content_bytes')} for r in rows]
        request = {'query_text': TEXTS[0], 'allowed_tracks': allowed, 'retrieval_mode': 'segment',
                   'top_k': min(20, len(allowed)), 'index_version': index.meta['index_version'],
                   'model_version': index.meta['model_version']}
        observed = []
        for qi, (text, vector) in enumerate(zip(TEXTS, vectors)):
            for mode in ('segment', 'whole_track'):
                status, body = post({**request, 'query_text': text, 'retrieval_mode': mode})
                check('real text query ' + str(qi) + '/' + mode,
                      status == 200 and body['engine_kind'] == 'clap_identity'
                      and body['model_version'] == MODEL_VERSION and body['retrieval_mode'] == mode)
                # Separate straightforward cosine/order calculation, not index.search().
                scores = {}
                for tid in index.tracks:
                    if mode == 'whole_track': score = float(np.dot(index.whole[index.positions[tid]], vector))
                    else: score = max(float(np.dot(index.segments[i], vector)) for i in index.indices[tid])
                    scores[tid] = score
                order = sorted(scores, key=lambda tid: (-scores[tid], int(tid)))[:request['top_k']]
                results = body['results']
                check('independent cosine ranks ' + str(qi) + '/' + mode,
                      [r['track_id'] for r in results] == order and all(
                          abs(row['score'] - scores[row['track_id']]) <= SCORE_TOLERANCE for row in results))
                for row in results:
                    clips = row['segments']
                    valid = 1 <= len(clips) <= 3 and all(0 <= s['start_ms'] < s['end_ms'] <= row['duration_ms'] for s in clips)
                    valid &= all(max(a['start_ms'], b['start_ms']) >= min(a['end_ms'], b['end_ms'])
                                 for i, a in enumerate(clips) for b in clips[i+1:])
                    check('real clip bounds/nonoverlap ' + str(qi) + '/' + mode + '/' + row['track_id'], valid)
                observed.append({'query_number': qi, 'mode': mode, 'track_order': order,
                                 'timings_ms': body['timings_ms'], 'quality_label': None})
        check('worker authentication required', post(request, authenticated=False)[0] == 401)
        status, body = post({**request, 'allowed_tracks': []})
        check('empty whitelist avoids model encoding', status == 200 and body['results'] == []
              and body['timings_ms']['query_encoding'] == 0)
        status, body = post({**request, 'allowed_tracks': allowed[-1:]})
        check('current whitelist filters before topk', status == 200
              and [r['track_id'] for r in body['results']] == [allowed[-1]['track_id']])
        stale = [dict(x) for x in allowed]; stale[0]['content_md5'] = '0' * 32
        status, body = post({**request, 'allowed_tracks': stale})
        check('stale indexed content excluded', status == 200
              and allowed[0]['track_id'] not in [r['track_id'] for r in body['results']])
        for key in ('index_version', 'model_version'):
            status, body = post({**request, key: 'wrong-version'})
            check('actual worker rejects ' + key, status == 503 and body['error_type'] == 'version_mismatch')
        status, body = post({**request, 'query_text': 'a ' * 300})
        check('actual tokenizer rejects over256 without truncation', status == 400
              and body['error_type'] == 'query_tokens_exceeded')
        for path, pin in pins.items(): require(file_hash(path) == pin, 'Probe input changed')
        encoder.verify_assets()
        report.update(status='passed', queries=observed, tracks=len(index.tracks), segments=len(index.meta['segments']),
                      index_version=index.meta['index_version'], model_version=index.meta['model_version'],
                      manifest_sha256=file_hash(manifest_path))
    except Exception as error:
        report['failure'] = {'error_type': type(error).__name__, 'message': str(error)[:300]}
        raise
    finally:
        if server:
            server.shutdown(); server.server_close()
        if thread:
            thread.join(timeout=5)
        report['worker_stopped'] = thread is None or not thread.is_alive()
        write_json(output / 'result.json', report)
    return {'status': report['status'], 'checks': len(report['checks']), 'real_model_loads': 1,
            'quality_evaluation': False, 'worker_stopped': report['worker_stopped']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--slot', choices=['a', 'b'], default='b')
    for name in ('index', 'catalog', 'audio-root', 'checkpoint', 'offline-cache', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    try:
        print(json.dumps(verify(**vars(parser.parse_args()))))
        return 0
    except Exception as error:
        print(json.dumps({'status': 'failed', 'error_type': type(error).__name__}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
