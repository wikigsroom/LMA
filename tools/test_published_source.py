"""Check post-release documentation auditing without models, browsers or devices."""
import copy
import hashlib
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import warnings
import zipfile

import program_release

ROOT = Path(__file__).resolve().parents[1]


class PublishedSourceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="readme-audit-", dir=ROOT / "build")
        base = Path(self.temporary.name)
        self.repository = base / "repository"
        self.repository.mkdir()
        self.source = base / "source.zip"
        self.files = {"README.md": b"# Original README\n",
                      "app/Runner.java": b"class Runner {}\r\n"}
        for name, data in self.files.items():
            path = self.repository / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        self.git("init", "-q")
        self.git("config", "core.autocrlf", "false")
        self.git("add", "--", *self.files)
        self.git("-c", "user.name=LMA audit fixture", "-c", "user.email=lma-audit@example.invalid",
                 "-c", "commit.gpgsign=false", "commit", "-qm", "Immutable fixture")
        self.git("tag", "v0.3.1")
        self.root_patch = patch.object(program_release, "ROOT", self.repository)
        self.version_patch = patch.object(program_release, "VERSION", "0.3.1")
        self.root_patch.start()
        self.version_patch.start()
        self.index = self.package(self.files)

    def tearDown(self):
        self.version_patch.stop()
        self.root_patch.stop()
        self.temporary.cleanup()

    def git(self, *args):
        return subprocess.run(["git", *args], cwd=self.repository, check=True, capture_output=True)

    def package(self, files):
        with zipfile.ZipFile(self.source, "w", zipfile.ZIP_DEFLATED) as archive:
            for name, data in files.items():
                archive.writestr("LMA/" + name, data)
        return {"sha256": program_release.sha(self.source),
                "files": {name: {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
                          for name, data in files.items()}}

    def check(self, *, published=True, index=None):
        program_release.check_source_archive(index or self.index, self.source, published=published)

    def test_current_and_tagged_snapshots_pass(self):
        self.check()
        self.check(published=False)

    def test_readme_edits_pass_only_published_mode(self):
        (self.repository / "README.md").write_text("# Expanded documentation\n", encoding="utf-8")
        self.check()
        with self.assertRaisesRegex(AssertionError, "Stale archive source"):
            self.check(published=False)

    def test_new_document_does_not_rewrite_old_archive(self):
        (self.repository / "new-guide.md").write_text("New guide", encoding="utf-8")
        self.check()
        with self.assertRaisesRegex(AssertionError, "Repackage"):
            self.check(published=False)

    def test_removed_current_document_preserves_tag_identity(self):
        (self.repository / "README.md").unlink()
        self.check()
        with self.assertRaises(AssertionError):
            self.check(published=False)

    def test_forged_index_and_archive_cannot_replace_tagged_bytes(self):
        files = dict(self.files, **{"README.md": b"= Original README\n"})
        forged = self.package(files)
        with self.assertRaisesRegex(AssertionError, "differs from published tag"):
            self.check(index=forged)

    def test_extra_index_file_rejected(self):
        index = copy.deepcopy(self.index)
        index["files"]["extra.md"] = dict(index["files"]["README.md"])
        with self.assertRaisesRegex(AssertionError, "index differs"):
            self.check(index=index)

    def test_missing_index_file_rejected(self):
        index = copy.deepcopy(self.index)
        del index["files"]["README.md"]
        with self.assertRaisesRegex(AssertionError, "index differs"):
            self.check(index=index)

    def test_duplicate_archive_member_rejected(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            with zipfile.ZipFile(self.source, "a") as archive:
                archive.writestr("LMA/README.md", self.files["README.md"])
        self.index["sha256"] = program_release.sha(self.source)
        with self.assertRaisesRegex(AssertionError, "Unexpected source archive entries"):
            self.check()

    def test_unindexed_archive_member_rejected(self):
        with zipfile.ZipFile(self.source, "a") as archive:
            archive.writestr("LMA/unindexed.md", b"not in tag")
        self.index["sha256"] = program_release.sha(self.source)
        with self.assertRaisesRegex(AssertionError, "Unexpected source archive entries"):
            self.check()

    def test_archive_hash_rejected(self):
        self.index["sha256"] = "0" * 64
        with self.assertRaisesRegex(AssertionError, "archive hash mismatch"):
            self.check()

    def test_entry_size_rejected(self):
        self.index["files"]["README.md"]["bytes"] += 1
        with self.assertRaisesRegex(AssertionError, "Source size mismatch"):
            self.check()

    def test_entry_digest_rejected(self):
        self.index["files"]["README.md"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(AssertionError, "content hash mismatch"):
            self.check()

    def test_truncated_zip_rejected(self):
        self.source.write_bytes(self.source.read_bytes()[:20])
        self.index["sha256"] = program_release.sha(self.source)
        with self.assertRaises(zipfile.BadZipFile):
            self.check()

    def test_missing_tag_fails_closed(self):
        with patch.object(program_release, "VERSION", "9.9.9"):
            with self.assertRaises(subprocess.CalledProcessError):
                self.check()


if __name__ == "__main__":
    unittest.main(verbosity=2)
