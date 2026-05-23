"""QSS stylesheet for IIMP — light theme (default).

Shell-level visual decisions are mapped from ``DESIGN.md`` through the token
owner in ``ui.styles.design_tokens`` so views can style via object names and
semantic roles instead of scattered inline QSS.
"""
from __future__ import annotations

from ui.styles.design_tokens import COLORS, FONTS, RADII, SPACING, rgba


LIGHT_STYLESHEET = f"""
QWidget {{
    font-family: {FONTS['body']};
    font-size: 14px;
    color: {COLORS['on_background']};
    background-color: {COLORS['background']};
}}

QLabel {{
    background-color: transparent;
}}

QMainWindow {{
    background-color: {COLORS['background']};
}}

#sidebar {{
    background-color: {COLORS['primary']};
    color: {COLORS['on_primary']};
    border-right: 1px solid {rgba(COLORS['outline_variant'], 180)};
}}

#sidebar QPushButton {{
    background-color: transparent;
    color: {COLORS['on_primary']};
    border: none;
    border-radius: {RADII['md']}px;
    text-align: left;
    padding: 12px 16px;
    margin: 0 10px;
    font-family: {FONTS['body']};
    font-size: 14px;
    font-weight: 600;
}}

#sidebar QPushButton:hover {{
    background-color: {rgba(COLORS['on_primary'], 24)};
}}

#sidebar QPushButton:checked {{
    background-color: {COLORS['tertiary']};
    color: {COLORS['on_tertiary']};
}}

QStatusBar {{
    background-color: {COLORS['surface_container']};
    color: {COLORS['on_surface']};
    border-top: 1px solid {COLORS['outline_variant']};
    font-size: 11px;
}}

QToolBar {{
    background-color: {COLORS['surface']};
    border-bottom: 1px solid {COLORS['outline_variant']};
    spacing: {SPACING['xs']}px;
    padding: {SPACING['xs']}px {SPACING['sm']}px;
}}

QPushButton {{
    background-color: {COLORS['tertiary']};
    color: {COLORS['on_tertiary']};
    border: none;
    border-radius: {RADII['md']}px;
    min-height: 28px;
    padding: 8px 14px;
    font-family: "Segoe UI";
    font-size: 12px;
    font-weight: 700;
}}

QPushButton:hover {{
    background-color: {COLORS['tertiary_container']};
    color: {COLORS['on_tertiary_container']};
}}

QPushButton:pressed {{
    background-color: {COLORS['warning']};
    color: {COLORS['on_warning']};
}}

QPushButton:disabled {{
    background-color: {COLORS['surface_container_high']};
    color: {COLORS['outline']};
}}

QPushButton[role="secondary"] {{
    background-color: {COLORS['primary']};
    color: {COLORS['on_primary']};
}}

QPushButton[role="secondary"]:hover {{
    background-color: {COLORS['primary_container']};
}}

QPushButton[role="ghost"] {{
    background-color: transparent;
    color: {COLORS['primary']};
    border: 1px solid {COLORS['outline']};
}}

QPushButton[role="ghost"]:hover {{
    background-color: {COLORS['surface_container']};
    color: {COLORS['primary']};
}}

QPushButton[role="workspace-link"] {{
    min-width: 170px;
}}

QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
    background-color: {COLORS['surface']};
    border: 1px solid {COLORS['outline_variant']};
    border-radius: {RADII['md']}px;
    min-height: 24px;
    padding: 8px 10px;
    selection-background-color: {COLORS['primary_container']};
    selection-color: {COLORS['on_primary']};
}}

QSpinBox, QDoubleSpinBox {{
    padding-right: 8px;
}}

QSpinBox::up-button,
QSpinBox::down-button,
QDoubleSpinBox::up-button,
QDoubleSpinBox::down-button {{
    width: 0px;
    height: 0px;
    border: none;
    padding: 0px;
    margin: 0px;
    image: none;
}}

QComboBox {{
    padding-right: 26px;
}}

QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 20px;
    border-left: 1px solid {COLORS['outline_variant']};
    border-top-right-radius: {RADII['md']}px;
    border-bottom-right-radius: {RADII['md']}px;
    background-color: {COLORS['surface_container_low']};
}}

QComboBox::down-arrow {{
    image: none;
    width: 0px;
    height: 0px;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 7px solid {COLORS['on_surface']};
}}

QComboBox QAbstractItemView {{
    background-color: {COLORS['surface']};
    color: {COLORS['on_surface']};
    border: 1px solid {COLORS['outline_variant']};
    outline: none;
    selection-background-color: {COLORS['secondary_container']};
    selection-color: {COLORS['on_secondary_container']};
    padding: 4px;
}}

QTableWidget,
QTableView {{
    background-color: {COLORS['surface']};
    alternate-background-color: {COLORS['surface_container_low']};
    gridline-color: {COLORS['outline_variant']};
}}

QTableWidget QLineEdit,
QTableView QLineEdit,
QTableWidget QSpinBox,
QTableView QSpinBox,
QTableWidget QDoubleSpinBox,
QTableView QDoubleSpinBox,
QTableWidget QComboBox {{
    min-height: 20px;
    padding: 2px 6px;
}}

QTableWidget QPushButton,
QTableView QPushButton {{
    min-height: 20px;
    padding: 2px 8px;
}}

QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
    border-color: {COLORS['primary_container']};
}}

QLineEdit#librarySearch {{
    min-height: 20px;
    font-size: 14px;
    padding: 10px 12px;
}}

QScrollArea {{
    border: none;
    background-color: transparent;
}}

QScrollBar:vertical {{
    width: 10px;
    background: transparent;
    margin: 2px;
}}

QScrollBar::handle:vertical {{
    background: {COLORS['surface_container_highest']};
    border-radius: {RADII['pill']}px;
    min-height: 24px;
}}

QScrollBar::handle:vertical:hover {{
    background: {COLORS['outline']};
}}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {{
    background: transparent;
    height: 0px;
}}

QFrame#libraryHeader,
QFrame#libraryToolbar,
QFrame#librarySectionHeader,
QFrame#libraryChrome,
QFrame#folder_panel,
QFrame#module_card,
QFrame#workspace_state_container {{
    background-color: {COLORS['surface']};
    border: 1px solid {COLORS['outline_variant']};
}}

QFrame#libraryHeader,
QFrame#libraryToolbar,
QFrame#librarySectionHeader,
QFrame#libraryChrome,
QFrame#folder_panel,
QFrame#module_card {{
    border-radius: {RADII['lg']}px;
}}

QFrame#libraryHeader {{
    background-color: {COLORS['surface_container_low']};
}}

QFrame#libraryToolbar,
QFrame#librarySectionHeader {{
    background-color: {COLORS['surface_container_low']};
}}

QFrame#libraryChrome {{
    background-color: {rgba(COLORS['surface'], 220)};
}}

QFrame#module_card:hover {{
    border-color: {COLORS['primary_container']};
    background-color: {COLORS['surface_container_low']};
}}

QLabel#pageEyebrow {{
    font-family: {FONTS['label']};
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.08em;
    color: {COLORS['primary_container']};
    text-transform: uppercase;
}}

QLabel#pageTitle {{
    font-family: {FONTS['display']};
    font-size: 28px;
    font-weight: 700;
    color: {COLORS['on_background']};
}}

QLabel#pageDescription,
QLabel#sectionMeta,
QLabel#workspace_state_message,
QLabel#moduleDescription,
QLabel#moduleMeta,
QLabel#moduleFootnote,
QLabel#folderHint {{
    color: {rgba(COLORS['on_surface'], 190)};
}}

QLabel#metricPill,
QLabel#moduleBadge,
QLabel#moduleStatus {{
    font-family: {FONTS['label']};
    font-size: 11px;
    font-weight: 700;
    border-radius: {RADII['pill']}px;
    padding: 4px 10px;
}}

QLabel#metricPill {{
    background-color: {COLORS['tertiary_container']};
    color: {COLORS['on_tertiary_container']};
}}

QLabel#sectionTitle,
QLabel#moduleTitle,
QLabel#workspace_state_title,
QLabel#folderHeader {{
    font-family: {FONTS['display']};
    font-size: 18px;
    font-weight: 600;
    color: {COLORS['on_surface']};
}}

QLabel#moduleBadge {{
    background-color: {COLORS['secondary_container']};
    color: {COLORS['on_secondary_container']};
}}

QLabel#moduleStatus[status="ready"] {{
    background-color: {COLORS['secondary_container']};
    color: {COLORS['on_secondary_container']};
}}

QLabel#moduleStatus[status="disabled"] {{
    background-color: {COLORS['surface_container_high']};
    color: {COLORS['outline']};
}}

QLabel#workspace_state_kicker {{
    font-family: {FONTS['label']};
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.08em;
    color: {COLORS['primary_container']};
    text-transform: uppercase;
}}

QFrame#workspace_state_container {{
    border-radius: {RADII['xl']}px;
    background-color: {COLORS['surface_container_low']};
}}

QFrame#workspace_state_container[state="error"] {{
    background-color: {COLORS['error_container']};
    border-color: {rgba(COLORS['error'], 120)};
}}

QLabel#workspace_state_title {{
    font-size: 24px;
}}

QLabel#workspace_state_message {{
    font-size: 14px;
}}

QListWidget#folder_list {{
    border: none;
    background: transparent;
    outline: none;
}}

QListWidget#folder_list::item {{
    padding: 8px 10px;
    margin: 2px 0;
    border-radius: {RADII['md']}px;
}}

QListWidget#folder_list::item:selected {{
    background-color: {COLORS['primary']};
    color: {COLORS['on_primary']};
}}

QListWidget#folder_list::item:hover:!selected {{
    background-color: {COLORS['surface_container']};
}}

#module_host_frame {{
    background-color: {COLORS['surface']};
    border-left: 1px solid {COLORS['outline_variant']};
}}

QTabWidget::pane {{
    background-color: {COLORS['surface']};
    border: 1px solid {COLORS['outline_variant']};
    border-top: none;
}}

QTabBar::tab {{
    background-color: {COLORS['surface_container']};
    color: {COLORS['on_surface']};
    padding: 7px 14px;
    margin-right: 2px;
    border: 1px solid {COLORS['outline_variant']};
    border-bottom: none;
    border-top-left-radius: {RADII['sm']}px;
    border-top-right-radius: {RADII['sm']}px;
    font-size: 12px;
}}

QTabBar::tab:selected {{
    background-color: {COLORS['primary']};
    color: {COLORS['on_primary']};
    font-weight: 700;
    border-color: {COLORS['primary']};
}}

QTabBar::tab:hover:!selected {{
    background-color: {COLORS['surface_container_high']};
}}

QFrame#pageHeaderPanel,
QFrame#managerToolbar,
QFrame#dashboardSection,
QFrame#settingsIntroPanel,
QFrame#statCard,
QFrame#activityRow,
QFrame#managerModuleRow {{
    background-color: {COLORS['surface']};
    border: 1px solid {COLORS['outline_variant']};
}}

QFrame#pageHeaderPanel,
QFrame#managerToolbar,
QFrame#dashboardSection,
QFrame#settingsIntroPanel {{
    border-radius: {RADII['lg']}px;
}}

QFrame#pageHeaderPanel,
QFrame#managerToolbar,
QFrame#settingsIntroPanel {{
    background-color: {COLORS['surface_container_low']};
}}

QFrame#statCard,
QFrame#activityRow,
QFrame#managerModuleRow {{
    border-radius: {RADII['md']}px;
}}

QFrame#activityRow[alt="true"] {{
    background-color: {COLORS['surface_container_low']};
}}

QFrame#managerModuleRow:hover {{
    background-color: {COLORS['surface_container_low']};
    border-color: {COLORS['primary_container']};
}}

QFrame#statCard[accent="primary"] {{
    border-left: 4px solid {COLORS['primary_container']};
}}

QFrame#statCard[accent="success"] {{
    border-left: 4px solid {COLORS['success']};
}}

QFrame#statCard[accent="warning"] {{
    border-left: 4px solid {COLORS['warning']};
}}

QFrame#statCard[accent="danger"] {{
    border-left: 4px solid {COLORS['error']};
}}

QLabel#mutedText,
QLabel#sectionDescription,
QLabel#activityDetail {{
    color: {rgba(COLORS['on_surface'], 190)};
}}

QLabel#statValue {{
    font-family: {FONTS['display']};
    font-size: 26px;
    font-weight: 700;
    color: {COLORS['on_surface']};
}}

QLabel#statValue[accent="primary"] {{
    color: {COLORS['primary_container']};
}}

QLabel#statValue[accent="success"] {{
    color: {COLORS['success']};
}}

QLabel#statValue[accent="warning"] {{
    color: {COLORS['warning']};
}}

QLabel#statValue[accent="danger"] {{
    color: {COLORS['error']};
}}

QLabel#statLabel {{
    font-family: {FONTS['label']};
    font-size: 11px;
    font-weight: 600;
    color: {rgba(COLORS['on_surface'], 190)};
    letter-spacing: 0.04em;
}}

QLabel#statusBadge {{
    font-family: {FONTS['label']};
    font-size: 11px;
    font-weight: 700;
    border-radius: {RADII['pill']}px;
    padding: 4px 10px;
}}

QLabel#statusBadge[variant="info"] {{
    background-color: {COLORS['tertiary_container']};
    color: {COLORS['on_tertiary_container']};
}}

QLabel#statusBadge[variant="success"] {{
    background-color: {COLORS['secondary_container']};
    color: {COLORS['on_secondary_container']};
}}

QLabel#statusBadge[variant="warning"] {{
    background-color: {COLORS['tertiary_container']};
    color: {COLORS['on_tertiary_container']};
}}

QLabel#statusBadge[variant="danger"] {{
    background-color: {COLORS['error_container']};
    color: {COLORS['on_error_container']};
}}

QLabel#statusBadge[variant="muted"] {{
    background-color: {COLORS['surface_container_high']};
    color: {COLORS['outline']};
}}

QPushButton[role="success"] {{
    background-color: {COLORS['success']};
    color: {COLORS['on_success']};
}}

QPushButton[role="success"]:hover {{
    background-color: {COLORS['secondary']};
    color: {COLORS['on_secondary']};
}}

QPushButton[role="warning"] {{
    background-color: {COLORS['warning']};
    color: {COLORS['on_warning']};
}}

QPushButton[role="warning"]:hover {{
    background-color: {COLORS['tertiary']};
    color: {COLORS['on_tertiary']};
}}

QPushButton[role="danger"] {{
    background-color: {COLORS['error']};
    color: {COLORS['on_error']};
}}

QPushButton[role="danger"]:hover {{
    background-color: {COLORS['on_error_container']};
    color: {COLORS['on_error']};
}}

QPushButton[role="subtle"] {{
    background-color: {COLORS['surface_container']};
    color: {COLORS['on_surface']};
    border: 1px solid {COLORS['outline_variant']};
}}

QPushButton[role="subtle"]:hover {{
    background-color: {COLORS['surface_container_high']};
}}

QLineEdit[readonlyField="true"] {{
    background-color: {COLORS['surface_container_low']};
    color: {rgba(COLORS['on_surface'], 200)};
}}

QGroupBox#settingsSection {{
    font-family: {FONTS['body']};
    font-size: 13px;
    font-weight: 600;
    color: {COLORS['on_surface']};
    border: 1px solid {COLORS['outline_variant']};
    border-radius: {RADII['lg']}px;
    margin-top: 10px;
    padding: 12px 14px 14px 14px;
    background-color: {COLORS['surface']};
}}

QGroupBox#settingsSection::title {{
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: {COLORS['primary']};
}}

QWidget[moduleShell="root"] {{
    background-color: {COLORS['surface']};
}}

QWidget[moduleShell="sidebar"] {{
    background-color: {COLORS['surface_container_low']};
}}

QGroupBox[moduleShell="panel"] {{
    font-family: {FONTS['body']};
    font-size: 13px;
    font-weight: 600;
    color: {COLORS['on_surface']};
    border: 1px solid {COLORS['outline_variant']};
    border-radius: {RADII['md']}px;
    margin-top: 8px;
    padding-top: 8px;
    background-color: {COLORS['surface']};
}}

QGroupBox[moduleShell="panel"]::title {{
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
    color: {COLORS['primary']};
}}

QLabel[moduleShell="hint"] {{
    color: {rgba(COLORS['on_surface'], 185)};
    font-size: 12px;
}}

QLabel[moduleShell="result"] {{
    font-family: "Consolas", "Cascadia Mono", monospace;
    font-size: 13px;
    color: {COLORS['on_surface']};
}}

QLabel[moduleShell="infoPanel"] {{
    background-color: {COLORS['surface_container_low']};
    border: 1px solid {COLORS['outline_variant']};
    border-radius: {RADII['md']}px;
    padding: 8px 12px;
    color: {COLORS['on_surface']};
}}

QLabel[moduleShell="sectionLabel"] {{
    font-size: 13px;
    font-weight: 700;
    color: {COLORS['on_surface']};
}}

QWidget[moduleShell="sidebar"] QRadioButton,
QWidget[moduleShell="sidebar"] QCheckBox {{
    font-size: 13px;
    color: {COLORS['on_surface']};
    spacing: 6px;
}}

QWidget[moduleShell="sidebar"] QRadioButton::indicator {{
    width: 15px;
    height: 15px;
    border-radius: 8px;
}}

QWidget[moduleShell="sidebar"] QRadioButton::indicator:unchecked {{
    border: 2px solid {COLORS['outline']};
    background: {COLORS['surface']};
}}

QWidget[moduleShell="sidebar"] QRadioButton::indicator:checked {{
    border: 2px solid {COLORS['primary_container']};
    background: {COLORS['primary_container']};
}}

QWidget[moduleShell="sidebar"] QCheckBox::indicator {{
    width: 14px;
    height: 14px;
    border-radius: 3px;
}}

QWidget[moduleShell="sidebar"] QCheckBox::indicator:unchecked {{
    border: 2px solid {COLORS['outline']};
    background: {COLORS['surface']};
}}

QWidget[moduleShell="sidebar"] QCheckBox::indicator:checked {{
    border: 2px solid {COLORS['primary_container']};
    background: {COLORS['primary_container']};
}}

QWidget[moduleShell="sidebar"] QGroupBox {{
    font-size: 13px;
    font-weight: 700;
}}

QWidget[moduleShell="sidebar"] QComboBox,
QWidget[moduleShell="sidebar"] QDoubleSpinBox,
QWidget[moduleShell="sidebar"] QPushButton {{
    font-size: 12px;
}}

QLabel[moduleShell="overlayDot"] {{
    font-size: 15px;
    font-weight: 700;
}}

QPushButton#overlayRemoveButton {{
    min-width: 22px;
    max-width: 22px;
    min-height: 22px;
    max-height: 22px;
    padding: 0;
    border: none;
    border-radius: {RADII['pill']}px;
    background: transparent;
    color: {COLORS['error']};
    font-size: 15px;
    font-weight: 700;
}}

QPushButton#overlayRemoveButton:hover {{
    background: {COLORS['error_container']};
    color: {COLORS['on_error_container']};
}}

QLabel[moduleShell="equationPanel"] {{
    background-color: {COLORS['surface_container_low']};
    border: 1px solid {COLORS['outline_variant']};
    border-radius: {RADII['md']}px;
    padding: 5px 14px;
    font-size: 14px;
    font-family: "Consolas", "Cascadia Mono", monospace;
    color: {COLORS['on_surface']};
}}

QLabel[moduleShell="tooltipPanel"] {{
    background-color: {COLORS['surface_container_low']};
    border: 1px solid {COLORS['outline_variant']};
    border-radius: {RADII['md']}px;
    padding: 8px 12px;
    font-size: 13px;
    color: {COLORS['on_surface']};
}}

QLabel[moduleShell="curveTitle"] {{
    font-weight: 700;
    font-size: 12px;
}}

QLabel[moduleShell="curveTitle"][curve="supply"] {{
    color: {COLORS['success']};
}}

QLabel[moduleShell="curveTitle"][curve="demand"] {{
    color: {COLORS['tertiary_container']};
}}
"""
