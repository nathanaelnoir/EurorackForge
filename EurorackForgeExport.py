from EurorackForgeCore import (
    export_selected_object_to_stl as _core_export_selected_object_to_stl,
    export_selected_object_to_svg as _core_export_selected_object_to_svg,
    export_selected_object_to_png as _core_export_selected_object_to_png,
    export_selected_object_to_kicad_pcb as _core_export_selected_object_to_kicad_pcb,
    export_selected_object_to_kicad_svg as _core_export_selected_object_to_kicad_svg,
    export_selected_object_to_kicad_dxf as _core_export_selected_object_to_kicad_dxf,
)


def export_selected_object_to_stl(obj=None, filename=None, deflection=0.1):
    return _core_export_selected_object_to_stl(obj=obj, filename=filename, deflection=deflection)


def export_selected_object_to_svg(obj=None, filename=None):
    return _core_export_selected_object_to_svg(obj=obj, filename=filename)


def export_selected_object_to_png(
    obj=None,
    filename=None,
    width=2048,
    height=2048,
    fit=True,
    background_color=(1.0, 1.0, 1.0),
    panel_color=(0.85, 0.87, 0.90),
):
    return _core_export_selected_object_to_png(
        obj=obj,
        filename=filename,
        width=width,
        height=height,
        fit=fit,
        background_color=background_color,
        panel_color=panel_color,
    )


def export_selected_object_to_kicad_pcb(obj=None, filename=None, segments_per_curve=32):
    return _core_export_selected_object_to_kicad_pcb(
        obj=obj,
        filename=filename,
        segments_per_curve=segments_per_curve,
    )


def export_selected_object_to_kicad_svg(obj=None, filename=None, segments_per_curve=32):
    return _core_export_selected_object_to_kicad_svg(
        obj=obj,
        filename=filename,
        segments_per_curve=segments_per_curve,
    )


def export_selected_object_to_kicad_dxf(obj=None, filename=None):
    return _core_export_selected_object_to_kicad_dxf(obj=obj, filename=filename)
