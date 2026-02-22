from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]


def main() -> int:
    (ROOT / ".template-cleaned").write_text(
        "Template cleanup completed. Remove unused mock/demo assets and docs text.\n",
        encoding="utf-8",
    )
    print("Wrote .template-cleaned")
    print("Manual follow-up:")
    print("- Keep or remove mock camera mode depending on product needs")
    print("- Update CLAUDE.md and ProjectMap.md for the actual application")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
