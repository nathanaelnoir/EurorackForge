import FreeCAD as App
import FreeCADGui as Gui


class CreateEurorackPanelCommand:
    def GetResources(self):
        import os
        import EurorackForge

        icon_path = os.path.join(os.path.dirname(os.path.abspath(EurorackForge.__file__)), "EurorackForge.svg")
        return {
            "Pixmap": icon_path,
            "MenuText": "Create Faceplate",
            "ToolTip": "Open the Eurorack faceplate task panel with Doepfer, 1U, Kosmo, and custom formats.",
            "Accel": "E, P"
        }

    def Activated(self):
        import EurorackForge
        EurorackForge.create_single_eurorack_panel()

    def IsActive(self):
        return True


Gui.addCommand("EurorackForge_CreatePanel", CreateEurorackPanelCommand())


class ExportPanelCommand:
    def GetResources(self):
        import os
        import EurorackForge

        icon_path = os.path.join(os.path.dirname(os.path.abspath(EurorackForge.__file__)), "EurorackForgeExport.svg")
        return {
            "Pixmap": icon_path,
            "MenuText": "Export Panel",
            "ToolTip": "Open the export dialog for STL, SVG, or PNG.",
        }

    def Activated(self):
        import EurorackForge

        EurorackForge.open_export_dialog()

    def IsActive(self):
        return Gui.ActiveDocument is not None


Gui.addCommand("EurorackForge_ExportPanel", ExportPanelCommand())


class EurorackForgeWorkbench(Gui.Workbench):
    MenuText = "Eurorack Forge"
    ToolTip = "Tools for creating Eurorack front panels."
    Icon = "EurorackForge.svg"

    def Initialize(self):
        commands = ["EurorackForge_CreatePanel", "EurorackForge_ExportPanel"]
        self.appendToolbar("Eurorack Forge", commands)
        self.appendMenu("Eurorack Forge", commands)

    def Activated(self):
        pass

    def Deactivated(self):
        pass

    def ContextMenu(self, recipient):
        self.appendContextMenu("Eurorack Forge", ["EurorackForge_CreatePanel", "EurorackForge_ExportPanel"])

    def GetClassName(self):
        return "Gui::PythonWorkbench"


Gui.addWorkbench(EurorackForgeWorkbench())
