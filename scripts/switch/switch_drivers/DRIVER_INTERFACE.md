# Interfaz del driver de switch

Este documento define el contrato que debe implementar un módulo driver de switch. Los drivers se cargan dinámicamente según `POE_SWITCH_DRIVER` en `~/.config/poe_switch_control.conf`.

Para agregar soporte para un switch nuevo:

1. Crear `switch_drivers/<nombre>.py` implementando la interfaz que se describe abajo.
2. Configurar `POE_SWITCH_DRIVER=<nombre>` y `POE_SWITCH_DEVICE_TYPE=<netmiko_type>` en tu config.
3. Ver [Netmiko PLATFORMS](https://github.com/ktbyers/netmiko/blob/develop/PLATFORMS.md) para los valores de `device_type` soportados.

## Exportaciones requeridas

### PRESETS (dict)

Diccionario que mapea nombres de preset a definiciones. Lo usa `switch_vlan_preset.py`.

```python
PRESETS = {
    "isolated": (PRESET_ISOLATED_TUPLES, create_vlan_200=False),
    "mesh": (PRESET_MESH_TUPLES, create_vlan_200=True),
}
```

Cada preset es una lista de tuplas `(puerto, list[str] de comandos de interfaz)`. El driver convierte esto en una lista de comandos CLI completos.

### build_preset_commands(preset_name: str) -> list[str]

Construye los comandos CLI para un preset VLAN completo (isolated o mesh). Lo llama `switch_vlan_preset.py`.

- **preset_name**: Una de las claves en `PRESETS`.
- **Retorna**: Lista de comandos CLI a enviar al switch.
- **Lanza**: `ValueError` si preset_name es desconocido.

### build_poe_commands(port: int, action: str) -> list[str]

Construye los comandos CLI para habilitar o deshabilitar PoE en un puerto. Lo llama `poe_switch_control.py` vía `switch_client.py`.

- **port**: Número de puerto del switch (base 1).
- **action**: `"on"` u `"off"`.
- **Retorna**: Lista de comandos CLI.
- **Lanza**: `ValueError` si action no es `"on"` u `"off"`.

Para switches sin PoE, retornar una lista vacía o comandos idempotentes que no hagan nada.

### build_hybrid_commands(port_assignments, ...) -> list[str]

Construye los comandos CLI para asignación híbrida de VLANs (DUTs repartidos entre pools openwrt y libremesh). Lo llama `pool-manager.py`.

**Parámetros:**

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| port_assignments | list[tuple[int, str, int]] | (puerto, pool, isolated_vlan) por puerto DUT. Pool es `"isolated"` o `"mesh"`. |
| active_isolated_vlans | set[int] | IDs de VLAN usados por DUTs del pool openwrt. |
| has_libremesh_duts | bool | Si hay algún DUT en el pool libremesh. |
| uplink_ports | list[int] | Puertos que llevan tráfico etiquetado (trunk al host). |
| vlan_mesh | int | ID de VLAN para la red mesh (por defecto 200). |
| ports_to_include | set[int] \| None | Si está definido, solo configurar estos puertos (aplicación diferencial). |
| include_uplinks | bool | Si es False, omitir la config de puertos uplink. |

**Retorna:** Lista de comandos CLI.

### ensure_vlan_commands(vlan_id: int, name: str | None = None) -> list[str]

Construye los comandos CLI para crear una VLAN si no existe. Opcional; se usa para creación dinámica de VLANs.

### assign_port_vlan_commands(port, vlan_id, mode, remove_vlans) -> list[str]

Construye los comandos CLI para asignar un puerto a una VLAN. Opcional; se usa para config de puerto de bajo nivel.

- **port**: Número de puerto del switch.
- **vlan_id**: VLAN a asignar.
- **mode**: `"untagged"` o `"tagged"`.
- **remove_vlans**: VLANs a quitar del puerto antes de asignar.

## Implementación de referencia

Ver [tplink_jetstream.py](tplink_jetstream.py) para una implementación completa orientada a switches TP-Link JetStream (p. ej. SG2016P). Netmiko device_type para este driver: `tplink_jetstream`.
