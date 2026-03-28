---
title: Rack físico
---

# Rack físico

Vista general del **rack DIY** del lab: cajoneras, caja de control, enlace a esquemáticos eléctricos en [arduino-relay](../configuracion/arduino-relay.md) y piezas impresas para conductos y soportes. Fuentes CAD: carpeta **`3d_parts/`** en la raíz del repo (OpenSCAD homónimo del STL cuando aplica).

## Fotos del rack

<div class="rack-gallery" data-rack-gallery tabindex="0">
  <div class="rack-gallery__viewport">
    <figure class="rack-gallery__slide" data-caption="Vista general del rack en torre: cajoneras, cableado y equipos por cajón.">
      <img src="../../img/rack/rack.png" alt="Rack en torre con cajoneras plásticas y cableado" loading="lazy" decoding="async">
    </figure>
    <figure class="rack-gallery__slide" data-caption="Montaje inicial en mesa: routers, hub USB, relés y cableado antes de integrar al rack.">
      <img src="../../img/rack/starting_point.jpg" alt="Banco de pruebas en mesa con routers y relés" loading="lazy" decoding="async">
    </figure>
    <figure class="rack-gallery__slide" data-caption="Interior de un cajón: hub USB, módulo de relés y distribución de cables.">
      <img src="../../img/rack/rack_2nd_level.jpg" alt="Cajón del rack con hub USB y relés" loading="lazy" decoding="async">
    </figure>
    <figure class="rack-gallery__slide" data-caption="Cajones superiores abiertos: fuente, hub y cableado entre niveles.">
      <img src="../../img/rack/rack_1st_2nd_level.jpg" alt="Dos niveles del rack abiertos con fuente y cableado" loading="lazy" decoding="async">
    </figure>
    <div class="rack-gallery__overlay">
      <span class="rack-gallery__counter" data-rack-counter aria-live="polite"></span>
      <button type="button" class="rack-gallery__btn" data-rack-prev aria-label="Imagen anterior">&#8249;</button>
      <button type="button" class="rack-gallery__btn" data-rack-next aria-label="Imagen siguiente">&#8250;</button>
    </div>
  </div>
  <p class="rack-gallery__caption" data-rack-caption></p>
</div>

## Caja de control (módulo de relés)

Caja aparte del rack: relés/SSR, **UTP** (señal) y **230 V** hacia cooler y fuente. Detalle eléctrico: [arduino-relay](../configuracion/arduino-relay.md).

<div class="rack-gallery" data-rack-gallery tabindex="0">
  <div class="rack-gallery__viewport">
    <figure class="rack-gallery__slide" data-caption="Caja externa del módulo de relés (caja de control).">
      <img src="../../img/rack/reles_box_1.jpg" alt="Caja de módulo de relés vista exterior" loading="lazy" decoding="async">
    </figure>
    <figure class="rack-gallery__slide" data-caption="Interior: Arduino, relés/SSR y cableado a bornes y UTP.">
      <img src="../../img/rack/reles_box_inside.jpg" alt="Interior de la caja de relés" loading="lazy" decoding="async">
    </figure>
    <div class="rack-gallery__overlay">
      <span class="rack-gallery__counter" data-rack-counter aria-live="polite"></span>
      <button type="button" class="rack-gallery__btn" data-rack-prev aria-label="Imagen anterior">&#8249;</button>
      <button type="button" class="rack-gallery__btn" data-rack-next aria-label="Imagen siguiente">&#8250;</button>
    </div>
  </div>
  <p class="rack-gallery__caption" data-rack-caption></p>
</div>

## Conexiones y cableado eléctrico {: #conexiones-y-cableado-electrico }

Los esquemáticos de referencia están en [arduino-relay - Esquemas eléctricos](../configuracion/arduino-relay.md#esquemas-electricos-referencia) junto con tablas de pines y comandos serial.

## Consideraciones térmicas y ventilación {: #consideraciones-termicas }

Con el apilado vertical, el aire caliente de los niveles inferiores **asciende** y tiende a estancarse arriba, con riesgo de sobrecalentamiento en los equipos superiores. La mitigación es un **ventilador inferior** (120 mm, 220 V) que empuja aire **frío de abajo hacia arriba** y **conductos impresos** que encaminan el flujo hacia los cajones. Ficha del ventilador: [Catálogo - Bosser 120 mm](../configuracion/catalogo-hardware.md#ventilador-bosser-120-mm-rack).

## Piezas impresas en 3D

Renders y fotos de las piezas usadas en conductos, bases y accesorios. Modelos orientados a imprimir **sin soportes** cuando corresponde (referencia: Creality Ender 3 Pro).

| Cantidad | Archivo STL | Uso |
|----------|-------------|-----|
| 1 | `curved_intake_duct.stl` | Conducto curvo: ventilador 120 mm → chimenea |
| 4 | `airflow_chimney_duct_3levels.stl` | Segmentos verticales con rejillas (3 niveles c/u) |
| 1 | `airflow_chimney_duct_2levels.stl` | Segmento con 2 niveles |
| 1 | `chimney_duct_cover.stl` | Tapa superior de la chimenea |
| 3 | `belkin_rt3200_base.stl` | Base compacta Belkin RT3200 |
| 1 | `CE3PRO_librerouter_rack.stl` | Carcasa abierta LibreRouter (base ventilada, standoffs) |
| 1 | `NanoHolderA.stl` | Soporte Arduino Nano |
| 1 | (aux.) `drawer_stop` | Guía / tope de cajón (asset visual; nombre de archivo según `3d_parts/`) |
| (var.) | `logo fcefyn.stl`, `logo unc.stl` | Logos decorativos |

<div class="rack-gallery rack-gallery--schematics" data-rack-gallery tabindex="0">
  <div class="rack-gallery__viewport">
    <figure class="rack-gallery__slide" data-caption="Conducto de admisión curvado (render OpenSCAD / referencia).">
      <img src="../../img/rack/curved_intake_duct.png" alt="Render conducto admisión curvado" loading="lazy" decoding="async">
    </figure>
    <figure class="rack-gallery__slide" data-caption="Módulo chimenea 3 niveles (rejillas orientadas a los routers).">
      <img src="../../img/rack/airflow_chimney_duct_3levels.png" alt="Render chimenea tres niveles" loading="lazy" decoding="async">
    </figure>
    <figure class="rack-gallery__slide" data-caption="Módulo chimenea 2 niveles.">
      <img src="../../img/rack/airflow_chimney_duct_2levels.png" alt="Render chimenea dos niveles" loading="lazy" decoding="async">
    </figure>
    <figure class="rack-gallery__slide" data-caption="Tapa superior de chimenea.">
      <img src="../../img/rack/chimney_duct_cover.png" alt="Render tapa chimenea" loading="lazy" decoding="async">
    </figure>
    <figure class="rack-gallery__slide" data-caption="Ventilador 120 mm con conducto curvo montado (foto).">
      <img src="../../img/rack/cooler_with_duct.jpeg" alt="Ventilador con conducto curvo montado" loading="lazy" decoding="async">
    </figure>
    <figure class="rack-gallery__slide" data-caption="Base impresa Belkin RT3200 en el rack.">
      <img src="../../img/rack/belkin_case_adapted.jpg" alt="Base Belkin adaptada en rack" loading="lazy" decoding="async">
    </figure>
    <figure class="rack-gallery__slide" data-caption="Carcasa abierta LibreRouter.">
      <img src="../../img/rack/librerouter-opencase.jpeg" alt="Carcasa abierta LibreRouter" loading="lazy" decoding="async">
    </figure>
    <figure class="rack-gallery__slide" data-caption="Soporte Arduino Nano (NanoHolder).">
      <img src="../../img/rack/NanoHolder.jpg" alt="Soporte Nano impreso" loading="lazy" decoding="async">
    </figure>
    <figure class="rack-gallery__slide" data-caption="Logos FCEFyN y UNC.">
      <img src="../../img/rack/logos.png" alt="Logos FCEFyN y UNC" loading="lazy" decoding="async">
    </figure>
    <div class="rack-gallery__overlay">
      <span class="rack-gallery__counter" data-rack-counter aria-live="polite"></span>
      <button type="button" class="rack-gallery__btn" data-rack-prev aria-label="Imagen anterior">&#8249;</button>
      <button type="button" class="rack-gallery__btn" data-rack-next aria-label="Imagen siguiente">&#8250;</button>
    </div>
  </div>
  <p class="rack-gallery__caption" data-rack-caption></p>
</div>

La base Belkin deriva de [RT3200/E8450 Wall Mount Case](https://www.thingiverse.com/thing:5864938) (TuxInvader): solo la base, parte superior abierta para ventilación.
