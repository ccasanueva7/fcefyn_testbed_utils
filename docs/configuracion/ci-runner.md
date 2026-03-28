# GitHub Actions Self-Hosted Runner

Para ejecutar workflows de libremesh-tests directamente en el host del lab, se instala un **GitHub Actions self-hosted runner**. Los jobs de Daily, Healthcheck y Pull Requests corren directamente sobre este hardware en lugar de usar runners de GitHub o de terceros.

---

## 1. Requisitos

- Cuenta/repo en GitHub (ej. `francoriba/libremesh-tests` o la org que corresponda).
- Acceso SSH al host del lab.

---

## 2. Instalación

1. Descargar el runner desde [GitHub Actions Runner](https://github.com/actions/runner/releases) (Linux x64).

2. En el repo: **Settings** → **Actions** → **Runners** → **New self-hosted runner**. Copiar el comando de configuración.

3. En el host del lab:

   ```bash
   mkdir -p ~/actions-runner && cd ~/actions-runner
   # Descargar el archivo .tar.gz de la release, extraer
   ./config.sh --url https://github.com/OWNER/REPO --token TOKEN
   ```

4. Durante la configuración:
   - **Runner name**: p.ej. `runner-fcefyn` o `labgrid-fcefyn`
   - **Additional labels**: p.ej. `testbed-fcefyn` (para usar `runs-on: [self-hosted, testbed-fcefyn]` en los workflows)

5. Instalar y arrancar el servicio:

   ```bash
   sudo ./svc.sh install
   sudo ./svc.sh start
   ```

---

## 3. Verificación

```bash
sudo systemctl status actions.runner.*
```

En GitHub, el runner debería aparecer como **Idle** en **Settings** → **Actions** → **Runners**.

---

## 4. Permisos de /etc/labgrid

El coordinator de labgrid escribe en `/etc/labgrid` (estado de places, resources). Si el directorio tiene permisos incorrectos, el coordinator falla con `PermissionError` al guardar. El playbook de libremesh-tests debe crear `/etc/labgrid` con `owner: labgrid-dev` y `group: labgrid-dev`. Si se corrige manualmente:

```bash
sudo chown -R labgrid-dev:labgrid-dev /etc/labgrid
sudo systemctl restart labgrid-coordinator
```

---

## 5. Reasociar el runner a otro repo

Para mover el runner de un repo a otro (o de user a org):

1. En el host: `./config.sh remove --token TOKEN` (el token se obtiene desde la UI del repo/org actual).
2. En el nuevo repo/org: **New self-hosted runner** → copiar el nuevo comando.
3. Ejecutar `./config.sh` con la nueva URL y token.
4. `sudo ./svc.sh uninstall` y luego `sudo ./svc.sh install` + `sudo ./svc.sh start`.

---

## 6. Transferencia de ownership

Al transferir el repo a una org, los runners asociados se transfieren con él. El nombre del servicio en systemd puede seguir referenciando al owner anterior y esto no deberia afectar el funcionamiento.

---

## 7. Setup realizado (FCEFyN)

Resumen de lo que se hizo para dejar operativo el runner en el host labgrid-fcefyn:

1. **Instalación del runner** en `~/actions-runner` siguiendo [sección 2](#2-instalacion).
2. **Configuración inicial**: Runner asociado al fork (`francoriba/libremesh-tests`). Nombre: `runner-fcefyn`. Labels: `self-hosted`, `testbed-fcefyn`.
3. **Servicio systemd**: Instalado con `sudo ./svc.sh install`. Nombre del servicio: `actions.runner.francoriba-libremesh-tests.runner-fcefyn.service`.
4. **Re-registro**: El runner se había instalado inicialmente en el repo `libremesh-tests Private`. Para asociarlo al fork, se ejecutó `./config.sh remove --token TOKEN` (token desde la UI del repo original), luego `./config.sh` con la URL del fork, y finalmente `sudo ./svc.sh uninstall` + `sudo ./svc.sh install` + `sudo ./svc.sh start`.
5. **Permisos /etc/labgrid**: El coordinator fallaba con `PermissionError` al escribir en `/etc/labgrid`. Se corrigió con `sudo chown -R labgrid-dev:labgrid-dev /etc/labgrid`. El playbook de openwrt-tests fue actualizado para que la tarea "Create labgrid folder" use `owner: labgrid-dev` y `group: labgrid-dev`.
6. **Verificación**: Jobs Daily, Healthcheck y Pull Requests ejecutan en el runner con `runs-on: [self-hosted, testbed-fcefyn]`. Tests validados con openwrt_one.
