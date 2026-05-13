# EurorackForge

<p align="center">
  <img src="EurorackForge.svg" alt="EurorackForge icon" width="96">
</p>

<p align="center">
  <strong>A FreeCAD workbench for creating Eurorack faceplates.</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/FreeCAD-Macro-blue" alt="FreeCAD Macro">
  <img src="https://img.shields.io/badge/License-MIT-green" alt="MIT License">
  <img src="https://img.shields.io/badge/Version-1.0.0-orange" alt="Version 1.0.0">
</p>

---

## Overview

**EurorackForge** is a FreeCAD workbench for creating Eurorack synthesizer faceplates directly inside FreeCAD.

It is designed to help makers, musicians, DIY synthesizer builders, and hardware designers quickly generate panel geometry for Eurorack modules.

Typical use cases include:

- Creating Eurorack faceplates / front panels
- Prototyping module layouts
- Generating simple panel geometry in FreeCAD
- Preparing designs for CNC, laser cutting, 3D printing, or further CAD work

---

## Features

- Generates Doepfer-style Eurorack panels by default
- Also supports Intellijel 1U, Pulp Logic 1U, Kosmo, and custom panel formats
- Opens a guided task panel with presets, a live summary, and a 2D preview
- Lets you save, load, and delete panel presets locally
- Opens an export dialog for STL, SVG, PNG, and KiCad PCB output
- Includes a custom SVG icon
- Can be installed through FreeCAD Addon Manager as a custom GitHub repository
- Exposes the generator from the Eurorack Forge workbench toolbar
- Keeps a macro wrapper for compatibility

---

## Preview

<p align="center">
  <img src="EurorackForge.svg" alt="EurorackForge icon preview" width="128">
</p>

> Screenshot preview can be added here later.

Recommended screenshot path:

```text
screenshots/eurorackforge-preview.png
```

Then add this to the README after you add a screenshot:

```markdown
![EurorackForge preview](screenshots/eurorackforge-preview.png)
```

---

## Files

```text
EurorackForge/
├── EurorackForge.FCMacro
├── EurorackForge.svg
├── README.md
├── LICENSE
└── package.xml
```

File descriptions:

- `EurorackForge.FCMacro` — the FreeCAD macro
- `EurorackForge.svg` — the macro icon
- `package.xml` — FreeCAD Addon Manager metadata
- `README.md` — project documentation
- `LICENSE` — project license

---

# Installation

## Option 1: Install through FreeCAD Addon Manager using a custom GitHub repository

This is the recommended installation method while the macro is hosted on GitHub.

### 1. Add this repository to FreeCAD

Open FreeCAD and go to:

```text
Edit → Preferences → Addon Manager
```

Find the section for custom repositories.

Add this repository URL:

```text
https://github.com/nathanaelnoir/EurorackForge
```

Use this branch:

```text
main
```

Click **Apply** or **OK**.

Restart FreeCAD if needed.

---

### 2. Install EurorackForge

Open:

```text
Tools → Addon Manager
```

Search for:

```text
EurorackForge
```

Install it.

After installation, the macro should be available from:

```text
Macro → Macros…
```

---

## Option 2: Manual installation

Download these two files:

```text
EurorackForge.FCMacro
EurorackForge.svg
```

Copy both files into your FreeCAD macro directory.

You can find your macro directory in FreeCAD here:

```text
Macro → Macros…
```

Restart FreeCAD if needed.

Then run the macro from:

```text
Macro → Macros… → EurorackForge
```

---

# Add EurorackForge to a toolbar

Addon Manager installs the macro, but FreeCAD does **not** automatically place macro buttons into a toolbar.

To add EurorackForge to a toolbar manually, follow these steps.

---

## Step 1: Register the macro as a toolbar command

In FreeCAD, open:

```text
Tools → Customize…
```

Go to the **Macros** tab.

Select the macro file:

```text
EurorackForge.FCMacro
```

Fill in the fields like this:

```text
Menu text: EurorackForge
Tool tip: Generate Eurorack facepanels
Status text: Generate Eurorack facepanels
Pixmap / Icon: EurorackForge.svg
```

Click:

```text
Add
```

This makes the macro appear as a command in the **Macros** category.

---

## Step 2: Create a “My Tools” toolbar

Still inside:

```text
Tools → Customize…
```

Go to the **Toolbars** tab.

Create a new toolbar.

Name it:

```text
My Tools
```

Make sure the toolbar is enabled.

---

## Step 3: Add EurorackForge to the toolbar

In the **Toolbars** tab:

1. Select the toolbar:

   ```text
   My Tools
   ```

2. In the command category list, choose:

   ```text
   Macros
   ```

3. Select:

   ```text
   EurorackForge
   ```

4. Click the arrow button or **Add** button to move it into the toolbar.

5. Click:

   ```text
   Apply
   ```

6. Click:

   ```text
   OK
   ```

The EurorackForge button should now appear in your **My Tools** toolbar.

---

## If EurorackForge does not appear in the Macros category

Make sure you completed this step first:

```text
Tools → Customize… → Macros tab → Add
```

Simply installing or creating the macro is not enough.

FreeCAD only shows the macro in the **Macros** command category after it has been added through the **Macros** tab in the Customize dialog.

Also check that these files are inside the FreeCAD macro folder:

```text
EurorackForge.FCMacro
EurorackForge.svg
```

---

# Usage

After installation, run EurorackForge from:

```text
Macro → Macros… → EurorackForge
```

or, if you added it to a toolbar:

```text
My Tools → EurorackForge button
```

The macro will generate Eurorack facepanel geometry inside the active FreeCAD document.

To export a panel, select the panel body in the model tree and use:

```text
Eurorack Forge → Export Panel
```

The export dialog lets you choose:

- STL for the solid body
- SVG for vector geometry
- PNG for a rendered image of the current view
- KiCad PCB for Edge.Cuts-only board geometry

If no document is open, the macro may create a new one depending on the macro implementation.

---

# Best Practices

## Keep the macro and icon names identical

Use matching base names:

```text
EurorackForge.FCMacro
EurorackForge.svg
```

This makes FreeCAD icon handling easier and keeps the project clean.

---

## Keep the repository structure simple

Recommended structure:

```text
EurorackForge/
├── EurorackForge.FCMacro
├── EurorackForge.svg
├── README.md
├── LICENSE
├── package.xml
└── screenshots/
    └── eurorackforge-preview.png
```

---

## Use clear version numbers

Use semantic versioning:

```text
1.0.0
1.0.1
1.1.0
2.0.0
```

Example:

- `1.0.0` — first stable release
- `1.0.1` — small bug fix
- `1.1.0` — new feature
- `2.0.0` — major change

---

## Add screenshots

A screenshot helps users understand what the macro does before installing it.

Recommended location:

```text
screenshots/eurorackforge-preview.png
```

Then show it in the README:

```markdown
![EurorackForge preview](screenshots/eurorackforge-preview.png)
```

---

## Keep `package.xml` updated

When you release a new version, update:

```xml
<version>1.0.0</version>
<date>2026-05-11</date>
```

Also make sure the icon is listed at the package level:

```xml
<icon>EurorackForge.svg</icon>
```

and inside the macro block:

```xml
<content>
  <macro>
    <name>EurorackForge</name>
    <description>A simple FreeCAD macro for generating Eurorack facepanels.</description>
    <file>EurorackForge.FCMacro</file>
    <icon>EurorackForge.svg</icon>
  </macro>
</content>
```

---

## Use a release on GitHub

After changes are tested, create a GitHub release.

Example tag:

```text
v1.0.0
```

Example release notes:

```markdown
Initial release.

Features:
- Generates Eurorack facepanel geometry
- Includes FreeCAD macro
- Includes SVG icon
- Includes Addon Manager package metadata
```

---

# Current limitations

EurorackForge ships as a FreeCAD workbench with a macro wrapper for compatibility.

That means:

- Addon Manager can install the workbench package.
- The Create Faceplate command appears in the Eurorack Forge toolbar and menu.
- The macro entry point still works for users who prefer launching it from the Macro dialog.

---

# Troubleshooting

## The macro installed, but no toolbar button appeared

This is expected.

Add it manually using:

```text
Tools → Customize… → Macros tab
```

Then add it to:

```text
Tools → Customize… → Toolbars tab → My Tools
```

---

## The icon does not appear in the toolbar

Check that the icon file exists:

```text
EurorackForge.svg
```

Check that the file name matches exactly, including capitalization.

Correct:

```text
EurorackForge.svg
```

Incorrect:

```text
eurorackforge.svg
Eurorackforge.svg
EurorackForge.SVG
```

Then re-add the macro through:

```text
Tools → Customize… → Macros
```

and select the SVG icon again.

---

## The Addon Manager shows a default image

Make sure `package.xml` contains:

```xml
<icon>EurorackForge.svg</icon>
```

near the top level of the package.

Also make sure this file exists in the repository root:

```text
EurorackForge.svg
```

If it still shows a default image, refresh the Addon Manager cache or restart FreeCAD.

Some FreeCAD versions may handle PNG previews more reliably than SVG package icons. In that case, add:

```text
EurorackForge.png
```

and use this in `package.xml`:

```xml
<icon>EurorackForge.png</icon>
```

You can still keep the toolbar macro icon as SVG.

---

# License

This project is licensed under the MIT License.

See:

```text
LICENSE
```

---

# Author

Created by **nathanaelnoir**.

Repository:

```text
https://github.com/nathanaelnoir/EurorackForge
```
