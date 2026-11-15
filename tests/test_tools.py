# SPDX-License-Identifier: MIT
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from shotdiff import compare


class ImageTests(unittest.TestCase):
    def test_identical_and_threshold_boundary(self):
        a = Image.new("RGB", (3, 1))
        b = Image.new("RGB", (3, 1))
        b.putdata([(0, 0, 0), (24, 0, 0), (25, 0, 0)])
        same, _ = compare(a, a)
        self.assertEqual(same["identical"], 1)
        stats, diff = compare(a, b)
        self.assertEqual(stats["identical"], 1 / 3)
        self.assertEqual(stats["small"], 1 / 3)
        self.assertEqual(stats["big"], 1 / 3)
        self.assertAlmostEqual(stats["mean_absolute"], 49 / 9)
        self.assertEqual(diff.getpixel((2, 0)), (25, 0, 0))

    def test_bad_sizes_and_threshold(self):
        a = Image.new("RGB", (1, 1))
        with self.assertRaises(ValueError):
            compare(a, Image.new("RGB", (2, 1)))
        with self.assertRaises(ValueError):
            compare(a, a, -1)
        with self.assertRaises(ValueError):
            compare(a, a, 256)

    def test_cli_output_and_no_input_overwrite(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            a, b, output = (folder / name for name in ("a.png", "b.png", "difference.png"))
            Image.new("RGB", (2, 2)).save(a)
            Image.new("RGB", (2, 2), (40, 0, 0)).save(b)
            command = [sys.executable, "-B", str(ROOT / "tools" / "shotdiff.py"), str(a), str(b)]
            result = subprocess.run([*command, str(output)], capture_output=True, text=True, check=True)
            self.assertIn("big diffs 100.00%", result.stdout)
            with Image.open(output) as image:
                self.assertEqual(image.getpixel((0, 0)), (255, 0, 0))
            original = a.read_bytes()
            result = subprocess.run([*command, str(a)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(a.read_bytes(), original)


class BuildProfileTests(unittest.TestCase):
    def test_configure_switch_and_invalid_profile(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            command = ["cmake", "-S", str(ROOT / "examples" / "build-profile"), "-B", str(output)]
            # Same cache is reconfigured to exercise profile ownership.
            for profile, configuration in (("release", "Release"), ("dev", "RelWithDebInfo"), ("release", "Release")):
                subprocess.run([*command, f"-DRA3_BUILD_PROFILE={profile}"], capture_output=True, check=True)
                metadata = json.loads((output / "ra3-build-profile.json").read_text())
                self.assertEqual(metadata, {"profile": profile, "cmake_configuration": configuration})
                header = (output / "build-profile" / "ra3_build_profile.h").read_text()
                self.assertIn(f'"{profile}"', header)
                cache = (output / "CMakeCache.txt").read_text()
                self.assertIn(f"CMAKE_BUILD_TYPE:STRING={configuration}", cache)
            invalid = subprocess.run([*command, "-DRA3_BUILD_PROFILE=unknown"], capture_output=True, text=True)
            self.assertNotEqual(invalid.returncode, 0)
            self.assertIn("must be dev or release", invalid.stderr)


if __name__ == "__main__":
    unittest.main()
