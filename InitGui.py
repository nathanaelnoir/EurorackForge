import FreeCADGui as Gui


class CreateEurorackPanelCommand:
    def GetResources(self):
        return {
            "Pixmap": "/Users/sarahmair/Library/Application Support/FreeCAD/v1-1/Mod/EurorackForge/EurorackForge.svg",
            "MenuText": "Create Eurorack Panel",
            "ToolTip": "Create a Eurorack front panel with mounting holes or slots.",
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
    Icon = "/Users/sarahmair/Library/Application Support/FreeCAD/v1-1/Mod/EurorackForge/EurorackForge.svg"

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