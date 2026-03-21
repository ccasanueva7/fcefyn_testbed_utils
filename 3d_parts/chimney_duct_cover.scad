// TAPA_FINAL_CHIMENEA.scad
// Diseñada para cerrar el sistema modular y forzar el flujo de aire por las branquias.
$fn = 80;

// Medidas coincidentes con tubo.scad para un encastre perfecto
rect_x = 134.7; 
rect_y = 32;    
radio_final = 8;
grosor_pared = 2.0;
tolerancia = 0.5; 

tapa_chimenea();

module tapa_chimenea() {
    color("IndianRed")
    union() {
        // 1. PLACA SUPERIOR (El techo que sella el tubo)
        // La hacemos un poco más ancha para que sea fácil de agarrar
        linear_extrude(3) 
            offset(r = grosor_pared + tolerancia + 1) 
                perfil_rect(0);
        
        // 2. FALDA DE ENCASTRE (Hembra)
        // Esta parte abraza el conector macho superior del último tubo
        translate([0, 0, -15]) {
            difference() {
                // Exterior de la falda
                linear_extrude(15) 
                    offset(r = grosor_pared + tolerancia) 
                        perfil_rect(0);
                
                // Hueco interno (Hembra)
                // Usamos la misma lógica de tolerancia que en la base del tubo
                translate([0, 0, -1]) 
                    linear_extrude(17) 
                        perfil_rect(tolerancia);
            }
        }
    }
}

module perfil_rect(extra) {
    offset(r = radio_final + extra) 
        square([rect_x - 2*radio_final, rect_y - 2*radio_final], center = true);
}