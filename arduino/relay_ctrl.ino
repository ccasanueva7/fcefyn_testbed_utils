/**
 * ------------------------------------------------------------
 *  Proyecto: fcefyn-testbed-utils
 *  Script:   relay_ctrl.ino
 *  Autor:    Franco Riba
 *
 *  Descripción:
 *    Control de módulos de relés mediante interfaz USB-Serial.
 *    Diseñado para pruebas automatizadas (HIL - Hardware-in-the-loop).
 *
 *  Hardware:
 *    - Arduino Nano (ATmega328P)
 *    - Módulo relé KY-019 de 8 canales (DUTs) -> D2..D9
 *    - SSR 4 canales (Switch+Cooler) y SSR simple (Fuente) -> D10..D12
 *    - Conexión por USB (baudrate 115200)
 *
 *  Pines:
 *    Canales 0-7: D2..D9   (módulo 8 relés mecánicos, DUTs)
 *    Canal 8:     D10      (SSR Switch, módulo 4ch)
 *    Canal 9:     D11      (SSR Cooler, módulo 4ch)
 *    Canal 10:    D12      (SSR Fuente, Fotek SSR25DA)
 *
 *  Comandos disponibles por Serial:
 *    ON n [n ...]      : enciende uno o varios relés (0..10)
 *    OFF n [n ...]     : apaga uno o varios relés
 *    TOGGLE n [n ...]  : alterna uno o varios relés
 *    PULSE n ms        : enciende el relé n durante ms milisegundos
 *    ALLON             : enciende todos los relés
 *    ALLOFF            : apaga todos los relés
 *    STATUS            : imprime el estado de todos los relés
 *    HELP              : muestra ayuda
 *    ID                : identificación del dispositivo
 *
 *  Notas:
 *    - La mayoría de módulos son activos en bajo (LOW = ON).
 *    - Si tu módulo es activo en alto, cambia RELAY_ACTIVE_LOW a false.
 * ------------------------------------------------------------
 */

#include <Arduino.h>

// Configuración
constexpr bool RELAY_ACTIVE_LOW = true;        // true = activo-bajo, false = activo-alto
constexpr uint8_t RELAY_COUNT   = 11;          // 8 DUTs + 3 SSR (Switch, Cooler, Fuente)
constexpr uint8_t RELAY_PINS[RELAY_COUNT] = {
  2, 3, 4, 5, 6, 7, 8, 9,   // D2..D9: módulo 8 relés (DUTs)
  10, 11, 12                 // D10..D12: SSR Switch, Cooler, Fuente
};

enum RelayState : uint8_t { R_OFF = 0, R_ON = 1 };
RelayState states[RELAY_COUNT];

/**
 * @brief Aplica el estado a un relé individual.
 */
void applyRelay(uint8_t ch, RelayState s) {
  if (ch >= RELAY_COUNT) return;
  states[ch] = s;

  // Activo-bajo: LOW = ON, HIGH = OFF
  if (RELAY_ACTIVE_LOW) {
    digitalWrite(RELAY_PINS[ch], (s == R_ON) ? LOW : HIGH);
  } else {
    digitalWrite(RELAY_PINS[ch], (s == R_ON) ? HIGH : LOW);
  }
}

/**
 * @brief Aplica el mismo estado a todos los relés.
 */
void allRelays(RelayState s) {
  for (uint8_t i = 0; i < RELAY_COUNT; i++) {
    applyRelay(i, s);
  }
}

/**
 * @brief Imprime el estado actual de todos los relés.
 */
void printStatus() {
  Serial.print(F("STATUS "));
  for (uint8_t i = 0; i < RELAY_COUNT; i++) {
    Serial.print(i);
    Serial.print(':');
    Serial.print(states[i] == R_ON ? F("ON") : F("OFF"));
    if (i < RELAY_COUNT - 1) Serial.print(' ');
  }
  Serial.println();
}

/**
 * @brief Muestra ayuda de comandos.
 */
void help() {
  Serial.println(F("Comandos disponibles:"));
  Serial.println(F("  ON n [n ...] | OFF n [n ...] | TOGGLE n [n ...]"));
  Serial.println(F("  PULSE n ms"));
  Serial.println(F("  ALLON | ALLOFF | STATUS | HELP | ID"));
  Serial.println(F("  n=0..10, ms=milisegundos (1..60000)"));
}

void setup() {
  Serial.begin(115200);

  // Configurar pines como salida
  for (uint8_t i = 0; i < RELAY_COUNT; i++) {
    pinMode(RELAY_PINS[i], OUTPUT);
  }

  // Estado inicial seguro: todo apagado
  allRelays(R_OFF);

  Serial.println(F("OK RELAY-CTRL v2 (11ch) listo @115200"));
  help();
}

/**
 * @brief Lee una línea completa del puerto serial.
 */
bool readLine(String &out) {
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\r') continue;
    if (c == '\n') return true;
    if (out.length() < 128) out += c; // un poco más de margen
  }
  return false;
}

/**
 * @brief Convierte string a entero con validación.
 */
int toIntSafe(const String &s, bool &ok) {
  if (s.length() == 0) { ok = false; return 0; }
  // Validación básica: debe empezar en dígito (permitimos '0')
  bool digitFound = false;
  for (uint16_t i = 0; i < s.length(); i++) {
    if (isDigit(s[i])) { digitFound = true; break; }
  }
  if (!digitFound) { ok = false; return 0; }
  long v = s.toInt();
  ok = true;
  return (int)v;
}

/**
 * @brief Procesa comandos de múltiples canales: ON/OFF/TOGGLE <n> [n ...]
 */
void processMultiChannelCommand(const String &cmd, String rest) {
  if (rest.length() == 0) {
    Serial.println(F("ERR se requieren canales (0..10). Ej: ON 0 1 8"));
    return;
  }

  bool anyApplied = false;

  // Iterar por tokens separados por espacio
  while (rest.length() > 0) {
    int sp = rest.indexOf(' ');
    String tok = (sp < 0) ? rest : rest.substring(0, sp);
    rest = (sp < 0) ? "" : rest.substring(sp + 1);
    rest.trim();
    tok.trim();

    if (tok.length() == 0) continue;

    bool ok = false;
    int ch = toIntSafe(tok, ok);
    if (!ok || ch < 0 || ch >= (int)RELAY_COUNT) {
      Serial.print(F("WARN token inválido/ fuera de rango: "));
      Serial.println(tok);
      continue;
    }

    if (cmd == F("ON")) {
      applyRelay((uint8_t)ch, R_ON);
    } else if (cmd == F("OFF")) {
      applyRelay((uint8_t)ch, R_OFF);
    } else { // TOGGLE
      applyRelay((uint8_t)ch, states[ch] == R_ON ? R_OFF : R_ON);
    }
    anyApplied = true;
  }

  if (anyApplied) printStatus();
  else Serial.println(F("ERR no se aplicó ningún canal válido"));
}

void loop() {
  static String line;
  if (!readLine(line)) return;

  line.trim();
  line.toUpperCase();
  if (line.length() == 0) { line = ""; return; }

  // Tokenizar
  int sp1 = line.indexOf(' ');
  String cmd  = (sp1 < 0) ? line : line.substring(0, sp1);
  String rest = (sp1 < 0) ? ""   : line.substring(sp1 + 1);
  rest.trim();

  if (cmd == F("ON") || cmd == F("OFF") || cmd == F("TOGGLE")) {
    processMultiChannelCommand(cmd, rest);

  } else if (cmd == F("PULSE")) {
    int sp = rest.indexOf(' ');
    if (sp < 0) {
      Serial.println(F("ERR uso: PULSE n ms"));
    } else {
      bool ok1 = false, ok2 = false;
      int ch = toIntSafe(rest.substring(0, sp), ok1);
      int ms = toIntSafe(rest.substring(sp + 1), ok2);
      if (!ok1 || !ok2 || ch < 0 || ch >= RELAY_COUNT || ms < 1 || ms > 60000) {
        Serial.println(F("ERR args (n=0..10, ms=1..60000)"));
      } else {
        applyRelay(ch, R_ON);
        delay(ms);
        applyRelay(ch, R_OFF);
        printStatus();
      }
    }

  } else if (cmd == F("ALLON")) {
    allRelays(R_ON); printStatus();

  } else if (cmd == F("ALLOFF")) {
    allRelays(R_OFF); printStatus();

  } else if (cmd == F("STATUS")) {
    printStatus();

  } else if (cmd == F("HELP")) {
    help();

  } else if (cmd == F("ID")) {
    Serial.println(F("RELAY-CTRL v2 (11ch)"));

  } else {
    Serial.println(F("ERR comando desconocido (try HELP)"));
  }

  line = "";
}
