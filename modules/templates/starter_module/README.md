# Starter Module

A minimal module template for IIMP. Copy this directory and rename to create a new module.

## Steps to create a new module

1. Copy this folder to the appropriate category under `modules/`
2. Rename the folder to your module's `id`
3. Update `module.json` with your metadata
4. Update `entry.py` to export your class
5. Implement logic in `module.py`
6. Add tests in `tests/`

## Files

| File | Purpose |
|---|---|
| `module.json` | Manifest — metadata and compatibility |
| `entry.py` | Exports the module class |
| `module.py` | Main module implementation |
| `README.md` | This file |

## Permissions

- `storage.read` — reads module persistent data

## Limitations

This is a template only. No real functionality.
