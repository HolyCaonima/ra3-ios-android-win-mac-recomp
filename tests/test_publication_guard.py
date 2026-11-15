# SPDX-License-Identifier: MIT
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import publication_guard as guard


class BlobTests(unittest.TestCase):
    def test_safe_text_and_unknown_path(self):
        self.assertEqual(guard.inspect_blob("note.md", b"original prose\n", "100644", {"note.md"}), [])
        self.assertTrue(guard.inspect_blob("extra.md", b"text", "100644", {"note.md"}))

    def test_disguised_content(self):
        examples = [
            b"MZ" + b"synthetic executable",
            b"\x7fELF" + b"synthetic executable",
            b"PK\x03\x04" + b"synthetic archive",
            b"\x00text",
            b"\xff\xfe",
            b"version https://git-lfs.github.com/spec/v1\n",
            b"a" * (guard.MAX_BYTES + 1),
            ("ghp_" + "X" * 36).encode(),
            ("-----BEGIN " + "PRIVATE KEY-----").encode(),
            ("/Users/" + "synthetic-person/file").encode(),
            ("sub_" + "01234567").encode(),
            ("0x12, " * 20).encode(),
        ]
        for number, data in enumerate(examples):
            with self.subTest(case=number):
                self.assertTrue(guard.inspect_blob("note.md", data, "100644", {"note.md"}))

    def test_links_and_submodules(self):
        for mode in ("120000", "160000"):
            self.assertTrue(guard.inspect_blob("note.md", b"", mode, {"note.md"}))


class RepositoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.git("init", "-q")
        self.git("config", "user.name", "Synthetic Test")
        self.git("config", "user.email", "test@example.invalid")
        self.git("config", "commit.gpgsign", "false")
        self.git("config", "core.hooksPath", str(self.root / "unused-hooks"))
        self.write_inventory(["PUBLICATION.json", "note.md"])
        (self.root / "note.md").write_text("original prose\n", encoding="utf-8")
        self.git("add", "PUBLICATION.json", "note.md")
        self.allowed = guard.inventory(self.root)

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.root), *args], stderr=subprocess.PIPE)

    def write_inventory(self, paths):
        (self.root / "PUBLICATION.json").write_text(json.dumps({
            "schema": 1,
            "files": [{"path": path, "provenance": "synthetic test"} for path in paths],
        }), encoding="utf-8")

    def test_unborn_history_and_clean_index(self):
        self.assertEqual(guard.check_history(self.root, self.allowed), [])
        self.assertEqual(guard.check_entries(guard.git_entries(self.root), self.allowed, True), [])

    def test_staged_blob_checked_instead_of_working_copy(self):
        path = self.root / "note.md"
        path.write_text("ghp_" + "X" * 36, encoding="utf-8")
        self.git("add", "note.md")
        path.write_text("clean working file\n", encoding="utf-8")
        self.assertEqual(guard.check_entries(guard.working_entries(self.root), self.allowed, True), [])
        errors = guard.check_entries(guard.git_entries(self.root), self.allowed, True)
        self.assertTrue(any("GitHub token" in error for error in errors))
        self.assertFalse(any("X" * 36 in error for error in errors))

    def test_history_detects_removed_content(self):
        self.git("commit", "-qm", "Synthetic baseline")
        (self.root / "extra.txt").write_text("not approved\n", encoding="utf-8")
        self.git("add", "extra.txt")
        self.git("commit", "-qm", "Synthetic disallowed content")
        self.git("rm", "-q", "extra.txt")
        self.git("commit", "-qm", "Synthetic removal")
        self.assertEqual(guard.check_entries(guard.git_entries(self.root), self.allowed, True), [])
        self.assertTrue(any("extra.txt" in error for error in guard.check_history(self.root, self.allowed)))

    def test_history_detects_changed_allowed_blob(self):
        self.git("commit", "-qm", "Synthetic baseline")
        (self.root / "note.md").write_text("ghp_" + "X" * 36, encoding="utf-8")
        self.git("add", "note.md")
        self.git("commit", "-qm", "Synthetic token")
        (self.root / "note.md").write_text("clean again\n", encoding="utf-8")
        self.git("add", "note.md")
        self.git("commit", "-qm", "Synthetic cleanup")
        self.assertTrue(any("GitHub token" in error for error in guard.check_history(self.root, self.allowed)))

    def test_working_tree_rejects_untracked_and_symlink(self):
        (self.root / "unexpected.txt").write_text("extra\n", encoding="utf-8")
        errors = guard.check_entries(guard.working_entries(self.root), self.allowed, True)
        self.assertTrue(any("unexpected.txt" in error for error in errors))
        (self.root / "unexpected.txt").unlink()
        (self.root / "note.md").unlink()
        (self.root / "note.md").symlink_to(self.root / "PUBLICATION.json")
        errors = guard.check_entries(guard.working_entries(self.root), self.allowed, True)
        self.assertTrue(any("symlink" in error for error in errors))

    def test_venv_excluded_only_from_working_scan(self):
        (self.root / ".venv").mkdir()
        (self.root / ".venv" / "local.txt").write_text("local only\n", encoding="utf-8")
        self.assertEqual(guard.check_entries(guard.working_entries(self.root), self.allowed, True), [])
        self.git("add", ".venv/local.txt")
        self.assertTrue(guard.check_entries(guard.git_entries(self.root), self.allowed, True))

    def test_missing_inventory_file(self):
        (self.root / "note.md").unlink()
        self.assertTrue(guard.check_entries(guard.working_entries(self.root), self.allowed, True))

    def test_reject_bad_inventory(self):
        for paths in (["PUBLICATION.json", "../outside"], ["PUBLICATION.json", "PUBLICATION.json"]):
            self.write_inventory(paths)
            with self.assertRaises(ValueError):
                guard.inventory(self.root)

    def test_shallow_history_fails_closed(self):
        self.git("commit", "-qm", "Synthetic baseline")
        (self.root / ".git" / "shallow").write_bytes(self.git("rev-parse", "HEAD"))
        with self.assertRaises(ValueError):
            guard.check_history(self.root, self.allowed)


if __name__ == "__main__":
    unittest.main()
