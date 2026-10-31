#!/usr/bin/env python3
"""Bounded official MTG per-track transport/EOF preflight; never train or write Java APIs."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import ssl
import sys
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, HTTPSHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'services/audio-search'))
import holdout_contract as hc
import mtg_dataset as mtg
import review_pack as rp


class Budget:
    def __init__(self, maximum, used=0): self.maximum, self.used = maximum, used
    def read(self, response, size):
        rp.require(0 <= size <= self.maximum - self.used, 'Global body-read budget exhausted')
        body = response.read(size); self.used += len(body); return body


def range_total(status, headers, start, end, total=None):
    match = re.fullmatch(r'bytes ([0-9]+)-([0-9]+)/([0-9]+)', headers.get('Content-Range', ''))
    rp.require(status == 206 and match is not None, 'Exact HTTP206 range required; no whole-archive fallback')
    a, b, n = map(int, match.groups())
    rp.require((a, b) == (start, end) and b < n and int(headers.get('Content-Length', '-1')) == end - start + 1
               and headers.get('Content-Encoding', 'identity') == 'identity' and (total is None or total == n), 'Range/length/encoding mismatch')
    return n


def official_url(url):
    p = urlsplit(url)
    rp.require(p.scheme == 'https' and p.netloc == 'cdn.freesound.org' and not p.query and not p.fragment
               and re.fullmatch(r'/mtg-jamendo/raw_30s/audio-low/[0-9]{2}/[0-9]+\.low\.mp3', p.path), 'Unexpected individual official audio URL')
    return url


class Redirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        rp.require(official_url(newurl) == req.full_url, 'Redirect cannot change pinned source identity')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def write_raw(path, raw):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600); os.fchmod(fd, 0o600)
    with os.fdopen(fd, 'wb') as f: f.write(raw)


def fetch_one(opener, track, policy, budget):
    url = official_url(policy['audio_base_url'] + track['low_path'])
    def request(start, end, validator=None):
        headers = {'User-Agent': 'Sonora-research-preflight/1', 'Range': f'bytes={start}-{end}', 'Accept-Encoding': 'identity'}
        if validator: headers['If-Range'] = validator
        return opener.open(Request(url, headers=headers), timeout=25)
    with request(0, 0) as response:
        rp.require(response.url == url, 'Audio URL changed')
        total = range_total(response.status, response.headers, 0, 0)
        rp.require(1 < total <= policy['max_track_bytes'], 'Audio size outside preflight bounds')
        validator_key = 'ETag' if response.headers.get('ETag') and not response.headers['ETag'].startswith('W/') else 'Last-Modified'
        validator = response.headers.get(validator_key); rp.require(bool(validator), 'Stable representation validator required')
        rp.require(len(budget.read(response, 1)) == 1, 'Truncated range probe')
    with request(0, total - 1, validator) as response:
        rp.require(response.url == url, 'Audio URL changed')
        range_total(response.status, response.headers, 0, total - 1, total)
        rp.require(response.headers.get(validator_key) == validator, 'Audio representation changed during fetch')
        raw = budget.read(response, total)
        rp.require(len(raw) == total and hc.digest(raw) == track['audio_sha256'], 'Audio body/official per-track SHA mismatch')
    return raw, {'url': url, 'status': 206, 'bytes': total, 'sha256': hc.digest(raw),
                 'validator_header': validator_key, 'validator': validator, 'official_sha_matched': True}


def fetch(*, selection, selection_sha256, policy, policy_sha256, output, ca_file=None):
    p = hc.assets.document(policy, policy_sha256); s = hc.assets.document(selection, selection_sha256)
    rp.require(s['policy_sha256'] == policy_sha256 and s['adapter_sha256'] == hc.file_hash(ROOT/'services/audio-search/mtg_dataset.py')
               and s['summary']['selected_tracks'] == len(s['selected']) == 20
               and all(t['official_split'] == 'train' and t['audio_license']['family'] in ('by','by-sa') for t in s['selected']), 'Fixed adapter selection required')
    target = hc.private_output(output)
    budget = Budget(p['max_total_body_bytes'], p['prior_network_body_bytes'])
    context = ssl.create_default_context(cafile=ca_file)
    opener = build_opener(Redirects(), HTTPSHandler(context=context))
    results = []
    try:
        for i, t in enumerate(s['selected'], 1):
            for attempt in range(1, p['max_download_attempts_per_track'] + 1):
                try:
                    raw, proof = fetch_one(opener, t, p, budget)
                    filename = t['source_track_id'] + '.low.mp3'
                    write_raw(target / filename, raw)
                    proof.update(source_track_id=t['source_track_id'], filename=filename, attempt=attempt)
                    hc.write_json(target / (filename + '.proof.json'), proof); results.append(proof)
                    print(json.dumps({'downloaded': i, 'total': 20, 'body_bytes_used': budget.used}), flush=True)
                    break
                except Exception as exc:
                    hc.write_json(target / f'failure-{i}-{attempt}.json', {'error_type': type(exc).__name__, 'error': str(exc), 'body_bytes_used': budget.used})
                    if attempt == p['max_download_attempts_per_track']: raise
        result = {'schema': 'sonora-mtg-audio-fetch-v1', 'status': 'downloaded20_official_low_hashes_verified',
                  'selection_sha256': selection_sha256, 'policy_sha256': policy_sha256, 'body_bytes_used': budget.used,
                  'created_at_utc': hc.now(), 'tracks': results, 'script_sha256': hc.file_hash(Path(__file__))}
        hc.write_json(target / 'fetch.json', result); return result
    except Exception as exc:
        hc.write_json(target / 'failed.json', {'status': 'blocked_audio_transport', 'completed': len(results), 'error_type': type(exc).__name__, 'error': str(exc), 'body_bytes_used': budget.used})
        raise


def decode(*, selection, selection_sha256, fetched, fetched_sha256, inputs, inputs_sha256, policy, policy_sha256, output):
    s = hc.assets.document(selection, selection_sha256); f = hc.assets.document(fetched, fetched_sha256)
    rp.require(f['selection_sha256'] == selection_sha256 and len(f['tracks']) == 20, 'Complete hash-verified fetch required')
    target = hc.private_output(output)
    import numpy as np
    import soundfile as sf
    from research_corpus import decode_source_mono
    from corpus import window_bounds
    manifest = hc.assets.document(inputs, inputs_sha256)
    config = hc.assets.document(policy, policy_sha256)
    rp.require(s['inputs_sha256'] == inputs_sha256 and s['policy_sha256'] == policy_sha256, 'Original source/policy pins required')
    prior40 = hc.assets.document(manifest['files']['prior40']['path'], config['input_sha256']['prior40'])
    prior20 = hc.assets.document(manifest['files']['prior20']['path'], config['input_sha256']['prior20'])
    prior_bytes = {t['sha256'] for t in prior40['audioTracks']} | {t['content_sha256'] for t in prior20['tracks']}
    prior_pcm = {t['pcm_sha256'] for t in prior20['tracks']}
    # Existing developer decode manifests may use a different PCM hash convention; report limited coverage.
    seen_bytes, seen_pcm, results = set(), set(), []
    try:
        for t, proof in zip(s['selected'], f['tracks']):
            rp.require(t['source_track_id'] == proof['source_track_id'] and proof['sha256'] == t['audio_sha256'], 'Fetch ordering/identity mismatch')
            path = Path(fetched).parent / proof['filename']
            rp.require(hc.file_hash(path) == proof['sha256'] and proof['sha256'] not in prior_bytes | seen_bytes, 'Duplicate or changed audio bytes')
            with sf.SoundFile(path) as source:
                header = {'frames': source.frames, 'sample_rate_hz': source.samplerate, 'channels': source.channels,
                          'format': source.format, 'duration_ms': source.frames * 1000 // source.samplerate}
            audio, info = decode_source_mono(path, header)
            pcm = hashlib.sha256(audio.astype('<f4', copy=False).tobytes()).hexdigest()
            rp.require(pcm not in prior_pcm | seen_pcm, 'Exact normalized PCM duplicate')
            slots = window_bounds(len(audio))
            rp.require(slots and all(0 <= a < b <= len(audio) and b-a <= 480000 for a,b in slots), 'Invalid fixed windows')
            # Actual first/tail arrays validate right-padding without encoding a model.
            from preprocess import prepare_window
            for start,end in (slots[0],slots[-1]):
                window, meta = prepare_window(audio[start:end], 48000)
                rp.require(window.shape == (480000,) and np.isfinite(window).all()
                           and meta['real_samples'] == end-start and meta['padded_samples'] == 480000-(end-start)
                           and np.count_nonzero(window[end-start:]) == 0, 'Invalid padded preflight window')
            results.append({'source_track_id': t['source_track_id'], **info, 'pcm_sha256': pcm,
                            'segments': len(slots), 'tail_real_samples': slots[-1][1]-slots[-1][0],
                            'tail_padded_samples': 480000-(slots[-1][1]-slots[-1][0])})
            seen_bytes.add(proof['sha256']); seen_pcm.add(pcm)
        report = {'schema': 'sonora-mtg-real-audio-preflight-v1', 'status': 'passed20_actual_EOF_and_weak_label_linkage',
                  'created_at_utc': hc.now(), 'selection_sha256': selection_sha256, 'fetched_sha256': fetched_sha256,
                  'tracks': results, 'summary': {'tracks': 20, 'source_official_hashes_verified': 20, 'actual_EOF_decoded': 20,
                  'segments': sum(r['segments'] for r in results), 'first_and_tail_windows_checked': 40,
                  'mono_source_tracks': sum(r['source_channels']==1 for r in results), 'prior60_exact_byte_duplicates': 0,
                  'prior20_same_decoder_PCM_duplicates': 0, 'selected_exact_PCM_duplicates': 0,
                  'models_loaded': 0, 'training_runs': 0},
                  'limits': ['Exact byte check covers all prior60; same-normalization PCM pins cover prior20 only, not all60.',
                             'No acoustic fingerprint/cover/alias completeness or pretraining-unseen proof.',
                             'Data transport/decode preflight is not training or model-quality evaluation.']}
        hc.write_json(target/'decode.json', report); return report
    except Exception as exc:
        hc.write_json(target/'failed.json', {'status':'failed_audio_preflight','decoded':len(results),'error_type':type(exc).__name__,'error':str(exc)})
        raise


def main():
    p = argparse.ArgumentParser(description=__doc__); commands = p.add_subparsers(dest='command', required=True)
    a = commands.add_parser('prepare')
    for key in ('inputs','policy','output'): a.add_argument('--'+key, type=Path, required=True)
    for key in ('inputs-sha256','policy-sha256'): a.add_argument('--'+key, required=True)
    a = commands.add_parser('fetch')
    for key in ('selection','policy','output'): a.add_argument('--'+key, type=Path, required=True)
    for key in ('selection-sha256','policy-sha256'): a.add_argument('--'+key, required=True)
    a.add_argument('--ca-file')
    a = commands.add_parser('decode')
    for key in ('selection','fetched','inputs','policy','output'): a.add_argument('--'+key, type=Path, required=True)
    for key in ('selection-sha256','fetched-sha256','inputs-sha256','policy-sha256'): a.add_argument('--'+key, required=True)
    args=vars(p.parse_args());command=args.pop('command')
    result = mtg.prepare(**args) if command=='prepare' else globals()[command](**args)
    print(json.dumps(result.get('summary', {'status': result.get('status'), 'tracks':len(result.get('tracks',[]))})))


if __name__=='__main__': main()
