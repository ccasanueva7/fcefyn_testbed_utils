// tubo.scad - CORREGIDO PARA ENCASTRE Y FUSIÓN
$fn = 80;

niveles_por_modulo = 2; 
dist_niveles = 60;
altura_cuerpo = niveles_por_modulo * dist_niveles; 

rect_x = 134.7; 
rect_y = 32;    
radio_final = 8;
grosor_pared = 2.0;
tolerancia = 0.5; // Aumentada ligeramente para facilitar encastre

chimenea_larga();

module chimenea_larga() {
    union() {
        difference() {
            // --- CUERPO EXTERIOR ---
            union() {
                // 1. Zócalo Hembra inferior (Reforzado y más ancho)
                linear_extrude(20) 
                    offset(r = grosor_pared + tolerancia) perfil_rect(0);
                
                // 2. Cuerpo principal (Ahora nace desde Z=0 para una fusión total)
                linear_extrude(altura_cuerpo) 
                    perfil_rect(0);
            }
            
            // --- VACIADO INTERIOR ---
            union() {
                // 3. HUECO HEMBRA (Ajustado para el saxofón ya impreso)
                // Usamos '+' tolerancia para que el hueco sea más grande que el macho
                translate([0,0,-1]) 
                    linear_extrude(16) 
                        perfil_rect(tolerancia); 
                
                // 4. RAMPA DE TRANSICIÓN (Aerodinámica y anti-soporte)
                hull() {
                    translate([0,0,15]) linear_extrude(0.1) perfil_rect(tolerancia);
                    translate([0,0,15 + 10]) linear_extrude(0.1) perfil_rect(-grosor_pared);
                }
                
                // 5. TÚNEL DE AIRE SUPERIOR
                translate([0,0,15 + 10]) 
                    linear_extrude(altura_cuerpo + 10) perfil_rect(-grosor_pared);
            }
            
            // --- BRANQUIAS SEGMENTADAS ---
            for(nivel = [0 : niveles_por_modulo - 1]) {
                z_base = nivel * dist_niveles;
                for(j = [0:2], c = [0:3]) { 
                    x_pos = - (rect_x-40)/2 + c*((rect_x-40)/4) + (rect_x-40)/8;
                    translate([x_pos, rect_y/2, z_base + 25 + j*12])
                        rotate([45, 0, 0]) 
                            cube([(rect_x-40)/4 - 2, 25, 8], center=true);
                }
            }
        }

        // --- CONECTOR MACHO SUPERIOR ---
        // Para seguir apilando más tubos
        translate([0, 0, altura_cuerpo]) {
            difference() {
                linear_extrude(15) perfil_rect(-tolerancia/2); 
                translate([0,0,-1]) linear_extrude(17) perfil_rect(-grosor_pared);
            }
        }
    }
}

module perfil_rect(extra) {
    offset(r = radio_final + extra) 
        square([rect_x - 2*radio_final, rect_y - 2*radio_final], center = true);
}