# Labgrid helper scripts

Two utility scripts assist with coordinator configuration and target file
resolution. Both are optional — normal pytest runs handle these automatically
via `LG_PLACE` and `LG_ENV` — but they are useful for debugging and manual
setup.

---

## `generate_places_yaml.py`

Renders `places.yaml` for the labgrid-coordinator from `labnet.yaml` and a
Jinja2 template. Run after any change to the lab's device list or DUT
configuration.

### Usage

```bash
# Default: generate for labgrid-fcefyn, output to coordinator path
python3 scripts/generate_places_yaml.py

# Specify a different lab entry from labnet.yaml
python3 scripts/generate_places_yaml.py --lab labgrid-hsn

# Custom paths
python3 scripts/generate_places_yaml.py \
    --labnet /path/to/labnet.yaml \
    --output ~/labgrid-coordinator/places.yaml
```

### How it finds `labnet.yaml`

The script searches in order:

1. `--labnet` CLI argument (explicit path)
2. `$OPENWRT_TESTS_DIR/labnet.yaml`
3. Sibling clone: `../openwrt-tests/labnet.yaml` (relative to repo root)
4. `~/openwrt-tests/labnet.yaml`

### When to regenerate

- After adding or removing a DUT from `labnet.yaml`
- After changing place names, resources, or device instances
- After any `labnet.yaml` update that affects the `labgrid-fcefyn` entry

!!! tip "Coordinator reload"
    After regenerating, restart the labgrid-coordinator so it picks up the
    new places: `sudo systemctl restart labgrid-coordinator`.

---

## `resolve_target.py`

Maps a device instance name (as registered in `labnet.yaml`) to the
labgrid target YAML file that Labgrid needs to configure resources.

!!! note "Usually not needed"
    When running pytest with `LG_PLACE` set, Labgrid resolves `LG_ENV`
    automatically from the coordinator. Use this script only for debugging
    or manual environment setup outside pytest.

### Usage

```bash
# Find which target file corresponds to a device instance
python3 scripts/resolve_target.py belkin_rt3200_1
# Output: targets/linksys_e8450.yaml

python3 scripts/resolve_target.py librerouter_1
# Output: targets/librerouter_librerouter-v1.yaml
```

### How it finds `labnet.yaml`

Same search order as `generate_places_yaml.py`:
`$LABNET_PATH` → `$OPENWRT_TESTS_DIR/labnet.yaml` → sibling clone.

### Mapping logic

```
device_instance (e.g. belkin_rt3200_1)
  └─► labnet.yaml device_instances → device_type (e.g. linksys_e8450)
        └─► targets/<device_type>.yaml
```

The mapping uses the `device_instances` section of the lab entry in
`labnet.yaml`. If an instance is not found, the script exits with an error
and a list of known instances.

### Troubleshooting

| Error | Fix |
|-------|-----|
| `labnet.yaml not found` | Set `LABNET_PATH` or `OPENWRT_TESTS_DIR`, or ensure `../openwrt-tests/` exists as sibling clone |
| `Unknown device instance` | Check `labnet.yaml` `device_instances` for the `labgrid-fcefyn` entry |
| `targets/<type>.yaml not found` | The device type is in labnet but the target file is missing from `openwrt-tests/targets/` |

---

## See also

- [Running tests](lab-running-tests.md) — how `LG_PLACE`, `LG_ENV`, `LG_IMAGE` work together
- [Ansible / Labgrid](../configuracion/ansible-labgrid.md) — generating `places.yaml` via Ansible
- `openwrt-tests/labnet.yaml` — device instances and lab registration
