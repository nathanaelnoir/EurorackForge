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

DOEPFER_WIDTH_MATHEMATICAL = "mathematical"
DOEPFER_WIDTH_ACTUAL = "actual"
DOEPFER_WIDTH_OPTIONS = [
    (DOEPFER_WIDTH_MATHEMATICAL, "Mathematical"),
    (DOEPFER_WIDTH_ACTUAL, "Actual"),
]

DOEPFER_ACTUAL_WIDTHS_MM = {
    1: 5.00,
    1.5: 7.50,
    2: 9.80,
    4: 20.00,
    6: 30.00,
    8: 40.30,
    10: 50.50,
    12: 60.60,
    14: 70.80,
    16: 80.90,
    18: 91.30,
    20: 101.30,
    21: 106.30,
    22: 111.40,
    28: 141.90,
    42: 213.00,
}

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
PCB_HEIGHT_MM = 100.0
PCB_CLEARANCE_MM = 1.0
PCB_THICKNESS_MM = 1.6
PCB_BACK_OFFSET_MM = 0.8


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


def hp_to_width_text(hp, width_mode=DOEPFER_WIDTH_MATHEMATICAL):
    mathematical_width = hp * HP_MM - WIDTH_CLEARANCE

    if width_mode == DOEPFER_WIDTH_ACTUAL:
        actual_width = doepfer_actual_width_mm(hp)
        if actual_width is not None:
            return f"{hp} HP / {actual_width:.2f} mm ({mathematical_width:.2f} mm mathematical)"

    return f"{hp} HP / {mathematical_width:.2f} mm"


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


def doepfer_width_mm(hp, width_mode=DOEPFER_WIDTH_MATHEMATICAL):
    if width_mode == DOEPFER_WIDTH_ACTUAL:
        actual_width = doepfer_actual_width_mm(hp)
        if actual_width is not None:
            return actual_width

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


def doepfer_width_mode_label(width_mode):
    for key, label in DOEPFER_WIDTH_OPTIONS:
        if key == width_mode:
            return label

    return DOEPFER_WIDTH_OPTIONS[0][1]


def doepfer_width_mode_suffix(width_mode):
    if width_mode == DOEPFER_WIDTH_MATHEMATICAL:
        return ""

    return f" [{doepfer_width_mode_label(width_mode)}]"


def doepfer_actual_width_mm(hp):
    return DOEPFER_ACTUAL_WIDTHS_MM.get(hp)


def build_panel_spec(
    standard_key,
    cutout_type,
    *,
    doepfer_hp=8,
    doepfer_width_mode=DOEPFER_WIDTH_ACTUAL,
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
        width_mm = doepfer_width_mm(width_value, doepfer_width_mode)
        mathematical_width_mm = width_value * HP_MM - WIDTH_CLEARANCE
        height_mm = PANEL_HEIGHT
        thickness_mm = doepfer_thickness_mm
        hole_diameter_mm = HOLE_DIAMETER
        hole_x_margin_mm = HOLE_X_FIRST
        hole_y_margin_mm = HOLE_Y_FROM_EDGE
        hole_layout_key = "doepfer"
        width_unit_label = "HP"
        if doepfer_width_mode == DOEPFER_WIDTH_ACTUAL:
            width_display = f"{width_value} HP / {width_mm:.2f} mm ({mathematical_width_mm:.2f} mm mathematical)"
        else:
            width_display = f"{width_value} HP / {width_mm:.2f} mm"
        display_name = f"Doepfer Eurorack {width_value} HP{doepfer_width_mode_suffix(doepfer_width_mode)}"
        if doepfer_width_mode == DOEPFER_WIDTH_ACTUAL and doepfer_actual_width_mm(width_value) is None:
            conformance_note = (
                f"Doepfer-style 3U panel using the published actual widths where available; "
                f"unsupported HP values fall back to the mathematical 5.08 mm grid. "
                f"Height is 128.5 mm and thickness is {thickness_mm:.1f} mm."
            )
        elif doepfer_width_mode == DOEPFER_WIDTH_ACTUAL:
            conformance_note = (
                f"Doepfer-style 3U panel using Doepfer's published actual front-panel widths, "
                f"128.5 mm height, and {thickness_mm:.1f} mm thickness."
            )
        else:
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
        "doepfer_width_mode": doepfer_width_mode,
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


def pcb_outline_dimensions_from_spec(spec):
    if spec["standard_key"] == STANDARD_PULP_LOGIC_1U:
        width_mm = (spec["width_value"] * 6 * HP_MM) - PCB_CLEARANCE_MM
    elif spec["standard_key"] == STANDARD_DOEPFER:
        actual_width_mm = doepfer_actual_width_mm(spec["width_value"])
        if actual_width_mm is not None:
            width_mm = actual_width_mm - PCB_CLEARANCE_MM
        else:
            width_mm = (spec["width_value"] * HP_MM) - PCB_CLEARANCE_MM
    elif spec["standard_key"] == STANDARD_INTELLIJEL_1U:
        width_mm = (spec["width_value"] * HP_MM) - PCB_CLEARANCE_MM
    else:
        width_mm = spec["width_mm"] - PCB_CLEARANCE_MM

    width_mm = max(1.0, width_mm)
    return width_mm, PCB_HEIGHT_MM, PCB_THICKNESS_MM


def make_pcb_shape_from_spec(spec):
    pcb_width_mm, pcb_height_mm, pcb_thickness_mm = pcb_outline_dimensions_from_spec(spec)
    points = [
        App.Vector(-pcb_width_mm / 2.0, -pcb_height_mm / 2.0, 0),
        App.Vector(pcb_width_mm / 2.0, -pcb_height_mm / 2.0, 0),
        App.Vector(pcb_width_mm / 2.0, pcb_height_mm / 2.0, 0),
        App.Vector(-pcb_width_mm / 2.0, pcb_height_mm / 2.0, 0),
        App.Vector(-pcb_width_mm / 2.0, -pcb_height_mm / 2.0, 0),
    ]
    wire = Part.makePolygon(points)
    face = Part.Face(wire)
    face.Placement = App.Placement(
        App.Vector(0, 0, spec["thickness_mm"] + PCB_BACK_OFFSET_MM),
        App.Rotation()
    )
    return face


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


def _spec_name_suffix(spec):
    if spec.get("standard_key") != STANDARD_DOEPFER:
        return ""

    width_mode = spec.get("doepfer_width_mode", DOEPFER_WIDTH_MATHEMATICAL)
    if width_mode == DOEPFER_WIDTH_MATHEMATICAL:
        return ""

    return f"_{width_mode}"


def create_body_from_spec(doc, shape, spec):
    clean_name = (
        f"{spec['standard_key']}_{str(spec['width_value']).replace('.', '_')}"
        f"{_spec_name_suffix(spec)}_{spec['cutout_type']}"
    )

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


def create_pcb_from_spec(doc, spec):
    pcb_shape = make_pcb_shape_from_spec(spec)

    pcb_name = (
        f"{spec['standard_key']}_{str(spec['width_value']).replace('.', '_')}"
        f"{_spec_name_suffix(spec)}_{spec['cutout_type']}_PCB"
    )
    pcb = doc.addObject("Part::Feature", pcb_name)
    pcb.Label = f"{spec['display_name']} PCB"
    pcb.Shape = pcb_shape

    try:
        pcb.addProperty("App::PropertyString", "EurorackForgeSpecJSON", "EurorackForge", "Stored PCB specification for export helpers.")
    except Exception:
        pass

    try:
        pcb.addProperty("App::PropertyString", "EurorackForgeRole", "EurorackForge", "Geometry role used by export helpers.")
    except Exception:
        pass

    try:
        pcb.addProperty("App::PropertyString", "EurorackForgePCBOf", "EurorackForge", "Name of the faceplate body this PCB belongs to.")
    except Exception:
        pass

    try:
        pcb.EurorackForgeSpecJSON = json.dumps(spec)
    except Exception:
        pass

    try:
        pcb.ViewObject.ShapeColor = (0.20, 0.62, 0.48)
        pcb.ViewObject.Transparency = 72
    except Exception:
        pass

    return pcb


def create_reference_sketch(body, source, spec):
    if body is None or source is None:
        return None

    try:
        import Sketcher
    except Exception:
        return None

    doc = body.Document
    sketch_name = (
        f"{spec['standard_key']}_{str(spec['width_value']).replace('.', '_')}"
        f"{_spec_name_suffix(spec)}_Reference"
    )

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
    width_mode=DOEPFER_WIDTH_ACTUAL,
):
    width = doepfer_width_mm(hp, width_mode)
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
        f"Width: {hp_to_width_text(hp, width_mode)}\n"
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
    pcb_width_mm, pcb_height_mm, pcb_thickness_mm = pcb_outline_dimensions_from_spec(spec)

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
        f"PCB outline: {pcb_width_mm:.2f} x {pcb_height_mm:.2f} x {pcb_thickness_mm:.2f} mm\n"
        f"Mounting points: {format_point_positions(points)}\n"
        f"X positions: {format_positions(x_positions)}\n"
        f"Y positions: {format_positions(y_positions)}\n"
        f"Notes: {spec['conformance_note']}"
    )


class FaceplatePreviewWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.spec = build_panel_spec(STANDARD_DOEPFER, "circles")
        self.show_pcb = False
        self.setMinimumHeight(220)
        self.setMinimumWidth(260)

    def setParameters(self, spec, show_pcb=False):
        self.spec = spec
        self.show_pcb = bool(show_pcb)
        self.update()

    def sizeHint(self):
        return QtCore.QSize(360, 300)

    def _panel_rect(self, bounds):
        panel_width = self.spec["width_mm"]
        panel_height = self.spec["height_mm"]
        margin = 18.0

        available_width = max(1.0, bounds.width() - margin * 2.0)
        available_height = max(1.0, bounds.height() - margin * 2.0)

        scale = min(available_width / panel_width, available_height / panel_height)
        scaled_width = panel_width * scale
        scaled_height = panel_height * scale

        x = bounds.center().x() - scaled_width / 2.0
        y = bounds.center().y() - scaled_height / 2.0
        return QtCore.QRectF(x, y, scaled_width, scaled_height), scale

    def _pcb_rect(self, panel_rect, scale):
        pcb_width_mm, pcb_height_mm, _ = pcb_outline_dimensions_from_spec(self.spec)
        scaled_width = pcb_width_mm * scale
        scaled_height = pcb_height_mm * scale
        x = panel_rect.center().x() - scaled_width / 2.0
        y = panel_rect.center().y() - scaled_height / 2.0
        return QtCore.QRectF(x, y, scaled_width, scaled_height)

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
        if self.show_pcb:
            pcb_rect = self._pcb_rect(panel_rect, scale)

            pcb_shadow = pcb_rect.translated(3, 5)
            painter.setBrush(QtGui.QColor(0, 0, 0, 55))
            painter.drawRoundedRect(pcb_shadow, 8, 8)

            painter.setBrush(QtGui.QColor(46, 112, 86, 120))
            painter.setPen(QtGui.QPen(QtGui.QColor(118, 198, 160, 160), 1.0))
            painter.drawRoundedRect(pcb_rect, 8, 8)

            pcb_label_font = QtGui.QFont()
            pcb_label_font.setPointSizeF(max(8.0, self.font().pointSizeF()))
            pcb_label_font.setBold(True)
            painter.setFont(pcb_label_font)
            painter.setPen(QtGui.QPen(QtGui.QColor(205, 241, 224)))
            painter.drawText(
                pcb_rect.adjusted(8, 8, -8, -8),
                QtCore.Qt.AlignCenter,
                f"PCB {pcb_rect.width() / scale:.0f} x {pcb_rect.height() / scale:.0f} mm"
            )

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

        display_top_clearance = self.spec["bottom_clearance_mm"]
        display_bottom_clearance = self.spec["top_clearance_mm"]
        top_keepout_y = map_y(self.spec["height_mm"] / 2.0 - display_top_clearance)
        bottom_keepout_y = map_y(-self.spec["height_mm"] / 2.0 + display_bottom_clearance)
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
            f"Top keep-out {display_top_clearance:.0f} mm"
        )
        painter.drawText(
            QtCore.QRectF(panel_rect.left() + 8, bottom_keepout_y + 4, panel_rect.width() - 16, 14),
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter,
            f"Bottom keep-out {display_bottom_clearance:.0f} mm"
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

    filename = os.path.abspath(os.path.normpath(filename))
    if _export_path_conflict(filename):
        return False, _export_conflict_message(filename)

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
    label = getattr(obj, "Name", getattr(obj, "Label", "EurorackPanel"))
    return _sanitize_file_stem(label) + extension


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

    pcb_name = (
        f"{spec['standard_key']}_{str(spec['width_value']).replace('.', '_')}"
        f"{_spec_name_suffix(spec)}_{spec['cutout_type']}_PCB"
    )
    candidate = doc.getObject(pcb_name)
    if candidate is not None:
        return candidate

    return None


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
            (
                STANDARD_DOEPFER,
                r"^Doepfer Eurorack (\d+) HP(?: \[(Mathematical|Actual)\])? - ([0-9.]+)mm - (circles|slots)$",
            ),
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
                width_mode_text = groups[1]
                width_mode = (
                    DOEPFER_WIDTH_ACTUAL if width_mode_text == "Actual" else DOEPFER_WIDTH_MATHEMATICAL
                )
                thickness_mm = float(groups[2])
                return build_panel_spec(
                    STANDARD_DOEPFER,
                    cutout_type,
                    doepfer_hp=hp,
                    doepfer_width_mode=width_mode,
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
    if getattr(obj, "TypeId", "") == "PartDesign::Body":
        return obj

    shape = getattr(obj, "Shape", None)
    if shape is not None and not getattr(shape, "isNull", lambda: True)():
        return obj

    base = getattr(obj, "BaseFeature", None)
    if base is not None:
        base_shape = getattr(base, "Shape", None)
        if base_shape is not None and not getattr(base_shape, "isNull", lambda: True)():
            return base

    return None


def _draft_projection_source(obj):
    if obj is None:
        return None

    # If a PartDesign Body is selected, use the final result first.
    # This is usually the last feature, e.g. Pocket, Pad, Fillet, etc.
    if getattr(obj, "TypeId", "") == "PartDesign::Body":
        tip = getattr(obj, "Tip", None)
        if tip is not None:
            tip_shape = getattr(tip, "Shape", None)
            if tip_shape is not None and not getattr(tip_shape, "isNull", lambda: True)():
                return tip

        shape = getattr(obj, "Shape", None)
        if shape is not None and not getattr(shape, "isNull", lambda: True)():
            return obj

        base = getattr(obj, "BaseFeature", None)
        if base is not None:
            base_shape = getattr(base, "Shape", None)
            if base_shape is not None and not getattr(base_shape, "isNull", lambda: True)():
                return base

    # If a normal feature such as Pocket is selected, use it directly.
    shape = getattr(obj, "Shape", None)
    if shape is not None and not getattr(shape, "isNull", lambda: True)():
        return obj

    tip = getattr(obj, "Tip", None)
    if tip is not None:
        tip_shape = getattr(tip, "Shape", None)
        if tip_shape is not None and not getattr(tip_shape, "isNull", lambda: True)():
            return tip

    base = getattr(obj, "BaseFeature", None)
    if base is not None:
        base_shape = getattr(base, "Shape", None)
        if base_shape is not None and not getattr(base_shape, "isNull", lambda: True)():
            return base

    return obj


def _containing_body(obj):
    if obj is None:
        return None

    if getattr(obj, "TypeId", "") == "PartDesign::Body":
        return obj

    try:
        parent = obj.getParentGeoFeatureGroup()
        if parent is not None and getattr(parent, "TypeId", "") == "PartDesign::Body":
            return parent
    except Exception:
        pass

    for parent in getattr(obj, "InList", []) or []:
        if getattr(parent, "TypeId", "") == "PartDesign::Body":
            return parent

    return None


def _body_feature_path_name(obj):
    if obj is None:
        return None

    name = getattr(obj, "Name", None)
    if name:
        return name

    label = getattr(obj, "Label", None)
    if label:
        return label

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

    filename = os.path.abspath(os.path.normpath(filename))
    if _export_path_conflict(filename):
        return False, _export_conflict_message(filename)

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

    filename = os.path.abspath(os.path.normpath(filename))
    if _export_path_conflict(filename):
        return False, _export_conflict_message(filename)

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

    filename = os.path.abspath(os.path.normpath(filename))
    if _export_path_conflict(filename):
        return False, _export_conflict_message(filename)

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

    filename = os.path.abspath(os.path.normpath(filename))
    if _export_path_conflict(filename):
        return False, _export_conflict_message(filename)

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


def export_selected_object_to_kicad_dxf(obj=None, filename=None):
    if Gui is None:
        return False, "GUI is required for KiCad DXF export."

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

        suggested = _default_export_filename(obj, ".dxf")
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(
            None,
            "Export Selected Panel as KiCad DXF",
            os.path.join(default_dir, suggested),
            "DXF Files (*.dxf)",
        )
        if not filename:
            return False, "Export cancelled."
        if not filename.lower().endswith(".dxf"):
            filename += ".dxf"

    filename = os.path.abspath(os.path.normpath(filename))
    if _export_path_conflict(filename):
        return False, _export_conflict_message(filename)
    output_dir = os.path.dirname(filename)
    if output_dir:
        try:
            os.makedirs(output_dir, exist_ok=True)
        except Exception:
            pass

    doc = obj.Document or App.ActiveDocument
    if doc is None:
        return False, "No active document is available for DXF export."

    companion_pcb = _pcb_object_for_export(obj)
    pcb_filename = _pcb_export_filename(filename) if companion_pcb is not None else None
    if pcb_filename is not None and _export_path_conflict(pcb_filename):
        return False, _export_conflict_message(pcb_filename)

    try:
        try:
            import Draft
            import importDXF
        except Exception as exc:
            return False, f"Draft DXF export is required for KiCad DXF export: {exc}"

        projection_source = _draft_projection_source(obj)
        if projection_source is None:
            return False, "Could not resolve the Draft source selection."

        previous_workbench_name = None
        try:
            active_wb = Gui.activeWorkbench()
            previous_workbench_name = active_wb.name()
        except Exception:
            previous_workbench_name = None

        try:
            App.Console.PrintMessage(
                "\nKiCad DXF export source: "
                + getattr(projection_source, "Name", "<none>")
                + " / "
                + getattr(projection_source, "TypeId", "<unknown>")
                + "\n"
            )
        except Exception:
            pass

        try:
            Gui.activateWorkbench("DraftWorkbench")
        except Exception:
            try:
                Gui.activateWorkbench("Draft")
            except Exception:
                pass

        try:
            temp_view = Draft.make_shape2dview(projection_source, App.Vector(0, 0, 1))
        except Exception as exc:
            return False, f"Could not create Draft Shape2DView: {exc}"

        try:
            doc.recompute()
        except Exception:
            pass

        if temp_view is None:
            return False, "Draft did not create a Shape2DView object."

        try:
            temp_view.Label = _sanitize_file_stem(getattr(obj, "Label", getattr(obj, "Name", "EurorackPanel"))) + "_2D"
        except Exception:
            pass

        try:
            shape = getattr(temp_view, "Shape", None)
            if shape is not None:
                try:
                    shape_info = (
                        f"isNull={shape.isNull()} "
                        f"edges={len(getattr(shape, 'Edges', []) or [])} "
                        f"wires={len(getattr(shape, 'Wires', []) or [])}"
                    )
                except Exception:
                    shape_info = "unavailable"
            else:
                shape_info = "missing"

            try:
                App.Console.PrintMessage(
                    "\nKiCad DXF debug:\n"
                    f"  target file: {filename}\n"
                    f"  source: {getattr(projection_source, 'Name', '<none>')} / {getattr(projection_source, 'TypeId', '<unknown>')}\n"
                    f"  temp view: {getattr(temp_view, 'Name', '<none>')} / {getattr(temp_view, 'TypeId', '<unknown>')}\n"
                    f"  shape: {shape_info}\n"
                )
            except Exception:
                pass

            try:
                temp_view.ViewObject.Visibility = True
            except Exception:
                pass

            try:
                App.Console.PrintMessage("KiCad DXF debug: running importDXF.export\n")
            except Exception:
                pass

            try:
                importDXF.export([temp_view], filename)
            except Exception as exc:
                return False, f"KiCad DXF export failed: {exc}"

            try:
                App.Console.PrintMessage("KiCad DXF debug: importDXF.export returned\n")
            except Exception:
                pass

            if companion_pcb is not None and pcb_filename is not None:
                pcb_spec = _export_spec_from_obj(companion_pcb) or _export_spec_from_obj(obj)
                if pcb_spec is None:
                    return False, "Could not resolve PCB dimensions for DXF export."

                try:
                    App.Console.PrintMessage(
                        f"KiCad DXF debug: writing direct PCB DXF to {pcb_filename}\n"
                    )
                except Exception:
                    pass

                try:
                    pcb_text = _pcb_dxf_text_from_spec(pcb_spec)
                    with open(pcb_filename, "w", encoding="utf-8") as handle:
                        handle.write(pcb_text)
                except Exception as exc:
                    return False, f"KiCad PCB DXF export failed: {exc}"

                if not os.path.exists(pcb_filename):
                    return False, "KiCad PCB DXF export did not create a file."

        except Exception as exc:
            return False, f"KiCad DXF export failed: {exc}"

        try:
            exists = os.path.exists(filename)
            size_text = str(os.path.getsize(filename)) if exists else "<missing>"
            App.Console.PrintMessage(
                f"KiCad DXF debug: post-export exists={exists} size={size_text}\n"
            )
        except Exception:
            pass

        if not os.path.exists(filename):
            return False, "KiCad DXF export did not create a file."

    except Exception as exc:
        return False, f"KiCad DXF export failed: {exc}"
    finally:
        try:
            if previous_workbench_name:
                Gui.activateWorkbench(previous_workbench_name)
        except Exception:
            pass
        try:
            doc.recompute()
        except Exception:
            pass

    return True, filename


