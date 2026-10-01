"""Acceptance entry point that must be run by the repository OUEM venv."""

from __future__ import annotations

import argparse
import platform
import sys

from ouem.runtime import validate_ouem_runtime


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-python", required=True)
    args = parser.parse_args()
    validate_ouem_runtime(args.expected_python)
    import ouem

    print(f"OUEM runtime OK: {sys.executable}")
    print(f"Python: {platform.python_version()}")
    print(f"OUEM: {ouem.__file__}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
