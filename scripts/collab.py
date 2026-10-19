#!/usr/bin/env python3
"""Exchange committed handoffs through per-account Git refs, without checkout/merge."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

ACCOUNTS = ("a", "b")
MAX_BYTES = 1024 * 1024
SCHEMA = "music-handoff-v1"


class SyncError(Exception):
    pass


def git(root, *args, data=None):
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0")
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *args], input=data, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, env=env, timeout=45,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise SyncError(f"Git could not complete: {type(exc).__name__}") from exc
    if result.returncode:
        # Git can include a credential-bearing remote URL in stderr. Do not echo it.
        raise SyncError(f"git {args[0]} failed (exit {result.returncode}); check network, credentials, refs and write access")
    return result.stdout


def stamp():
    return datetime.now(timezone.utc).isoformat()


def feed(account):
    return f"refs/heads/collab/account-{account}"


def local_feed(account):
    return f"refs/music-collab/received/account-{account}"


def remote_feeds(root, remote):
    raw = git(root, "ls-remote", "--heads", remote, *(feed(a) for a in ACCOUNTS))
    refs = {}
    for line in raw.decode("utf-8").splitlines():
        sha, name = line.split("\t", 1)
        for account in ACCOUNTS:
            if name == feed(account):
                refs[account] = sha
    return refs


def fetch_feed(root, remote, account, expected):
    previous = git(root, "for-each-ref", "--format=%(objectname)", local_feed(account)).decode().strip()
    pending = f"refs/music-collab/pending/account-{account}"
    git(root, "fetch", "--no-tags", remote, f"{feed(account)}:{pending}")
    actual = git(root, "rev-parse", pending).decode().strip()
    if actual != expected:
        raise SyncError("Remote handoff changed during fetch; retry sync")
    if previous:
        # Fetch outside refs/heads may accept non-FF updates even without '+'.
        # Explicit ancestry checking protects our last accepted handoff.
        git(root, "merge-base", "--is-ancestor", previous, actual)
    git(root, "update-ref", local_feed(account), actual, previous or "0" * len(actual))
    return actual


def read_blob(root, revision, name):
    spec = f"{revision}:{name}"
    size = int(git(root, "cat-file", "-s", spec))
    if size > MAX_BYTES:
        raise SyncError(f"Handoff file exceeds {MAX_BYTES} bytes")
    return git(root, "show", spec)


def validate(root, revision, account):
    try:
        info = json.loads(read_blob(root, revision, "handoff.json"))
        report = read_blob(root, revision, "latest.md")
        report.decode("utf-8")
        if info["schema"] != SCHEMA or info["account"] != account:
            raise ValueError("wrong schema/account")
        if not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", info["source_sha"]):
            raise ValueError("invalid source SHA")
        branch = info["source_branch"]
        if not isinstance(branch, str) or branch in ("main", "master") or branch.startswith("collab/"):
            raise ValueError("invalid source branch")
        git(root, "check-ref-format", f"refs/heads/{branch}")
        if info["report_sha256"] != hashlib.sha256(report).hexdigest():
            raise ValueError("report hash mismatch")
        if not isinstance(info["published_at"], str):
            raise ValueError("missing timestamp")
    except (KeyError, ValueError, TypeError, UnicodeError) as exc:
        raise SyncError(f"Invalid account {account.upper()} handoff: {exc}") from exc
    return info, report


def atomic_write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(content)
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def sync(root, remote):
    advertised = remote_feeds(root, remote)
    records = {}
    # Validate every available feed before replacing any cached content.
    for account, sha in advertised.items():
        actual = fetch_feed(root, remote, account, sha)
        info, report = validate(root, actual, account)
        source_ref = f"refs/music-collab/sources/account-{account}/{info['source_branch']}"
        git(root, "fetch", "--no-tags", remote, f"refs/heads/{info['source_branch']}:{source_ref}")
        git(root, "merge-base", "--is-ancestor", info["source_sha"], source_ref)
        records[account] = (actual, info, report)
    cache = root / ".local" / "collaboration" / "inbox"
    summary = {}
    for account in ACCOUNTS:
        folder = cache / f"account-{account}"
        receipt = {"account": account, "checked_at": stamp(), "remote": remote}
        if account in records:
            sha, info, report = records[account]
            atomic_write(folder / "latest.md", report)
            atomic_write(folder / "handoff.json", json.dumps(info, indent=2).encode() + b"\n")
            receipt.update(status="fetched", feed_sha=sha, source_sha=info["source_sha"])
        else:
            # A missing feed is never an acknowledgement or an empty successful delivery.
            receipt.update(status="not_published")
        atomic_write(folder / "receipt.json", json.dumps(receipt, indent=2).encode() + b"\n")
        summary[account] = receipt
    print(json.dumps(summary, indent=2))


def publish(root, remote, account):
    if git(root, "status", "--porcelain=v1").strip():
        raise SyncError("Working tree is not clean; commit intended files first (nothing was stashed or added)")
    branch = git(root, "symbolic-ref", "--quiet", "--short", "HEAD").decode().strip()
    if branch in ("main", "master") or branch.startswith("collab/"):
        raise SyncError("Publish from a task branch, never main/master or a handoff branch")
    source = git(root, "rev-parse", "HEAD").decode().strip()
    path = f"docs/collaboration/account-{account}/latest.md"
    entry = git(root, "ls-tree", source, "--", path).decode()
    if not entry.startswith("100644 blob "):
        raise SyncError(f"Commit a regular UTF-8 report at {path} first")
    report = read_blob(root, source, path)
    try:
        report.decode("utf-8")
    except UnicodeError as exc:
        raise SyncError("Report must be UTF-8") from exc
    advertised = remote_feeds(root, remote)
    previous = None
    if account in advertised:
        previous = fetch_feed(root, remote, account, advertised[account])
        validate(root, previous, account)
    info = {
        "schema": SCHEMA, "account": account, "published_at": stamp(),
        "source_branch": branch, "source_sha": source,
        "report_path": path, "report_sha256": hashlib.sha256(report).hexdigest(),
    }
    entries = []
    for name, content in (("latest.md", report), ("handoff.json", json.dumps(info, indent=2).encode() + b"\n")):
        blob = git(root, "hash-object", "-w", "--stdin", data=content).decode().strip()
        entries.append(f"100644 blob {blob}\t{name}\n")
    tree = git(root, "mktree", data="".join(entries).encode()).decode().strip()
    parents = ["-p", previous] if previous else []
    revision = git(root, "commit-tree", tree, *parents, "-m", f"docs: publish account {account.upper()} handoff").decode().strip()
    # Both refs succeed or neither does. Racing/non-FF source or feed writes are rejected.
    git(root, "push", "--atomic", remote, f"{source}:refs/heads/{branch}", f"{revision}:{feed(account)}")
    print(json.dumps({"status": "published", "account": account, "source_sha": source,
                      "source_branch": branch, "feed_sha": revision}, indent=2))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("sync", "publish"))
    parser.add_argument("--account", required=True, choices=ACCOUNTS)
    parser.add_argument("--remote", default="origin")
    options = parser.parse_args(argv)
    try:
        if options.remote.startswith("-") or not re.fullmatch(r"[A-Za-z0-9_.-]+", options.remote):
            raise SyncError("Use a configured Git remote name, not a URL or option")
        root = Path(git(Path.cwd(), "rev-parse", "--show-toplevel").decode().strip())
        if options.action == "sync":
            sync(root, options.remote)
        else:
            publish(root, options.remote, options.account)
    except SyncError as exc:
        print(f"{options.action} failed: {exc}. Cached reports, if any, are NOT a fresh sync.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
