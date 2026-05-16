# Integrated Interactive Module Platform

[![Python CI](https://github.com/vuquangvinh1004/IIM-Platform/actions/workflows/python-ci.yml/badge.svg)](https://github.com/vuquangvinh1004/IIM-Platform/actions/workflows/python-ci.yml)
[![Design Lint](https://github.com/vuquangvinh1004/IIM-Platform/actions/workflows/design-lint.yml/badge.svg)](https://github.com/vuquangvinh1004/IIM-Platform/actions/workflows/design-lint.yml)
[![Windows Package Smoke](https://github.com/vuquangvinh1004/IIM-Platform/actions/workflows/windows-package-smoke.yml/badge.svg)](https://github.com/vuquangvinh1004/IIM-Platform/actions/workflows/windows-package-smoke.yml)

Desktop platform for interactive modular applications. Built with Python and PySide6.

## Requirements

- Python >= 3.11
- See `requirements.txt` for dependencies

## Setup

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

## Run

```bash
python main.py
```

## Run Tests

```bash
pytest tests/ --cov=. --cov-report=term-missing
```

## Project Structure

See `IIMP_ARCHITECTURE.md` for full architecture documentation.

## Development

See `IIMP_MODULE_SDK.md` for module development guidelines.
See `IIMP_ROADMAP.md` for project roadmap and sprint planning.

## Design Philosophy

This project follows the principles from *A Philosophy of Software Design* (John Ousterhout) to keep accumulated complexity under control as the codebase grows.

Core principles applied throughout:

- **Deep modules** — services hide complex implementation behind simple interfaces; callers only need to know what, not how.
- **Information hiding** — each layer exposes only what callers truly need; DB schema, ORM models, and internal service detail never leak upward into UI.
- **Strategic programming** — 10–20% of every sprint is reserved for design improvement, not just new features. Tactical fixes always have a cleanup plan.
- **Pull complexity down** — business logic lives in `core/services/`, not in UI handlers. Shell only sees results.
- **Obvious code** — no magic strings or integers in logic; state and navigation use enums; signal-slot chains have comments explaining the trigger flow.

Full binding rules with layer-specific guidance: `IIMP_ARCHITECTURE.md §2.3`
Module-specific guidance: `IIMP_MODULE_SDK.md §2.3`
Sustainability and debt management: `IIMP_ROADMAP.md §9.5`
Source material: `philosophy_of_software_design.md`
