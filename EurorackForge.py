import json
import os
import math
import re

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

DOEPFER_NARROW_UPPER_LEFT_LOWER_RIGHT = "upper_left_lower_right"
DOEPFER_NARROW_UPPER_RIGHT_LOWER_LEFT = "upper_right_lower_left"

DOEPFER_NARROW_DIAGONAL_OPTIONS = [
    (DOEPFER_NARROW_UPPER_LEFT_LOWER_RIGHT, "Upper-left / lower-right"),
    (DOEPFER_NARROW_UPPER_RIGHT_LOWER_LEFT, "Upper-right / lower-left"),
]

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


def format_point_positions(points):
    return "[" + ", ".join(f"({x:.2f}, {y:.2f})" for x, y in points) + "]"


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


def effective_slot_length_mm(width_mm, x_margin_mm, slot_height_mm=DEFAULT_SLOT_HEIGHT_MM, target_length_mm=DEFAULT_SLOT_LENGTH_MM):
    edge_distance = max(0.0, min(x_margin_mm, width_mm - x_margin_mm))
    available_length = 2.0 * edge_distance
    return min(target_length_mm, max(slot_height_mm, available_length))


def doepfer_narrow_layout_label(layout_key):
    for key, label in DOEPFER_NARROW_DIAGONAL_OPTIONS:
        if key == layout_key:
            return label

    return DOEPFER_NARROW_DIAGONAL_OPTIONS[0][1]


def build_panel_spec(
    standard_key,
    cutout_type,
    *,
    doepfer_hp=8,
    doepfer_center_single_hole_column=CENTER_SINGLE_HOLE_COLUMN,
    doepfer_narrow_diagonal_key=DOEPFER_NARROW_UPPER_LEFT_LOWER_RIGHT,
    doepfer_thickness_mm=PANEL_THICKNESS,
    kosmo_units=8,
    custom_width_mm=80.0,
    custom_height_mm=128.5,
    custom_thickness_mm=2.0,
    custom_hole_diameter_mm=3.2,
    custom_hole_x_margin_mm=7.5,
    custom_hole_y_margin_mm=3.0,
    custom_layout_key="corners",
    top_clearance_mm=10.0,
    bottom_clearance_mm=10.0,
):
    beta_suffix = "" if standard_key == STANDARD_DOEPFER else " [BETA]"

    if standard_key == STANDARD_DOEPFER:
        width_value = doepfer_hp
        width_mm = doepfer_width_mm(width_value)
        height_mm = PANEL_HEIGHT
        thickness_mm = doepfer_thickness_mm
        hole_diameter_mm = HOLE_DIAMETER
        hole_x_margin_mm = HOLE_X_FIRST
        hole_y_margin_mm = HOLE_Y_FROM_EDGE
        hole_layout_key = "doepfer"
        width_unit_label = "HP"
        width_display = f"{width_value} HP"
        display_name = f"Doepfer Eurorack {width_value} HP"
        conformance_note = (
            f"Doepfer-style 3U panel with 5.08 mm HP grid, 128.5 mm height, and {thickness_mm:.1f} mm thickness."
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
        display_name = f"Intellijel 1U {width_value} HP{beta_suffix}"
        conformance_note = (
            "BETA: Intellijel-style 1U panel with a 39.65 mm row height and 3 mm corner margins."
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
        display_name = f"Pulp Logic 1U {width_value} tile(s){beta_suffix}"
        conformance_note = (
            "BETA: Pulp Logic-style 1U tile with a 43.18 mm row height and 6 HP tile increments."
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
        display_name = f"Kosmo {width_mm:.0f} mm{beta_suffix}"
        conformance_note = (
            "BETA: Kosmo-style 20 cm panel with 2.5 cm width steps and 3 mm mounting margins."
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
        display_name = f"Custom panel{beta_suffix}"
        conformance_note = "BETA: Custom panel geometry."

    slot_length_mm = effective_slot_length_mm(width_mm, hole_x_margin_mm)

    return {
        "standard_key": standard_key,
        "standard_label": standard_label(standard_key) + beta_suffix,
        "cutout_type": cutout_type,
        "width_value": width_value,
        "width_unit_label": width_unit_label,
        "width_display": width_display,
        "width_mm": width_mm,
        "height_mm": height_mm,
        "thickness_mm": thickness_mm,
        "hole_diameter_mm": hole_diameter_mm,
        "slot_height_mm": DEFAULT_SLOT_HEIGHT_MM,
        "slot_length_mm": slot_length_mm,
        "hole_x_margin_mm": hole_x_margin_mm,
        "hole_y_margin_mm": hole_y_margin_mm,
        "hole_layout_key": hole_layout_key,
        "doepfer_center_single_hole_column": doepfer_center_single_hole_column,
        "doepfer_narrow_diagonal_key": doepfer_narrow_diagonal_key,
        "doepfer_four_holes_start_hp": FOUR_HOLES_START_HP,
        "top_clearance_mm": top_clearance_mm,
        "bottom_clearance_mm": bottom_clearance_mm,
        "display_name": display_name,
        "conformance_note": conformance_note,
    }


def eurorack_panel_width(hp):
    return hp * HP_MM - WIDTH_CLEARANCE


def ordered_unique(values):
    unique = []
    for value in values:
        if value not in unique:
            unique.append(value)
    return unique


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


def generic_mounting_points(spec):
    width = spec["width_mm"]
    height = spec["height_mm"]
    left_edge = -width / 2.0
    right_edge = width / 2.0
    bottom_edge = -height / 2.0
    top_edge = height / 2.0

    if spec["hole_layout_key"] == "doepfer":
        width_value = spec["width_value"]
        threshold = spec["doepfer_four_holes_start_hp"]
        x_left = left_edge + spec["hole_x_margin_mm"]
        x_right = left_edge + spec["hole_x_margin_mm"] + (width_value - 3) * HP_MM
        y_bottom = bottom_edge + spec["hole_y_margin_mm"]
        y_top = top_edge - spec["hole_y_margin_mm"]

        if width_value < threshold:
            if spec["doepfer_center_single_hole_column"]:
                points = [(0.0, y_bottom), (0.0, y_top)]
            else:
                if spec.get("doepfer_narrow_diagonal_key") == DOEPFER_NARROW_UPPER_RIGHT_LOWER_LEFT:
                    points = [(x_right, y_top), (x_left, y_bottom)]
                else:
                    points = [(x_left, y_top), (x_right, y_bottom)]
        else:
            points = [
                (x_left, y_bottom),
                (x_left, y_top),
                (x_right, y_bottom),
                (x_right, y_top),
            ]

        if spec["cutout_type"] == "slots":
            x_min = left_edge + spec["slot_length_mm"] / 2.0
            x_max = right_edge - spec["slot_length_mm"] / 2.0
            y_min = bottom_edge + spec["slot_height_mm"] / 2.0
            y_max = top_edge - spec["slot_height_mm"] / 2.0

            points = [
                (
                    min(max(x, x_min), x_max),
                    min(max(y, y_min), y_max)
                )
                for x, y in points
            ]

        return points

    x_margin = spec["hole_x_margin_mm"]
    y_margin = spec["hole_y_margin_mm"]

    if spec["cutout_type"] == "slots":
        x_margin = max(x_margin, spec["slot_length_mm"] / 2.0)
        y_margin = max(y_margin, spec["slot_height_mm"] / 2.0)

    left_x = left_edge + x_margin
    right_x = right_edge - x_margin
    bottom_y = bottom_edge + y_margin
    top_y = top_edge - y_margin

    points = [
        (left_x, bottom_y),
        (left_x, top_y),
        (right_x, bottom_y),
        (right_x, top_y),
    ]

    if spec["cutout_type"] == "slots":
        x_min = left_edge + spec["slot_length_mm"] / 2.0
        x_max = right_edge - spec["slot_length_mm"] / 2.0
        y_min = bottom_edge + spec["slot_height_mm"] / 2.0
        y_max = top_edge - spec["slot_height_mm"] / 2.0

        points = [
            (
                min(max(x, x_min), x_max),
                min(max(y, y_min), y_max)
            )
            for x, y in points
        ]

    return points


def generic_mounting_hole_x_positions(spec):
    return ordered_unique([x for x, _ in generic_mounting_points(spec)])


def generic_mounting_hole_y_positions(spec):
    return ordered_unique([y for _, y in generic_mounting_points(spec)])


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


def make_mounting_cutter(x, y, cutout_type, slot_length_mm=None):
    if cutout_type == "circles":
        return make_round_hole_cutter(x, y)

    if slot_length_mm is not None:
        return make_horizontal_slot_cutter_mm(x, y, SLOT_HEIGHT, slot_length_mm, PANEL_THICKNESS)

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


def make_panel_shape(
    width,
    hp,
    cutout_type,
    center_single_hole_column=CENTER_SINGLE_HOLE_COLUMN,
    narrow_diagonal_key=DOEPFER_NARROW_UPPER_LEFT_LOWER_RIGHT,
):
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

    if hp < FOUR_HOLES_START_HP:
        y_positions = mounting_hole_y_positions()
        if center_single_hole_column:
            points = [(0.0, y) for y in y_positions]
        else:
            left_x = -width / 2.0 + HOLE_X_FIRST
            right_x = width / 2.0 - HOLE_X_FIRST
            if narrow_diagonal_key == DOEPFER_NARROW_UPPER_RIGHT_LOWER_LEFT:
                points = [(right_x, y_positions[1]), (left_x, y_positions[0])]
            else:
                points = [(left_x, y_positions[1]), (right_x, y_positions[0])]
    else:
        x_positions = mounting_hole_x_positions(width, hp, center_single_hole_column)
        y_positions = mounting_hole_y_positions()
        points = [(x, y) for x in x_positions for y in y_positions]

    if cutout_type == "slots":
        slot_length = effective_slot_length_mm(width, HOLE_X_FIRST)
        x_min = -width / 2.0 + slot_length / 2.0
        x_max = width / 2.0 - slot_length / 2.0
        y_min = -PANEL_HEIGHT / 2.0 + SLOT_HEIGHT / 2.0
        y_max = PANEL_HEIGHT / 2.0 - SLOT_HEIGHT / 2.0

        points = [
            (
                min(max(x, x_min), x_max),
                min(max(y, y_min), y_max)
            )
            for x, y in points
        ]

    for x, y in points:
        cutter = make_mounting_cutter(x, y, cutout_type, slot_length if cutout_type == "slots" else None)
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

    for x, y in generic_mounting_points(spec):
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
        source.addProperty("App::PropertyString", "EurorackForgeSpecJSON", "EurorackForge", "Stored panel specification for export helpers.")
    except Exception:
        pass

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
        body.addProperty("App::PropertyString", "EurorackForgeSpecJSON", "EurorackForge", "Stored panel specification for export helpers.")
    except Exception:
        pass

    try:
        source.addProperty("App::PropertyString", "EurorackForgeSpecJSON", "EurorackForge", "Stored panel specification for export helpers.")
    except Exception:
        pass

    try:
        body.EurorackForgeSpecJSON = json.dumps(spec)
    except Exception:
        pass

    try:
        source.EurorackForgeSpecJSON = json.dumps(spec)
    except Exception:
        pass

    try:
        source.ViewObject.Visibility = False
    except Exception:
        pass

    return body, source


def create_reference_sketch(body, source, spec):
    if body is None or source is None:
        return None

    try:
        import Sketcher
    except Exception:
        return None

    doc = body.Document
    sketch_name = f"{spec['standard_key']}_{str(spec['width_value']).replace('.', '_')}_Reference"

    try:
        existing = doc.getObject(sketch_name)
        if existing is not None:
            try:
                body.removeObject(existing)
            except Exception:
                pass
            try:
                doc.removeObject(existing.Name)
            except Exception:
                pass
    except Exception:
        pass

    sketch = body.newObject("Sketcher::SketchObject", sketch_name)
    try:
        sketch.MapMode = "FlatFace"
        sketch.Support = (source, ["Face6"])
    except Exception:
        pass

    try:
        sketch.Placement = App.Placement(
            App.Vector(0, 0, spec["thickness_mm"]),
            App.Rotation()
        )
    except Exception:
        pass

    try:
        sketch.addExternal(source, "Face6")
    except Exception:
        pass

    half_width = spec["width_mm"] / 2.0
    top_y = spec["height_mm"] / 2.0 - spec["top_clearance_mm"]
    bottom_y = -spec["height_mm"] / 2.0 + spec["bottom_clearance_mm"]

    top_line = Part.LineSegment(
        App.Vector(-half_width, top_y, 0),
        App.Vector(half_width, top_y, 0)
    )
    bottom_line = Part.LineSegment(
        App.Vector(-half_width, bottom_y, 0),
        App.Vector(half_width, bottom_y, 0)
    )

    top_id = sketch.addGeometry(top_line, True)
    bottom_id = sketch.addGeometry(bottom_line, True)

    # Keep the sketch flexible for later manual constraints. The geometry is already
    # positioned from the panel reference, so adding extra dimensions here can easily
    # over-constrain the sketch in FreeCAD.

    try:
        sketch.recompute()
    except Exception:
        pass

    return sketch


def panel_layout_summary(
    hp,
    cutout_type,
    center_single_hole_column=CENTER_SINGLE_HOLE_COLUMN,
    narrow_diagonal_key=DOEPFER_NARROW_UPPER_LEFT_LOWER_RIGHT,
):
    width = eurorack_panel_width(hp)
    y_positions = mounting_hole_y_positions()

    if hp < FOUR_HOLES_START_HP:
        if center_single_hole_column:
            hole_layout = "Single centered mounting column"
        else:
            hole_layout = doepfer_narrow_layout_label(narrow_diagonal_key)
    else:
        hole_layout = "Two mounting columns, four holes"

    if hp < FOUR_HOLES_START_HP and center_single_hole_column:
        points = [(0.0, y) for y in y_positions]
    elif hp < FOUR_HOLES_START_HP:
        left_x = -width / 2.0 + HOLE_X_FIRST
        right_x = width / 2.0 - HOLE_X_FIRST
        if narrow_diagonal_key == DOEPFER_NARROW_UPPER_RIGHT_LOWER_LEFT:
            points = [(right_x, y_positions[1]), (left_x, y_positions[0])]
        else:
            points = [(left_x, y_positions[1]), (right_x, y_positions[0])]
    else:
        x_positions = mounting_hole_x_positions(width, hp, center_single_hole_column)
        points = [(x, y) for x in x_positions for y in y_positions]

    return (
        f"Width: {hp_to_width_text(hp)}\n"
        f"Height: {PANEL_HEIGHT:.2f} mm\n"
        f"Thickness: {PANEL_THICKNESS:.2f} mm\n"
        f"Mounting style: {cutout_label(cutout_type)}\n"
        f"Layout: {hole_layout}\n"
        f"Mounting points: {format_point_positions(points)}\n"
        "Output: centered PartDesign Body with hidden base shape"
    )


def panel_layout_summary_from_spec(spec):
    points = generic_mounting_points(spec)
    x_positions = ordered_unique([x for x, _ in points])
    y_positions = ordered_unique([y for _, y in points])

    if spec["standard_key"] == STANDARD_DOEPFER:
        if spec["width_value"] < spec["doepfer_four_holes_start_hp"]:
            if spec["doepfer_center_single_hole_column"]:
                hole_layout = "Single centered mounting column"
            else:
                hole_layout = doepfer_narrow_layout_label(
                    spec.get("doepfer_narrow_diagonal_key", DOEPFER_NARROW_UPPER_LEFT_LOWER_RIGHT)
                )
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
        f"Top keep-out: {format_mm(spec['top_clearance_mm'])}\n"
        f"Bottom keep-out: {format_mm(spec['bottom_clearance_mm'])}\n"
        f"Mounting points: {format_point_positions(points)}\n"
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
        points = generic_mounting_points(self.spec)

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
            for x, y in points:
                cx = map_x(x)
                cy = map_y(y)
                painter.drawEllipse(QtCore.QPointF(cx, cy), radius, radius)
                painter.setBrush(highlight)
                painter.drawEllipse(QtCore.QPointF(cx, cy), radius * 0.45, radius * 0.45)
                painter.setBrush(hole_fill)
        else:
            slot_width = self.spec["slot_length_mm"] * scale
            slot_height = self.spec["slot_height_mm"] * scale
            for x, y in points:
                painter.setBrush(hole_fill)
                self._draw_slot(painter, map_x(x), map_y(y), slot_width, slot_height)
                painter.setBrush(highlight)
                inner_width = max(slot_width * 0.5, slot_height * 0.8)
                inner_height = max(slot_height * 0.35, 1.0)
                self._draw_slot(painter, map_x(x), map_y(y), inner_width, inner_height)
                painter.setBrush(hole_fill)

        top_keepout_y = map_y(self.spec["height_mm"] / 2.0 - self.spec["top_clearance_mm"])
        bottom_keepout_y = map_y(-self.spec["height_mm"] / 2.0 + self.spec["bottom_clearance_mm"])
        keepout_pen = QtGui.QPen(QtGui.QColor(255, 196, 112, 190), max(1.2, scale * 0.14), QtCore.Qt.DashLine)
        keepout_pen.setDashPattern([6.0, 5.0])
        painter.setPen(keepout_pen)
        painter.setBrush(QtCore.Qt.NoBrush)
        painter.drawLine(QtCore.QLineF(panel_rect.left(), top_keepout_y, panel_rect.right(), top_keepout_y))
        painter.drawLine(QtCore.QLineF(panel_rect.left(), bottom_keepout_y, panel_rect.right(), bottom_keepout_y))

        callout_font = QtGui.QFont()
        callout_font.setPointSizeF(max(8.0, self.font().pointSizeF()))
        painter.setFont(callout_font)
        painter.setPen(QtGui.QPen(QtGui.QColor(255, 214, 153)))
        painter.drawText(
            QtCore.QRectF(panel_rect.left() + 8, top_keepout_y - 18, panel_rect.width() - 16, 14),
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter,
            f"Top keep-out {self.spec['top_clearance_mm']:.0f} mm"
        )
        painter.drawText(
            QtCore.QRectF(panel_rect.left() + 8, bottom_keepout_y + 4, panel_rect.width() - 16, 14),
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter,
            f"Bottom keep-out {self.spec['bottom_clearance_mm']:.0f} mm"
        )

        label_margin = 10.0
        top_label_y = max(outer.top(), panel_rect.top() - 26.0)
        bottom_label_y = min(outer.bottom() - 20.0, panel_rect.bottom() + 6.0)

        title_font = QtGui.QFont()
        title_font.setPointSizeF(max(10.0, self.font().pointSizeF() + 1.0))
        title_font.setBold(True)
        painter.setFont(title_font)
        painter.setPen(QtGui.QPen(QtGui.QColor(242, 246, 250)))
        painter.drawText(
            QtCore.QRectF(panel_rect.left() + label_margin, top_label_y, panel_rect.width() * 0.58, 20.0),
            QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter,
            f"{self.spec['display_name']}"
        )

        meta_font = QtGui.QFont()
        meta_font.setPointSizeF(max(8.5, self.font().pointSizeF()))
        painter.setFont(meta_font)
        painter.setPen(QtGui.QPen(QtGui.QColor(180, 194, 205)))
        painter.drawText(
            QtCore.QRectF(panel_rect.left() + panel_rect.width() * 0.58, top_label_y, panel_rect.width() * 0.38, 20.0),
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter,
            f"{panel_width:.2f} mm"
        )
        painter.drawText(
            QtCore.QRectF(panel_rect.left() + label_margin, bottom_label_y, panel_rect.width() * 0.58, 20.0),
            QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter,
            cutout_label(self.spec["cutout_type"])
        )
        painter.drawText(
            QtCore.QRectF(panel_rect.left() + panel_rect.width() * 0.58, bottom_label_y, panel_rect.width() * 0.38, 20.0),
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter,
            f"{self.spec['height_mm']:.2f} mm tall"
        )

        painter.end()


ACTIVE_FACEPLATE_TASK_PANEL = None
ACTIVE_EXPORT_TASK_PANEL = None


class FaceplateTaskPanel(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Create Eurorack Faceplate")
        self.setMinimumWidth(1080)
        self.setMinimumHeight(760)
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

    def _build_ui(self):
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(14)

        self.tabs = QtWidgets.QTabWidget()
        root.addWidget(self.tabs, 1)

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
        panel_root.addWidget(self.button_box)

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
        self.preview.setParameters(spec)

    def getStandardButtons(self):
        return int(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)

    def accept(self):
        global ACTIVE_FACEPLATE_TASK_PANEL
        panel_spec = self._current_spec()
        self.created_spec = panel_spec
        self.created_body = create_panel_from_spec(panel_spec)
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


def create_panel_from_spec(spec):
    doc = App.ActiveDocument
    if doc is None:
        doc = App.newDocument("Eurorack_Panel")

    shape = make_panel_shape_from_spec(spec)
    body, source = create_body_from_spec(doc, shape, spec)

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
        f"Top keep-out: {spec['top_clearance_mm']:.2f} mm\n"
        f"Bottom keep-out: {spec['bottom_clearance_mm']:.2f} mm\n"
        f"Mounting points: {generic_mounting_points(spec)}\n\n"
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
    return create_panel_from_spec(spec)


def create_single_eurorack_panel():
    global ACTIVE_FACEPLATE_TASK_PANEL

    if Gui is None:
        return create_panel_from_spec(build_panel_spec(STANDARD_DOEPFER, "circles"))

    if ACTIVE_FACEPLATE_TASK_PANEL is None:
        ACTIVE_FACEPLATE_TASK_PANEL = FaceplateTaskPanel()

    try:
        ACTIVE_FACEPLATE_TASK_PANEL.show()
        ACTIVE_FACEPLATE_TASK_PANEL.raise_()
        ACTIVE_FACEPLATE_TASK_PANEL.activateWindow()
    except Exception:
        return create_panel_from_spec(build_panel_spec(STANDARD_DOEPFER, "circles"))

    return ACTIVE_FACEPLATE_TASK_PANEL


def _sanitize_file_stem(text):
    cleaned = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in text.strip())
    cleaned = cleaned.strip("_")
    return cleaned or "EurorackPanel"


def export_selected_object_to_stl(obj=None, filename=None, deflection=0.1):
    if Gui is None:
        return False, "GUI is required for STL export."

    if obj is None:
        selection = Gui.Selection.getSelection()
        if not selection:
            return False, "Select a panel body in the model tree first."
        obj = selection[0]

    shape = getattr(obj, "Shape", None)
    if shape is None or getattr(shape, "isNull", lambda: True)():
        return False, "The selected object does not have a valid shape to export."

    if filename is None:
        try:
            from PySide6 import QtWidgets
        except ImportError:
            try:
                from PySide2 import QtWidgets
            except ImportError:
                from PySide import QtWidgets

        doc = App.ActiveDocument
        default_dir = ""
        if doc is not None and getattr(doc, "FileName", ""):
            default_dir = os.path.dirname(doc.FileName)
        if not default_dir:
            default_dir = os.path.expanduser("~")

        suggested = _sanitize_file_stem(getattr(obj, "Label", getattr(obj, "Name", "EurorackPanel"))) + ".stl"
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(
            None,
            "Export Selected Panel as STL",
            os.path.join(default_dir, suggested),
            "STL Files (*.stl)",
        )
        if not filename:
            return False, "Export cancelled."
        if not filename.lower().endswith(".stl"):
            filename += ".stl"

    try:
        try:
            obj.Document.recompute()
        except Exception:
            pass
        shape.exportStl(filename, float(deflection))
    except Exception as exc:
        return False, f"STL export failed: {exc}"

    return True, filename


def _default_export_filename(obj, extension):
    label = getattr(obj, "Label", getattr(obj, "Name", "EurorackPanel"))
    return _sanitize_file_stem(label) + extension


def _kicad_num(value):
    text = f"{float(value):.6f}".rstrip("0").rstrip(".")
    if text in ("-0", "-0.0", ""):
        return "0"
    return text


def _kicad_point_text(point):
    return f"{_kicad_num(point.x)} {_kicad_num(point.y)}"


def _same_xy(a, b, tolerance=1e-6):
    return abs(a.x - b.x) <= tolerance and abs(a.y - b.y) <= tolerance


def _top_planar_face(shape):
    faces = list(getattr(shape, "Faces", []) or [])
    if not faces:
        return None

    candidates = []
    for face in faces:
        try:
            center = face.CenterOfMass
            normal = face.normalAt(0.5, 0.5)
            if abs(abs(normal.z) - 1.0) <= 1e-3:
                candidates.append((center.z, face))
        except Exception:
            continue

    if candidates:
        return max(candidates, key=lambda item: item[0])[1]

    try:
        return max(faces, key=lambda face: face.CenterOfMass.z)
    except Exception:
        return faces[0]


def _edge_points_for_kicad(edge, segments_per_curve=32):
    curve = getattr(edge, "Curve", None)
    type_id = getattr(curve, "TypeId", "")
    try:
        if "Line" in type_id:
            vertices = list(getattr(edge, "Vertexes", []) or [])
            if len(vertices) >= 2:
                return [vertices[0].Point, vertices[-1].Point]
    except Exception:
        pass

    count = max(8, int(segments_per_curve))
    try:
        points = edge.discretize(Number=count)
    except Exception:
        vertices = list(getattr(edge, "Vertexes", []) or [])
        points = [vertex.Point for vertex in vertices]

    return list(points or [])


def _wire_to_kicad_segments(wire, segments_per_curve=32):
    points = []
    for edge in getattr(wire, "Edges", []) or []:
        edge_points = _edge_points_for_kicad(edge, segments_per_curve)
        if not edge_points:
            continue

        if points and _same_xy(points[-1], edge_points[0]):
            edge_points = edge_points[1:]

        for point in edge_points:
            if not points or not _same_xy(points[-1], point):
                points.append(point)

    if len(points) > 1 and not _same_xy(points[0], points[-1]):
        points.append(points[0])

    segments = []
    for start, end in zip(points, points[1:]):
        if not _same_xy(start, end):
            segments.append((start, end))

    return segments


def _shape_to_kicad_edgecuts(shape, segments_per_curve=32):
    face = _top_planar_face(shape)
    if face is None:
        return []

    segments = []
    for wire in getattr(face, "Wires", []) or []:
        try:
            points = list(wire.discretize(Number=max(8, int(segments_per_curve))))
        except Exception:
            points = []

        if len(points) < 2:
            points = []
            for edge in getattr(wire, "Edges", []) or []:
                points.extend(_edge_points_for_kicad(edge, segments_per_curve))

        if len(points) < 2:
            continue

        ordered = []
        for point in points:
            if not ordered or not _same_xy(ordered[-1], point):
                ordered.append(point)

        if len(ordered) > 1 and not _same_xy(ordered[0], ordered[-1]):
            ordered.append(ordered[0])

        for start, end in zip(ordered, ordered[1:]):
            if not _same_xy(start, end):
                segments.append((start, end))

    return segments


def _kicad_pcb_text_from_edgecuts(edgecuts, thickness_mm=1.6):
    lines = [
        '(kicad_pcb (version 20211014) (generator "EurorackForge")',
        f'  (general (thickness {_kicad_num(thickness_mm)}))',
        '  (paper "A4")',
        '  (layers',
        '    (0 "F.Cu" signal)',
        '    (31 "B.Cu" signal)',
        '    (44 "Edge.Cuts" user)',
        '  )',
    ]

    for start, end in edgecuts:
        lines.append(
            f'  (gr_line (start {_kicad_point_text(start)}) (end {_kicad_point_text(end)}) '
            '(layer "Edge.Cuts") (width 0.1))'
        )

    lines.append(')')
    return "\n".join(lines) + "\n"


def _kicad_pcb_text(shape, segments_per_curve=32, thickness_mm=1.6):
    edgecuts = _shape_to_kicad_edgecuts(shape, segments_per_curve)
    return _kicad_pcb_text_from_edgecuts(edgecuts, thickness_mm=thickness_mm)


def _export_spec_from_obj(obj):
    if obj is None:
        return None

    spec_text = getattr(obj, "EurorackForgeSpecJSON", "")
    if spec_text:
        try:
            spec = json.loads(spec_text)
            if isinstance(spec, dict):
                return spec
        except Exception:
            pass

    base = getattr(obj, "BaseFeature", None)
    if base is not None:
        spec_text = getattr(base, "EurorackForgeSpecJSON", "")
        if spec_text:
            try:
                spec = json.loads(spec_text)
                if isinstance(spec, dict):
                    return spec
            except Exception:
                pass

    def parse_label(label):
        if not label:
            return None

        patterns = [
            (STANDARD_DOEPFER, r"^Doepfer Eurorack (\d+) HP - ([0-9.]+)mm - (circles|slots)$"),
            (STANDARD_INTELLIJEL_1U, r"^Intellijel 1U (\d+) HP(?: \[BETA\])? - ([0-9.]+)mm - (circles|slots)$"),
            (STANDARD_PULP_LOGIC_1U, r"^Pulp Logic 1U (\d+) tile\(s\)(?: \[BETA\])? - ([0-9.]+)mm - (circles|slots)$"),
            (STANDARD_KOSMO, r"^Kosmo ([0-9.]+) mm(?: \[BETA\])? - ([0-9.]+)mm - (circles|slots)$"),
            (STANDARD_CUSTOM, r"^Custom panel(?: \[BETA\])? - ([0-9.]+)mm - (circles|slots)$"),
        ]

        for standard_key, pattern in patterns:
            match = re.match(pattern, label)
            if not match:
                continue

            groups = match.groups()
            cutout_type = groups[-1]
            if standard_key == STANDARD_DOEPFER:
                hp = int(groups[0])
                thickness_mm = float(groups[1])
                return build_panel_spec(
                    STANDARD_DOEPFER,
                    cutout_type,
                    doepfer_hp=hp,
                    doepfer_thickness_mm=thickness_mm,
                )

            if standard_key == STANDARD_INTELLIJEL_1U:
                hp = int(groups[0])
                thickness_mm = float(groups[1])
                return build_panel_spec(
                    STANDARD_INTELLIJEL_1U,
                    cutout_type,
                    doepfer_hp=hp,
                    custom_thickness_mm=thickness_mm,
                )

            if standard_key == STANDARD_PULP_LOGIC_1U:
                tiles = int(groups[0])
                thickness_mm = float(groups[1])
                return build_panel_spec(
                    STANDARD_PULP_LOGIC_1U,
                    cutout_type,
                    doepfer_hp=tiles,
                    custom_thickness_mm=thickness_mm,
                )

            if standard_key == STANDARD_KOSMO:
                width_mm = float(groups[0])
                thickness_mm = float(groups[1])
                units = max(1, int(round(width_mm / KOSMO_UNIT_MM)))
                return build_panel_spec(
                    STANDARD_KOSMO,
                    cutout_type,
                    kosmo_units=units,
                    custom_thickness_mm=thickness_mm,
                )

            if standard_key == STANDARD_CUSTOM:
                thickness_mm = float(groups[0])
                return build_panel_spec(
                    STANDARD_CUSTOM,
                    cutout_type,
                    custom_width_mm=float(getattr(obj.Shape.BoundBox, "XLength", 80.0)) if getattr(obj, "Shape", None) is not None else 80.0,
                    custom_height_mm=float(getattr(obj.Shape.BoundBox, "YLength", 128.5)) if getattr(obj, "Shape", None) is not None else 128.5,
                    custom_thickness_mm=thickness_mm,
                )

        return None

    label_spec = parse_label(getattr(obj, "Label", ""))
    if label_spec is not None:
        return label_spec

    label_spec = parse_label(getattr(base, "Label", "") if base is not None else "")
    if label_spec is not None:
        return label_spec

    return None


def _circle_loop(cx, cy, radius, segments):
    steps = max(8, int(segments))
    points = []
    for index in range(steps):
        angle = (2.0 * 3.141592653589793 * index) / steps
        points.append(App.Vector(cx + radius * math.cos(angle), cy + radius * math.sin(angle), 0))
    points.append(points[0])
    return points


def _capsule_loop(cx, cy, length, height, segments):
    radius = height / 2.0
    straight = max(0.0, length - height)
    arc_segments = max(4, int(segments) // 2)
    left_center_x = cx - straight / 2.0
    right_center_x = cx + straight / 2.0

    def arc_points(center_x, start_angle, end_angle):
        segment_count = max(2, arc_segments)
        values = []
        for index in range(segment_count + 1):
            t = index / float(segment_count)
            angle = start_angle + (end_angle - start_angle) * t
            values.append(App.Vector(center_x + radius * math.cos(angle), cy + radius * math.sin(angle), 0))
        return values

    left_top = App.Vector(left_center_x, cy + radius, 0)
    right_top = App.Vector(right_center_x, cy + radius, 0)
    right_bottom = App.Vector(right_center_x, cy - radius, 0)
    left_bottom = App.Vector(left_center_x, cy - radius, 0)

    points = [left_top]
    points.append(right_top)
    points.extend(arc_points(right_center_x, math.pi / 2.0, -math.pi / 2.0)[1:])
    points.append(left_bottom)
    points.extend(arc_points(left_center_x, -math.pi / 2.0, math.pi / 2.0)[1:])

    points.append(points[0])
    return points


def _loops_from_spec(spec, segments_per_curve=32):
    if not isinstance(spec, dict):
        return []

    loops = []
    width = float(spec["width_mm"])
    height = float(spec["height_mm"])
    half_width = width / 2.0
    half_height = height / 2.0

    outer = [
        App.Vector(-half_width, -half_height, 0),
        App.Vector(half_width, -half_height, 0),
        App.Vector(half_width, half_height, 0),
        App.Vector(-half_width, half_height, 0),
        App.Vector(-half_width, -half_height, 0),
    ]
    loops.append(outer)

    if spec["cutout_type"] == "circles":
        radius = float(spec["hole_diameter_mm"]) / 2.0
        for x, y in generic_mounting_points(spec):
            loops.append(_circle_loop(x, y, radius, segments_per_curve))
    else:
        slot_length = float(spec["slot_length_mm"])
        slot_height = float(spec["slot_height_mm"])
        for x, y in generic_mounting_points(spec):
            loops.append(_capsule_loop(x, y, slot_length, slot_height, segments_per_curve))

    return loops


def _loops_to_edgecuts_lines(loops):
    lines = []
    for loop in loops:
        if len(loop) < 2:
            continue
        for start, end in zip(loop, loop[1:]):
            if _same_xy(start, end):
                continue
            lines.append((start, end))
    return lines


def _kicad_pcb_text_from_spec(spec, segments_per_curve=32, thickness_mm=1.6):
    loops = _loops_from_spec(spec, segments_per_curve)
    edgecuts = _loops_to_edgecuts_lines(loops)
    lines = [
        '(kicad_pcb (version 20211014) (generator "EurorackForge")',
        f'  (general (thickness {_kicad_num(thickness_mm)}))',
        '  (paper "A4")',
        '  (layers',
        '    (0 "F.Cu" signal)',
        '    (31 "B.Cu" signal)',
        '    (44 "Edge.Cuts" user)',
        '  )',
    ]

    for start, end in edgecuts:
        lines.append(
            f'  (gr_line (start {_kicad_point_text(start)}) (end {_kicad_point_text(end)}) '
            '(layer "Edge.Cuts") (width 0.1))'
        )

    lines.append(')')
    return "\n".join(lines) + "\n"


def _kicad_edge_svg_text_from_spec(spec, segments_per_curve=32):
    loops = _loops_from_spec(spec, segments_per_curve)
    edgecuts = _loops_to_edgecuts_lines(loops)
    if not edgecuts:
        return None

    all_points = [point for segment in edgecuts for point in segment]
    min_x = min(point.x for point in all_points)
    max_x = max(point.x for point in all_points)
    min_y = min(point.y for point in all_points)
    max_y = max(point.y for point in all_points)
    width = max(1.0, max_x - min_x)
    height = max(1.0, max_y - min_y)
    pad = max(width, height) * 0.05

    def svg_x(value):
        return value - min_x + pad

    def svg_y(value):
        return (max_y - value) + pad

    svg_width = width + pad * 2.0
    svg_height = height + pad * 2.0

    lines = [
        '<?xml version="1.0" encoding="UTF-8" standalone="no"?>',
        '<svg xmlns="http://www.w3.org/2000/svg" version="1.1"',
        f'     width="{_kicad_num(svg_width)}mm" height="{_kicad_num(svg_height)}mm"',
        f'     viewBox="0 0 {_kicad_num(svg_width)} {_kicad_num(svg_height)}">',
        '  <g fill="none" stroke="#000000" stroke-width="0.1" stroke-linecap="round" stroke-linejoin="round">',
    ]

    for start, end in edgecuts:
        lines.append(
            f'    <line x1="{_kicad_num(svg_x(start.x))}" y1="{_kicad_num(svg_y(start.y))}" '
            f'x2="{_kicad_num(svg_x(end.x))}" y2="{_kicad_num(svg_y(end.y))}" />'
        )

    lines.extend([
        '  </g>',
        '</svg>',
    ])
    return "\n".join(lines) + "\n"


def _kicad_edge_svg_text_from_edgecuts(edgecuts):
    if not edgecuts:
        return None

    all_points = [point for segment in edgecuts for point in segment]
    min_x = min(point.x for point in all_points)
    max_x = max(point.x for point in all_points)
    min_y = min(point.y for point in all_points)
    max_y = max(point.y for point in all_points)
    width = max(1.0, max_x - min_x)
    height = max(1.0, max_y - min_y)
    pad = max(width, height) * 0.05

    def svg_x(value):
        return value - min_x + pad

    def svg_y(value):
        return (max_y - value) + pad

    svg_width = width + pad * 2.0
    svg_height = height + pad * 2.0

    lines = [
        '<?xml version="1.0" encoding="UTF-8" standalone="no"?>',
        '<svg xmlns="http://www.w3.org/2000/svg" version="1.1"',
        f'     width="{_kicad_num(svg_width)}mm" height="{_kicad_num(svg_height)}mm"',
        f'     viewBox="0 0 {_kicad_num(svg_width)} {_kicad_num(svg_height)}">',
        '  <g fill="none" stroke="#000000" stroke-width="0.1" stroke-linecap="round" stroke-linejoin="round">',
    ]

    for start, end in edgecuts:
        lines.append(
            f'    <line x1="{_kicad_num(svg_x(start.x))}" y1="{_kicad_num(svg_y(start.y))}" '
            f'x2="{_kicad_num(svg_x(end.x))}" y2="{_kicad_num(svg_y(end.y))}" />'
        )

    lines.extend([
        '  </g>',
        '</svg>',
    ])
    return "\n".join(lines) + "\n"


def _kicad_edge_svg_text(shape, segments_per_curve=32):
    edgecuts = _shape_to_kicad_edgecuts(shape, segments_per_curve)
    return _kicad_edge_svg_text_from_edgecuts(edgecuts)


def _kicad_edgecuts_from_obj(obj, segments_per_curve=32):
    if obj is None:
        return []

    shape = getattr(obj, "Shape", None)
    if shape is not None and not getattr(shape, "isNull", lambda: True)():
        edgecuts = _shape_to_kicad_edgecuts(shape, segments_per_curve)
        if edgecuts:
            return edgecuts

    base = getattr(obj, "BaseFeature", None)
    if base is not None:
        base_shape = getattr(base, "Shape", None)
        if base_shape is not None and not getattr(base_shape, "isNull", lambda: True)():
            edgecuts = _shape_to_kicad_edgecuts(base_shape, segments_per_curve)
            if edgecuts:
                return edgecuts

    spec = _export_spec_from_obj(obj)
    if spec is not None:
        loops = _loops_from_spec(spec, segments_per_curve)
        return _loops_to_edgecuts_lines(loops)

    return []


def _selected_export_target():
    if Gui is None:
        return None

    try:
        selection = Gui.Selection.getSelection()
    except Exception:
        selection = []

    if not selection:
        return None

    obj = selection[0]
    shape = getattr(obj, "Shape", None)
    if shape is not None and not getattr(shape, "isNull", lambda: True)():
        return obj

    base = getattr(obj, "BaseFeature", None)
    if base is not None:
        base_shape = getattr(base, "Shape", None)
        if base_shape is not None and not getattr(base_shape, "isNull", lambda: True)():
            return base

    return None


def export_selected_object_to_svg(obj=None, filename=None):
    if Gui is None:
        return False, "GUI is required for SVG export."

    if obj is None:
        obj = _selected_export_target()
        if obj is None:
            return False, "Select a panel body in the model tree first."

    shape = getattr(obj, "Shape", None)
    if shape is None or getattr(shape, "isNull", lambda: True)():
        return False, "The selected object does not have a valid shape to export."

    if filename is None:
        try:
            from PySide6 import QtWidgets
        except ImportError:
            try:
                from PySide2 import QtWidgets
            except ImportError:
                from PySide import QtWidgets

        doc = App.ActiveDocument
        default_dir = ""
        if doc is not None and getattr(doc, "FileName", ""):
            default_dir = os.path.dirname(doc.FileName)
        if not default_dir:
            default_dir = os.path.expanduser("~")

        suggested = _default_export_filename(obj, ".svg")
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(
            None,
            "Export Selected Panel as SVG",
            os.path.join(default_dir, suggested),
            "SVG Files (*.svg)",
        )
        if not filename:
            return False, "Export cancelled."
        if not filename.lower().endswith(".svg"):
            filename += ".svg"

    doc = obj.Document
    temp_name = _sanitize_file_stem(getattr(obj, "Name", "EurorackPanel")) + "_SVG"
    temp_obj = None
    try:
        temp_obj = doc.addObject("Part::Feature", temp_name)
        temp_obj.Shape = shape.copy() if hasattr(shape, "copy") else shape
        try:
            doc.recompute()
        except Exception:
            pass

        try:
            import importSVG
        except Exception:
            importSVG = None

        if importSVG is not None:
            try:
                importSVG.export([temp_obj], filename)
            except Exception:
                try:
                    Gui.export([temp_obj], filename)
                except Exception:
                    if Gui.ActiveDocument is not None:
                        Gui.ActiveDocument.ActiveView.saveVectorGraphic(filename)
        else:
            try:
                Gui.export([temp_obj], filename)
            except Exception:
                if Gui.ActiveDocument is not None:
                    Gui.ActiveDocument.ActiveView.saveVectorGraphic(filename)
    except Exception as exc:
        return False, f"SVG export failed: {exc}"
    finally:
        try:
            if temp_obj is not None:
                doc.removeObject(temp_obj.Name)
                try:
                    doc.recompute()
                except Exception:
                    pass
        except Exception:
            pass

    return True, filename


def export_selected_object_to_png(
    obj=None,
    filename=None,
    width=2048,
    height=2048,
    fit=True,
    background_color=(1.0, 1.0, 1.0),
    panel_color=(0.85, 0.87, 0.90),
):
    if Gui is None:
        return False, "GUI is required for PNG export."

    if obj is None:
        obj = _selected_export_target()
        if obj is None:
            return False, "Select a panel body in the model tree first."

    if filename is None:
        try:
            from PySide6 import QtWidgets
        except ImportError:
            try:
                from PySide2 import QtWidgets
            except ImportError:
                from PySide import QtWidgets

        doc = App.ActiveDocument
        default_dir = ""
        if doc is not None and getattr(doc, "FileName", ""):
            default_dir = os.path.dirname(doc.FileName)
        if not default_dir:
            default_dir = os.path.expanduser("~")

        suggested = _default_export_filename(obj, ".png")
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(
            None,
            "Export Selected Panel as PNG",
            os.path.join(default_dir, suggested),
            "PNG Files (*.png)",
        )
        if not filename:
            return False, "Export cancelled."
        if not filename.lower().endswith(".png"):
            filename += ".png"

    if Gui.ActiveDocument is None:
        return False, "No active 3D view is available for PNG export."

    view = Gui.ActiveDocument.ActiveView
    selection_snapshot = []
    try:
        selection_snapshot = list(Gui.Selection.getSelection())
    except Exception:
        selection_snapshot = []

    view_object = getattr(obj, "ViewObject", None)
    original_shape_color = None
    original_diffuse_color = None
    if view_object is not None:
        try:
            original_shape_color = view_object.ShapeColor
        except Exception:
            original_shape_color = None
        try:
            original_diffuse_color = view_object.DiffuseColor
        except Exception:
            original_diffuse_color = None

    try:
        if fit:
            try:
                view.fitAll()
            except Exception:
                pass

        try:
            Gui.Selection.clearSelection()
        except Exception:
            pass

        if view_object is not None:
            try:
                if isinstance(panel_color, QtGui.QColor):
                    rgb = (panel_color.redF(), panel_color.greenF(), panel_color.blueF())
                else:
                    rgb = tuple(panel_color)
                view_object.ShapeColor = rgb
                if original_diffuse_color is not None:
                    if isinstance(original_diffuse_color, (list, tuple)) and original_diffuse_color:
                        view_object.DiffuseColor = [rgb for _ in original_diffuse_color]
            except Exception:
                pass

        try:
            import OfflineRenderingUtils
            scene = view.getSceneGraph()
            camera = view.getCameraNode()
            OfflineRenderingUtils.render(
                filename,
                scene=scene,
                camera=camera,
                zoom=fit,
                width=int(width),
                height=int(height),
                background=background_color,
            )
        except Exception:
            try:
                bg = QtGui.QColor.fromRgbF(*background_color) if not isinstance(background_color, QtGui.QColor) else background_color
                view.saveImage(filename, int(width), int(height), bg)
            except Exception:
                try:
                    view.saveImage(filename, int(width), int(height), QtGui.QColor("white"))
                except Exception:
                    view.saveImage(filename)
    except Exception as exc:
        return False, f"PNG export failed: {exc}"
    finally:
        if view_object is not None:
            try:
                if original_shape_color is not None:
                    view_object.ShapeColor = original_shape_color
            except Exception:
                pass
            try:
                if original_diffuse_color is not None:
                    view_object.DiffuseColor = original_diffuse_color
            except Exception:
                pass
        try:
            Gui.Selection.clearSelection()
            for selected in selection_snapshot:
                try:
                    Gui.Selection.addSelection(selected)
                except Exception:
                    pass
        except Exception:
            pass

    return True, filename


def export_selected_object_to_kicad_pcb(obj=None, filename=None, segments_per_curve=32):
    if obj is None:
        obj = _selected_export_target()
        if obj is None:
            return False, "Select a panel body in the model tree first."

    if filename is None:
        try:
            from PySide6 import QtWidgets
        except ImportError:
            try:
                from PySide2 import QtWidgets
            except ImportError:
                from PySide import QtWidgets

        doc = App.ActiveDocument
        default_dir = ""
        if doc is not None and getattr(doc, "FileName", ""):
            default_dir = os.path.dirname(doc.FileName)
        if not default_dir:
            default_dir = os.path.expanduser("~")

        suggested = _default_export_filename(obj, ".kicad_pcb")
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(
            None,
            "Export Selected Panel as KiCad PCB",
            os.path.join(default_dir, suggested),
            "KiCad PCB Files (*.kicad_pcb)",
        )
        if not filename:
            return False, "Export cancelled."
        if not filename.lower().endswith(".kicad_pcb"):
            filename += ".kicad_pcb"

    try:
        edgecuts = _kicad_edgecuts_from_obj(obj, segments_per_curve=int(segments_per_curve))
        if not edgecuts:
            return False, "Could not derive KiCad Edge.Cuts geometry from the selected shape."

        thickness_mm = 1.6
        spec = _export_spec_from_obj(obj)
        if spec is not None:
            try:
                thickness_mm = float(spec.get("thickness_mm", thickness_mm))
            except Exception:
                pass

        board_text = _kicad_pcb_text_from_edgecuts(edgecuts, thickness_mm=thickness_mm)
        with open(filename, "w", encoding="utf-8") as handle:
            handle.write(board_text)
    except Exception as exc:
        return False, f"KiCad PCB export failed: {exc}"

    return True, filename


def export_selected_object_to_kicad_svg(obj=None, filename=None, segments_per_curve=32):
    if obj is None:
        obj = _selected_export_target()
        if obj is None:
            return False, "Select a panel body in the model tree first."

    if filename is None:
        try:
            from PySide6 import QtWidgets
        except ImportError:
            try:
                from PySide2 import QtWidgets
            except ImportError:
                from PySide import QtWidgets

        doc = App.ActiveDocument
        default_dir = ""
        if doc is not None and getattr(doc, "FileName", ""):
            default_dir = os.path.dirname(doc.FileName)
        if not default_dir:
            default_dir = os.path.expanduser("~")

        suggested = _default_export_filename(obj, ".svg")
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(
            None,
            "Export Selected Panel as KiCad Edge SVG",
            os.path.join(default_dir, suggested),
            "SVG Files (*.svg)",
        )
        if not filename:
            return False, "Export cancelled."
        if not filename.lower().endswith(".svg"):
            filename += ".svg"

    try:
        edgecuts = _kicad_edgecuts_from_obj(obj, segments_per_curve=int(segments_per_curve))
        if not edgecuts:
            return False, "Could not derive Edge.Cuts geometry from the selected shape."
        svg_text = _kicad_edge_svg_text_from_edgecuts(edgecuts)
        with open(filename, "w", encoding="utf-8") as handle:
            handle.write(svg_text)
    except Exception as exc:
        return False, f"KiCad Edge SVG export failed: {exc}"

    return True, filename


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
            "Choose STL for the solid body, SVG for vector output, or PNG for a rendered image."
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
        self.format_combo.addItem("KiCad PCB", "kicad")
        self.format_combo.addItem("KiCad Edge SVG", "kicad_svg")
        self.format_combo.currentIndexChanged.connect(self._update_format_ui)

        format_form.addRow("Export as", self.format_combo)
        format_layout.addLayout(format_form)

        self.options_stack = QtWidgets.QStackedWidget()
        self.options_stack.addWidget(self._build_stl_options())
        self.options_stack.addWidget(self._build_svg_options())
        self.options_stack.addWidget(self._build_png_options())
        self.options_stack.addWidget(self._build_kicad_options())
        self.options_stack.addWidget(self._build_kicad_svg_options())
        format_layout.addWidget(self.options_stack)

        left_column.addWidget(format_box)

        output_box = QtWidgets.QGroupBox("Output")
        output_layout = QtWidgets.QVBoxLayout(output_box)
        output_layout.setSpacing(10)

        path_row = QtWidgets.QHBoxLayout()
        path_row.setSpacing(8)

        self.output_path = QtWidgets.QLineEdit()
        self.output_path.setPlaceholderText("Choose an output file")

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

        form = QtWidgets.QFormLayout()
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)

        self.kicad_segments_spin = QtWidgets.QSpinBox()
        self.kicad_segments_spin.setRange(8, 256)
        self.kicad_segments_spin.setSingleStep(4)
        self.kicad_segments_spin.setValue(32)

        form.addRow("Curve segments", self.kicad_segments_spin)
        layout.addLayout(form)

        note = QtWidgets.QLabel(
            "KiCad PCB exports the panel as Edge.Cuts geometry in a minimal .kicad_pcb file."
        )
        note.setWordWrap(True)
        note.setObjectName("helperText")
        layout.addWidget(note)
        layout.addStretch(1)

        return page

    def _build_kicad_svg_options(self):
        page = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        form = QtWidgets.QFormLayout()
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)

        self.kicad_svg_segments_spin = QtWidgets.QSpinBox()
        self.kicad_svg_segments_spin.setRange(8, 256)
        self.kicad_svg_segments_spin.setSingleStep(4)
        self.kicad_svg_segments_spin.setValue(32)

        form.addRow("Curve segments", self.kicad_svg_segments_spin)
        layout.addLayout(form)

        note = QtWidgets.QLabel(
            "KiCad Edge SVG exports the panel outline and cutouts as a simple SVG suitable for Edge.Cuts workflows."
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
            "kicad": ".kicad_pcb",
            "kicad_svg": ".svg",
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
        elif fmt == "kicad_svg":
            notes.append("KiCad Edge SVG exports the panel outline as SVG for Edge.Cuts workflows.")
        else:
            notes.append("KiCad PCB exports Edge.Cuts geometry as a board file.")

        self.notes.setPlainText("\n".join(notes))

    def _update_format_ui(self, *args):
        self.options_stack.setCurrentIndex({"stl": 0, "svg": 1, "png": 2, "kicad": 3, "kicad_svg": 4}.get(self._current_format(), 0))
        self._update_output_path()
        self._update_notes()

    def _update_output_path(self):
        obj = self.export_target
        if obj is None:
            return

        current = self.output_path.text().strip()
        if current:
            stem, _ = os.path.splitext(current)
            if stem:
                self.output_path.setText(stem + self._current_extension())
                return

        doc = App.ActiveDocument
        default_dir = ""
        if doc is not None and getattr(doc, "FileName", ""):
            default_dir = os.path.dirname(doc.FileName)
        if not default_dir:
            default_dir = os.path.expanduser("~")

        self.output_path.setText(os.path.join(default_dir, _default_export_filename(obj, self._current_extension())))

    def refresh_selection(self):
        self.export_target = _selected_export_target()
        self.target_name.setText(self._selected_object_name())
        self.target_type.setText(self._selected_object_type())

        if self.export_target is None:
            self.export_status.setText("Select a panel body in the tree or model view.")
        else:
            self.export_status.setText(f"Ready to export {self._selected_object_name()}.")
            self._update_output_path()

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
        default_dir = ""
        if doc is not None and getattr(doc, "FileName", ""):
            default_dir = os.path.dirname(doc.FileName)
        if not default_dir:
            default_dir = os.path.expanduser("~")

        current = self.output_path.text().strip()
        if not current:
            current = os.path.join(default_dir, _default_export_filename(obj, self._current_extension()))

        fmt = self._current_format()
        filters = {
            "stl": "STL Files (*.stl)",
            "svg": "SVG Files (*.svg)",
            "png": "PNG Files (*.png)",
            "kicad": "KiCad PCB Files (*.kicad_pcb)",
            "kicad_svg": "SVG Files (*.svg)",
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
        self.output_path.setText(filename)

    def export_selected(self):
        self.refresh_selection()
        obj = self.export_target
        if obj is None:
            self.export_status.setText("Select a panel body before exporting.")
            return

        filename = self.output_path.text().strip()
        if not filename:
            self.choose_output_path()
            filename = self.output_path.text().strip()
        if not filename:
            self.export_status.setText("Export cancelled.")
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
        elif fmt == "kicad_svg":
            ok, result = export_selected_object_to_kicad_svg(
                obj=obj,
                filename=filename,
                segments_per_curve=self.kicad_svg_segments_spin.value(),
            )
        else:
            ok, result = export_selected_object_to_kicad_pcb(
                obj=obj,
                filename=filename,
                segments_per_curve=self.kicad_segments_spin.value(),
            )

        if ok:
            self.export_status.setText(f"Exported {os.path.basename(result)}.")
            try:
                App.Console.PrintMessage(f"\nExported panel: {result}\n")
            except Exception:
                pass
        else:
            self.export_status.setText(result)

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
