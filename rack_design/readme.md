# Rack Design 3D Models

This folder contains the 3D design files (OpenSCAD, Fusion 360, and STL) used to build a custom cooling rack for routers. The system uses a modular chimney approach to distribute fresh air from a single 120mm fan across multiple levels.

## Printed Parts Summary

To assemble the full rack, the following parts were printed using the provided STL files:

*   **1x Curved Intake Duct (`curved_intake_duct.stl`):** Connects the 120mm fan to the vertical chimney.
*   **2x Airflow Chimney Duct 3 levels (`airflow_chimney_duct_3levels.stl`):** Vertical segments with vents for three router levels.
*   **1x Airflow Chimney Duct 2 levels (`airflow_chimney_duct_2levels.stl`):** Vertical segment with vents for two router levels.
*   **1x Chimney End Cap (`chimney_duct_cover.stl`):** Seals the top of the chimney to force air through the vents.
*   **8x Drawer Stops:** Custom heavy-duty stops to replace generic plastic ones.

## 3D Design Details

### 1. Curved Intake Duct (`curved_intake_duct.scad` / `.stl`)
A "saxophone-style" lofted duct that transitions from a 120mm circular fan mount to a rectangular chimney connector. Designed for smooth airflow with no internal sharp corners.

*   **Key Parameters:**
    *   `ancho_placa_base`: Width of the fan mounting plate (120mm for Bosser fans).
    *   `altura_saxofon`: Vertical height of the transition.
    *   `desplazamiento_y`: Lateral offset between the fan center and chimney center.
    *   `rect_x` / `rect_y`: Dimensions of the rectangular exit to match the chimney.

### 2. Airflow Chimney Duct (`airflow_chimney_duct.scad` / `_2levels.stl` / `_3levels.stl`)
A modular, stackable vertical duct. Each module features segmented vents ("branquias") angled at 45° to project air towards the routers without requiring print supports.

*   **Key Parameters:**
    *   `niveles_por_modulo`: Number of cooling levels in the segment (set to 2 or 3 for the provided STLs).
    *   `dist_niveles`: Vertical distance between levels (60mm).
    *   `tolerancia`: Clearance for the male/female stacking connectors.
    *   `grosor_pared`: Wall thickness for structural rigidity.

### 3. Chimney End Cap (`chimney_duct_cover.scad` / `.stl`)
A simple female-connector cap that fits onto the top of the last chimney segment to seal the system.

### 4. Drawer Stop (`drawer_stop.f3d`)
Customized stops designed in Autodesk Fusion 360. These are intended to be "encastrados" into U-shaped cuts made in the generic plastic drawers used for the rack chassis.

---
*Note: All OpenSCAD models are designed to be printed without supports when oriented correctly on the build plate. All models were printed in a Creality Ender 3 Pro printer*
