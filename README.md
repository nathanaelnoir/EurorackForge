
# EurorackForge

EurorackForge is a FreeCAD macro for generating Eurorack faceplates / facepanels.
EuroRackForge — a FreeCAD macro for generating Eurorack facepanels.
It is intended to make it easier to create simple Eurorack panel geometry directly inside FreeCAD.

## Features

- Generates Eurorack facepanel geometry in FreeCAD.
- Uses a dedicated SVG icon.
- Can be installed through FreeCAD Addon Manager when added as a custom repository.
- Can be added manually to a FreeCAD toolbar.

## Files

- `EurorackForge.FCMacro` - the FreeCAD macro.
- `EurorackForge.svg` - the macro icon.
- `package.xml` - FreeCAD Addon Manager metadata.
- `LICENSE` - project license.

## Requirements

- FreeCAD 0.20 or newer recommended.

## Installation

### Option 1: Install through FreeCAD Addon Manager as a custom repository

1. Open FreeCAD.
2. Go to **Edit → Preferences → Addon Manager**.
3. Find the custom repositories section.
4. Add this repository URL:

   ```text
   https://github.com/nathanaelnoir/EurorackForge