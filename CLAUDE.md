# Spinnaker + PySide6 Template

Primary agent guide for this repository.

## What This Repo Is

Desktop camera application template for FLIR Spinnaker + PySide6, with mock-camera mode and test scaffolding.

## Standard Commands

- `just install`
- `just install-spinnaker`
- `just sync` (preserves Spinnaker reinstall flow)
- `just run`
- `just run-mock`
- `just test`
- `just test-mock`
- `just lint`
- `just format`
- `just typecheck`
- `just run-ci`

## Hardware Caveats

- Python `3.10` is required for Spinnaker SDK compatibility.
- Spinnaker Python bindings are not on PyPI.
- Use `just sync` instead of raw `uv sync` to preserve/reinstall Spinnaker bindings.

## Template Bootstrap Flow

- Run `just bootstrap` to rename template metadata and identifiers.

## Post-First-Build Cleanup (Required)

After the first successful build and smoke test:
1. Run `just template-clean`
2. Remove or replace template/demo-specific UI text/assets and example behaviors
3. Update `CLAUDE.md` and `ProjectMap.md` to describe the actual application

## Validation

- `just test-mock`
- `just lint`
- `just typecheck`
- `just run-ci`

## Fast Search

- Camera interfaces/impls: `rg -n "class .*Camera|Protocol|ABC" src/camera`
- UI widgets: `rg -n "QWidget|QMainWindow|Signal" src/ui`
- Hardware-gated tests: `rg -n "hardware" tests`
