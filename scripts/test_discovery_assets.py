"""Bounded setup I/O guards with explicit fake HTTP, no model/network downloads."""
import hashlib
import copy
import io
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import Mock, patch

import prepare_discovery_assets as assets
from discovery_index import DiscoveryError


class Response(io.BytesIO):
    status = 200
    url = 'https://huggingface.co/explicit-synthetic-unit-response'


class AssetSetupTest(unittest.TestCase):
    def setUp(self):
        parent = assets.ROOT / '.local/b'; parent.mkdir(parents=True, exist_ok=True)
        temporary = tempfile.TemporaryDirectory(prefix='explicit-asset-test-', dir=parent)
        self.addCleanup(temporary.cleanup); self.root = Path(temporary.name)
        self.fetcher = assets.Fetcher(1024)
        self.fetcher.opener = Mock()

    def test_only_expected_https_origins_without_credentials(self):
        for url in ('http://huggingface.co/file', 'file:///private', 'https://localhost:8091/x',
                    'https://user:secret@huggingface.co/x', 'https://huggingface.co.evil.invalid/x'):
            with self.subTest(url=url), self.assertRaises(DiscoveryError): assets.safe_url(url)

    def test_hash_size_and_private_permissions(self):
        self.fetcher.opener.open.return_value = Response(b'abcd')
        target = self.root / 'asset'
        self.fetcher.fetch('https://huggingface.co/test', target, 4, hashlib.sha256(b'abcd').hexdigest())
        self.assertEqual(target.read_bytes(), b'abcd'); self.assertEqual(self.fetcher.received, 4)
        self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o600)

    def test_oversize_keeps_partial_and_never_retries_same_target(self):
        self.fetcher.opener.open.return_value = Response(b'abcde')
        target = self.root / 'asset'
        with self.assertRaises(DiscoveryError): self.fetcher.fetch('https://huggingface.co/test', target, 4)
        self.assertFalse(target.exists()); self.assertTrue((self.root / 'asset.partial').exists())
        with self.assertRaises(DiscoveryError): self.fetcher.fetch('https://huggingface.co/test', target, 4)
        self.fetcher.opener.open.assert_called_once()

    def test_wrong_hash_keeps_failed_bytes_unactivated(self):
        self.fetcher.opener.open.return_value = Response(b'abcd')
        target = self.root / 'asset'
        with self.assertRaises(DiscoveryError): self.fetcher.fetch('https://huggingface.co/test', target, 4, '0' * 64)
        self.assertFalse(target.exists()); self.assertEqual((self.root / 'asset.partial').read_bytes(), b'abcd')

    def test_budget_rejects_before_request(self):
        with self.assertRaises(DiscoveryError): self.fetcher.fetch('https://huggingface.co/test', self.root / 'asset', 1024)
        self.fetcher.opener.open.assert_not_called(); self.assertFalse((self.root / 'asset').exists())

    def test_destinations_reject_traversal_and_links(self):
        for path in ('../other', '/absolute', 'folder/../../other'):
            with self.assertRaises(DiscoveryError): assets.destination(self.root, path)
        (self.root / 'link').symlink_to(self.root / 'elsewhere')
        with self.assertRaises(DiscoveryError): assets.destination(self.root, 'link')

    def test_existing_bundle_is_never_overwritten_or_downloaded(self):
        marker = self.root / 'preserve'; marker.write_text('unchanged')
        with patch.object(assets, 'Fetcher') as fetcher, patch.object(assets, 'load_plan', return_value={}):
            with self.assertRaises(FileExistsError): assets.prepare(self.root, 'b')
            fetcher.assert_not_called()
        self.assertEqual(marker.read_text(), 'unchanged')

    def test_complete_setup_with_explicit_fake_http_produces_consumable_proofs(self):
        plan = copy.deepcopy(assets.load_plan())
        responses, by_path = {}, {}
        checkpoint = plan['checkpoint']; payload = b'explicit synthetic checkpoint, never loaded'
        checkpoint.update(bytes=len(payload), sha256=hashlib.sha256(payload).hexdigest())
        responses[checkpoint['url']] = payload
        for row in plan['cache_files']:
            if row['operation'] == 'copy': payload = by_path[row['copy_from']]
            else:
                payload = ('explicit synthetic tokenizer file: ' + row['key']).encode()
                responses[row['url']] = payload
            by_path[row['path']] = payload
            row.update(bytes=len(payload), sha256=hashlib.sha256(payload).hexdigest())
        pieces = []
        for row in plan['music']:
            pieces.append({'isrc': row['source_id'], 'title': row['title'], 'filename': row['source_filename']})
            payload = ('explicit synthetic audio, no decoder/model: ' + row['source_id']).encode()
            row.update(content_bytes=len(payload), content_md5=hashlib.md5(payload).hexdigest(),
                       content_sha256=hashlib.sha256(payload).hexdigest())
            responses[row['source_url']] = b'explicit fake source snapshot'
            responses[assets.SOURCE_BASE + 'mp3-royaltyfree/' + assets.quote(row['source_filename'], safe='')] = payload
        responses[assets.SOURCE_BASE + 'pieces.json'] = assets.json.dumps(pieces).encode()
        responses[assets.SOURCE_BASE + 'licenses/'] = b'Kevin MacLeod creativecommons.org/licenses/by/4.0/'
        def reply(request, **kwargs):
            response = Response(responses[request.full_url]); response.url = request.full_url
            return response
        opener = Mock(); opener.open.side_effect = reply
        with patch.object(assets, 'load_plan', return_value=plan), patch.object(assets, 'build_opener', return_value=opener):
            result = assets.prepare(self.root / 'bundle', 'b')
            self.assertEqual(result['status'], 'assets_ready'); self.assertFalse(result['model_run'])
            self.assertEqual(result['tracks'], 2); self.assertEqual(result['cache_files'], 22)
            self.assertEqual(assets.verify_assets(self.root / 'bundle', 'b', plan)['status'], 'assets_ready')
        self.assertTrue((self.root / 'bundle/ready.json').exists())
        self.assertFalse(list((self.root / 'bundle').rglob('*.partial')))


if __name__ == '__main__': unittest.main()
