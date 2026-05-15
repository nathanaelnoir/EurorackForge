from EurorackForgeCore import *
from EurorackForgeExport import *
# Ensure helper is explicitly available (fixes runtime name-resolution in some FreeCAD loads)
from EurorackForgeCore import _selected_export_target

ACTIVE_FACEPLATE_TASK_PANEL = None
ACTIVE_EXPORT_TASK_PANEL = None


class FaceplateTaskPanel(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Create Eurorack Faceplate")
        self.setMinimumWidth(720)
        self.setMinimumHeight(480)
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.Window)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
        self.form = self
        self.created_body = None
        self.created_source = None
        self.created_spec = None

        self._build_ui()
        self._apply_style()
        self._apply_standard_defaults(STANDARD_DOEPFER)
        self.refresh_preset_list()
        self.refresh_summary()
        self._fit_to_available_screen()

    def _build_ui(self):
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(14)

        body_scroll = QtWidgets.QScrollArea()
        body_scroll.setWidgetResizable(True)
        body_scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        body_scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        body_scroll.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        root.addWidget(body_scroll, 1)

        body = QtWidgets.QWidget()
        body_scroll.setWidget(body)
        body_layout = QtWidgets.QVBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(14)

        self.tabs = QtWidgets.QTabWidget()
        body_layout.addWidget(self.tabs, 1)

        panel_tab = QtWidgets.QWidget()
        panel_root = QtWidgets.QVBoxLayout(panel_tab)
        panel_root.setContentsMargins(0, 0, 0, 0)
        panel_root.setSpacing(14)
        self.tabs.addTab(panel_tab, "Panel")

        hero = QtWidgets.QFrame()
        hero.setObjectName("heroPanel")
        hero_layout = QtWidgets.QHBoxLayout(hero)
        hero_layout.setContentsMargins(18, 16, 18, 16)
        hero_layout.setSpacing(14)

        icon_label = QtWidgets.QLabel()
        icon_label.setFixedSize(56, 56)
        icon = QtGui.QIcon(resource_path("EurorackForge.svg"))
        icon_label.setPixmap(icon.pixmap(48, 48))
        icon_label.setAlignment(QtCore.Qt.AlignCenter)

        title_block = QtWidgets.QVBoxLayout()
        title_block.setSpacing(4)

        title = QtWidgets.QLabel("Create Eurorack Faceplate")
        title.setObjectName("heroTitle")
        subtitle = QtWidgets.QLabel(
            "Select a panel standard, tune the dimensions, and preview the faceplate before it is "
            "built as a centered PartDesign body."
        )
        subtitle.setObjectName("heroSubtitle")
        subtitle.setWordWrap(True)

        title_block.addWidget(title)
        title_block.addWidget(subtitle)
        title_block.addStretch(1)

        hero_layout.addWidget(icon_label, 0, QtCore.Qt.AlignTop)
        hero_layout.addLayout(title_block, 1)

        panel_root.addWidget(hero)

        content = QtWidgets.QHBoxLayout()
        content.setSpacing(14)

        left_column = QtWidgets.QVBoxLayout()
        left_column.setSpacing(14)

        standard_box = QtWidgets.QGroupBox("Standard")
        standard_layout = QtWidgets.QVBoxLayout(standard_box)
        standard_layout.setSpacing(10)

        standard_form = QtWidgets.QFormLayout()
        standard_form.setHorizontalSpacing(12)
        standard_form.setVerticalSpacing(10)

        self.standard_combo = QtWidgets.QComboBox()
        for key, label in STANDARD_OPTIONS:
            self.standard_combo.addItem(label, key)
        self.standard_combo.currentIndexChanged.connect(self._on_standard_changed)

        self.cutout_combo = QtWidgets.QComboBox()
        self.cutout_combo.addItem("Round mounting holes", "circles")
        self.cutout_combo.addItem("Horizontal slots", "slots")
        self.cutout_combo.currentIndexChanged.connect(self.refresh_summary)

        standard_form.addRow("Format", self.standard_combo)
        standard_form.addRow("Cutout style", self.cutout_combo)
        standard_layout.addLayout(standard_form)

        self.standard_hint = QtWidgets.QLabel()
        self.standard_hint.setWordWrap(True)
        self.standard_hint.setObjectName("helperText")
        standard_layout.addWidget(self.standard_hint)

        presets_box = QtWidgets.QGroupBox("Presets")
        presets_layout = QtWidgets.QVBoxLayout(presets_box)
        presets_layout.setSpacing(10)

        self.preset_combo = QtWidgets.QComboBox()
        self.preset_combo.currentIndexChanged.connect(self._on_preset_selection_changed)

        preset_buttons = QtWidgets.QHBoxLayout()
        preset_buttons.setSpacing(8)

        self.save_preset_button = QtWidgets.QToolButton()
        self.save_preset_button.setText("Save Current")
        self.save_preset_button.clicked.connect(self.save_current_preset)

        self.load_preset_button = QtWidgets.QToolButton()
        self.load_preset_button.setText("Load")
        self.load_preset_button.clicked.connect(self.load_selected_preset)

        self.delete_preset_button = QtWidgets.QToolButton()
        self.delete_preset_button.setText("Delete")
        self.delete_preset_button.clicked.connect(self.delete_selected_preset)

        preset_buttons.addWidget(self.save_preset_button)
        preset_buttons.addWidget(self.load_preset_button)
        preset_buttons.addWidget(self.delete_preset_button)
        preset_buttons.addStretch(1)

        self.preset_status = QtWidgets.QLabel("No saved presets yet.")
        self.preset_status.setWordWrap(True)
        self.preset_status.setObjectName("helperText")

        presets_layout.addWidget(self.preset_combo)
        presets_layout.addLayout(preset_buttons)
        presets_layout.addWidget(self.preset_status)

        placement_box = QtWidgets.QGroupBox("Placement clearances")
        placement_layout = QtWidgets.QVBoxLayout(placement_box)
        placement_layout.setSpacing(10)

        placement_form = QtWidgets.QFormLayout()
        placement_form.setHorizontalSpacing(12)
        placement_form.setVerticalSpacing(10)

        self.top_clearance_spin = QtWidgets.QDoubleSpinBox()
        self.top_clearance_spin.setRange(0.0, 1000.0)
        self.top_clearance_spin.setDecimals(2)
        self.top_clearance_spin.setSingleStep(1.0)
        self.top_clearance_spin.setValue(10.0)
        self.top_clearance_spin.setSuffix(" mm")
        self.top_clearance_spin.valueChanged.connect(self.refresh_summary)

        self.bottom_clearance_spin = QtWidgets.QDoubleSpinBox()
        self.bottom_clearance_spin.setRange(0.0, 1000.0)
        self.bottom_clearance_spin.setDecimals(2)
        self.bottom_clearance_spin.setSingleStep(1.0)
        self.bottom_clearance_spin.setValue(10.0)
        self.bottom_clearance_spin.setSuffix(" mm")
        self.bottom_clearance_spin.valueChanged.connect(self.refresh_summary)

        placement_form.addRow("Top keep-out", self.top_clearance_spin)
        placement_form.addRow("Bottom keep-out", self.bottom_clearance_spin)
        placement_layout.addLayout(placement_form)

        placement_hint = QtWidgets.QLabel(
            "The reference sketch is created automatically when you click Create Panel."
        )
        placement_hint.setWordWrap(True)
        placement_hint.setObjectName("helperText")
        placement_layout.addWidget(placement_hint)

        self.create_pcb_checkbox = QtWidgets.QCheckBox("Create PCB behind faceplate")
        self.create_pcb_checkbox.setChecked(False)
        self.create_pcb_checkbox.stateChanged.connect(self.refresh_summary)
        placement_layout.addWidget(self.create_pcb_checkbox)

        self.page_stack = QtWidgets.QStackedWidget()
        self._build_doepfer_page()
        self._build_intellijel_1u_page()
        self._build_pulplogic_1u_page()
        self._build_kosmo_page()
        self._build_custom_page()

        left_column.addWidget(standard_box)
        left_column.addWidget(presets_box)
        left_column.addWidget(placement_box)
        left_column.addWidget(self.page_stack)

        summary_box = QtWidgets.QGroupBox("Live summary")
        summary_layout = QtWidgets.QVBoxLayout(summary_box)
        summary_layout.setSpacing(10)

        self.summary_box = QtWidgets.QPlainTextEdit()
        self.summary_box.setReadOnly(True)
        self.summary_box.setLineWrapMode(QtWidgets.QPlainTextEdit.NoWrap)
        self.summary_box.setMinimumHeight(230)
        self.summary_box.setFont(QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.FixedFont))
        summary_layout.addWidget(self.summary_box)

        note = QtWidgets.QLabel(
            "The generator creates a hidden base solid and a PartDesign Body, then selects the new body."
        )
        note.setWordWrap(True)
        note.setObjectName("helperText")
        summary_layout.addWidget(note)

        left_column.addWidget(summary_box, 1)

        preview_box = QtWidgets.QGroupBox("Preview")
        preview_layout = QtWidgets.QVBoxLayout(preview_box)
        preview_layout.setSpacing(10)

        self.preview = FaceplatePreviewWidget()
        preview_layout.addWidget(self.preview, 1)

        self.preview_caption = QtWidgets.QLabel(
            "The preview updates immediately when you change the parameters."
        )
        self.preview_caption.setWordWrap(True)
        self.preview_caption.setObjectName("helperText")
        preview_layout.addWidget(self.preview_caption)

        content.addLayout(left_column, 1)
        content.addWidget(preview_box, 1)

        panel_root.addLayout(content)

        self.button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        self.button_box.button(QtWidgets.QDialogButtonBox.Ok).setText("Create Panel")
        self.button_box.button(QtWidgets.QDialogButtonBox.Cancel).setText("Close")
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        root.addWidget(self.button_box)

    def _fit_to_available_screen(self):
        app = QtWidgets.QApplication.instance()
        if app is None:
            return

        screen = None
        if hasattr(self, "windowHandle") and self.windowHandle() is not None:
            screen = self.windowHandle().screen()
        if screen is None and hasattr(app, "primaryScreen"):
            screen = app.primaryScreen()
        if screen is None:
            return

        available = screen.availableGeometry()
        if available.isNull():
            return

        target_width = min(940, int(available.width() * 0.88))
        target_height = min(650, int(available.height() * 0.78))
        target_width = max(self.minimumWidth(), target_width)
        target_height = max(self.minimumHeight(), target_height)
        self.resize(target_width, target_height)

    def showEvent(self, event):
        super().showEvent(event)
        QtCore.QTimer.singleShot(0, self._fit_to_available_screen)

    def _build_doepfer_page(self):
        page = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(page)
        layout.setSpacing(10)

        form = QtWidgets.QFormLayout()
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)

        self.doepfer_hp_spin = QtWidgets.QSpinBox()
        self.doepfer_hp_spin.setRange(1, 168)
        self.doepfer_hp_spin.setSuffix(" HP")
        self.doepfer_hp_spin.valueChanged.connect(self.refresh_summary)

        self.doepfer_thickness_spin = QtWidgets.QDoubleSpinBox()
        self.doepfer_thickness_spin.setRange(0.5, 20.0)
        self.doepfer_thickness_spin.setDecimals(2)
        self.doepfer_thickness_spin.setSingleStep(0.1)
        self.doepfer_thickness_spin.setSuffix(" mm")
        self.doepfer_thickness_spin.valueChanged.connect(self.refresh_summary)

        self.doepfer_center_checkbox = QtWidgets.QCheckBox("Use centered single column below 12 HP")
        self.doepfer_center_checkbox.setChecked(CENTER_SINGLE_HOLE_COLUMN)
        self.doepfer_center_checkbox.stateChanged.connect(self._update_doepfer_narrow_controls)
        self.doepfer_center_checkbox.stateChanged.connect(self.refresh_summary)

        self.doepfer_narrow_combo = QtWidgets.QComboBox()
        for key, label in DOEPFER_NARROW_DIAGONAL_OPTIONS:
            self.doepfer_narrow_combo.addItem(label, key)
        self.doepfer_narrow_combo.currentIndexChanged.connect(self.refresh_summary)

        form.addRow("Width", self.doepfer_hp_spin)
        form.addRow("Thickness", self.doepfer_thickness_spin)
        form.addRow("", self.doepfer_center_checkbox)
        form.addRow("Narrow layout", self.doepfer_narrow_combo)

        layout.addLayout(form)

        helper = QtWidgets.QLabel(
            "Doepfer mode follows the Eurorack 3U panel conventions with HP-based width, 2 mm default thickness, and a selectable narrow-panel diagonal below 12 HP."
        )
        helper.setWordWrap(True)
        helper.setObjectName("helperText")
        layout.addWidget(helper)
        layout.addStretch(1)

        self.page_stack.addWidget(page)

    def _update_doepfer_narrow_controls(self, *args):
        self.doepfer_narrow_combo.setEnabled(not self.doepfer_center_checkbox.isChecked())

    def _build_intellijel_1u_page(self):
        page = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(page)
        layout.setSpacing(10)

        form = QtWidgets.QFormLayout()
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)

        self.intellijel_1u_hp_spin = QtWidgets.QSpinBox()
        self.intellijel_1u_hp_spin.setRange(1, 84)
        self.intellijel_1u_hp_spin.setSuffix(" HP")
        self.intellijel_1u_hp_spin.valueChanged.connect(self.refresh_summary)

        form.addRow("Width", self.intellijel_1u_hp_spin)
        layout.addLayout(form)

        helper = QtWidgets.QLabel(
            "Intellijel 1U uses a 39.65 mm row height and follows the Eurorack HP grid."
        )
        helper.setWordWrap(True)
        helper.setObjectName("helperText")
        layout.addWidget(helper)
        layout.addStretch(1)

        self.page_stack.addWidget(page)

    def _build_pulplogic_1u_page(self):
        page = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(page)
        layout.setSpacing(10)

        form = QtWidgets.QFormLayout()
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)

        self.pulplogic_tiles_spin = QtWidgets.QSpinBox()
        self.pulplogic_tiles_spin.setRange(1, 16)
        self.pulplogic_tiles_spin.setSuffix(" tiles")
        self.pulplogic_tiles_spin.valueChanged.connect(self.refresh_summary)

        form.addRow("Width", self.pulplogic_tiles_spin)
        layout.addLayout(form)

        helper = QtWidgets.QLabel(
            "Pulp Logic 1U uses a 43.18 mm row height and 6 HP tile increments."
        )
        helper.setWordWrap(True)
        helper.setObjectName("helperText")
        layout.addWidget(helper)
        layout.addStretch(1)

        self.page_stack.addWidget(page)

    def _build_kosmo_page(self):
        page = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(page)
        layout.setSpacing(10)

        form = QtWidgets.QFormLayout()
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)

        self.kosmo_units_spin = QtWidgets.QSpinBox()
        self.kosmo_units_spin.setRange(1, 32)
        self.kosmo_units_spin.setSuffix(" x 2.5 cm")
        self.kosmo_units_spin.valueChanged.connect(self.refresh_summary)

        form.addRow("Width", self.kosmo_units_spin)
        layout.addLayout(form)

        helper = QtWidgets.QLabel(
            "Kosmo mode uses 20 cm tall panels and widths in 2.5 cm increments."
        )
        helper.setWordWrap(True)
        helper.setObjectName("helperText")
        layout.addWidget(helper)
        layout.addStretch(1)

        self.page_stack.addWidget(page)

    def _build_custom_page(self):
        page = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(page)
        layout.setSpacing(10)

        form = QtWidgets.QFormLayout()
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)

        self.custom_width_spin = QtWidgets.QDoubleSpinBox()
        self.custom_width_spin.setRange(10.0, 2000.0)
        self.custom_width_spin.setDecimals(2)
        self.custom_width_spin.setSingleStep(1.0)
        self.custom_width_spin.setSuffix(" mm")
        self.custom_width_spin.valueChanged.connect(self.refresh_summary)

        self.custom_height_spin = QtWidgets.QDoubleSpinBox()
        self.custom_height_spin.setRange(10.0, 2000.0)
        self.custom_height_spin.setDecimals(2)
        self.custom_height_spin.setSingleStep(1.0)
        self.custom_height_spin.setSuffix(" mm")
        self.custom_height_spin.valueChanged.connect(self.refresh_summary)

        self.custom_thickness_spin = QtWidgets.QDoubleSpinBox()
        self.custom_thickness_spin.setRange(0.5, 20.0)
        self.custom_thickness_spin.setDecimals(2)
        self.custom_thickness_spin.setSingleStep(0.1)
        self.custom_thickness_spin.setSuffix(" mm")
        self.custom_thickness_spin.valueChanged.connect(self.refresh_summary)

        self.custom_hole_diameter_spin = QtWidgets.QDoubleSpinBox()
        self.custom_hole_diameter_spin.setRange(0.5, 20.0)
        self.custom_hole_diameter_spin.setDecimals(2)
        self.custom_hole_diameter_spin.setSingleStep(0.1)
        self.custom_hole_diameter_spin.setSuffix(" mm")
        self.custom_hole_diameter_spin.valueChanged.connect(self.refresh_summary)

        self.custom_x_margin_spin = QtWidgets.QDoubleSpinBox()
        self.custom_x_margin_spin.setRange(0.0, 100.0)
        self.custom_x_margin_spin.setDecimals(2)
        self.custom_x_margin_spin.setSingleStep(0.5)
        self.custom_x_margin_spin.setSuffix(" mm")
        self.custom_x_margin_spin.valueChanged.connect(self.refresh_summary)

        self.custom_y_margin_spin = QtWidgets.QDoubleSpinBox()
        self.custom_y_margin_spin.setRange(0.0, 100.0)
        self.custom_y_margin_spin.setDecimals(2)
        self.custom_y_margin_spin.setSingleStep(0.5)
        self.custom_y_margin_spin.setSuffix(" mm")
        self.custom_y_margin_spin.valueChanged.connect(self.refresh_summary)

        form.addRow("Width", self.custom_width_spin)
        form.addRow("Height", self.custom_height_spin)
        form.addRow("Thickness", self.custom_thickness_spin)
        form.addRow("Hole diameter", self.custom_hole_diameter_spin)
        form.addRow("Side margin", self.custom_x_margin_spin)
        form.addRow("Top/bottom margin", self.custom_y_margin_spin)

        layout.addLayout(form)

        helper = QtWidgets.QLabel(
            "Custom mode uses direct millimeter control and corner mounting holes."
        )
        helper.setWordWrap(True)
        helper.setObjectName("helperText")
        layout.addWidget(helper)
        layout.addStretch(1)

        self.page_stack.addWidget(page)

    def _apply_style(self):
        self.setStyleSheet(
            """
            QDialog {
                background: palette(window);
            }

            QFrame#heroPanel {
                border: 1px solid rgba(120, 140, 160, 90);
                border-radius: 14px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                            stop:0 rgba(29, 41, 52, 240),
                                            stop:1 rgba(22, 58, 63, 240));
            }

            QLabel#heroTitle {
                font-size: 18px;
                font-weight: 700;
                color: white;
            }

            QLabel#heroSubtitle,
            QLabel#helperText {
                color: rgba(230, 235, 240, 200);
            }

            QGroupBox {
                font-weight: 600;
                border: 1px solid rgba(120, 140, 160, 90);
                border-radius: 12px;
                margin-top: 14px;
                padding-top: 12px;
                background: rgba(255, 255, 255, 14);
            }

            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px;
            }

            QPlainTextEdit {
                border: 1px solid rgba(120, 140, 160, 90);
                border-radius: 10px;
                background: rgba(0, 0, 0, 20);
                padding: 8px;
            }

            QToolButton {
                border: 1px solid rgba(120, 140, 160, 120);
                border-radius: 8px;
                padding: 6px 10px;
                background: rgba(255, 255, 255, 20);
            }

            QToolButton:hover {
                background: rgba(255, 255, 255, 34);
            }

            QToolButton:pressed {
                background: rgba(255, 255, 255, 50);
            }

            QCheckBox {
                spacing: 8px;
            }

            QPushButton#primaryButton {
                min-width: 110px;
                padding: 7px 14px;
                border-radius: 8px;
                background: #1f7a4a;
                color: white;
                font-weight: 600;
            }

            QPushButton#primaryButton:hover {
                background: #25945a;
            }

            QPushButton#primaryButton:pressed {
                background: #17613a;
            }
            """
        )

    def _apply_standard_defaults(self, standard_key):
        if standard_key == STANDARD_DOEPFER:
            self.doepfer_hp_spin.setValue(8)
            self.doepfer_thickness_spin.setValue(2.0)
            self.doepfer_center_checkbox.setChecked(CENTER_SINGLE_HOLE_COLUMN)
            default_orientation = self.doepfer_narrow_combo.findData(DOEPFER_NARROW_UPPER_LEFT_LOWER_RIGHT)
            if default_orientation >= 0:
                self.doepfer_narrow_combo.setCurrentIndex(default_orientation)
            self._update_doepfer_narrow_controls()
            self.standard_hint.setText(
                "Doepfer Eurorack mode uses HP units, a 128.5 mm panel height, and a 2 mm default thickness."
            )
            self.page_stack.setCurrentIndex(0)
        elif standard_key == STANDARD_INTELLIJEL_1U:
            self.intellijel_1u_hp_spin.setValue(10)
            self.standard_hint.setText(
                "Intellijel 1U mode uses the 39.65 mm row height and HP-based widths."
            )
            self.page_stack.setCurrentIndex(1)
        elif standard_key == STANDARD_PULP_LOGIC_1U:
            self.pulplogic_tiles_spin.setValue(2)
            self.standard_hint.setText(
                "Pulp Logic 1U mode uses the 43.18 mm tile height and 6 HP tile widths."
            )
            self.page_stack.setCurrentIndex(2)
        elif standard_key == STANDARD_KOSMO:
            self.kosmo_units_spin.setValue(8)
            self.standard_hint.setText(
                "Kosmo mode uses 20 cm panel height and 2.5 cm width increments."
            )
            self.page_stack.setCurrentIndex(3)
        else:
            self.custom_width_spin.setValue(80.0)
            self.custom_height_spin.setValue(128.5)
            self.custom_thickness_spin.setValue(2.0)
            self.custom_hole_diameter_spin.setValue(3.2)
            self.custom_x_margin_spin.setValue(7.5)
            self.custom_y_margin_spin.setValue(3.0)
            self.standard_hint.setText(
                "Custom mode gives exact millimeter control over panel size and mounting geometry."
            )
            self.page_stack.setCurrentIndex(4)

        if hasattr(self, "top_clearance_spin"):
            self.top_clearance_spin.setValue(10.0)
        if hasattr(self, "bottom_clearance_spin"):
            self.bottom_clearance_spin.setValue(10.0)

    def _set_standard(self, standard_key):
        index = self.standard_combo.findData(standard_key)
        if index >= 0:
            self.standard_combo.setCurrentIndex(index)

    def _get_saved_presets(self):
        store = load_preset_store()
        presets = store.get("presets", [])
        if not isinstance(presets, list):
            return []
        return presets

    def refresh_preset_list(self, preferred_name=None):
        presets = self._get_saved_presets()

        self.preset_combo.blockSignals(True)
        self.preset_combo.clear()
        self.preset_combo.addItem("Select a saved preset", None)

        selected_index = 0
        for index, record in enumerate(presets, start=1):
            name = record.get("name", "Unnamed preset")
            summary = record.get("summary", name)
            self.preset_combo.addItem(f"{name} - {summary}", name)
            if preferred_name is not None and name == preferred_name:
                selected_index = index

        self.preset_combo.setCurrentIndex(selected_index)
        self.preset_combo.blockSignals(False)

        if presets:
            self.preset_status.setText(f"Saved presets: {len(presets)}")
        else:
            self.preset_status.setText("No saved presets yet.")

    def _find_preset_record(self, name):
        for record in self._get_saved_presets():
            if record.get("name") == name:
                return record
        return None

    def _normalize_preset_name(self, name):
        return " ".join(name.strip().split())

    def save_current_preset(self):
        spec = self._current_spec()
        default_name = spec["display_name"]

        name, ok = QtWidgets.QInputDialog.getText(
            self,
            "Save Preset",
            "Preset name:",
            QtWidgets.QLineEdit.Normal,
            default_name
        )

        if not ok:
            return

        name = self._normalize_preset_name(name)
        if not name:
            return

        store = load_preset_store()
        presets = store.get("presets", [])
        if not isinstance(presets, list):
            presets = []

        presets = [record for record in presets if record.get("name") != name]
        presets.append(make_preset_record(name, spec))
        store["version"] = PRESET_STORE_VERSION
        store["presets"] = presets
        save_preset_store(store)
        self.refresh_preset_list(preferred_name=name)
        self.preset_status.setText(f"Saved preset '{name}'.")

    def _selected_preset_name(self):
        data = self.preset_combo.currentData()
        if not data:
            return None
        return data

    def load_selected_preset(self):
        name = self._selected_preset_name()
        if not name:
            return

        record = self._find_preset_record(name)
        if not record:
            self.preset_status.setText(f"Preset '{name}' was not found.")
            self.refresh_preset_list()
            return

        spec = record.get("spec")
        if not isinstance(spec, dict):
            self.preset_status.setText(f"Preset '{name}' is invalid.")
            return

        self.apply_spec_to_ui(spec)
        self.preset_status.setText(f"Loaded preset '{name}'.")

    def delete_selected_preset(self):
        name = self._selected_preset_name()
        if not name:
            return

        store = load_preset_store()
        presets = store.get("presets", [])
        if not isinstance(presets, list):
            presets = []

        new_presets = [record for record in presets if record.get("name") != name]
        if len(new_presets) == len(presets):
            self.preset_status.setText(f"Preset '{name}' was not found.")
            return

        store["version"] = PRESET_STORE_VERSION
        store["presets"] = new_presets
        save_preset_store(store)
        self.refresh_preset_list()
        self.preset_status.setText(f"Deleted preset '{name}'.")

    def _current_standard_key(self):
        return self.standard_combo.currentData()

    def _on_standard_changed(self, index):
        self._apply_standard_defaults(self._current_standard_key())
        self.refresh_summary()

    def _on_preset_selection_changed(self, index):
        if index <= 0:
            return

    def apply_spec_to_ui(self, spec):
        standard_key = spec.get("standard_key", STANDARD_DOEPFER)
        self._set_standard(standard_key)

        if standard_key == STANDARD_DOEPFER:
            self.doepfer_hp_spin.setValue(int(spec.get("width_value", 8)))
            self.doepfer_thickness_spin.setValue(float(spec.get("thickness_mm", 2.0)))
            self.doepfer_center_checkbox.setChecked(
                bool(spec.get("doepfer_center_single_hole_column", CENTER_SINGLE_HOLE_COLUMN))
            )
            narrow_key = spec.get("doepfer_narrow_diagonal_key", DOEPFER_NARROW_UPPER_LEFT_LOWER_RIGHT)
            narrow_index = self.doepfer_narrow_combo.findData(narrow_key)
            if narrow_index >= 0:
                self.doepfer_narrow_combo.setCurrentIndex(narrow_index)
            self._update_doepfer_narrow_controls()
        elif standard_key == STANDARD_INTELLIJEL_1U:
            self.intellijel_1u_hp_spin.setValue(int(spec.get("width_value", 10)))
        elif standard_key == STANDARD_PULP_LOGIC_1U:
            self.pulplogic_tiles_spin.setValue(int(spec.get("width_value", 2)))
        elif standard_key == STANDARD_KOSMO:
            self.kosmo_units_spin.setValue(int(spec.get("width_value", 8)))
        else:
            self.custom_width_spin.setValue(float(spec.get("width_mm", 80.0)))
            self.custom_height_spin.setValue(float(spec.get("height_mm", 128.5)))
            self.custom_thickness_spin.setValue(float(spec.get("thickness_mm", 2.0)))
            self.custom_hole_diameter_spin.setValue(float(spec.get("hole_diameter_mm", 3.2)))
            self.custom_x_margin_spin.setValue(float(spec.get("hole_x_margin_mm", 7.5)))
            self.custom_y_margin_spin.setValue(float(spec.get("hole_y_margin_mm", 3.0)))

        if hasattr(self, "top_clearance_spin"):
            self.top_clearance_spin.setValue(float(spec.get("top_clearance_mm", 10.0)))
        if hasattr(self, "bottom_clearance_spin"):
            self.bottom_clearance_spin.setValue(float(spec.get("bottom_clearance_mm", 10.0)))

        cutout_type = spec.get("cutout_type", "circles")
        cutout_index = self.cutout_combo.findData(cutout_type)
        if cutout_index >= 0:
            self.cutout_combo.setCurrentIndex(cutout_index)

        self.refresh_summary()

    def _current_spec(self):
        standard_key = self._current_standard_key()
        cutout_type = self.cutout_combo.currentData()

        if standard_key == STANDARD_DOEPFER:
            return build_panel_spec(
                standard_key,
                cutout_type,
                doepfer_hp=self.doepfer_hp_spin.value(),
                doepfer_center_single_hole_column=self.doepfer_center_checkbox.isChecked(),
                doepfer_narrow_diagonal_key=self.doepfer_narrow_combo.currentData(),
                doepfer_thickness_mm=self.doepfer_thickness_spin.value(),
                top_clearance_mm=self.top_clearance_spin.value(),
                bottom_clearance_mm=self.bottom_clearance_spin.value(),
            )

        if standard_key == STANDARD_INTELLIJEL_1U:
            return build_panel_spec(
                standard_key,
                cutout_type,
                doepfer_hp=self.intellijel_1u_hp_spin.value(),
                top_clearance_mm=self.top_clearance_spin.value(),
                bottom_clearance_mm=self.bottom_clearance_spin.value(),
            )

        if standard_key == STANDARD_PULP_LOGIC_1U:
            return build_panel_spec(
                standard_key,
                cutout_type,
                doepfer_hp=self.pulplogic_tiles_spin.value(),
                top_clearance_mm=self.top_clearance_spin.value(),
                bottom_clearance_mm=self.bottom_clearance_spin.value(),
            )

        if standard_key == STANDARD_KOSMO:
            return build_panel_spec(
                standard_key,
                cutout_type,
                kosmo_units=self.kosmo_units_spin.value(),
                top_clearance_mm=self.top_clearance_spin.value(),
                bottom_clearance_mm=self.bottom_clearance_spin.value(),
            )

        return build_panel_spec(
            standard_key,
            cutout_type,
            custom_width_mm=self.custom_width_spin.value(),
            custom_height_mm=self.custom_height_spin.value(),
            custom_thickness_mm=self.custom_thickness_spin.value(),
            custom_hole_diameter_mm=self.custom_hole_diameter_spin.value(),
            custom_hole_x_margin_mm=self.custom_x_margin_spin.value(),
            custom_hole_y_margin_mm=self.custom_y_margin_spin.value(),
            top_clearance_mm=self.top_clearance_spin.value(),
            bottom_clearance_mm=self.bottom_clearance_spin.value(),
        )

    def selected_parameters(self):
        return self._current_spec()

    def refresh_summary(self, *args):
        spec = self._current_spec()
        self.summary_box.setPlainText(panel_layout_summary_from_spec(spec))
        self.preview.setParameters(spec, show_pcb=self.create_pcb_checkbox.isChecked())

    def getStandardButtons(self):
        return int(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)

    def accept(self):
        global ACTIVE_FACEPLATE_TASK_PANEL
        panel_spec = self._current_spec()
        self.created_spec = panel_spec
        self.created_body = create_panel_from_spec(panel_spec, create_pcb=self.create_pcb_checkbox.isChecked())
        self.created_source = getattr(self.created_body, "BaseFeature", None) if self.created_body is not None else None
        ACTIVE_FACEPLATE_TASK_PANEL = self
        self.refresh_summary()
        return True

    def reject(self):
        global ACTIVE_FACEPLATE_TASK_PANEL
        super().reject()
        ACTIVE_FACEPLATE_TASK_PANEL = None
        return True

    def closeEvent(self, event):
        global ACTIVE_FACEPLATE_TASK_PANEL
        ACTIVE_FACEPLATE_TASK_PANEL = None
        super().closeEvent(event)


def create_panel_from_spec(spec, create_pcb=False):
    doc = App.ActiveDocument
    if doc is None:
        doc = App.newDocument("Eurorack_Panel")

    shape = make_panel_shape_from_spec(spec)
    body, source = create_body_from_spec(doc, shape, spec)
    pcb = create_pcb_from_spec(doc, spec) if create_pcb else None

    if pcb is not None:
        try:
            body.addProperty("App::PropertyString", "EurorackForgePCBObjectName", "EurorackForge", "Name of the matching PCB object.")
        except Exception:
            pass
        try:
            source.addProperty("App::PropertyString", "EurorackForgePCBObjectName", "EurorackForge", "Name of the matching PCB object.")
        except Exception:
            pass
        try:
            body.EurorackForgePCBObjectName = pcb.Name
        except Exception:
            pass
        try:
            source.EurorackForgePCBObjectName = pcb.Name
        except Exception:
            pass
        try:
            pcb.EurorackForgeRole = "PCB"
        except Exception:
            pass
        try:
            pcb.EurorackForgePCBOf = body.Name
        except Exception:
            pass

    doc.recompute()

    reference_sketch = None
    if Gui is not None:
        reference_sketch = create_reference_sketch(body, source, spec)
        try:
            doc.recompute()
        except Exception:
            pass

    if Gui is not None:
        try:
            Gui.Selection.clearSelection()
            Gui.Selection.addSelection(body)
            Gui.ActiveDocument.ActiveView.fitAll()
        except Exception:
            pass

    pcb_line = (
        f"PCB outline: {pcb.Shape.BoundBox.XLength:.2f} mm x {pcb.Shape.BoundBox.YLength:.2f} mm x {pcb.Shape.BoundBox.ZLength:.2f} mm\n"
        if pcb is not None
        else "PCB outline: not created\n"
    )

    App.Console.PrintMessage(
        (
            "\nCreated Eurorack panel\n"
            f"Standard: {spec['standard_label']}\n"
            f"Size: {spec['width_display']}\n"
            f"Width: {spec['width_mm']:.2f} mm\n"
            f"Height: {spec['height_mm']:.2f} mm\n"
            f"Thickness: {spec['thickness_mm']:.2f} mm\n"
            f"{pcb_line}"
            f"Cutout type: {spec['cutout_type']}\n"
            f"Hole diameter: {spec['hole_diameter_mm']:.2f} mm\n"
            f"Slot size: {spec['slot_length_mm']:.2f} mm x {spec['slot_height_mm']:.2f} mm\n"
            f"Top keep-out: {spec['top_clearance_mm']:.2f} mm\n"
            f"Bottom keep-out: {spec['bottom_clearance_mm']:.2f} mm\n"
            f"Mounting points: {generic_mounting_points(spec)}\n\n"
        )
    )

    return body


def create_eurorack_panel(
    hp,
    cutout_type,
    center_single_hole_column=CENTER_SINGLE_HOLE_COLUMN,
    narrow_diagonal_key=DOEPFER_NARROW_UPPER_LEFT_LOWER_RIGHT,
    thickness_mm=PANEL_THICKNESS,
):
    spec = build_panel_spec(
        STANDARD_DOEPFER,
        cutout_type,
        doepfer_hp=hp,
        doepfer_center_single_hole_column=center_single_hole_column,
        doepfer_narrow_diagonal_key=narrow_diagonal_key,
        doepfer_thickness_mm=thickness_mm,
    )
    return create_panel_from_spec(spec, create_pcb=False)


def create_single_eurorack_panel():
    global ACTIVE_FACEPLATE_TASK_PANEL

    if Gui is None:
        return create_panel_from_spec(build_panel_spec(STANDARD_DOEPFER, "circles"), create_pcb=False)

    if ACTIVE_FACEPLATE_TASK_PANEL is None:
        ACTIVE_FACEPLATE_TASK_PANEL = FaceplateTaskPanel()

    try:
        ACTIVE_FACEPLATE_TASK_PANEL.show()
        ACTIVE_FACEPLATE_TASK_PANEL.raise_()
        ACTIVE_FACEPLATE_TASK_PANEL.activateWindow()
    except Exception:
        return create_panel_from_spec(build_panel_spec(STANDARD_DOEPFER, "circles"), create_pcb=False)

    return ACTIVE_FACEPLATE_TASK_PANEL


def _sanitize_file_stem(text):
    cleaned = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in text.strip())
    cleaned = cleaned.strip("_")
    return cleaned or "EurorackPanel"


def _export_path_conflict(filename):
    return os.path.exists(filename)


def _export_conflict_message(filename):
    return f"Export target already exists: {filename}"


def _pcb_export_filename(filename):
    stem, ext = os.path.splitext(filename)
    if not ext:
        ext = ".dxf"
    return stem + "_pcb" + ext


def _pcb_dxf_text_from_spec(spec):
    width_mm, height_mm, _ = pcb_outline_dimensions_from_spec(spec)
    half_width = width_mm / 2.0
    half_height = height_mm / 2.0

    lines = [
        "0", "SECTION",
        "2", "HEADER",
        "0", "ENDSEC",
        "0", "SECTION",
        "2", "TABLES",
        "0", "ENDSEC",
        "0", "SECTION",
        "2", "ENTITIES",
        "0", "LWPOLYLINE",
        "8", "0",
        "90", "4",
        "70", "1",
    ]

    points = [
        (-half_width, -half_height),
        (half_width, -half_height),
        (half_width, half_height),
        (-half_width, half_height),
    ]
    for x, y in points:
        lines.extend([
            "10", _kicad_num(x),
            "20", _kicad_num(y),
        ])

    lines.extend([
        "0", "ENDSEC",
        "0", "EOF",
    ])
    return "\n".join(lines) + "\n"


def _pcb_object_for_export(obj):
    if obj is None:
        return None

    doc = obj.Document or App.ActiveDocument
    if doc is None:
        return None

    candidate_names = [
        getattr(obj, "EurorackForgePCBObjectName", ""),
        getattr(getattr(obj, "BaseFeature", None), "EurorackForgePCBObjectName", ""),
    ]
    for candidate_name in candidate_names:
        if not candidate_name:
            continue
        candidate = doc.getObject(candidate_name)
        if candidate is not None:
            return candidate

    linked_name = getattr(obj, "Name", "")
    if linked_name:
        for candidate in getattr(doc, "Objects", []) or []:
            if getattr(candidate, "EurorackForgeRole", "") == "PCB" and getattr(candidate, "EurorackForgePCBOf", "") == linked_name:
                return candidate

    spec = _export_spec_from_obj(obj)
    if spec is None:
        return None

    pcb_name = f"{spec['standard_key']}_{str(spec['width_value']).replace('.', '_')}_{spec['cutout_type']}_PCB"
    candidate = doc.getObject(pcb_name)
    if candidate is not None:
        return candidate

    return None


class ExportTaskPanel(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Export Eurorack Panel")
        self.setMinimumWidth(980)
        self.setMinimumHeight(640)
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.Window)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
        self.form = self
        self.export_target = None
        self._export_directory = None

        self._build_ui()
        FaceplateTaskPanel._apply_style(self)
        self.refresh_selection()
        self._update_format_ui()

    def _build_ui(self):
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(14)

        hero = QtWidgets.QFrame()
        hero.setObjectName("heroPanel")
        hero_layout = QtWidgets.QHBoxLayout(hero)
        hero_layout.setContentsMargins(18, 16, 18, 16)
        hero_layout.setSpacing(14)

        icon_label = QtWidgets.QLabel()
        icon_label.setFixedSize(56, 56)
        icon = QtGui.QIcon(resource_path("EurorackForgeExport.svg"))
        icon_label.setPixmap(icon.pixmap(48, 48))
        icon_label.setAlignment(QtCore.Qt.AlignCenter)

        title_block = QtWidgets.QVBoxLayout()
        title_block.setSpacing(4)

        title = QtWidgets.QLabel("Export Selected Panel")
        title.setObjectName("heroTitle")
        subtitle = QtWidgets.QLabel(
            "Choose STL for the solid body, SVG for vector output, PNG for a rendered image, or DXF for Draft projection."
        )
        subtitle.setObjectName("heroSubtitle")
        subtitle.setWordWrap(True)

        title_block.addWidget(title)
        title_block.addWidget(subtitle)
        title_block.addStretch(1)

        hero_layout.addWidget(icon_label, 0, QtCore.Qt.AlignTop)
        hero_layout.addLayout(title_block, 1)
        root.addWidget(hero)

        content = QtWidgets.QHBoxLayout()
        content.setSpacing(14)

        left_column = QtWidgets.QVBoxLayout()
        left_column.setSpacing(14)

        target_box = QtWidgets.QGroupBox("Target")
        target_layout = QtWidgets.QVBoxLayout(target_box)
        target_layout.setSpacing(10)

        target_form = QtWidgets.QFormLayout()
        target_form.setHorizontalSpacing(12)
        target_form.setVerticalSpacing(10)

        self.target_name = QtWidgets.QLineEdit()
        self.target_name.setReadOnly(True)
        self.target_name.setPlaceholderText("Select a panel body in the model tree")

        self.target_type = QtWidgets.QLineEdit()
        self.target_type.setReadOnly(True)
        self.target_type.setPlaceholderText("Object type")

        target_form.addRow("Object", self.target_name)
        target_form.addRow("Type", self.target_type)

        self.export_name = QtWidgets.QLineEdit()
        self.export_name.setPlaceholderText("Export file name")
        self.export_name.textEdited.connect(self._update_output_path)
        target_form.addRow("Export name", self.export_name)
        target_layout.addLayout(target_form)

        target_buttons = QtWidgets.QHBoxLayout()
        target_buttons.setSpacing(8)

        self.refresh_target_button = QtWidgets.QToolButton()
        self.refresh_target_button.setText("Use Selected")
        self.refresh_target_button.clicked.connect(self.refresh_selection)

        target_buttons.addWidget(self.refresh_target_button)
        target_buttons.addStretch(1)
        target_layout.addLayout(target_buttons)

        left_column.addWidget(target_box)

        format_box = QtWidgets.QGroupBox("Format")
        format_layout = QtWidgets.QVBoxLayout(format_box)
        format_layout.setSpacing(10)

        format_form = QtWidgets.QFormLayout()
        format_form.setHorizontalSpacing(12)
        format_form.setVerticalSpacing(10)

        self.format_combo = QtWidgets.QComboBox()
        self.format_combo.addItem("STL", "stl")
        self.format_combo.addItem("SVG", "svg")
        self.format_combo.addItem("PNG", "png")
        self.format_combo.addItem("KiCad DXF", "kicad")
        self.format_combo.currentIndexChanged.connect(self._update_format_ui)

        format_form.addRow("Export as", self.format_combo)
        format_layout.addLayout(format_form)

        self.options_stack = QtWidgets.QStackedWidget()
        self.options_stack.addWidget(self._build_stl_options())
        self.options_stack.addWidget(self._build_svg_options())
        self.options_stack.addWidget(self._build_png_options())
        self.options_stack.addWidget(self._build_kicad_options())
        format_layout.addWidget(self.options_stack)

        left_column.addWidget(format_box)

        output_box = QtWidgets.QGroupBox("Output")
        output_layout = QtWidgets.QVBoxLayout(output_box)
        output_layout.setSpacing(10)

        path_row = QtWidgets.QHBoxLayout()
        path_row.setSpacing(8)

        self.output_path = QtWidgets.QLineEdit()
        self.output_path.setPlaceholderText("Enter a file name or path")

        self.browse_button = QtWidgets.QToolButton()
        self.browse_button.setText("Browse")
        self.browse_button.clicked.connect(self.choose_output_path)

        path_row.addWidget(self.output_path, 1)
        path_row.addWidget(self.browse_button, 0)
        output_layout.addLayout(path_row)

        self.export_status = QtWidgets.QLabel("Select a panel and choose a format.")
        self.export_status.setWordWrap(True)
        self.export_status.setObjectName("helperText")
        output_layout.addWidget(self.export_status)

        self.export_feedback = QtWidgets.QLabel("")
        self.export_feedback.setWordWrap(True)
        self.export_feedback.setVisible(False)
        self.export_feedback.setObjectName("exportFeedback")
        output_layout.addWidget(self.export_feedback)

        left_column.addWidget(output_box)

        left_column.addStretch(1)

        preview_box = QtWidgets.QGroupBox("Notes")
        preview_layout = QtWidgets.QVBoxLayout(preview_box)
        preview_layout.setSpacing(10)

        self.notes = QtWidgets.QPlainTextEdit()
        self.notes.setReadOnly(True)
        self.notes.setLineWrapMode(QtWidgets.QPlainTextEdit.WidgetWidth)
        self.notes.setMinimumHeight(220)
        self.notes.setFont(QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.FixedFont))
        preview_layout.addWidget(self.notes)

        content.addLayout(left_column, 1)
        content.addWidget(preview_box, 1)
        root.addLayout(content)

        self.button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        self.button_box.button(QtWidgets.QDialogButtonBox.Ok).setText("Export")
        self.button_box.button(QtWidgets.QDialogButtonBox.Cancel).setText("Close")
        self.button_box.accepted.connect(self.export_selected)
        self.button_box.rejected.connect(self.reject)
        root.addWidget(self.button_box)

    def _build_stl_options(self):
        page = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        form = QtWidgets.QFormLayout()
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)

        self.stl_deflection_spin = QtWidgets.QDoubleSpinBox()
        self.stl_deflection_spin.setRange(0.001, 5.0)
        self.stl_deflection_spin.setDecimals(3)
        self.stl_deflection_spin.setSingleStep(0.01)
        self.stl_deflection_spin.setValue(0.10)
        self.stl_deflection_spin.setSuffix(" mm")

        form.addRow("Deflection", self.stl_deflection_spin)
        layout.addLayout(form)

        note = QtWidgets.QLabel("STL uses the selected object's solid shape.")
        note.setWordWrap(True)
        note.setObjectName("helperText")
        layout.addWidget(note)
        layout.addStretch(1)

        return page

    def _build_svg_options(self):
        page = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        note = QtWidgets.QLabel(
            "SVG exports the selected shape as vector geometry. It creates a temporary Part feature from the panel shape so the result stays clean."
        )
        note.setWordWrap(True)
        note.setObjectName("helperText")
        layout.addWidget(note)
        layout.addStretch(1)

        return page

    def _build_png_options(self):
        page = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        form = QtWidgets.QFormLayout()
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)

        self.png_width_spin = QtWidgets.QSpinBox()
        self.png_width_spin.setRange(64, 8192)
        self.png_width_spin.setSingleStep(64)
        self.png_width_spin.setValue(2048)
        self.png_width_spin.setSuffix(" px")

        self.png_height_spin = QtWidgets.QSpinBox()
        self.png_height_spin.setRange(64, 8192)
        self.png_height_spin.setSingleStep(64)
        self.png_height_spin.setValue(2048)
        self.png_height_spin.setSuffix(" px")

        self.png_fit_checkbox = QtWidgets.QCheckBox("Fit selected panel before rendering")
        self.png_fit_checkbox.setChecked(True)

        self.png_panel_color_button = QtWidgets.QPushButton("Choose...")
        self.png_panel_color_button.clicked.connect(self.choose_png_panel_color)
        self.png_panel_color_preview = QtWidgets.QLabel()
        self.png_panel_color_preview.setFixedSize(28, 18)
        self.png_panel_color_preview.setObjectName("colorSwatch")
        self.png_panel_color = QtGui.QColor("#d9dde4")
        self._sync_png_color_preview(self.png_panel_color_preview, self.png_panel_color)

        self.png_background_button = QtWidgets.QPushButton("Choose...")
        self.png_background_button.clicked.connect(self.choose_png_background_color)
        self.png_background_preview = QtWidgets.QLabel()
        self.png_background_preview.setFixedSize(28, 18)
        self.png_background_preview.setObjectName("colorSwatch")
        self.png_background_color = QtGui.QColor("#ffffff")
        self._sync_png_color_preview(self.png_background_preview, self.png_background_color)

        form.addRow("Width", self.png_width_spin)
        form.addRow("Height", self.png_height_spin)
        form.addRow("Panel color", self._color_row(self.png_panel_color_preview, self.png_panel_color_button))
        form.addRow("Background", self._color_row(self.png_background_preview, self.png_background_button))
        layout.addLayout(form)
        layout.addWidget(self.png_fit_checkbox)

        note = QtWidgets.QLabel(
            "PNG is rendered from the current 3D view. Panel and background colors can be changed here."
        )
        note.setWordWrap(True)
        note.setObjectName("helperText")
        layout.addWidget(note)
        layout.addStretch(1)

        return page

    def _build_kicad_options(self):
        page = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        note = QtWidgets.QLabel(
            "KiCad DXF follows the manual Draft flow: select the last feature in the Body, run Shape2DView, then export the generated 2D object as a legacy-friendly DXF."
        )
        note.setWordWrap(True)
        note.setObjectName("helperText")
        layout.addWidget(note)
        layout.addStretch(1)

        return page

    def _color_row(self, preview, button):
        row = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(preview, 0)
        layout.addWidget(button, 0)
        layout.addStretch(1)
        return row

    def _sync_png_color_preview(self, preview, color):
        preview.setStyleSheet(
            "QLabel#colorSwatch {"
            f"background-color: {color.name()};"
            "border: 1px solid rgba(90, 100, 115, 180);"
            "border-radius: 4px;"
            "}"
        )

    def choose_png_panel_color(self):
        color = QtWidgets.QColorDialog.getColor(self.png_panel_color, self, "Choose PNG Panel Color")
        if color.isValid():
            self.png_panel_color = color
            self._sync_png_color_preview(self.png_panel_color_preview, color)

    def choose_png_background_color(self):
        color = QtWidgets.QColorDialog.getColor(self.png_background_color, self, "Choose PNG Background Color")
        if color.isValid():
            self.png_background_color = color
            self._sync_png_color_preview(self.png_background_preview, color)

    def _selected_object_name(self):
        return getattr(self.export_target, "Label", getattr(self.export_target, "Name", "No selection")) if self.export_target else "No selection"

    def _selected_object_type(self):
        return getattr(self.export_target, "TypeId", "") if self.export_target else ""

    def _current_format(self):
        return self.format_combo.currentData()

    def _current_extension(self):
        return {
            "stl": ".stl",
            "svg": ".svg",
            "png": ".png",
            "kicad": ".dxf",
        }.get(self._current_format(), ".stl")

    def _update_notes(self):
        fmt = self._current_format()
        notes = [
            "Select a panel body in the tree or model view, then export.",
            f"Current target: {self._selected_object_name()}",
        ]
        if fmt == "stl":
            notes.append("STL exports the solid shape.")
        elif fmt == "svg":
            notes.append("SVG exports vector geometry from the selected shape.")
        elif fmt == "png":
            notes.append("PNG captures the active 3D view.")
        else:
            notes.append("KiCad DXF follows the Draft Shape2DView workflow on the final Body feature, then exports the generated 2D object as a legacy-friendly DXF.")

        self.notes.setPlainText("\n".join(notes))

    def _update_format_ui(self, *args):
        self.options_stack.setCurrentIndex({"stl": 0, "svg": 1, "png": 2, "kicad": 3}.get(self._current_format(), 0))
        self._update_output_path()
        self._update_notes()

    def _update_output_path(self, *args):
        obj = self.export_target
        if obj is None:
            return

        current_path = self.output_path.text().strip()
        current_dir = os.path.dirname(current_path) if current_path else ""

        current_name = self.export_name.text().strip()
        if current_name:
            stem = _sanitize_file_stem(current_name)
        elif current_path:
            stem = _sanitize_file_stem(os.path.splitext(os.path.basename(current_path))[0])
        else:
            stem = _sanitize_file_stem(getattr(obj, "Name", getattr(obj, "Label", "EurorackPanel")))

        doc = App.ActiveDocument
        default_dir = current_dir or self._export_directory
        if not default_dir and doc is not None and getattr(doc, "FileName", ""):
            default_dir = os.path.dirname(doc.FileName)
        if not default_dir:
            default_dir = os.path.expanduser("~")

        self._export_directory = default_dir

        self.output_path.setText(os.path.join(default_dir, stem + self._current_extension()))

    def _set_export_feedback(self, success, message):
        self.export_feedback.setVisible(True)
        self.export_feedback.setText(message)
        if success:
            self.export_feedback.setStyleSheet(
                "QLabel#exportFeedback {"
                "background: rgba(31, 122, 74, 0.18);"
                "border: 1px solid rgba(31, 122, 74, 150);"
                "border-radius: 10px;"
                "padding: 8px 10px;"
                "color: #1f7a4a;"
                "font-weight: 600;"
                "}"
            )
        else:
            self.export_feedback.setStyleSheet(
                "QLabel#exportFeedback {"
                "background: rgba(160, 55, 55, 0.12);"
                "border: 1px solid rgba(160, 55, 55, 150);"
                "border-radius: 10px;"
                "padding: 8px 10px;"
                "color: #a03737;"
                "font-weight: 600;"
                "}"
            )

    def refresh_selection(self):
        self.export_target = _selected_export_target()
        self.target_name.setText(self._selected_object_name())
        self.target_type.setText(self._selected_object_type())

        doc = App.ActiveDocument
        doc_stem = None
        if doc is not None and getattr(doc, "FileName", ""):
            doc_stem = _sanitize_file_stem(os.path.splitext(os.path.basename(doc.FileName))[0])

        if self.export_target is None:
            self.export_status.setText("Select a panel body in the tree or model view.")
            self.export_feedback.setVisible(False)
            self.export_name.setText("")
        else:
            self.export_status.setText(f"Ready to export {self._selected_object_name()}.")
            if not self.export_name.text().strip():
                self.export_name.setText(doc_stem or getattr(self.export_target, "Name", getattr(self.export_target, "Label", "EurorackPanel")))
            self._update_output_path()
            self.export_feedback.setVisible(False)

        self._update_notes()

    def choose_output_path(self):
        obj = self.export_target
        if obj is None:
            self.refresh_selection()
            obj = self.export_target
        if obj is None:
            self.export_status.setText("Select a panel first.")
            return

        doc = App.ActiveDocument
        current_output = self.output_path.text().strip()
        default_dir = self._export_directory or (os.path.dirname(current_output) if current_output else "")
        if not default_dir and doc is not None and getattr(doc, "FileName", ""):
            default_dir = os.path.dirname(doc.FileName)
        if not default_dir:
            default_dir = os.path.expanduser("~")

        current_name = self.export_name.text().strip()
        if current_name:
            stem = _sanitize_file_stem(current_name)
        elif current_output:
            stem = _sanitize_file_stem(os.path.splitext(os.path.basename(current_output))[0])
        else:
            doc_stem = None
            if doc is not None and getattr(doc, "FileName", ""):
                doc_stem = _sanitize_file_stem(os.path.splitext(os.path.basename(doc.FileName))[0])
            stem = doc_stem or _sanitize_file_stem(getattr(obj, "Name", getattr(obj, "Label", "EurorackPanel")))
        current = os.path.join(default_dir, stem + self._current_extension())

        fmt = self._current_format()
        filters = {
            "stl": "STL Files (*.stl)",
            "svg": "SVG Files (*.svg)",
            "png": "PNG Files (*.png)",
            "kicad": "DXF Files (*.dxf)",
        }
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Choose Export File",
            current,
            filters.get(fmt, "All Files (*)"),
        )
        if not filename:
            return
        if not filename.lower().endswith(self._current_extension()):
            filename += self._current_extension()
        self._export_directory = os.path.dirname(filename)
        self.output_path.setText(filename)

    def export_selected(self):
        self.refresh_selection()
        obj = self.export_target
        if obj is None:
            self.export_status.setText("Select a panel body before exporting.")
            self._set_export_feedback(False, "No panel selected.")
            return

        filename = self.output_path.text().strip()
        if not filename:
            self.export_status.setText("Enter a file name before exporting.")
            self._set_export_feedback(False, "File name is required.")
            return

        fmt = self._current_format()
        if fmt == "stl":
            ok, result = export_selected_object_to_stl(obj=obj, filename=filename, deflection=self.stl_deflection_spin.value())
        elif fmt == "svg":
            ok, result = export_selected_object_to_svg(obj=obj, filename=filename)
        elif fmt == "png":
            ok, result = export_selected_object_to_png(
                obj=obj,
                filename=filename,
                width=self.png_width_spin.value(),
                height=self.png_height_spin.value(),
                fit=self.png_fit_checkbox.isChecked(),
                background_color=self.png_background_color,
                panel_color=self.png_panel_color,
            )
        else:
            ok, result = export_selected_object_to_kicad_dxf(obj=obj, filename=filename)

        if ok:
            self._export_directory = os.path.dirname(result)
            exported_label = os.path.basename(result)
            pcb_obj = _pcb_object_for_export(obj) if fmt == "kicad" else None
            if fmt == "kicad" and pcb_obj is not None:
                pcb_name = os.path.basename(_pcb_export_filename(result))
                self.export_status.setText(f"Exported {exported_label} and {pcb_name}.")
                self._set_export_feedback(True, f"Export complete: {exported_label} and {pcb_name}")
            else:
                self.export_status.setText(f"Exported {exported_label}.")
                self._set_export_feedback(True, f"Export complete: {exported_label}")
            try:
                App.Console.PrintMessage(f"\nExported panel: {result}\n")
            except Exception:
                pass
        else:
            self.export_status.setText(result)
            self._set_export_feedback(False, result)

    def reject(self):
        global ACTIVE_EXPORT_TASK_PANEL
        super().reject()
        ACTIVE_EXPORT_TASK_PANEL = None
        return True

    def closeEvent(self, event):
        global ACTIVE_EXPORT_TASK_PANEL
        ACTIVE_EXPORT_TASK_PANEL = None
        super().closeEvent(event)


def open_export_dialog():
    global ACTIVE_EXPORT_TASK_PANEL

    if Gui is None:
        return None

    if ACTIVE_EXPORT_TASK_PANEL is None:
        ACTIVE_EXPORT_TASK_PANEL = ExportTaskPanel()

    try:
        ACTIVE_EXPORT_TASK_PANEL.show()
        ACTIVE_EXPORT_TASK_PANEL.raise_()
        ACTIVE_EXPORT_TASK_PANEL.activateWindow()
    except Exception:
        return ACTIVE_EXPORT_TASK_PANEL

    return ACTIVE_EXPORT_TASK_PANEL
