"""Real Git integration checks using temporary bare remotes and independent clones."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).with_name("collab.py").resolve()


class CollaborationTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.remote = self.base / "shared.git"
        self.run_git(self.base, "init", "--bare", str(self.remote))
        self.a = self.base / "A"
        self.b = self.base / "B"
        for root in (self.a, self.b):
            self.run_git(self.base, "clone", str(self.remote), str(root))
            self.run_git(root, "config", "user.name", "Test")
            self.run_git(root, "config", "user.email", "test@example.invalid")
            self.run_git(root, "checkout", "-b", "task/initial")
            (root / ".gitignore").write_text(".local/\n")
            for account in ("a", "b"):
                path = root / f"docs/collaboration/account-{account}/latest.md"
                path.parent.mkdir(parents=True)
                path.write_text(f"Report {account}\n")
            self.run_git(root, "add", ".")
            self.run_git(root, "commit", "-m", f"test: initial {root.name}")
        # Independent source branches, as required for different accounts/tasks.
        self.run_git(self.b, "branch", "-m", "review/B")

    def run_git(self, root, *args):
        result = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True,
                                env=dict(os.environ, GIT_TERMINAL_PROMPT="0"))
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.strip()

    def command(self, root, action, account="a", expected=0):
        result = subprocess.run([sys.executable, str(SCRIPT), action, "--account", account],
                                cwd=root, capture_output=True, text=True)
        self.assertEqual(result.returncode, expected, result.stderr + result.stdout)
        return json.loads(result.stdout) if expected == 0 else result.stderr

    def remote_refs(self):
        return self.run_git(self.remote, "show-ref")

    def test_round_trip_and_dirty_reader_preserved(self):
        before = self.run_git(self.b, "rev-parse", "HEAD")
        published = self.command(self.a, "publish")
        dirty = self.b / "unfinished.txt"
        dirty.write_text("keep me")
        tracked = self.b / "docs/collaboration/account-b/latest.md"
        tracked.write_text("unfinished tracked report\n")
        self.command(self.b, "sync", "b")
        inbox = self.b / ".local/collaboration/inbox/account-a"
        self.assertEqual((inbox / "latest.md").read_text(), "Report a\n")
        info = json.loads((inbox / "handoff.json").read_text())
        self.assertEqual(info["source_sha"], published["source_sha"])
        self.assertEqual(info["report_sha256"], hashlib.sha256(b"Report a\n").hexdigest())
        self.assertEqual(self.run_git(self.b, "rev-parse", "HEAD"), before)
        self.assertEqual(dirty.read_text(), "keep me")
        self.assertEqual(tracked.read_text(), "unfinished tracked report\n")
        self.run_git(self.b, "cat-file", "-e", f'{published["source_sha"]}^{{commit}}')

    def test_missing_feed_not_delivery(self):
        result = self.command(self.a, "sync")
        self.assertEqual(result["b"]["status"], "not_published")
        self.assertFalse((self.a / ".local/collaboration/inbox/account-b/latest.md").exists())

    def test_b_publish_does_not_overwrite_a(self):
        first = self.command(self.a, "publish")
        self.command(self.b, "publish", "b")
        received = self.command(self.a, "sync")
        self.assertEqual(received["a"]["feed_sha"], first["feed_sha"])
        self.assertEqual(received["b"]["status"], "fetched")

    def test_switch_task_keeps_feed_history(self):
        first = self.command(self.a, "publish")
        self.run_git(self.a, "checkout", "--orphan", "task/next")
        self.run_git(self.a, "commit", "-m", "test: independent task")
        second = self.command(self.a, "publish")
        parent = self.run_git(self.remote, "rev-parse", second["feed_sha"] + "^")
        self.assertEqual(parent, first["feed_sha"])

    def test_dirty_publish_refused(self):
        (self.a / "pending.txt").write_text("uncommitted")
        error = self.command(self.a, "publish", expected=1)
        self.assertIn("not clean", error)
        self.assertEqual(self.run_git(self.remote, "for-each-ref"), "")

    def test_main_publish_refused(self):
        self.run_git(self.a, "branch", "-m", "main")
        error = self.command(self.a, "publish", expected=1)
        self.assertIn("never main", error)
        self.assertEqual(self.run_git(self.remote, "for-each-ref"), "")

    def test_source_conflict_is_atomic(self):
        self.command(self.a, "publish")
        before = self.remote_refs()
        self.run_git(self.b, "branch", "-m", "task/initial")
        self.command(self.b, "publish", "b", expected=1)
        self.assertEqual(self.remote_refs(), before)

    def test_offline_sync_keeps_cache_and_fails(self):
        self.command(self.a, "publish")
        self.command(self.b, "sync", "b")
        cache = self.b / ".local/collaboration/inbox/account-a/receipt.json"
        before = cache.read_bytes()
        self.run_git(self.b, "remote", "set-url", "origin", str(self.base / "missing.git"))
        self.assertIn("NOT a fresh sync", self.command(self.b, "sync", "b", expected=1))
        self.assertEqual(cache.read_bytes(), before)

    def test_rewritten_feed_is_refused(self):
        self.command(self.a, "publish")
        self.command(self.b, "sync", "b")
        cache = self.b / ".local/collaboration/inbox/account-a/receipt.json"
        before = cache.read_bytes()
        # Simulate a remote force rewrite without actually using force-push in the tool.
        unrelated = self.run_git(self.b, "rev-parse", "HEAD")
        self.run_git(self.b, "push", "origin", "HEAD:refs/heads/review/B")
        self.run_git(self.remote, "update-ref", "refs/heads/collab/account-a", unrelated)
        self.command(self.b, "sync", "b", expected=1)
        self.assertEqual(cache.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
