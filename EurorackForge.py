import json
import os

import FreeCAD as App
import Part

try:
    import FreeCADGui as Gui
except Exception:
    Gui = None

try:
    from PySide6 import QtCore, QtGui, QtWidgets
except ImportError:
    try:
        from PySide2 import QtCore, QtGui, QtWidgets
    except ImportError:
        from PySide import QtCore, QtGui, QtWidgets


HP_MM = 5.08
PANEL_HEIGHT = 128.5
PANEL_THICKNESS = 2.0

WIDTH_CLEARANCE = 0.30

HOLE_DIAMETER = 3.2
HOLE_RADIUS = HOLE_DIAMETER / 2.0

SLOT_HEIGHT = 3.2
SLOT_LENGTH = 7.0

HOLE_X_FIRST = 7.5
HOLE_Y_FROM_EDGE = 3.0

FOUR_HOLES_START_HP = 12
CENTER_SINGLE_HOLE_COLUMN = True

STANDARD_DOEPFER = "doepfer"
STANDARD_INTELLIJEL_1U = "intellijel_1u"
STANDARD_PULP_LOGIC_1U = "pulplogic_1u"
STANDARD_KOSMO = "kosmo"
STANDARD_CUSTOM = "custom"

STANDARD_OPTIONS = [
    (STANDARD_DOEPFER, "Doepfer Eurorack"),
    (STANDARD_INTELLIJEL_1U, "Intellijel 1U"),
    (STANDARD_PULP_LOGIC_1U, "Pulp Logic 1U"),
    (STANDARD_KOSMO, "Kosmo (LMNC)"),
    (STANDARD_CUSTOM, "Custom"),
]

INTELLIJEL_1U_HEIGHT_MM = 39.65
PULP_LOGIC_1U_HEIGHT_MM = 43.18
ONE_U_HOLE_MARGIN_MM = 3.0

KOSMO_UNIT_MM = 25.0
KOSMO_HEIGHT_MM = 200.0
KOSMO_THICKNESS_MM = 1.5
KOSMO_HOLE_MARGIN_MM = 3.0

DEFAULT_SLOT_HEIGHT_MM = SLOT_HEIGHT
DEFAULT_SLOT_LENGTH_MM = SLOT_LENGTH
PRESET_STORE_VERSION = 1
PRESET_STORE_FILENAME = "presets.json"


def resource_path(filename):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, filename)


def preset_store_path():
    base_dir = None

    if hasattr(App, "getUserAppDataDir"):
        try:
            base_dir = App.getUserAppDataDir()
        except Exception:
            base_dir = None

    if not base_dir:
        base_dir = os.path.join(os.path.expanduser("~"), ".FreeCAD")

    store_dir = os.path.join(base_dir, "EurorackForge")
    return os.path.join(store_dir, PRESET_STORE_FILENAME)


def load_preset_store():
    path = preset_store_path()

    if not os.path.exists(path):
        return {"version": PRESET_STORE_VERSION, "presets": []}

    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except Exception:
        return {"version": PRESET_STORE_VERSION, "presets": []}

    if not isinstance(data, dict):
        return {"version": PRESET_STORE_VERSION, "presets": []}

    presets = data.get("presets", [])
    if not isinstance(presets, list):
        presets = []

    return {"version": PRESET_STORE_VERSION, "presets": presets}


def save_preset_store(store):
    path = preset_store_path()
    directory = os.path.dirname(path)
    os.makedirs(directory, exist_ok=True)

    with open(path, "w", encoding="utf-8") as handle:
        json.dump(store, handle, indent=2, ensure_ascii=False)


def preset_summary_text(spec):
    return (
        f"{spec['display_name']} | {spec['standard_label']} | "
        f"{spec['width_display']} | {cutout_label(spec['cutout_type'])}"
    )


def make_preset_record(name, spec):
    return {
        "name": name,
        "spec": spec,
        "summary": preset_summary_text(spec),
    }


def cutout_label(cutout_type):
    if cutout_type == "circles":
        return "Round mounting holes"

    return "Horizontal slots"


def hp_to_width_text(hp):
    width = eurorack_panel_width(hp)
    return f"{hp} HP / {width:.2f} mm"


def format_positions(values):
    return "[" + ", ".join(f"{value:.2f}" for value in values) + "]"


def format_mm(value):
    return f"{value:.2f} mm"


def standard_label(standard_key):
    for key, label in STANDARD_OPTIONS:
        if key == standard_key:
            return label

    return standard_key


def doepfer_width_mm(hp):
    return hp * HP_MM - WIDTH_CLEARANCE


def intellijel_1u_width_mm(hp):
    return hp * HP_MM - WIDTH_CLEARANCE


def pulp_logic_1u_width_mm(tiles):
    tile_width_mm = (6 * HP_MM) - 0.50
    return tiles * tile_width_mm


def kosmo_width_mm(units):
    return units * KOSMO_UNIT_MM


def build_panel_spec(
    standard_key,
    cutout_type,
    *,
    doepfer_hp=8,
    doepfer_center_single_hole_column=CENTER_SINGLE_HOLE_COLUMN,
    kosmo_units=8,
    custom_width_mm=80.0,
    custom_height_mm=128.5,
    custom_thickness_mm=2.0,
    custom_hole_diameter_mm=3.2,
    custom_hole_x_margin_mm=7.5,
    custom_hole_y_margin_mm=3.0,
    custom_layout_key="corners",
):
    if standard_key == STANDARD_DOEPFER:
        width_value = doepfer_hp
        width_mm = doepfer_width_mm(width_value)
        height_mm = PANEL_HEIGHT
        thickness_mm = PANEL_THICKNESS
        hole_diameter_mm = HOLE_DIAMETER
        hole_x_margin_mm = HOLE_X_FIRST
        hole_y_margin_mm = HOLE_Y_FROM_EDGE
        hole_layout_key = "doepfer"
        width_unit_label = "HP"
        width_display = f"{width_value} HP"
        display_name = f"Doepfer Eurorack {width_value} HP"
        conformance_note = (
            "Doepfer-style 3U panel with 5.08 mm HP grid, 128.5 mm height, and 2 mm thickness."
        )
    elif standard_key == STANDARD_INTELLIJEL_1U:
        width_value = doepfer_hp
        width_mm = intellijel_1u_width_mm(width_value)
        height_mm = INTELLIJEL_1U_HEIGHT_MM
        thickness_mm = 1.5
        hole_diameter_mm = HOLE_DIAMETER
        hole_x_margin_mm = ONE_U_HOLE_MARGIN_MM
        hole_y_margin_mm = ONE_U_HOLE_MARGIN_MM
        hole_layout_key = "corners"
        width_unit_label = "HP"
        width_display = f"{width_value} HP"
        display_name = f"Intellijel 1U {width_value} HP"
        conformance_note = (
            "Intellijel-style 1U panel with a 39.65 mm row height and 3 mm corner margins."
        )
    elif standard_key == STANDARD_PULP_LOGIC_1U:
        width_value = doepfer_hp
        width_mm = pulp_logic_1u_width_mm(width_value)
        height_mm = PULP_LOGIC_1U_HEIGHT_MM
        thickness_mm = 1.5
        hole_diameter_mm = HOLE_DIAMETER
        hole_x_margin_mm = ONE_U_HOLE_MARGIN_MM
        hole_y_margin_mm = ONE_U_HOLE_MARGIN_MM
        hole_layout_key = "corners"
        width_unit_label = "tiles"
        width_display = f"{width_value} tile(s) / {width_value * 6} HP"
        display_name = f"Pulp Logic 1U {width_value} tile(s)"
        conformance_note = (
            "Pulp Logic-style 1U tile with a 43.18 mm row height and 6 HP tile increments."
        )
    elif standard_key == STANDARD_KOSMO:
        width_value = kosmo_units
        width_mm = kosmo_width_mm(width_value)
        height_mm = KOSMO_HEIGHT_MM
        thickness_mm = KOSMO_THICKNESS_MM
        hole_diameter_mm = HOLE_DIAMETER
        hole_x_margin_mm = KOSMO_HOLE_MARGIN_MM
        hole_y_margin_mm = KOSMO_HOLE_MARGIN_MM
        hole_layout_key = "corners"
        width_unit_label = "x 2.5 cm"
        width_display = f"{width_value} x 2.5 cm"
        display_name = f"Kosmo {width_mm:.0f} mm"
        conformance_note = (
            "Kosmo-style 20 cm panel with 2.5 cm width steps and 3 mm mounting margins."
        )
    else:
        width_value = custom_width_mm
        width_mm = custom_width_mm
        height_mm = custom_height_mm
        thickness_mm = custom_thickness_mm
        hole_diameter_mm = custom_hole_diameter_mm
        hole_x_margin_mm = custom_hole_x_margin_mm
        hole_y_margin_mm = custom_hole_y_margin_mm
        hole_layout_key = custom_layout_key
        width_unit_label = "mm"
        width_display = f"{width_value:.2f} mm"
        display_name = "Custom panel"
        conformance_note = "Custom panel geometry."

    return {
        "standard_key": standard_key,
        "standard_label": standard_label(standard_key),
        "cutout_type": cutout_type,
        "width_value": width_value,
        "width_unit_label": width_unit_label,
        "width_display": width_display,
        "width_mm": width_mm,
        "height_mm": height_mm,
        "thickness_mm": thickness_mm,
        "hole_diameter_mm": hole_diameter_mm,
        "slot_height_mm": DEFAULT_SLOT_HEIGHT_MM,
        "slot_length_mm": DEFAULT_SLOT_LENGTH_MM,
        "hole_x_margin_mm": hole_x_margin_mm,
        "hole_y_margin_mm": hole_y_margin_mm,
        "hole_layout_key": hole_layout_key,
        "doepfer_center_single_hole_column": doepfer_center_single_hole_column,
        "doepfer_four_holes_start_hp": FOUR_HOLES_START_HP,
        "display_name": display_name,
        "conformance_note": conformance_note,
    }


def eurorack_panel_width(hp):
    return hp * HP_MM - WIDTH_CLEARANCE


def mounting_hole_x_positions(width, hp, center_single_hole_column=CENTER_SINGLE_HOLE_COLUMN):
    left_edge = -width / 2.0

    if hp < FOUR_HOLES_START_HP:
        if center_single_hole_column:
            return [0.0]

        return [left_edge + HOLE_X_FIRST]

    left_x = left_edge + HOLE_X_FIRST
    right_x = left_edge + HOLE_X_FIRST + (hp - 3) * HP_MM

    return [left_x, right_x]


def mounting_hole_y_positions():
    bottom_y = -PANEL_HEIGHT / 2.0
    top_y = PANEL_HEIGHT / 2.0

    return [
        bottom_y + HOLE_Y_FROM_EDGE,
        top_y - HOLE_Y_FROM_EDGE
    ]


def generic_mounting_hole_x_positions(spec):
    width = spec["width_mm"]
    left_edge = -width / 2.0

    if spec["hole_layout_key"] == "doepfer":
        width_value = spec["width_value"]
        threshold = spec["doepfer_four_holes_start_hp"]

        if width_value < threshold:
            if spec["doepfer_center_single_hole_column"]:
                return [0.0]

            return [left_edge + spec["hole_x_margin_mm"]]

        left_x = left_edge + spec["hole_x_margin_mm"]
        right_x = left_edge + spec["hole_x_margin_mm"] + (width_value - 3) * HP_MM
        return [left_x, right_x]

    if spec["hole_layout_key"] == "corners":
        return [
            left_edge + spec["hole_x_margin_mm"],
            width / 2.0 - spec["hole_x_margin_mm"]
        ]

    return [
        left_edge + spec["hole_x_margin_mm"],
        width / 2.0 - spec["hole_x_margin_mm"]
    ]


def generic_mounting_hole_y_positions(spec):
    height = spec["height_mm"]
    bottom_y = -height / 2.0
    top_y = height / 2.0

    return [
        bottom_y + spec["hole_y_margin_mm"],
        top_y - spec["hole_y_margin_mm"]
    ]


def make_round_hole_cutter(x, y):
    return Part.makeCylinder(
        HOLE_RADIUS,
        PANEL_THICKNESS + 2.0,
        App.Vector(x, y, -1.0),
        App.Vector(0, 0, 1)
    )


def make_horizontal_slot_cutter(x, y):
    radius = SLOT_HEIGHT / 2.0
    straight_length = SLOT_LENGTH - SLOT_HEIGHT

    left_center_x = x - straight_length / 2.0
    right_center_x = x + straight_length / 2.0

    left_round = Part.makeCylinder(
        radius,
        PANEL_THICKNESS + 2.0,
        App.Vector(left_center_x, y, -1.0),
        App.Vector(0, 0, 1)
    )

    right_round = Part.makeCylinder(
        radius,
        PANEL_THICKNESS + 2.0,
        App.Vector(right_center_x, y, -1.0),
        App.Vector(0, 0, 1)
    )

    center_box = Part.makeBox(
        straight_length,
        SLOT_HEIGHT,
        PANEL_THICKNESS + 2.0,
        App.Vector(
            x - straight_length / 2.0,
            y - SLOT_HEIGHT / 2.0,
            -1.0
        )
    )

    slot = left_round.fuse(right_round)
    slot = slot.fuse(center_box)

    return slot


def make_round_hole_cutter_mm(x, y, hole_diameter_mm, panel_thickness_mm):
    return Part.makeCylinder(
        hole_diameter_mm / 2.0,
        panel_thickness_mm + 2.0,
        App.Vector(x, y, -1.0),
        App.Vector(0, 0, 1)
    )


def make_horizontal_slot_cutter_mm(x, y, slot_height_mm, slot_length_mm, panel_thickness_mm):
    radius = slot_height_mm / 2.0
    straight_length = slot_length_mm - slot_height_mm

    left_center_x = x - straight_length / 2.0
    right_center_x = x + straight_length / 2.0

    left_round = Part.makeCylinder(
        radius,
        panel_thickness_mm + 2.0,
        App.Vector(left_center_x, y, -1.0),
        App.Vector(0, 0, 1)
    )

    right_round = Part.makeCylinder(
        radius,
        panel_thickness_mm + 2.0,
        App.Vector(right_center_x, y, -1.0),
        App.Vector(0, 0, 1)
    )

    center_box = Part.makeBox(
        straight_length,
        slot_height_mm,
        panel_thickness_mm + 2.0,
        App.Vector(
            x - straight_length / 2.0,
            y - slot_height_mm / 2.0,
            -1.0
        )
    )

    slot = left_round.fuse(right_round)
    slot = slot.fuse(center_box)

    return slot


def make_mounting_cutter(x, y, cutout_type):
    if cutout_type == "circles":
        return make_round_hole_cutter(x, y)

    return make_horizontal_slot_cutter(x, y)


def make_mounting_cutter_from_spec(x, y, spec):
    if spec["cutout_type"] == "circles":
        return make_round_hole_cutter_mm(
            x,
            y,
            spec["hole_diameter_mm"],
            spec["thickness_mm"]
        )

    return make_horizontal_slot_cutter_mm(
        x,
        y,
        spec["slot_height_mm"],
        spec["slot_length_mm"],
        spec["thickness_mm"]
    )


def make_panel_shape(width, hp, cutout_type, center_single_hole_column=CENTER_SINGLE_HOLE_COLUMN):
    panel = Part.makeBox(
        width,
        PANEL_HEIGHT,
        PANEL_THICKNESS,
        App.Vector(
            -width / 2.0,
            -PANEL_HEIGHT / 2.0,
            0
        )
    )

    for x in mounting_hole_x_positions(width, hp, center_single_hole_column):
        for y in mounting_hole_y_positions():
            cutter = make_mounting_cutter(x, y, cutout_type)
            panel = panel.cut(cutter)

    panel = panel.removeSplitter()
    return panel


def make_panel_shape_from_spec(spec):
    panel = Part.makeBox(
        spec["width_mm"],
        spec["height_mm"],
        spec["thickness_mm"],
        App.Vector(
            -spec["width_mm"] / 2.0,
            -spec["height_mm"] / 2.0,
            0
        )
    )

    for x in generic_mounting_hole_x_positions(spec):
        for y in generic_mounting_hole_y_positions(spec):
            cutter = make_mounting_cutter_from_spec(x, y, spec)
            panel = panel.cut(cutter)

    panel = panel.removeSplitter()
    return panel


def create_body_from_shape(doc, shape, hp, cutout_type):
    clean_name = f"Eurorack_{hp}HP_{cutout_type}"

    source = doc.addObject("Part::Feature", clean_name + "_BaseShape")
    source.Shape = shape
    source.Label = clean_name + " Base Shape"

    body = doc.addObject("PartDesign::Body", clean_name + "_Body")
    body.Label = f"Eurorack {hp}HP Panel - 2mm - {cutout_type}"

    body.BaseFeature = source

    try:
        source.ViewObject.Visibility = False
    except Exception:
        pass

    return body, source


def create_body_from_spec(doc, shape, spec):
    clean_name = f"{spec['standard_key']}_{str(spec['width_value']).replace('.', '_')}_{spec['cutout_type']}"

    source = doc.addObject("Part::Feature", clean_name + "_BaseShape")
    source.Shape = shape
    source.Label = f"{spec['display_name']} Base Shape"

    body = doc.addObject("PartDesign::Body", clean_name + "_Body")
    body.Label = f"{spec['display_name']} - {spec['thickness_mm']:.1f}mm - {spec['cutout_type']}"

    body.BaseFeature = source

    try:
        source.ViewObject.Visibility = False
    except Exception:
        pass

    return body, source


def panel_layout_summary(hp, cutout_type, center_single_hole_column=CENTER_SINGLE_HOLE_COLUMN):
    width = eurorack_panel_width(hp)
    x_positions = mounting_hole_x_positions(width, hp, center_single_hole_column)
    y_positions = mounting_hole_y_positions()

    if hp < FOUR_HOLES_START_HP:
        if center_single_hole_column:
            hole_layout = "Single centered mounting column"
        else:
            hole_layout = "Single left-side mounting column"
    else:
        hole_layout = "Two mounting columns, four holes"

    return (
        f"Width: {hp_to_width_text(hp)}\n"
        f"Height: {PANEL_HEIGHT:.2f} mm\n"
        f"Thickness: {PANEL_THICKNESS:.2f} mm\n"
        f"Mounting style: {cutout_label(cutout_type)}\n"
        f"Layout: {hole_layout}\n"
        f"X positions: {format_positions(x_positions)}\n"
        f"Y positions: {format_positions(y_positions)}\n"
        "Output: centered PartDesign Body with hidden base shape"
    )


def panel_layout_summary_from_spec(spec):
    x_positions = generic_mounting_hole_x_positions(spec)
    y_positions = generic_mounting_hole_y_positions(spec)

    if spec["standard_key"] == STANDARD_DOEPFER:
        if spec["width_value"] < spec["doepfer_four_holes_start_hp"]:
            if spec["doepfer_center_single_hole_column"]:
                hole_layout = "Single centered mounting column"
            else:
                hole_layout = "Single left-side mounting column"
        else:
            hole_layout = "Two mounting columns, four holes"
    elif spec["standard_key"] == STANDARD_INTELLIJEL_1U:
        hole_layout = "Intellijel 1U corner mounting holes"
    elif spec["standard_key"] == STANDARD_PULP_LOGIC_1U:
        hole_layout = "Pulp Logic 1U corner mounting holes"
    elif spec["standard_key"] == STANDARD_KOSMO:
        hole_layout = "Corner mounting holes"
    else:
        hole_layout = "Custom hole layout"

    return (
        f"Standard: {spec['standard_label']}\n"
        f"Size: {spec['width_display']}\n"
        f"Width: {format_mm(spec['width_mm'])}\n"
        f"Height: {format_mm(spec['height_mm'])}\n"
        f"Thickness: {format_mm(spec['thickness_mm'])}\n"
        f"Mounting style: {cutout_label(spec['cutout_type'])}\n"
        f"Layout: {hole_layout}\n"
        f"X positions: {format_positions(x_positions)}\n"
        f"Y positions: {format_positions(y_positions)}\n"
        f"Notes: {spec['conformance_note']}"
    )


class FaceplatePreviewWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.spec = build_panel_spec(STANDARD_DOEPFER, "circles")
        self.setMinimumHeight(320)
        self.setMinimumWidth(360)

    def setParameters(self, spec):
        self.spec = spec
        self.update()

    def sizeHint(self):
        return QtCore.QSize(420, 360)

    def _panel_rect(self, bounds):
        panel_width = self.spec["width_mm"]
        panel_height = self.spec["height_mm"]
        margin = 24.0

        available_width = max(1.0, bounds.width() - margin * 2.0)
        available_height = max(1.0, bounds.height() - margin * 2.0)

        scale = min(available_width / panel_width, available_height / panel_height)
        scaled_width = panel_width * scale
        scaled_height = panel_height * scale

        x = bounds.center().x() - scaled_width / 2.0
        y = bounds.center().y() - scaled_height / 2.0
        return QtCore.QRectF(x, y, scaled_width, scaled_height), scale

    def _draw_slot(self, painter, center_x, center_y, slot_width, slot_height):
        radius = slot_height / 2.0
        rect = QtCore.QRectF(
            center_x - slot_width / 2.0,
            center_y - slot_height / 2.0,
            slot_width,
            slot_height
        )
        painter.drawRoundedRect(rect, radius, radius)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setRenderHint(QtGui.QPainter.TextAntialiasing)

        bounds = QtCore.QRectF(self.rect()).adjusted(10, 10, -10, -10)
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(QtGui.QColor(16, 24, 30))
        painter.drawRoundedRect(bounds, 18, 18)

        outer = bounds.adjusted(8, 8, -8, -8)
        panel_rect, scale = self._panel_rect(outer)

        panel_shadow = panel_rect.translated(3, 5)
        painter.setBrush(QtGui.QColor(0, 0, 0, 70))
        painter.drawRoundedRect(panel_shadow, 10, 10)

        panel_gradient = QtGui.QLinearGradient(panel_rect.topLeft(), panel_rect.bottomRight())
        panel_gradient.setColorAt(0.0, QtGui.QColor(48, 62, 76))
        panel_gradient.setColorAt(1.0, QtGui.QColor(20, 33, 44))
        painter.setBrush(panel_gradient)
        painter.setPen(QtGui.QPen(QtGui.QColor(150, 170, 190, 180), 1.2))
        painter.drawRoundedRect(panel_rect, 10, 10)

        panel_width = self.spec["width_mm"]
        x_positions = generic_mounting_hole_x_positions(self.spec)
        y_positions = generic_mounting_hole_y_positions(self.spec)

        def map_x(value):
            return panel_rect.left() + ((value + panel_width / 2.0) / panel_width) * panel_rect.width()

        def map_y(value):
            return panel_rect.top() + ((value + self.spec["height_mm"] / 2.0) / self.spec["height_mm"]) * panel_rect.height()

        hole_pen = QtGui.QPen(QtGui.QColor(225, 234, 240, 200), max(1.2, scale * 0.16))
        hole_fill = QtGui.QBrush(QtGui.QColor(8, 10, 12, 220))
        highlight = QtGui.QBrush(QtGui.QColor(68, 220, 165, 95))

        painter.setBrush(hole_fill)
        painter.setPen(hole_pen)

        if self.spec["cutout_type"] == "circles":
            radius = (self.spec["hole_diameter_mm"] / 2.0) * scale
            for x in x_positions:
                for y in y_positions:
                    cx = map_x(x)
                    cy = map_y(y)
                    painter.drawEllipse(QtCore.QPointF(cx, cy), radius, radius)
                    painter.setBrush(highlight)
                    painter.drawEllipse(QtCore.QPointF(cx, cy), radius * 0.45, radius * 0.45)
                    painter.setBrush(hole_fill)
        else:
            slot_width = self.spec["slot_length_mm"] * scale
            slot_height = self.spec["slot_height_mm"] * scale
            for x in x_positions:
                for y in y_positions:
                    painter.setBrush(hole_fill)
                    self._draw_slot(painter, map_x(x), map_y(y), slot_width, slot_height)
                    painter.setBrush(highlight)
                    inner_width = max(slot_width * 0.5, slot_height * 0.8)
                    inner_height = max(slot_height * 0.35, 1.0)
                    self._draw_slot(painter, map_x(x), map_y(y), inner_width, inner_height)
                    painter.setBrush(hole_fill)

        title_font = QtGui.QFont()
        title_font.setPointSizeF(max(10.0, self.font().pointSizeF() + 1.0))
        title_font.setBold(True)
        painter.setFont(title_font)
        painter.setPen(QtGui.QPen(QtGui.QColor(242, 246, 250)))
        painter.drawText(
            outer.adjusted(14, 14, -14, -14),
            QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft,
            f"{self.spec['display_name']}"
        )

        meta_font = QtGui.QFont()
        meta_font.setPointSizeF(max(8.5, self.font().pointSizeF()))
        painter.setFont(meta_font)
        painter.setPen(QtGui.QPen(QtGui.QColor(180, 194, 205)))
        painter.drawText(
            outer.adjusted(14, 14, -14, -14),
            QtCore.Qt.AlignTop | QtCore.Qt.AlignRight,
            f"{panel_width:.2f} mm"
        )
        painter.drawText(
            outer.adjusted(14, 14, -14, -14),
            QtCore.Qt.AlignBottom | QtCore.Qt.AlignLeft,
            cutout_label(self.spec["cutout_type"])
        )
        painter.drawText(
            outer.adjusted(14, 14, -14, -14),
            QtCore.Qt.AlignBottom | QtCore.Qt.AlignRight,
            f"{self.spec['height_mm']:.2f} mm tall"
        )

        painter.end()


ACTIVE_FACEPLATE_TASK_PANEL = None


class FaceplateTaskPanel(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Create Eurorack Faceplate")
        self.setMinimumWidth(1080)
        self.setMinimumHeight(760)
        self.form = self

        self._build_ui()
        self._apply_style()
        self._apply_standard_defaults(STANDARD_DOEPFER)
        self.refresh_preset_list()
        self.refresh_summary()

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

        root.addWidget(hero)

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

        self.page_stack = QtWidgets.QStackedWidget()
        self._build_doepfer_page()
        self._build_intellijel_1u_page()
        self._build_pulplogic_1u_page()
        self._build_kosmo_page()
        self._build_custom_page()

        left_column.addWidget(standard_box)
        left_column.addWidget(presets_box)
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

        root.addLayout(content)

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

        self.doepfer_center_checkbox = QtWidgets.QCheckBox("Center single mounting column below 12 HP")
        self.doepfer_center_checkbox.setChecked(CENTER_SINGLE_HOLE_COLUMN)
        self.doepfer_center_checkbox.stateChanged.connect(self.refresh_summary)

        form.addRow("Width", self.doepfer_hp_spin)
        form.addRow("", self.doepfer_center_checkbox)

        layout.addLayout(form)

        helper = QtWidgets.QLabel(
            "Doepfer mode follows the Eurorack 3U panel conventions with HP-based width."
        )
        helper.setWordWrap(True)
        helper.setObjectName("helperText")
        layout.addWidget(helper)
        layout.addStretch(1)

        self.page_stack.addWidget(page)

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
            self.doepfer_center_checkbox.setChecked(CENTER_SINGLE_HOLE_COLUMN)
            self.standard_hint.setText(
                "Doepfer Eurorack mode uses HP units, a 128.5 mm panel height, and the familiar 5.08 mm grid."
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
            self.doepfer_center_checkbox.setChecked(
                bool(spec.get("doepfer_center_single_hole_column", CENTER_SINGLE_HOLE_COLUMN))
            )
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
                doepfer_center_single_hole_column=self.doepfer_center_checkbox.isChecked()
            )

        if standard_key == STANDARD_INTELLIJEL_1U:
            return build_panel_spec(
                standard_key,
                cutout_type,
                doepfer_hp=self.intellijel_1u_hp_spin.value()
            )

        if standard_key == STANDARD_PULP_LOGIC_1U:
            return build_panel_spec(
                standard_key,
                cutout_type,
                doepfer_hp=self.pulplogic_tiles_spin.value()
            )

        if standard_key == STANDARD_KOSMO:
            return build_panel_spec(
                standard_key,
                cutout_type,
                kosmo_units=self.kosmo_units_spin.value()
            )

        return build_panel_spec(
            standard_key,
            cutout_type,
            custom_width_mm=self.custom_width_spin.value(),
            custom_height_mm=self.custom_height_spin.value(),
            custom_thickness_mm=self.custom_thickness_spin.value(),
            custom_hole_diameter_mm=self.custom_hole_diameter_spin.value(),
            custom_hole_x_margin_mm=self.custom_x_margin_spin.value(),
            custom_hole_y_margin_mm=self.custom_y_margin_spin.value()
        )

    def selected_parameters(self):
        return self._current_spec()

    def refresh_summary(self, *args):
        spec = self._current_spec()
        self.summary_box.setPlainText(panel_layout_summary_from_spec(spec))
        self.preview.setParameters(spec)

    def getStandardButtons(self):
        return int(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)

    def accept(self):
        global ACTIVE_FACEPLATE_TASK_PANEL
        create_panel_from_spec(self._current_spec())
        if Gui is not None:
            try:
                Gui.Control.closeDialog()
            except Exception:
                pass
        ACTIVE_FACEPLATE_TASK_PANEL = None
        return True

    def reject(self):
        global ACTIVE_FACEPLATE_TASK_PANEL
        if Gui is not None:
            try:
                Gui.Control.closeDialog()
            except Exception:
                pass
        ACTIVE_FACEPLATE_TASK_PANEL = None
        return True


def create_panel_from_spec(spec):
    doc = App.ActiveDocument
    if doc is None:
        doc = App.newDocument("Eurorack_Panel")

    shape = make_panel_shape_from_spec(spec)
    body, source = create_body_from_spec(doc, shape, spec)

    doc.recompute()

    if Gui is not None:
        try:
            Gui.Selection.clearSelection()
            Gui.Selection.addSelection(body)
            Gui.ActiveDocument.ActiveView.fitAll()
        except Exception:
            pass

    App.Console.PrintMessage(
        "\nCreated Eurorack panel\n"
        f"Standard: {spec['standard_label']}\n"
        f"Size: {spec['width_display']}\n"
        f"Width: {spec['width_mm']:.2f} mm\n"
        f"Height: {spec['height_mm']:.2f} mm\n"
        f"Thickness: {spec['thickness_mm']:.2f} mm\n"
        f"Cutout type: {spec['cutout_type']}\n"
        f"Hole diameter: {spec['hole_diameter_mm']:.2f} mm\n"
        f"Slot size: {spec['slot_length_mm']:.2f} mm x {spec['slot_height_mm']:.2f} mm\n"
        f"X positions: {generic_mounting_hole_x_positions(spec)}\n"
        f"Y positions: {generic_mounting_hole_y_positions(spec)}\n\n"
    )

    return body


def create_eurorack_panel(hp, cutout_type, center_single_hole_column=CENTER_SINGLE_HOLE_COLUMN):
    spec = build_panel_spec(
        STANDARD_DOEPFER,
        cutout_type,
        doepfer_hp=hp,
        doepfer_center_single_hole_column=center_single_hole_column
    )
    return create_panel_from_spec(spec)


def create_single_eurorack_panel():
    global ACTIVE_FACEPLATE_TASK_PANEL

    if Gui is None:
        return create_panel_from_spec(build_panel_spec(STANDARD_DOEPFER, "circles"))

    ACTIVE_FACEPLATE_TASK_PANEL = FaceplateTaskPanel()

    try:
        Gui.Control.showDialog(ACTIVE_FACEPLATE_TASK_PANEL)
    except Exception:
        return create_panel_from_spec(build_panel_spec(STANDARD_DOEPFER, "circles"))

    return ACTIVE_FACEPLATE_TASK_PANEL
