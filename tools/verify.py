# SPDX-License-Identifier: MIT
"""Run only the public repository's checks, without proprietary inputs."""
import os
from pathlib import Path
import subprocess
import sys


def main():
    root = Path(__file__).resolve().parents[1]
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    for mode in ([], ["--index"], ["--history"]):
        subprocess.run([sys.executable, "-B", "tools/publication_guard.py", *mode],
                       cwd=root, env=env, check=True)
    subprocess.run([sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests", "-v"],
                   cwd=root, env=env, check=True)
    subprocess.run(["git", "diff", "--check"], cwd=root, check=True)
    subprocess.run(["git", "diff", "--cached", "--check"], cwd=root, check=True)
    print("Public tools verified; no game inputs used.")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError:
        raise SystemExit(1)
