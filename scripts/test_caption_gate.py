"""Synthetic persistent budget/locks and scale-normalized loss; no network/audio."""
from pathlib import Path
import tempfile,unittest,io,json
import numpy as np
from acquire_caption_gate import JournalBudget
sysmod=__import__('sys');sysmod.path.insert(0,str(Path(__file__).resolve().parents[1]/'services/audio-search'))
import tag_adapter as a


class GateTest(unittest.TestCase):
    def test_budget_charge_survives_reopen_and_prevents_read(self):
        with tempfile.TemporaryDirectory()as t:
            p=Path(t).resolve()/'events';b=JournalBudget(p,10);self.assertEqual(b.read(io.BytesIO(b'abc'),3),b'abc')
            resumed=JournalBudget(p,10);self.assertEqual(resumed.used,3);stream=io.BytesIO(b'x'*8)
            with self.assertRaises(ValueError):resumed.read(stream,8)
            self.assertEqual(stream.tell(),0)

    def test_truncated_or_throwing_body_is_conservatively_charged(self):
        class Bad:
            def read(self,n):raise TimeoutError('synthetic')
        with tempfile.TemporaryDirectory()as t:
            p=Path(t).resolve()/'events';b=JournalBudget(p,20)
            with self.assertRaises(TimeoutError):b.read(Bad(),10)
            self.assertEqual(JournalBudget(p,20).used,10)

    def test_partial_journal_is_not_silently_discarded(self):
        with tempfile.TemporaryDirectory()as t:
            p=Path(t).resolve()/'events';p.write_bytes(b'{"event":"charge"')
            with self.assertRaises(ValueError):JournalBudget(p,20)

    def test_parallel_reservations_respect_single_budget(self):
        from concurrent.futures import ThreadPoolExecutor
        with tempfile.TemporaryDirectory()as t:
            b=JournalBudget(Path(t).resolve()/'events',10)
            def one(_):
                try:b.read(io.BytesIO(b'a'*4),4);return 1
                except ValueError:return 0
            with ThreadPoolExecutor(max_workers=2)as pool:count=sum(pool.map(one,range(5)))
            self.assertEqual(count,2);self.assertEqual(b.used,8)

    def test_mean_loss_scale_is_invariant_to_duplicate_rows(self):
        rng=np.random.default_rng(7);x=a.unit(rng.normal(size=(5,4)));y=a.unit(rng.normal(size=(5,4)))
        w,_=a.fit(x,y,len(x)*1.0);z,_=a.fit(np.repeat(x,10,axis=0),np.repeat(y,10,axis=0),len(x)*10*1.0)
        np.testing.assert_allclose(w,z,atol=1e-12)

if __name__=='__main__':unittest.main()
