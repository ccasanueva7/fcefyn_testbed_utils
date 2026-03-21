// --- PARÁMETROS FINALES (COMPATIBLE CON TUBO.SCAD) ---
$fn = 80;

// Medidas cooler Bosser
ancho_placa_base = 120.0;     
distancia_agujeros_base = 105.0; 
diametro_tornillo = 4.5;
cooler_diam_interno = 116.0; 

// Medidas salida (Coincidentes con tubo.scad)
rect_x = 134.7;
rect_y = 32;
radio_final = 8; 

// Trayecto
altura_saxofon = 105;   // Altura de la curva
desplazamiento_y = 130; 
grosor_pared = 2.0;     // Pared robusta para mejor impresión
tolerancia = 0.4;       // Misma tolerancia que en tubo.scad

// --- MOTOR DE GENERACIÓN ---

module perfil_interpolado(t, offset_manual) {
    ease = t * t * (3 - 2 * t); 
    z_pos = t * altura_saxofon;
    y_pos = ease * desplazamiento_y;

    // Flare inferior (solo en la base del cooler)
    max_flare_inf = (ancho_placa_base - cooler_diam_interno) / 2;
    flare_inf = (t < 0.15) ? (1 - t/0.15) * max_flare_inf : 0;

    radio_actual = (cooler_diam_interno/2) * (1 - ease) + radio_final * ease;
    
    size_x = (cooler_diam_interno - 2*(cooler_diam_interno/2)) * (1 - ease) + (rect_x - 2*radio_final) * ease;
    size_y = (cooler_diam_interno - 2*(cooler_diam_interno/2)) * (1 - ease) + (rect_y - 2*radio_final) * ease;

    translate([0, y_pos, z_pos]) {
        linear_extrude(height = 0.1) {
            offset(r = radio_actual + offset_manual + flare_inf) {
                square([max(0.01, size_x), max(0.01, size_y)], center = true);
            }
        }
    }
}

module generar_loft(extra_offset) {
    pasos = 60; 
    for (i = [0 : pasos - 1]) {
        hull() {
            perfil_interpolado(i / pasos, extra_offset);
            perfil_interpolado((i + 1) / pasos, extra_offset);
        }
    }
}

// --- ENSAMBLE ---

union() {
    // 1. CUERPO CURVO (Saxofón)
    difference() {
        generar_loft(grosor_pared/2);
        generar_loft(-grosor_pared/2);
    }

    // 2. CONECTOR MACHO (Para encastrar en tubo.scad)
    // Se posiciona al final de la curva
    translate([0, desplazamiento_y, altura_saxofon]) {
        difference() {
            // El macho debe ser ligeramente más pequeño que el hueco hembra
            linear_extrude(15) 
                offset(r = radio_final - tolerancia/2) 
                    square([rect_x - 2*radio_final, rect_y - 2*radio_final], center = true);
            
            // Hueco interno para el aire
            translate([0,0,-1])
                linear_extrude(17) 
                    offset(r = radio_final - grosor_pared) 
                        square([rect_x - 2*radio_final, rect_y - 2*radio_final], center = true);
        }
    }

    // 3. PLACA BASE (Lado Ventilador)
    color("DarkSlateGray")
    difference() {
        translate([0, 0, 1])
            cube([ancho_placa_base, ancho_placa_base, 2], center = true);
        
        generar_loft(extra_offset = -grosor_pared/2);
        
        for(x=[-1,1], y=[-1,1]) 
            translate([x*distancia_agujeros_base/2, y*distancia_agujeros_base/2, -1]) 
                cylinder(d = diametro_tornillo, h = 5);
    }
}