# Rack Design 3D Models

This folder contains the 3D design files (OpenSCAD, Fusion 360, and STL) used to build a custom cooling rack for routers. The system uses a modular chimney approach to distribute fresh air from a single 120mm fan across multiple levels.

## Printed Parts Summary

To assemble the full rack, the following parts were printed using the provided STL files:

*   **1x Curved Intake Duct (`curved_intake_duct.stl`):** Connects the 120mm fan to the vertical chimney.
*   **2x Airflow Chimney Duct 3 levels (`airflow_chimney_duct_3levels.stl`):** Vertical segments with vents for three router levels.
*   **1x Airflow Chimney Duct 2 levels (`airflow_chimney_duct_2levels.stl`):** Vertical segment with vents for two router levels.
*   **1x Chimney End Cap (`chimney_duct_cover.stl`):** Seals the top of the chimney to force air through the vents.
*   **8x Drawer Stops (`drawer_stop.stl`):** Custom heavy-duty stops to replace generic plastic ones.
*   **3x Belkin RT3200 Base (`belkin_rt3200_base.stl`):** Custom bases for the routers to replace original bulky cases.
*   **1x USB Hub Shelf (`hub_shelf_TP-LINK_UH700.stl`):** Shelf for the TP-Link UH700 USB hub.
*   **1x Arduino Nano Holder (`NanoHolderA.stl`):** Mounting bracket for an Arduino Nano.
*   **Decorative Logos (`logo fcefyn.stl`, `logo unc.stl`):** Final aesthetic details representing FCEFyN and UNC.

## 3D Design Details

### 1. Curved Intake Duct (`curved_intake_duct.scad` / `.stl`)
A "saxophone-style" lofted duct that transitions from a 120mm circular fan mount to a rectangular chimney connector. Designed for smooth airflow with no internal sharp corners.

<img src="img/curved_intake_duct.png" width="300">

*   **Key Parameters:**
    *   `ancho_placa_base`: Width of the fan mounting plate (120mm for Bosser fans).
    *   `altura_saxofon`: Vertical height of the transition.
    *   `desplazamiento_y`: Lateral offset between the fan center and chimney center.
    *   `rect_x` / `rect_y`: Dimensions of the rectangular exit to match the chimney.

### 2. Airflow Chimney Duct (`airflow_chimney_duct.scad` / `_2levels.stl` / `_3levels.stl`)
A modular, stackable vertical duct. Each module features segmented vents ("branquias") angled at 45° to project air towards the routers without requiring print supports.

<img src="img/airflow_chimney_duct_3levels.png" width="300" height="273"> <img src="img/airflow_chimney_duct_2levels.png" width="300">

*   **Key Parameters:**
    *   `niveles_por_modulo`: Number of cooling levels in the segment (set to 2 or 3 for the provided STLs).
    *   `dist_niveles`: Vertical distance between levels (60mm).
    *   `tolerancia`: Clearance for the male/female stacking connectors.
    *   `grosor_pared`: Wall thickness for structural rigidity.

### 3. Chimney End Cap (`chimney_duct_cover.scad` / `.stl`)
A simple female-connector cap that fits onto the top of the last chimney segment to seal the system.

<img src="img/chimney_duct_cover.png" width="300">

*   **Key Parameters:**
    *   `grosor_pared`: Wall thickness.
    *   `tolerancia`: Fitting tolerance for the male connector.

### 4. Drawer Stop (`drawer_stop.f3d` / `.stl`)
Customized drawer stops designed in Autodesk Fusion 360. These parts are intended to be glued into U-shaped notches cut into the original plastic drawers using a Dremel rotary tool. Each stop features a base opening that allows the vertical chimney duct to pass through all levels, providing structural stability to the chimney while acting as a lock to prevent the drawers from opening accidentally.

<img src="img/drawer_stop.png" width="300">

### 5. Belkin RT3200 Base (`belkin_rt3200_base.stl`)
The original cases for the Belkin RT3200 routers were too large for the rack chassis. We replaced them with a 3D-printed base to save space and ensure the routers remain fixed when connecting or disconnecting cables. This design is an adaptation of the [RT3200/E8450 Wall Mount Case](https://www.thingiverse.com/thing:5864938) by Thingiverse user **TuxInvader**. We utilized only the base component, leaving the top of the router uncovered for optimal cooling.

<img src="img/belkin_case_adapted.jpg" width="300">

### 6. Auxiliary and Decorative Parts
*   **USB Hub Shelf (`hub_shelf_TP-LINK_UH700.stl`):** A custom shelf designed to securely house the TP-Link UH700 USB hub within the rack.

<img src="img/hub_shelf.jpg" width="300">

*   **Arduino Nano Holder (`NanoHolderA.stl`):** A small mounting bracket to keep the Arduino Nano fixed in its designated drawer level.

<img src="img/NanoHolder.jpg" width="300">

*   **FCEFyN & UNC Logos:** Decorative 3D-printed logos used as final aesthetic details, representing FCEFyN and UNC.

<img src="img/logos.png" width="300">

---
*Note: All OpenSCAD models are designed to be printed without supports when oriented correctly on the build plate. All models were printed in a Creality Ender 3 Pro printer*
