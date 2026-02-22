from __future__ import annotations

import argparse
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _replace(path: pathlib.Path, replacements: dict[str, str]) -> None:
    text = path.read_text(encoding="utf-8")
    new = text
    for old, value in replacements.items():
        new = new.replace(old, value)
    if new != text:
        path.write_text(new, encoding="utf-8")
        print(f"updated {path.relative_to(ROOT)}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-name", default="Camera QC")
    parser.add_argument("--project-slug", default="camera-qc")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    replacements = {
        "Spinnaker + PySide6 Camera Application": f"{args.project_name} Application",
        "camera-qc": args.project_slug,
    }
    targets = [
        ROOT / "README.md",
        ROOT / "CLAUDE.md",
        ROOT / "ProjectMap.md",
        ROOT / "justfile",
        ROOT / "pyproject.toml",
        ROOT / "devops/camera-qc.desktop",
        ROOT / "devops/camera-qc.svg",
    ]
    for path in targets:
        if path.exists():
            if args.dry_run:
                print(f"would update {path.relative_to(ROOT)}")
            else:
                _replace(path, replacements)

    print("Next: just install && just run-mock && just test-mock && just lint")
    print("After first successful build, run: just template-clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
