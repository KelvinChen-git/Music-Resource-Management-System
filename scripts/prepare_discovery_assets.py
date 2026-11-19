#!/usr/bin/env python3
"""Explicit bounded asset setup or read-only checks. Never invoked by the worker."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import sys
from urllib.parse import quote, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'services/audio-search'))
from discovery_build import checked_catalog, new_output, private_path, write_json
from discovery_index import ClapTextEncoder, file_hash, regular, require, strict_json

PLAN = ROOT / 'docs/verification/MUS-068-assets.json'
PLAN_SHA256 = '4b613fb5d4ed4d083af9001f47b368200e1b556f62b1922235fe60019f258cdd'
SOURCE_BASE = 'https://incompetech.com/music/royalty-free/'


def load_plan():
    require(file_hash(PLAN) == PLAN_SHA256, 'Asset plan was changed; freeze and review a new plan first')
    value = strict_json(PLAN.read_bytes())
    require(value['schema'] == 'sonora-discovery-asset-plan-v1', 'Wrong asset plan')
    return value


def destination(root, relative):
    require(isinstance(relative, str) and not PurePosixPath(relative).is_absolute()
            and '..' not in PurePosixPath(relative).parts and '\\' not in relative,
            'Asset destination must stay below fresh private output')
    target = root / relative
    require(target.resolve().is_relative_to(root.resolve())
            and not any(p.is_symlink() for p in (target, *target.parents)), 'Asset path traverses a link')
    return target


def safe_url(value):
    parsed = urlsplit(value)
    require(parsed.scheme == 'https' and parsed.hostname and not parsed.username and not parsed.password
            and parsed.port in (None, 443) and not parsed.fragment
            and (parsed.hostname in ('huggingface.co', 'incompetech.com', 'www.incompetech.com')
                 or parsed.hostname.endswith('.hf.co')), 'Unexpected asset origin')
    return value


class AssetRedirects(HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        safe_url(new_url)
        if urlsplit(request.full_url).hostname in ('incompetech.com', 'www.incompetech.com'):
            require(urlsplit(new_url).hostname in ('incompetech.com', 'www.incompetech.com'),
                    'Source redirect changed provider')
        return super().redirect_request(request, response, code, message, headers, new_url)


class Fetcher:
    def __init__(self, budget):
        self.budget, self.reserved, self.received = budget, 0, 0
        self.records = []
        self.opener = build_opener(AssetRedirects())

    def fetch(self, url, target, limit, expected_sha=None):
        safe_url(url)
        require(type(limit) is int and limit > 0 and self.reserved + limit + 1 <= self.budget,
                'Download budget would be exceeded')
        partial = target.with_name(target.name + '.partial')
        require(not target.exists() and not partial.exists(), 'Existing or failed asset output preserved')
        target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.reserved += limit + 1
        record = {'url': url, 'limit': limit, 'status': 'started'}; self.records.append(record)
        sha, size = hashlib.sha256(), 0
        try:
            request = Request(url, headers={'User-Agent': 'Sonora-MUS068-explicit-bounded-setup/1.0'})
            with self.opener.open(request, timeout=60) as response:
                require(response.status == 200, 'Unexpected asset response')
                record.update(http_status=response.status, final_host=urlsplit(response.url).hostname)
                descriptor = os.open(partial, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
                with os.fdopen(descriptor, 'wb') as output:
                    while True:
                        block = response.read(min(1024 * 1024, limit - size + 1))
                        if not block: break
                        size += len(block); self.received += len(block)
                        require(size <= limit, 'Asset response exceeds its byte bound')
                        output.write(block); sha.update(block)
            require(size > 0, 'Empty asset response')
            if expected_sha is not None:
                require(size == limit and sha.hexdigest() == expected_sha, 'Pinned asset bytes/hash differ')
            partial.rename(target)
            record.update(status='downloaded', bytes=size, sha256=sha.hexdigest())
            return target
        except Exception as error:
            record.update(status='failed', error_type=type(error).__name__, received_bytes=size)
            raise


def verify_assets(output, slot, plan=None):
    plan = plan or load_plan()
    output = private_path(output, slot, directory=True)
    checkpoint = plan['checkpoint']; path = destination(output, checkpoint['path'])
    require(regular(path).stat().st_size == checkpoint['bytes'] and file_hash(path) == checkpoint['sha256'],
            'Pinned A checkpoint missing or changed')
    expected = {}
    for row in plan['cache_files']:
        path = regular(destination(output, row['path']))
        require(path.stat().st_size == row['bytes'] and file_hash(path) == row['sha256'], 'Pinned cache bytes differ')
        expected[row['key']] = row['sha256']
    for row in plan['cache_aliases']:
        path = regular(destination(output, row['path']))
        require(path.read_text() == row['revision'] and file_hash(path) == row['sha256'], 'Unpinned SDK import alias')
        expected[row['key']] = row['sha256']
    checker = ClapTextEncoder.__new__(ClapTextEncoder)  # No SDK import or model construction.
    checker.offline_cache = output / 'hf-cache'
    require(checker._cache_identity() == expected, 'Cache layout differs from frozen plan')
    rows, _, _ = checked_catalog(output / 'music/catalog.json', output / 'music')
    require(len(rows) == len(plan['music']), 'Expected exactly the two fixed development recordings')
    for row, item in zip(rows, plan['music']):
        require(all(row[k] == item[k] for k in ('track_id', 'content_bytes', 'content_md5', 'content_sha256'))
                and all(row['source'][k] == item[k] for k in
                        ('source_url', 'license_url', 'title', 'artist', 'attribution')), 'Recording/provenance differs')
    return {'status': 'assets_ready', 'model_run': False, 'tracks': len(rows),
            'checkpoint_sha256': checkpoint['sha256'], 'cache_files': len(expected), 'asset_plan_sha256': PLAN_SHA256}


def prepare(output, slot):
    plan = load_plan()
    output = new_output(output, slot)
    fetcher = Fetcher(plan['asset_download_budget_bytes'])
    previous = os.umask(0o077)
    try:
        checkpoint = plan['checkpoint']
        fetcher.fetch(checkpoint['url'], destination(output, checkpoint['path']),
                      checkpoint['bytes'], checkpoint['sha256'])
        for row in plan['cache_files']:
            target = destination(output, row['path'])
            if row['operation'] == 'download':
                fetcher.fetch(row['url'], target, row['bytes'], row['sha256'])
            else:
                source = regular(destination(output, row['copy_from']))
                require(file_hash(source) == row['sha256'], 'Cache alias source changed')
                target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                with target.open('xb') as result, source.open('rb') as original:
                    shutil.copyfileobj(original, result)
        for row in plan['cache_aliases']:
            target = destination(output, row['path']); target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            with target.open('x') as result: result.write(row['revision'])
        music = output / 'music'; music.mkdir(mode=0o700)
        metadata_path = fetcher.fetch(SOURCE_BASE + 'pieces.json', music / 'pieces.json', 2 * 1024 * 1024)
        license_path = fetcher.fetch(SOURCE_BASE + 'licenses/', music / 'licenses.html', 2 * 1024 * 1024)
        catalog = strict_json(metadata_path.read_bytes()); license_text = license_path.read_text()
        require(isinstance(catalog, list) and 'Kevin MacLeod' in license_text
                and 'creativecommons.org/licenses/by/4.0/' in license_text, 'Current source/license evidence unavailable')
        tracks = []
        for row in plan['music']:
            matches = [x for x in catalog if x.get('isrc') == row['source_id']]
            require(len(matches) == 1 and matches[0]['title'] == row['title']
                    and matches[0]['filename'] == row['source_filename'], 'Fixed source identity changed')
            sid = row['source_id']
            fetcher.fetch(row['source_url'], music / (sid + '.html'), 2 * 1024 * 1024)
            audio = fetcher.fetch(SOURCE_BASE + 'mp3-royaltyfree/' + quote(row['source_filename'], safe=''),
                                  music / (sid + '.mp3'), row['content_bytes'], row['content_sha256'])
            require(hashlib.md5(audio.read_bytes()).hexdigest() == row['content_md5'], 'Java content MD5 differs')
            evidence = [{'filename': name, 'sha256': file_hash(music / name)}
                        for name in ('pieces.json', 'licenses.html', sid + '.html')]
            proof = {'schema': 'sonora-discovery-source-proof-v1',
                     **{k: row[k] for k in ('track_id', 'content_bytes', 'content_md5', 'content_sha256',
                         'source_url', 'license_url', 'title', 'artist', 'attribution')},
                     'changes': 'Audio file unchanged', 'evidence': evidence}
            proof_name = sid + '.source.json'; proof_sha = write_json(music / proof_name, proof)
            tracks.append({k: row[k] for k in ('track_id', 'content_bytes', 'content_md5', 'content_sha256')} |
                          {'audio_filename': audio.name, 'proof_filename': proof_name, 'proof_sha256': proof_sha})
        write_json(music / 'catalog.json', {'schema': 'sonora-discovery-catalog-v1', 'tracks': tracks})
        result = verify_assets(output, slot, plan)
        result['download_bytes'] = fetcher.received
        write_json(output / 'ready.json', result)
        return result
    except Exception as error:
        write_json(output / 'setup-failure.json', {'status': 'failed', 'error_type': type(error).__name__,
                   'partial_outputs_preserved': True})
        raise
    finally:
        write_json(output / 'setup-receipts.json', {'plan_sha256': PLAN_SHA256,
                   'budget_bytes': fetcher.budget, 'reserved_bytes': fetcher.reserved,
                   'received_bytes': fetcher.received, 'requests': fetcher.records})
        os.umask(previous)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--slot', choices=['a', 'b'], default='b')
    parser.add_argument('--output', type=Path, required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--download', action='store_true')
    group.add_argument('--verify-only', action='store_true')
    args = parser.parse_args()
    try:
        result = prepare(args.output, args.slot) if args.download else verify_assets(args.output, args.slot)
        print(json.dumps(result)); return 0
    except Exception as error:
        print(json.dumps({'status': 'failed', 'error_type': type(error).__name__})); return 1


if __name__ == '__main__':
    raise SystemExit(main())
