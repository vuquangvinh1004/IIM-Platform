# IIMP v1.0 Release Checklist

This checklist must be completed and signed-off before tagging the `v1.0.0` release.

---

## Section 1 — Code Quality

- [ ] All tests pass: `python -m pytest tests/` → 0 failures
- [ ] Coverage ≥ 80% for `core/`: `pytest --cov=core` reports ≥ 80%
- [ ] No open `TODO` / `FIXME` / `HACK` markers in non-test source files
- [ ] `requirements.txt` lists exact major/minor versions for all runtime deps
- [ ] `requirements-dev.txt` is up to date
- [ ] `config/settings.py` → `APP_VERSION = "1.0.0"` (bump from pre-release)
- [ ] `.env.example` lists all supported environment variables with defaults

---

## Section 2 — Documentation

- [ ] `docs/quickstart.md` reviewed and accurate for v1.0 feature set
- [ ] `docs/module_sdk.md` matches `IIMP_MODULE_SDK.md` — no stale references
- [ ] `README.md` updated: version badge, installation instructions, screenshot
- [ ] `CHANGELOG.md` entry written for v1.0.0
- [ ] All public API methods have docstrings

---

## Section 3 — Module Integrity

- [ ] `modules/templates/starter_module/` loads without error on a clean install
- [ ] `modules/statistics/normal_distribution/` loads and exports correctly
- [ ] `modules/templates/headless_test_module/` is listed as a dev-only template
  (not shipped in the release installer if not intended for end users)
- [ ] All bundled module `module.json` manifests validate against `sdk_version: 1.0.0`
- [ ] No bundled module has `min_platform_version` greater than `1.0.0`

---

## Section 4 — Platform Behaviour

- [ ] Cold start (fresh `%APPDATA%\IIMP\` directory) completes without errors
- [ ] DB schema creates correctly on first run; no migration failures
- [ ] Module Library shows all bundled modules after first scan
- [ ] Session state is saved on module switch and restored on re-open
- [ ] Export produces a valid file for all modules with `supports_export: true`
- [ ] Application exits cleanly (no orphaned threads or DB lock files)

---

## Section 5 — Build & Packaging

- [ ] `pyinstaller iimp.spec` completes without errors
- [ ] `dist/IIMP/IIMP.exe` launches on the build machine
- [ ] `dist/IIMP/IIMP.exe` launches on a separate machine **without Python installed**
- [ ] All bundled modules are present under `dist/IIMP/modules/`
- [ ] File size of `dist/IIMP/` directory is reasonable (< 600 MB)
- [ ] Inno Setup project built → `IIMP_Setup_v1.0.0.exe`
- [ ] Installer runs on a clean Windows 10 VM
- [ ] Uninstaller cleanly removes all application files

---

## Section 6 — Security

- [ ] No hard-coded credentials, secrets, or API keys in source
- [ ] SQLite database is stored in the user's `%APPDATA%` directory (not system-wide)
- [ ] Module sandbox policy (`sandbox_policy.py`) rejects incompatible modules
- [ ] Export paths are constrained to the configured export directory
- [ ] No shell execution (`os.system`, `subprocess` with `shell=True`) in core or modules

---

## Section 7 — Final Sign-off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Lead Developer | | | |
| QA | | | |
| Release Manager | | | |

**Tag command (run after all boxes are checked):**

```bash
git tag -a v1.0.0 -m "Release v1.0.0"
git push origin v1.0.0
```

---

*IIMP Release Process · Phase 6 Deliverable*
