"""`ds-check`: roda todas as verificações de conformidade no diretório atual."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ds_conformance.checks import CHECKS


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="ds-check", description=__doc__)
    parser.add_argument("path", nargs="?", default=".", help="raiz do projeto")
    parser.add_argument("--skip", action="append", default=[], choices=list(CHECKS))
    args = parser.parse_args(argv)
    root = Path(args.path).resolve()

    failed = 0
    for name, check in CHECKS.items():
        if name in args.skip:
            print(f"- {name} (pulado)")
            continue
        errors = check(root)
        print(f"{'✗' if errors else '✓'} {name}")
        for err in errors:
            print(f"    {err}")
        failed += bool(errors)

    if failed:
        print(f"\n{failed} verificação(ões) falharam.")
        sys.exit(1)
    print("\nTudo conforme.")


if __name__ == "__main__":
    main()
