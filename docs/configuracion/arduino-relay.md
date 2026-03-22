# Control de Relés Arduino - Laboratorio FCEFyN

Interfaz de control de potencia automatizada mediante USB-Serial (115200 baudios). Gestiona el encendido de DUTs y de la infraestructura del rack (switch, cooler, fuente).

---

## Índice

1. [Descripción del sistema](#1-descripcion-del-sistema)
2. [Hardware y asignación de canales](#2-hardware-y-asignacion-de-canales)
3. [Esquema de conexión física](#3-esquema-de-conexion-fisica-caja-de-reles)
4. [Cableado de señal (UTP)](#4-cableado-de-senal-utp)
5. [Comandos serial](#5-comandos-serial)
6. [Arduino Relay Daemon](#6-arduino-relay-daemon-arduino_daemonpy)
7. [Resolución del symlink](#7-resolucion-del-symlink)

---

## 1. Descripción del sistema

El Arduino Nano recibe comandos por USB-Serial y controla 11 canales digitales:

- **Canales 0-7:** Relés electromecánicos (módulo KY-019) para DUTs.
- **Canales 8-10:** Relés de estado sólido (SSR) para infraestructura del rack.

El puerto serial se expone como `/dev/arduino-relay` (symlink udev). El daemon `arduino_daemon.py` mantiene una conexión persistente para evitar resets al abrir/cerrar el puerto. El script `arduino_relay_control.py` envía comandos al daemon o directamente al puerto.

---

## 2. Hardware y asignación de canales

### 2.1 Infraestructura (SSR)

| Canal | Pin | Dispositivo | Hardware | Lógica |
|-------|-----|-------------|----------|--------|
| **8** | D10 | Switch TP-Link SG2016P | Módulo SSR 4 canales, CH1 | Activo-bajo |
| **9** | D11 | Cooler Booster AC | Módulo SSR 4 canales, CH2 | Activo-bajo |
| **10** | D12 | Fuente de alimentación | Fotek SSR-25DA (individual) | **Activo-alto** |

**Nota:** El canal 10 usa lógica invertida (HIGH = ON). Los canales 0-9 usan activo-bajo (LOW = ON).

### 2.2 DUTs (relés mecánicos)

| Canales | Pines | Hardware |
|---------|-------|---------|
| 0-7 | D2-D9 | Módulo KY-019 de 8 relés electromecánicos |

### 2.3 Especificaciones del hardware

**Módulo SSR 4 canales** (Switch, Cooler):

- Tipo: Relé de estado sólido SSR de 4 canales.
- Referencia: [Módulo SSR 4ch](https://www.mercadolibre.com.ar/modulo-de-rele-de-estado-solido-ssr-de-4-canales/p/MLA49603394).
- En uso: CH1 (Switch), CH2 (Cooler). Canales 3 y 4 disponibles.

**SSR individual Fotek SSR-25DA** (Fuente):

- Tipo: Relé de estado sólido CC a CA, alto voltaje.
- Referencia: [Fotek SSR-25DA](https://www.mercadolibre.com.ar/rele-de-estado-solido-fotek-ssr25da/up/MLAU3109910670).
- Entrada: 4-32 VDC.
- Salida: 90-480 VAC, 25 A máx.

**Cajas de tomas:**

- Llave Luz Armada Richi Quantum ERA 2 Tomas 3 Módulos Blanco PVC (corte de fase para seguridad).

**Fuente de alimentación (carga del canal 10):**

| Especificación | Valor |
|----------------|-------|
| Marca/Modelo | Coper Light Metálica |
| Potencia | 480 W |
| Entrada | 12-110 VAC, 50/60 Hz |
| Salida | 12-220 V |
| Temperatura de funcionamiento | 0-40 °C |
| Protección | Cortocircuito |

### 2.4 Carga AC del módulo SSR e inrush

- El corte en 230 V es solo sobre la **fase** (detalle en la sección 3 más abajo).
- El módulo SSR de 4 canales (switch / cooler) suele especificar del orden de **~2 A máximo por canal**; las cargas con **corriente de arranque alta (inrush)** pueden superar ese pico un instante. En este rack se evitó alimentar por ese módulo una fuente de **~495 W** por ese motivo.
- Switch SG2016P y cooler Booster AC quedaron acotados a carga acorde al canal usado.

### 2.5 Seguridad operativa (infra SSR / UTP)

1. El equipo desde el que administrás el lab (SSH, etc.) **no** debería depender solo del switch que cortás por el relé SSR, para no quedar sin acceso si apagás la red de gestión.
2. No encintar el UTP de señal (≈2 m) junto a cableado de **230 V** en tramos largos si se puede evitar.
3. Verificar **masa común**: GND del Arduino, hilos de retorno del UTP hacia DC− del módulo y negativo del cargador 5 V del lado del módulo.

---

## 3. Esquema de conexión física (caja de relés)

Corte de **fase** para seguridad industrial:

- **Fase (marrón/rojo):** Pared → Borne 1 Relé → Borne 2 Relé → Borne "L" Toma.
- **Neutro (celeste/azul):** Pared → Borne "N" Toma (directo).
- **Tierra (verde/amarillo):** Pared → Borne central Toma (directo).

---

## 4. Cableado de señal (UTP)

Cable UTP Cat5e/6 de 2 m para señales y masa común (GND).

| Par | Color | Función | Pin Arduino | Borne relé |
|-----|-------|---------|-------------|------------|
| Naranja | Naranja | Señal Switch | D10 | CH1 (SSR 4ch) |
| | Blanco/Naranja | GND | GND | DC- |
| Verde | Verde | Señal Cooler | D11 | CH2 (SSR 4ch) |
| | Blanco/Verde | GND | GND | DC- |
| Marrón | Marrón | Señal Fuente | D12 | Borne 3 (Fotek) |
| | Blanco/Marrón | GND | GND | Borne 4 (Fotek) |

---

## 5. Comandos serial

Baudrate: **115200** bps.

| Comando | Descripción | Ejemplo |
|---------|-------------|---------|
| `ON n [n ...]` | Enciende uno o más canales | `ON 8 9 10` |
| `OFF n [n ...]` | Apaga uno o más canales | `OFF 10` |
| `TOGGLE n [n ...]` | Alterna estado | `TOGGLE 8` |
| `PULSE n ms` | Pulso de ms milisegundos | `PULSE 0 500` |
| `ALLON` | Enciende todos los canales | |
| `ALLOFF` | Apaga todos los canales | |
| `STATUS` | Estado de los 11 canales | |
| `HELP` | Ayuda | |
| `ID` | Identificación del dispositivo | |

**Ejemplos de uso:**

```bash
# Encender infraestructura (switch, cooler, fuente)
arduino_relay_control.py on 8 9 10

# Apagar solo la fuente
arduino_relay_control.py off 10

# Power cycle de un DUT (canal 0)
arduino_relay_control.py pulse 0 3000

# Ver estado
arduino_relay_control.py status
```

**Uso directo por serial** (sin daemon):

```bash
stty -F /dev/arduino-relay 115200 raw -echo
echo "ON 8 9 10" > /dev/arduino-relay
```

---

## 6. Arduino Relay Daemon (`arduino_daemon.py`)

Para evitar que el Arduino se reinicie cada vez que se abre una conexión serial (el bootloader se activa al detectar apertura/cierre del puerto), el daemon mantiene una conexión persistente. Escucha en el socket Unix `/tmp/arduino-relay.sock`; cuando está corriendo, `arduino_relay_control.py` lo detecta y envía comandos por ahí en vez de abrir el puerto serial. PDUDaemon llama a `arduino_relay_control.py`; si el daemon está activo, no hay resets innecesarios.

### 6.1 Servicio systemd (recomendado)

Arranque automático al boot, reinicio si se cae.

Origen del unit: `configs/templates/arduino-relay-daemon.service` (dentro del repo fcefyn-testbed-utils). Destino: `/etc/systemd/system/`.

```bash
# Desde la raíz de fcefyn-testbed-utils:
sudo cp scripts/arduino/arduino_daemon.py /usr/local/bin/
sudo chmod +x /usr/local/bin/arduino_daemon.py
sudo cp configs/templates/arduino-relay-daemon.service /etc/systemd/system/

sudo systemctl daemon-reload
sudo systemctl enable arduino-relay-daemon
sudo systemctl start arduino-relay-daemon
```

### 6.2 Alternativa manual (pruebas)

```bash
./scripts/arduino/start_daemon.sh

# O manualmente:
python3 scripts/arduino/arduino_daemon.py start --port /dev/arduino-relay
```

**Comandos:** `start`, `stop`, `status`. Archivos generados: PID en `/tmp/arduino-relay.pid`, socket en `/tmp/arduino-relay.sock`, log en `/tmp/arduino-daemon.log` si se usa `start_daemon.sh`.

---

## 7. Resolución del symlink

Para saber a qué `/dev/ttyUSB*` apunta el symlink:

```bash
readlink -f /dev/arduino-relay
```