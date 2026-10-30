"""Loader trust-boundary tests with explicit synthetic pins; no real weights loaded."""
from copy import deepcopy
import hashlib
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import Mock, patch
import checkpoint_model as model


class CheckpointModelTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.path = self.root / 'synthetic.pt'; self.path.write_bytes(b'explicit synthetic checkpoint')
        self.pin = ('synthetic.pt', self.path.stat().st_size, hashlib.sha256(self.path.read_bytes()).hexdigest())
        self.sdk = SimpleNamespace(model=SimpleNamespace(load_state_dict=Mock(return_value=SimpleNamespace(
            missing_keys=[], unexpected_keys=[])), eval=Mock()))
        self.package = {'state_dict': {'module.weight': 'synthetic', 'module.text_branch.embeddings.position_ids': [0]}}
        for name, value in [('PINS', {'A': self.pin, 'B': self.pin}),
                            ('create_pinned_model', Mock(return_value=self.sdk))]:
            item = patch.object(model, name, value); item.start(); self.addCleanup(item.stop)
        item = patch.object(model.torch, 'load', side_effect=lambda *a, **k: deepcopy(self.package))
        self.load = item.start(); self.addCleanup(item.stop)

    def test_only_trusted_bytes_reach_restricted_strict_loader(self):
        sdk, meta = model.load_checkpoint(self.path, 'B')
        self.assertIs(sdk, self.sdk)
        self.load.assert_called_once_with(self.path, map_location='cpu', weights_only=True, mmap=True)
        self.sdk.model.load_state_dict.assert_called_once_with({'weight': 'synthetic'}, strict=True)
        self.assertTrue(meta['removed_nonlearned_position_ids'])
        self.assertEqual(meta['checkpoint_sha256'], self.pin[2])

    def test_unknown_model_rejected_before_construction(self):
        with self.assertRaises(ValueError): model.load_checkpoint(self.path, 'arbitrary')
        model.create_pinned_model.assert_not_called(); self.load.assert_not_called()

    def test_wrong_size_or_same_size_wrong_hash_rejected_before_construction(self):
        for raw in [b'wrong size', b'X' * self.pin[1]]:
            with self.subTest(raw=raw):
                self.path.write_bytes(raw)
                with self.assertRaises(ValueError): model.load_checkpoint(self.path, 'B')
        model.create_pinned_model.assert_not_called(); self.load.assert_not_called()

    def test_wrong_filename_rejected(self):
        path = self.root / 'renamed.pt'; path.write_bytes(self.path.read_bytes())
        with self.assertRaises(ValueError): model.load_checkpoint(path, 'B')
        self.load.assert_not_called()

    def test_symlink_and_hardlink_rejected(self):
        path = self.root / 'link.pt'; path.symlink_to(self.path)
        with self.assertRaises(ValueError): model.load_checkpoint(path, 'B')
        path.unlink(); path.hardlink_to(self.path)
        with self.assertRaises(ValueError): model.load_checkpoint(self.path, 'B')
        model.create_pinned_model.assert_not_called(); self.load.assert_not_called()

    def test_constructor_mutation_rejected_before_deserialization(self):
        model.create_pinned_model.side_effect = lambda: (self.path.write_bytes(b'X' * self.pin[1]), self.sdk)[1]
        with self.assertRaises(ValueError): model.load_checkpoint(self.path, 'B')
        self.load.assert_not_called()

    def test_malformed_state_and_duplicate_normalized_key_rejected(self):
        for value in [[], {'state_dict': []}, {'state_dict': {1: 0}},
                      {'state_dict': {'weight': 1, 'module.weight': 2}}]:
            self.package = value
            with self.subTest(value=value), self.assertRaises(ValueError): model.load_checkpoint(self.path, 'B')
        self.sdk.model.load_state_dict.assert_not_called()

    def test_strict_mismatch_is_not_retried_as_nonstrict(self):
        self.sdk.model.load_state_dict.side_effect = RuntimeError('synthetic strict mismatch')
        with self.assertRaises(RuntimeError): model.load_checkpoint(self.path, 'B')
        self.assertEqual(self.sdk.model.load_state_dict.call_count, 1)
        self.assertTrue(self.sdk.model.load_state_dict.call_args.kwargs['strict'])

    def test_reported_strict_missing_keys_rejected(self):
        self.sdk.model.load_state_dict.return_value = SimpleNamespace(missing_keys=['learned'], unexpected_keys=[])
        with self.assertRaises(ValueError): model.load_checkpoint(self.path, 'B')

    def test_only_registered_nonlearned_buffer_is_removed(self):
        self.package['state_dict']['module.other.position_ids'] = 'keep for strict load'
        model.load_checkpoint(self.path, 'B')
        self.assertIn('other.position_ids', self.sdk.model.load_state_dict.call_args.args[0])


if __name__ == '__main__': unittest.main()
