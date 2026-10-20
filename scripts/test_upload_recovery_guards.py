"""Reject unrelated process/proof/DDL targets without starting services."""
import hashlib
from pathlib import Path
import time
import unittest
from unittest.mock import Mock, patch

from baseline import Baseline
from upload_fault_smoke import cleanup_constraints
from upload_integrity_smoke import validate_restart_proof


class RecoveryGuardsTest(unittest.TestCase):
    def test_unowned_process_is_never_signalled(self):
        runner = Baseline.__new__(Baseline)
        runner.children = [Mock(pid=123)]
        with patch('baseline.os.killpg') as kill:
            with self.assertRaises(RuntimeError):
                runner.stop_owned(Mock(pid=123))
            kill.assert_not_called()

    def test_reaped_backend_is_removed_from_watch_list(self):
        runner = Baseline.__new__(Baseline)
        old, other = Mock(pid=123), Mock(pid=124)
        old.poll.return_value = None
        runner.children = [old, other]
        with patch('baseline.os.killpg') as kill:
            runner.stop_owned(old)
            kill.assert_called_once()
        self.assertEqual([other], runner.children)

    def test_restart_requires_checkpoint_and_observed_process_transition(self):
        checkpoint = b'private checkpoint'
        root = Path('/isolated/checkout')
        now = time.time()
        proof = dict(schema='music-backend-restart-v1', slot='a', checkout=str(root),
                     prepared_state_sha256=hashlib.sha256(checkpoint).hexdigest(),
                     old_backend_launcher_pid=101, new_backend_launcher_pid=102,
                     old_backend_exit_confirmed=True, backend_port_released=True, new_backend_ready=True,
                     stopped_at_unix=now-2, restarted_at_unix=now-1)
        validate_restart_proof(proof, 'a', root, checkpoint, now-3)
        for key, value in [('slot','b'), ('checkout','/other'), ('prepared_state_sha256','bad'),
                           ('old_backend_launcher_pid',102), ('new_backend_launcher_pid',True),
                           ('old_backend_exit_confirmed',False), ('backend_port_released',False),
                           ('new_backend_ready',False), ('stopped_at_unix',now-4),
                           ('restarted_at_unix',now+60)]:
            with self.subTest(key=key), self.assertRaises(RuntimeError):
                validate_restart_proof({**proof,key:value},'a',root,checkpoint,now-3)

    def test_constraint_cleanup_attempts_remaining_names_after_failure(self):
        calls=[]
        def query(sql):
            calls.append(sql)
            if '_merge' in sql:
                raise RuntimeError('unavailable')
            if sql.startswith('ALTER'):return []
            return ['0']
        names=['music_fault_012345abcdef_insert','music_fault_012345abcdef_merge']
        errors=cleanup_constraints(query,names)
        self.assertEqual(1,len(errors))
        self.assertTrue(any('_insert' in sql for sql in calls))

    def test_invalid_constraint_names_never_reach_sql(self):
        query=Mock()
        self.assertTrue(cleanup_constraints(query,['foreign_constraint','music_fault_012345abcdef_insert`;DROP']))
        query.assert_not_called()

    def test_constraint_drop_requires_absence_confirmation(self):
        query=Mock(side_effect=[['1'], [], ['1']])
        self.assertTrue(cleanup_constraints(query,['music_fault_012345abcdef_count']))
        self.assertEqual('ALTER TABLE `file_upload` DROP CHECK `music_fault_012345abcdef_count`;',query.call_args_list[1].args[0])


if __name__ == '__main__':
    unittest.main()
