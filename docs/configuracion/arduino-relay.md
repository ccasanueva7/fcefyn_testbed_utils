# Control de Relés mediante microcontrolador Arduino

Interfaz de control de potencia automatizada por USB-Serial (**115200** baudios): DUTs e infraestructura del rack (switch, cooler, fuente).

## 1. Descripción del sistema

El Arduino Nano controla **11 canales** por USB-Serial. Puerto: `/dev/arduino-relay` (udev). El daemon `arduino_daemon.py` mantiene serial abierto para evitar resets del bootloader; `arduino_relay_control.py` habla con el daemon o con el puerto.

| Rango | Rol |
|-------|-----|
| 0-7 | Relés electromecánicos (módulo 8 ch, 5 V, opto) para DUTs |
| 8-10 | SSR: infraestructura (switch, cooler, fuente) |

## 2. Hardware y asignación de canales

**Fotos de módulos y PSU del canal 10:** [Catálogo de hardware - Relés Arduino](catalogo-hardware.md#reles-arduino-rack) y [Fuente AC (canal 10)](catalogo-hardware.md#fuente-ac-carga-canal-10).

### 2.1 Infraestructura (SSR)

| Canal | Pin | Dispositivo | Hardware | Lógica |
|-------|-----|-------------|----------|--------|
| **8** | D10 | Switch TP-Link SG2016P | Módulo SSR 4 canales, CH1 | Activo-bajo |
| **9** | D11 | Cooler Booster AC | Módulo SSR 4 canales, CH2 | Activo-bajo |
| **10** | D12 | Fuente de alimentación | Fotek SSR-25DA (individual) | **Activo-alto** |

!!! note "Polaridad de los canales"
    Canal 10: HIGH = ON. Canales 0-9: LOW = ON.

### 2.2 DUTs (relés mecánicos)

| Canales | Pines | Hardware |
|---------|-------|---------|
| 0-7 | D2-D9 | Módulo de 8 relés electromecánicos (5 V DC, optoacoplado) |

### 2.3 Especificaciones de los módulos

Tablas de fabricante, límites de carga y datos de placa: [Catálogo de hardware - Relés Arduino](catalogo-hardware.md#reles-arduino-rack).

## 3. Esquema de conexión física (caja de relés)

Corte de **fase** (seguridad industrial):

| Conductor | Recorrido |
|-----------|-----------|
| Fase (marrón/rojo) | Pared → Borne 1 relé → Borne 2 relé → borne "L" toma |
| Neutro (celeste/azul) | Pared → borne "N" toma (directo) |
| Tierra (verde/amarillo) | Pared → borne central toma (directo) |

## 4. Cableado de señal (UTP)

UTP Cat5e/6, ~2 m: señales y GND común.

| Par | Color | Función | Pin Arduino | Borne relé |
|-----|-------|---------|-------------|------------|
| Naranja | Naranja | Señal switch | D10 | CH1 (SSR 4ch) |
| | Blanco/Naranja | GND | GND | DC- |
| Verde | Verde | Señal cooler | D11 | CH2 (SSR 4ch) |
| | Blanco/Verde | GND | GND | DC- |
| Marrón | Marrón | Señal fuente | D12 | Borne 3 (Fotek) |
| | Blanco/Marrón | GND | GND | Borne 4 (Fotek) |

## 5. Comandos serial

Baudrate: **115200** bps.

| Comando | Descripción | Ejemplo |
|---------|-------------|---------|
| `ON n [n ...]` | Enciende canal(es) | `ON 8 9 10` |
| `OFF n [n ...]` | Apaga | `OFF 10` |
| `TOGGLE n [n ...]` | Alterna | `TOGGLE 8` |
| `PULSE n ms` | Pulso ms | `PULSE 0 500` |
| `ALLON` / `ALLOFF` | Todos on/off | |
| `STATUS` | Estado 11 canales | |
| `HELP` / `ID` | Ayuda / ID | |

```bash
# Con arduino_relay_control.py (usa daemon si está activo)
arduino_relay_control.py on 8 9 10
arduino_relay_control.py off 10
arduino_relay_control.py pulse 0 3000
arduino_relay_control.py status

# Serial directo (sin daemon)
stty -F /dev/arduino-relay 115200 raw -echo && echo "ON 8 9 10" > /dev/arduino-relay
```

## 6. Arduino Relay Daemon (`arduino_daemon.py`)

Evita reset del Arduino al abrir/cerrar el puerto: conexión serial persistente, socket Unix `/tmp/arduino-relay.sock`. `arduino_relay_control.py` y PDUDaemon se benefician si el servicio está activo.

### 6.1 Servicio systemd (recomendado)

Unit de origen: `configs/templates/arduino-relay-daemon.service` → `/etc/systemd/system/`.

```bash
# Desde la raíz de fcefyn-testbed-utils:
sudo cp scripts/arduino/arduino_daemon.py /usr/local/bin/ && sudo chmod +x /usr/local/bin/arduino_daemon.py
sudo cp configs/templates/arduino-relay-daemon.service /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now arduino-relay-daemon
```

### 6.2 Manual (pruebas)

```bash
./scripts/arduino/start_daemon.sh
# o: python3 scripts/arduino/arduino_daemon.py start --port /dev/arduino-relay
```

Comandos del daemon: `start`, `stop`, `status`. PID `/tmp/arduino-relay.pid`, socket arriba, log `/tmp/arduino-daemon.log` con `start_daemon.sh`.

## 7. Resolución del symlink

```bash
readlink -f /dev/arduino-relay
```
