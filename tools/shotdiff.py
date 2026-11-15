# SPDX-License-Identifier: MIT
"""Compare user-supplied images; all examples/tests use synthetic data.

Usage: python tools/shotdiff.py A.png B.png [DIFF.png]
The optional difference image amplifies RGB differences by eight.
"""
import argparse
from pathlib import Path

from PIL import Image, ImageChops


def compare(a, b, threshold=24):
    """Return RGB statistics and an unamplified difference image.

    Alpha and metadata are ignored. Inputs are not aligned or resized.
    Fractions are per pixel; MAE is per channel on a 0..255 scale.
    """
    if not 0 <= threshold <= 255:
        raise ValueError("threshold must be between 0 and 255")
    if a.size != b.size:
        raise ValueError("image sizes differ")
    count = a.width * a.height
    if not count:
        raise ValueError("images must not be empty")
    difference = ImageChops.difference(a.convert("RGB"), b.convert("RGB"))
    small = big = total = 0
    # Iterating flattened RGB bytes avoids materializing tuples for all pixels.
    pixels = iter(difference.tobytes())
    for rgb in zip(pixels, pixels, pixels):
        peak = max(rgb)
        small += 0 < peak <= threshold
        big += peak > threshold
        total += sum(rgb)
    return {
        "identical": (count - small - big) / count,
        "small": small / count,
        "big": big / count,
        "mean_absolute": total / (3 * count),
    }, difference


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("a", type=Path)
    parser.add_argument("b", type=Path)
    parser.add_argument("output", nargs="?", type=Path)
    parser.add_argument("--threshold", type=int, default=24)
    args = parser.parse_args()
    try:
        if args.output and args.output.resolve() in {args.a.resolve(), args.b.resolve()}:
            raise ValueError("output must not overwrite either input")
        with Image.open(args.a) as a, Image.open(args.b) as b:
            stats, difference = compare(a, b, args.threshold)
            print(
                f"{a.width}x{a.height}: identical {stats['identical']:.2%}, "
                f"small diffs (<={args.threshold}) {stats['small']:.2%}, "
                f"big diffs {stats['big']:.2%}, mean abs {stats['mean_absolute']:.3f}"
            )
            if args.output:
                difference.point(lambda value: min(255, value * 8)).save(args.output)
    except (OSError, ValueError) as error:
        parser.exit(2, f"shotdiff: {error}\n")


if __name__ == "__main__":
    main()
