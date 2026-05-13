import os

import FreeCADGui as Gui


def resource_path(filename):
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)


class CreateEurorackPanelCommand:
    def GetResources(self):
        return {
            "Pixmap": resource_path("EurorackForge.svg"),
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


class EurorackForgeWorkbench(Gui.Workbench):
    MenuText = "Eurorack Forge"
    ToolTip = "Tools for creating Eurorack front panels."
    Icon = resource_path("EurorackForge.svg")

    def Initialize(self):
        self.appendToolbar("Eurorack Forge", ["EurorackForge_CreatePanel"])
        self.appendMenu("Eurorack Forge", ["EurorackForge_CreatePanel"])

    def Activated(self):
        pass

    def Deactivated(self):
        pass

    def ContextMenu(self, recipient):
        self.appendContextMenu("Eurorack Forge", ["EurorackForge_CreatePanel"])

    def GetClassName(self):
        return "Gui::PythonWorkbench"


Gui.addWorkbench(EurorackForgeWorkbench())
