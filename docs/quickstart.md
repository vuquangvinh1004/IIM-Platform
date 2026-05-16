# IIMP Quick Start Guide

**Integrated Interactive Module Platform (IIMP) v1.0**

---

## 1. Requirements

| Item | Minimum |
|------|---------|
| Operating System | Windows 10 64-bit or later |
| RAM | 4 GB (8 GB recommended) |
| Storage | 500 MB free disk space |

If running from source, also requires:
- Python 3.11 or later
- All packages listed in `requirements.txt`

---

## 2. Installation

### Option A — Pre-built Installer (Recommended)

1. Download `IIMP_Setup_v1.0.0.exe` from the release page.
2. Run the installer and follow the on-screen steps.
3. Launch **IIMP** from the Start menu or desktop shortcut.

### Option B — Run from Source

```bash
# 1. Clone the repository
git clone <repo-url>
cd Nen_tang_tich_hop_moduler

# 2. Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. (Optional) Copy environment template
copy .env.example .env

# 5. Run the application
python main.py
```

---

## 3. First Run

When IIMP starts for the first time it will:

1. Create the runtime data directories under `%APPDATA%\IIMP\`.
2. Initialise the local SQLite database.
3. Scan `modules/` and register any bundled module templates.
4. Open the main window.

---

## 4. Main Window Overview

| Area | Purpose |
|------|---------|
| **Module Library** (left panel) | Browse and open available modules |
| **Workspace** (centre) | Active module view — only one module is active at a time |
| **Status Strip** (bottom) | Shows current module, platform version, and log messages |
| **Module Manager** (menu → Modules) | Install, enable, disable, or uninstall modules |

---

## 5. Opening a Module

1. Click a module card in the **Module Library**.
2. If the module has not been loaded before, a brief loading animation plays.
3. The module view appears in the **Workspace**.
4. Session state is auto-saved when you switch to a different module.

---

## 6. Installing a New Module

1. Go to **Modules → Install from folder…**
2. Select the root directory of the module (must contain `module.json`).
3. IIMP validates the manifest and registers the module.
4. The new module appears in the Module Library immediately.

---

## 7. Exporting Results

Modules that support export show an **Export** button in their toolbar.

1. Click **Export** inside the module.
2. Choose a file location in the save dialog.
3. The file is written to the chosen path.

---

## 8. Settings

Open **File → Settings** to configure:

- **Theme** — Light / Dark
- **Default export directory** — Where exported files are suggested
- **Module-specific settings** — Each module may expose its own settings panel

---

## 9. Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+W` | Close / deactivate current module |
| `Ctrl+E` | Export (if the active module supports it) |
| `F5` | Reload module list |
| `Ctrl+,` | Open Settings |
| `Ctrl+Q` | Quit application |

---

## 10. Troubleshooting

**Application does not start**
- Check that all Visual C++ Redistributables are installed (x64, 2019+).
- Run from a terminal to see error output: `IIMP.exe` in the install folder.

**Module fails to load**
- Open **Modules → Module Manager**, locate the module, and check the error column.
- Ensure the module's `min_platform_version` in `module.json` is ≤ `1.0.0`.

**Database errors on startup**
- Delete `%APPDATA%\IIMP\iimp.db` to reset (all settings and session history will be lost).

**Log files**
- Located at `%APPDATA%\IIMP\logs\iimp_<date>.log`.

---

## 11. For Developers — Creating a Module

See [module_sdk.md](module_sdk.md) for the full Module SDK documentation.

Quick summary:
1. Copy `modules/templates/starter_module/` to a new folder.
2. Edit `module.json` — give it a unique `id`, update `name`, `version`, `entry_point`.
3. Implement your module class by extending `BaseModule` (`core/module_runtime/base_module.py`).
4. Run IIMP and install via **Modules → Install from folder…**

---

*IIMP v1.0 · Documentation generated for release build.*
