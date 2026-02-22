from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]

CONTENT = """# ProjectMap

Fast search map for `spinnaker-pyside-template`.

## Top-Level Map

```text
spinnaker-pyside-template/
├── CLAUDE.md
├── ProjectMap.md
├── AGENTS.md
├── justfile
├── pyproject.toml
├── src/
│   ├── app/
│   ├── camera/
│   ├── core/
│   └── ui/
├── tests/
├── devops/
└── scripts/
```

## Entrypoints

- App main: `src/app/main.py`
- Camera interface: `src/camera/protocol.py`
- UI main window: `src/ui/main_window.py`

## Commands

- `just install`
- `just run`
- `just run-mock`
- `just test`
- `just test-mock`
- `just lint`
- `just typecheck`
- `just run-ci`
- `just bootstrap`
- `just template-clean`

## Search Recipes

- Camera code: `rg -n "class .*Camera|def get_frame" src/camera`
- UI widgets: `rg -n "QWidget|QMainWindow" src/ui`
- Hardware tests: `rg -n "hardware" tests`
"""


def main() -> int:
    (ROOT / "ProjectMap.md").write_text(CONTENT, encoding="utf-8")
    print("Updated ProjectMap.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
