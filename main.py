from __future__ import annotations

import sys

from cli import build_parser, run_from_args
from errors import RZLogError


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        run_from_args(args)
        return 0
    except RZLogError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("Aborted by user.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())