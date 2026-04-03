---
title: DIY Rack
---

# DIY Rack

Overview of the lab's **DIY rack** consisting of:

* **Stackable plastic drawers**
* **Multiple 3D printed parts** (ventilation ducts and cases for devices) - CAD sources [`here`](https://github.com/fcefyn-testbed/fcefyn_testbed_utils/tree/main/3d_parts)
* **AC control box interface** for control of devices via SSR relays - electrical schematics can be found in [here](../configuracion/arduino-relay.md).


## Rack photos

<div class="rack-gallery" data-rack-gallery tabindex="0">
  <div class="rack-gallery__viewport">
    <figure class="rack-gallery__slide" data-caption="Tower rack overview: drawers, cabling, and gear per shelf.">
      <img src="../../img/rack/rack.png" alt="Tower rack with plastic drawers and cabling" loading="lazy" decoding="async">
    </figure>
    <figure class="rack-gallery__slide" data-caption="Initial bench setup: routers, USB hub, relays, and wiring before rack integration.">
      <img src="../../img/rack/starting_point.jpg" alt="Bench test setup with routers and relays" loading="lazy" decoding="async">
    </figure>
    <figure class="rack-gallery__slide" data-caption="Inside a drawer: USB hub, relay module, and cable routing.">
      <img src="../../img/rack/rack_2nd_level.jpg" alt="Rack drawer with USB hub and relays" loading="lazy" decoding="async">
    </figure>
    <figure class="rack-gallery__slide" data-caption="Upper drawers open: PSU, hub, and inter-level wiring.">
      <img src="../../img/rack/rack_1st_2nd_level.jpg" alt="Two rack levels open with PSU and wiring" loading="lazy" decoding="async">
    </figure>
    <div class="rack-gallery__overlay">
      <span class="rack-gallery__counter" data-rack-counter aria-live="polite"></span>
      <button type="button" class="rack-gallery__btn" data-rack-prev aria-label="Previous image">&#8249;</button>
      <button type="button" class="rack-gallery__btn" data-rack-next aria-label="Next image">&#8250;</button>
    </div>
  </div>
  <p class="rack-gallery__caption" data-rack-caption></p>
</div>

## AC Control box

Separate box from the rack: relays/SSR, **UTP** (signals) and **230 V** to cooler and PSU. Detailed wiring schematics [here](../configuracion/arduino-relay.md#electrical-schematics-reference).


<div class="rack-gallery" data-rack-gallery tabindex="0">
  <div class="rack-gallery__viewport">
    <figure class="rack-gallery__slide" data-caption="Relay module enclosure (control box) exterior.">
      <img src="../../img/rack/reles_box_1.jpg" alt="Relay module enclosure exterior" loading="lazy" decoding="async">
    </figure>
    <figure class="rack-gallery__slide" data-caption="Interior: Arduino, relays/SSR, wiring to terminals and UTP.">
      <img src="../../img/rack/reles_box_inside.jpg" alt="Relay box interior" loading="lazy" decoding="async">
    </figure>
    <div class="rack-gallery__overlay">
      <span class="rack-gallery__counter" data-rack-counter aria-live="polite"></span>
      <button type="button" class="rack-gallery__btn" data-rack-prev aria-label="Previous image">&#8249;</button>
      <button type="button" class="rack-gallery__btn" data-rack-next aria-label="Next image">&#8250;</button>
    </div>
  </div>
  <p class="rack-gallery__caption" data-rack-caption></p>
</div>

## Thermal considerations and ventilation {: #thermal-considerations }

With vertical stacking, hot air from lower levels **rises** and tends to stagnate at the top, risking overheating of upper equipment. Mitigation is a **bottom fan** (120 mm, 220 V) pushing **cold air upward** and **printed ducts** guiding flow toward the drawers. Fan datasheet: [Hardware catalog - Bosser 120 mm](../configuracion/catalogo-hardware.md#bosser-120mm-rack-fan).

## 3D printed parts

Renders and photos of parts used for ducts, bases, and accessories. Models aim for **support-free** printing where applicable (printer used was a Creality Ender 3 Pro).

| Qty | STL file | Use |
|-----|----------|-----|
| 1   | `curved_intake_duct.stl` | Curved duct: 120 mm fan to chimney |
| 4   | `airflow_chimney_duct_3levels.stl` | Vertical segments with grilles (3 levels each) |
| 1   | `airflow_chimney_duct_2levels.stl` | Segment with 2 levels |
| 1   | `chimney_duct_cover.stl` | Chimney top cover |
| 3   | `belkin_rt3200_base.stl` | Compact Belkin RT3200 base |
| 1   | `CE3PRO_librerouter_rack.stl` | Open LibreRouter enclosure (vented base, standoffs) |
| 1   | `NanoHolderA.stl` | Arduino Nano holder |
| 1   | (aux.) `drawer_stop` | Drawer guide / stop (visual asset; filename per `3d_parts/`) |
| 1   | `logo fcefyn.stl`, `logo unc.stl` | Decorative logos |

<div class="rack-gallery rack-gallery--schematics" data-rack-gallery tabindex="0">
  <div class="rack-gallery__viewport">
    <figure class="rack-gallery__slide" data-caption="Curved intake duct (OpenSCAD render / reference).">
      <img src="../../img/rack/curved_intake_duct.png" alt="Curved intake duct render" loading="lazy" decoding="async">
    </figure>
    <figure class="rack-gallery__slide" data-caption="3-level chimney module (grilles toward routers).">
      <img src="../../img/rack/airflow_chimney_duct_3levels.png" alt="Three-level chimney render" loading="lazy" decoding="async">
    </figure>
    <figure class="rack-gallery__slide" data-caption="2-level chimney module.">
      <img src="../../img/rack/airflow_chimney_duct_2levels.png" alt="Two-level chimney render" loading="lazy" decoding="async">
    </figure>
    <figure class="rack-gallery__slide" data-caption="Chimney top cover.">
      <img src="../../img/rack/chimney_duct_cover.png" alt="Chimney cover render" loading="lazy" decoding="async">
    </figure>
    <figure class="rack-gallery__slide" data-caption="120 mm fan with curved duct mounted (photo).">
      <img src="../../img/rack/cooler_with_duct.jpeg" alt="Fan with curved duct mounted" loading="lazy" decoding="async">
    </figure>
    <figure class="rack-gallery__slide" data-caption="Printed Belkin RT3200 base in rack.">
      <img src="../../img/rack/belkin_case_adapted.jpg" alt="Adapted Belkin base in rack" loading="lazy" decoding="async">
    </figure>
    <figure class="rack-gallery__slide" data-caption="Open LibreRouter enclosure.">
      <img src="../../img/rack/librerouter-opencase.jpeg" alt="Open LibreRouter enclosure" loading="lazy" decoding="async">
    </figure>
    <figure class="rack-gallery__slide" data-caption="Arduino Nano holder (NanoHolder).">
      <img src="../../img/rack/NanoHolder.jpg" alt="Printed Nano holder" loading="lazy" decoding="async">
    </figure>
    <figure class="rack-gallery__slide" data-caption="FCEFyN and UNC logos.">
      <img src="../../img/rack/logos.png" alt="FCEFyN and UNC logos" loading="lazy" decoding="async">
    </figure>
    <div class="rack-gallery__overlay">
      <span class="rack-gallery__counter" data-rack-counter aria-live="polite"></span>
      <button type="button" class="rack-gallery__btn" data-rack-prev aria-label="Previous image">&#8249;</button>
      <button type="button" class="rack-gallery__btn" data-rack-next aria-label="Next image">&#8250;</button>
    </div>
  </div>
  <p class="rack-gallery__caption" data-rack-caption></p>
</div>

The Belkin base was adapted from [RT3200/E8450 Wall Mount Case](https://www.thingiverse.com/thing:5864938) (TuxInvader): base only, open top for ventilation.
