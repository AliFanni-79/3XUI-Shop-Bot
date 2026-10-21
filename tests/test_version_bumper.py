import os
import tempfile
import unittest
from pathlib import Path

from scripts.bump_version import compute_next_version, parse_version, update_file_contents
from xuishop.updates import _version_tuple, is_newer


class TestVersionBumper(unittest.TestCase):
    def test_parse_version(self):
        self.assertEqual(parse_version("26.2.2"), (26, 2, 2, None))
        self.assertEqual(parse_version("v26.2.2"), (26, 2, 2, None))
        self.assertEqual(parse_version("26.2.2.1"), (26, 2, 2, 1))
        self.assertEqual(parse_version("v26.2.2.5"), (26, 2, 2, 5))
        with self.assertRaises(ValueError):
            parse_version("")
        with self.assertRaises(ValueError):
            parse_version("26.2")

    def test_compute_prerelease(self):
        # Adding patch to 3-part version
        self.assertEqual(compute_next_version("26.2.2", "prerelease", override_year=26), "26.2.2.1")
        # Incrementing patch on 4-part version
        self.assertEqual(compute_next_version("26.2.2.1", "prerelease", override_year=26), "26.2.2.2")
        self.assertEqual(compute_next_version("26.2.2.9", "prerelease", override_year=26), "26.2.2.10")

    def test_compute_minor_bump(self):
        # From 3-part version
        self.assertEqual(compute_next_version("26.2.2", "minor", override_year=26), "26.2.3")
        # From 4-part prerelease version (removes patch)
        self.assertEqual(compute_next_version("26.2.2.1", "minor", override_year=26), "26.2.3")
        self.assertEqual(compute_next_version("26.2.2.15", "minor", override_year=26), "26.2.3")

    def test_compute_major_bump(self):
        # From 3-part version (removes patch, resets minor to 0)
        self.assertEqual(compute_next_version("26.2.2", "major", override_year=26), "26.3.0")
        # From 4-part prerelease version (removes patch, resets minor to 0)
        self.assertEqual(compute_next_version("26.2.2.1", "major", override_year=26), "26.3.0")
        self.assertEqual(compute_next_version("26.2.2.15", "major", override_year=26), "26.3.0")

    def test_automatic_year_rollover(self):
        # In next calendar year 27:
        self.assertEqual(compute_next_version("26.2.2", "prerelease", override_year=27), "27.2.2.1")
        self.assertEqual(compute_next_version("26.2.2.3", "minor", override_year=27), "27.2.3")
        self.assertEqual(compute_next_version("26.2.2.3", "major", override_year=27), "27.1.0")

    def test_update_files(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            v_file = p / "VERSION.txt"
            init_file = p / "__init__.py"
            pkg_file = p / "package.json"

            v_file.write_text("26.2.2\n", encoding="utf-8")
            init_file.write_text('VERSION = "26.2.2"\n\ndef install():\n    pass\n', encoding="utf-8")
            pkg_file.write_text('{\n  "name": "app",\n  "version": "26.2.2"\n}\n', encoding="utf-8")

            update_file_contents(v_file, "26.2.2.1")
            update_file_contents(init_file, "26.2.2.1")
            update_file_contents(pkg_file, "26.2.2.1")

            self.assertEqual(v_file.read_text(encoding="utf-8").strip(), "26.2.2.1")
            self.assertIn('VERSION = "26.2.2.1"', init_file.read_text(encoding="utf-8"))
            self.assertIn('"version": "26.2.2.1"', pkg_file.read_text(encoding="utf-8"))

    def test_updates_is_newer_with_prerelease(self):
        self.assertEqual(_version_tuple("26.2.2"), (26, 2, 2))
        self.assertEqual(_version_tuple("26.2.2.1"), (26, 2, 2, 1))

        # Prerelease is newer than base release
        self.assertTrue(is_newer("26.2.2.1", "26.2.2"))
        # Next prerelease is newer than previous prerelease
        self.assertTrue(is_newer("26.2.2.2", "26.2.2.1"))
        # Minor bump is newer than any previous prerelease
        self.assertTrue(is_newer("26.2.3", "26.2.2.9"))
        # Major bump is newer than any previous prerelease
        self.assertTrue(is_newer("26.3.0", "26.2.2.9"))
        # Old version is not newer
        self.assertFalse(is_newer("26.2.2.1", "26.2.2.2"))
