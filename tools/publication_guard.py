# SPDX-License-Identifier: MIT
"""Conservative publication checks, not an ownership or secrecy proof.

Default: inspect working files. --index: inspect actual Git blobs staged for
commit. --history: inspect all snapshots reachable from local Git refs and HEAD.
Always use the current reviewed inventory, including for historical snapshots.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess

MAX_BYTES = 256 * 1024
PATTERNS = (
    ("private key", re.compile(r"-----BEGIN (?:[A-Z0-9]+ )*PRIVATE KEY-----")),
    ("GitHub token", re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})\b")),
    ("cloud key", re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")),
    ("service token", re.compile(r"\b(?:sk-(?:proj-)?[A-Za-z0-9_-]{24,}|xox[baprs]-[A-Za-z0-9-]{20,})\b")),
    ("credential URL", re.compile(r"https?://[^\s/:@]+:[^\s/@]+@")),
    ("personal home path", re.compile(r"(?:/(?:Users|home)/[A-Za-z0-9_.-]+|[A-Za-z]:[\\/]Users[\\/][A-Za-z0-9_.-]+)")),
    ("generated guest symbol", re.compile(r"\b(?:sub|loc|off|unk|byte|word|dword)_[0-9A-Fa-f]{8}\b")),
    ("embedded byte array", re.compile(r"(?:0x[0-9a-fA-F]{2}\s*,\s*){16,}")),
    ("long encoded payload", re.compile(r"[A-Za-z0-9+/=_-]{512,}")),
)
MAGIC = (b"MZ", b"\x7fELF", b"PK\x03\x04", b"\x1f\x8b", b"\xcf\xfa\xed\xfe", b"\xfe\xed\xfa\xcf")


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], stderr=subprocess.PIPE)


def inventory(root):
    document = json.loads((root / "PUBLICATION.json").read_text(encoding="utf-8"))
    if document.get("schema") != 1:
        raise ValueError("unsupported publication inventory schema")
    allowed = set()
    for entry in document["files"]:
        path = entry["path"]
        pure = PurePosixPath(path)
        if (not path or pure.is_absolute() or ".." in pure.parts or "\\" in path
                or str(pure) != path or path in allowed or pure.parts[0] in {".git", ".venv"}
                or not entry.get("provenance")):
            raise ValueError("invalid or duplicate inventory entry")
        allowed.add(path)
    if "PUBLICATION.json" not in allowed:
        raise ValueError("inventory must include itself")
    return allowed


def reviewed_images(root):
    """Only individually reviewed JPEG bytes are exempt from text checks."""
    document = json.loads((root / "PUBLICATION.json").read_text(encoding="utf-8"))
    images = {}
    for entry in document["files"]:
        if entry.get("kind") != "documentation-screenshot":
            continue
        path = entry["path"]
        digest = entry.get("sha256", "")
        if (not re.fullmatch(r"docs/images/[a-z0-9-]+\.jpg", path)
                or not re.fullmatch(r"[0-9a-f]{64}", digest)
                or not re.fullmatch(r"https://www\.bilibili\.com/video/BV[A-Za-z0-9]+/", entry.get("source", ""))
                or not isinstance(entry.get("timestamp_seconds"), (int, float))
                or entry["timestamp_seconds"] < 0
                or entry.get("rights") != "Documentation only; game imagery excluded from MIT"):
            raise ValueError("incomplete screenshot review record")
        images[path] = digest
    if len(images) > 6:
        raise ValueError("too many documentation screenshots")
    return images


def inspect_blob(path, data, mode, allowed, images=None):
    problems = []
    if path not in allowed:
        problems.append("path is not in reviewed inventory")
    if mode not in {"100644", "100755"}:
        problems.append("symlink, submodule or unsupported file mode")
    if len(data) > MAX_BYTES:
        problems.append("file exceeds public size limit")
    if path in (images or {}):
        if hashlib.sha256(data).hexdigest() != images[path]:
            problems.append("screenshot differs from reviewed SHA-256")
        if not data.startswith(b"\xff\xd8\xff") or not data.endswith(b"\xff\xd9"):
            problems.append("reviewed screenshot must be a complete JPEG")
        return problems
    if data.startswith(MAGIC):
        problems.append("binary/archive signature")
    if data.startswith(b"version https://git-lfs.github.com/spec/v1"):
        problems.append("LFS pointer")
    try:
        content = data.decode("utf-8")
    except UnicodeDecodeError:
        return problems + ["not UTF-8 text"]
    if any(ord(char) < 32 and char not in "\n\r\t" for char in content):
        problems.append("binary control characters")
    for label, pattern in PATTERNS:
        if pattern.search(content):
            problems.append(label)
    return problems


def working_entries(root):
    # Never follow symlinks, including directory symlinks.
    import os
    for folder, dirs, names in os.walk(root, followlinks=False):
        base = Path(folder)
        if base == root:
            dirs[:] = [name for name in dirs if name not in {".git", ".venv"}]
            names = [name for name in names if name != ".git"]
        for name in list(dirs):
            path = base / name
            if path.is_symlink():
                dirs.remove(name)
                names.append(name)
        for name in sorted(names):
            path = base / name
            relative = path.relative_to(root).as_posix()
            if path.is_symlink():
                yield relative, b"", "120000"
            else:
                yield relative, path.read_bytes(), "100644"


def git_entries(root, commit=None):
    args = ("ls-tree", "-r", "-z", commit) if commit else ("ls-files", "--stage", "-z")
    for record in git(root, *args).split(b"\0"):
        if not record:
            continue
        metadata, path = record.split(b"\t", 1)
        fields = metadata.decode("ascii").split()
        if commit:
            mode, kind, oid = fields
            readable = kind == "blob"
        else:
            mode, oid, stage = fields
            if stage != "0":
                raise ValueError("unmerged index entries")
            readable = mode != "160000"
        data = git(root, "cat-file", "blob", oid) if readable else b""
        yield path.decode("utf-8"), data, mode


def check_entries(entries, allowed, require_complete=False, images=None):
    problems, seen = [], set()
    for path, data, mode in entries:
        seen.add(path)
        for reason in inspect_blob(path, data, mode, allowed, images):
            # Report paths/reasons only, never print matching sensitive content.
            problems.append(f"{path!r}: {reason}")
    if require_complete:
        problems.extend(f"{path!r}: inventory file missing" for path in sorted(allowed - seen))
    return problems


def check_history(root, allowed, images=None):
    if git(root, "rev-parse", "--is-shallow-repository").strip() == b"true":
        raise ValueError("shallow history: fetch full history before publication")
    heads = ["--all"]
    try:
        git(root, "rev-parse", "--verify", "HEAD")
        heads.append("HEAD")
    except subprocess.CalledProcessError:
        pass  # A newly initialized repository has no commits yet.
    commits = git(root, "rev-list", *heads).decode("ascii").splitlines()
    problems, checked = [], set()
    for commit in commits:
        for path, data, mode in git_entries(root, commit):
            # Hash content locally only to avoid repeated pattern work.
            identity = (path, mode, hashlib.sha256(data).digest())
            if identity in checked:
                continue
            checked.add(identity)
            for reason in inspect_blob(path, data, mode, allowed, images):
                problems.append(f"{commit[:12]}:{path!r}: {reason}")
    return problems


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--index", action="store_true")
    selection.add_argument("--history", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    try:
        allowed = inventory(root)
        images = reviewed_images(root)
        if args.history:
            problems = check_history(root, allowed, images)
        else:
            entries = git_entries(root) if args.index else working_entries(root)
            problems = check_entries(entries, allowed, require_complete=True, images=images)
        if problems:
            print("Publication check failed:")
            print("\n".join(problems))
            return 1
    except (OSError, ValueError, KeyError, TypeError, subprocess.CalledProcessError):
        print("Publication check failed: could not validate inventory, files or full Git state.")
        return 1
    print("Publication check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
