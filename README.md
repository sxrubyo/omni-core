# Omni Core v2.1 - The Supreme Coordinator

Omni Core está orientado a restaurar un entorno productivo limpio en Linux o un `full-home` completo de `/home/ubuntu`, sincronizar estado real desde otros hosts y dejar mantenimiento automático sin arrastrar ruido innecesario.

Ahora el punto de entrada recomendado ya no es memorizar comandos bajos: es ejecutar `omni` o `omni start` y dejar que la CLI te guíe hacia `bridge`, `capture`, `restore`, `migrate` o `doctor`.

Por defecto no intenta clonar `/home/ubuntu` tal cual.
La regla base es preservar lo que sí construye producto y separar lo que debe viajar aparte. Si activas `full-home`, entonces sí captura literalmente todo `/home/ubuntu` como estado raíz y mantiene secretos aparte.

## Flujo productivo limpio

Este es el flujo recomendado para una reinstalación real, una migración entre máquinas o una recuperación desde backup:

1. **Inventory**
   - identificar qué es código, qué es estado y qué es ruido
   - dejar fuera caches, `node_modules`, logs viejos, temporales y artefactos reproducibles
   - conservar repos, configs, datos operativos y snapshots útiles

2. **Bundle state**
   - empaquetar `config/`, `data/`, `backups/`, `logs/`, `tasks.json` y manifiestos operativos
   - guardar el estado restaurable de forma determinista
   - mantener la restauración portable entre Ubuntu/Linux

3. **Secrets pack**
   - exportar secretos aparte de todo lo demás
   - incluir `.env`, tokens, credenciales SSH, llaves de servicio y sesiones sensibles
   - cifrarlo antes de moverlo
   - nunca versionarlo en Git ni mezclarlo con el bundle de estado

4. **Bootstrap**
   - instalar dependencias base del host
   - clonar o actualizar el repo privado
   - ejecutar `install.sh --compose --sync`
   - preparar `omni` en `/usr/local/bin`

5. **Reconcile**
   - reconciliar estado con `omni fix`
   - sincronizar snapshots remotos con `omni sync`
   - reforzar la configuración local sin tocar `src/`
   - aplicar el mismo proceso cuantas veces haga falta; debe ser idempotente

6. **Timer**
   - programar reconciliación diaria con `systemd`
   - ejecutar mantenimiento y sync cada 24 horas
   - dejar un punto único de actualización que no dependa de intervención manual

## Qué se preserva

Omni Core trabaja bien cuando se conservan estas piezas:

- `config/`
- `data/`
- `backups/`
- `logs/`
- `tasks.json`
- `.env` y secretos relacionados, pero solo en el secrets pack cifrado
- repositorios productivos definidos en `config/repos.json`
- inventario remoto de `config/servers.json`

## Qué no se debe arrastrar por defecto

- `node_modules`
- `.cache`
- `__pycache__`
- logs históricos reproducibles
- temporales de build
- artefactos derivados que se pueden regenerar
- `.git` en bundles de estado

## Perfiles

Omni usa perfiles de manifest para decidir qué captura y cómo activa la migración.

- `production-clean`: conserva la huella productiva principal, con estado y secretos separados
- `full-home`: captura todo `/home/ubuntu` como raíz de estado y mantiene secretos aparte
- el `system_manifest.example.json` del repositorio ya viene preparado para `full-home`
- `omni init --profile full-home`: activa el perfil completo antes de capturar o migrar
- `omni init --profile production-clean`: vuelve al perfil productivo limpio

### Qué entra realmente en `full-home`

Si activas `full-home`, Omni trata `/home/ubuntu` entero como estado. Eso significa que sí entran, entre otras cosas:

- `.codex`
- `.agents`
- `.nova`
- `.n8n`
- `melissa`
- `melissa-instances`
- `whatsapp-bridge`
- `nova-os`
- `Workflows-n8n`
- `xus-https`
- `melissa-backups`

`melissa-backups` importa si de verdad quieres poder reconstruir el host “con todo”. Suele ser uno de los bloques más pesados porque guarda respaldos históricos de Melissa. No es código fuente; es estado archivado.

### GitHub público por unos segundos: qué sí y qué no

Poner el repo de GitHub público por unos segundos sí puede hacer más fácil clonar `omni-core` o bajar el bootstrap en una máquina virgen.

Pero eso no sustituye una migración real. GitHub solo resuelve mejor el transporte del código del repositorio. No reemplaza:

- bundles de estado
- secrets pack
- `.env`
- claves SSH
- sesiones
- datos de `n8n`
- dumps de PM2
- estado vivo de `/home/ubuntu`

La forma correcta sigue siendo:

1. clonar o descargar `omni-core`
2. ejecutar `omni init --profile full-home` si quieres todo `/home/ubuntu`
3. correr `omni capture`
4. mover `state bundle` + `secrets bundle`
5. restaurar con `omni restore` o `omni migrate`

### Automatización de host y backups

Omni ya está orientado a que no tengas que ir persiguiendo IPs o snapshots a mano:

- `omni start` y `omni doctor` diagnostican si el host actual sigue teniendo referencias al host viejo
- `omni detect-ip` muestra la identidad actual y cuántos archivos siguen con drift
- `omni migrate` reescribe referencias del host automáticamente por defecto
- si quieres impedirlo, usas `omni migrate --skip-rewrite`
- `omni rewrite-ip --apply` sigue existiendo como comando directo

Además:

- `omni init`, `omni restore`, `omni migrate` y `omni rewrite-ip --apply` crean backup automático en `backups/auto-bundles`
- el timer diario `omni-update.timer` ahora ejecuta primero `omni backup`, luego `omni fix` y `omni sync`
- `omni timer-install` deja también `omni-watch.service`, que vigila cambios en el scope del manifest y dispara backup automático con cooldown
- `omni agent` abre un selector visual para configurar Claude, Gemini, OpenRouter, Qwen o un endpoint OpenAI-compatible propio

## Modos de instalación

### 0. Guía simple desde GitHub

Si no quieres complicarte con claves, wrappers ni PowerShell remoto:

- [GUIA_INSTALACION_SIMPLE_GITHUB.md](/home/ubuntu/omni-core/GUIA_INSTALACION_SIMPLE_GITHUB.md)

### 1. Bootstrap Linux local

Si ya estás en la máquina destino:

```bash
bash bootstrap.sh git@github.com:sxrubyo/omni-core.git /opt/omni-core main
```

Ese flujo:

- instala dependencias base de Ubuntu
- clona o actualiza el repo privado
- crea archivos base si faltan
- ejecuta `omni sync`
- levanta Docker Compose

### 2. Wrapper PowerShell a un host Linux remoto

Desde otra PC, incluyendo PowerShell en Windows:

```powershell
pwsh ./bootstrap.ps1 -TargetHost 1.2.3.4 -User ubuntu -RepoUrl git@github.com:sxrubyo/omni-core.git -Branch main -InstallTimer
Si no pasas `-Destination`, `bootstrap.ps1` escanea el host remoto, recomienda rutas y te deja elegir o escribir una personalizada.
```

Ese wrapper se conecta por SSH al host Linux, prepara paquetes base, clona o actualiza Omni Core y dispara el mismo bootstrap de producción.
Si agregas `-InstallTimer`, también deja programado el reconcile diario con `systemd`.

Guía dedicada:

- [GUIA_POWERSHELL_WINDOWS.md](/home/ubuntu/omni-core/GUIA_POWERSHELL_WINDOWS.md)

### 3. Carpeta copiada por SCP

```bash
scp -r omni-core ubuntu@tu-servidor:/opt/omni-core
ssh ubuntu@tu-servidor
cd /opt/omni-core
chmod +x install.sh bin/omni bootstrap.sh
./install.sh --compose --sync
```

### 4. GitHub privado

```bash
git clone git@github.com:sxrubyo/omni-core.git /opt/omni-core
cd /opt/omni-core
chmod +x install.sh bin/omni bootstrap.sh
./install.sh --compose --sync
```

## Entrada recomendada

La superficie principal ahora es:

```bash
omni
omni start
omni doctor
omni capture
omni restore
omni migrate
omni detect-ip
omni rewrite-ip
omni bridge
```

La regla práctica es:

- `omni` o `omni start`: entrar al asistente guiado
- `omni capture`: crear recovery pack completo
- `omni restore`: restaurar bundle + secrets
- `omni migrate`: reconstruir host y corregir referencias
- `omni doctor`: revisar salud, bundles y problemas de configuración

## Recuperación y reconciliación

El punto de entrada operativo sigue siendo `install.sh` y la CLI `omni`.

Comandos útiles:

```bash
omni
omni doctor
omni capture
omni restore
omni migrate
omni detect-ip
omni rewrite-ip
omni bridge create
omni bridge send --dest ubuntu@host:/ruta
omni help
omni status
omni inventory
omni bundle-create
omni secrets-export
omni reconcile --bundle-latest --secrets-latest
omni purge
omni sync
omni fix
omni install
omni logs
omni backup
docker compose up -d --build
docker compose logs -f omni-core
```

`omni doctor` revisa salud, bundles, manifest y problemas obvios como hosts placeholder.
`omni capture` produce estado + secretos + resumen verificable.
`omni migrate` reutiliza restore/reconcile y puede reescribir referencias de host/IP.
`omni sync` trae snapshots y archivos remotos definidos en `config/servers.json`.
`omni purge` hace un dry-run de todo lo que puede borrarse para recuperar disco; con `--yes` lo elimina de verdad.

## Reconciliación diaria

La recomendación es dejar un `systemd timer` que ejecute reconciliación cada 24 horas.

La idea operativa es:

- refrescar el repo
- correr `omni fix`
- correr `omni sync`
- validar salud del stack

Si la máquina se reconstruye desde cero, el timer vuelve a instalarse junto con el bootstrap.

## Inventario de servidores

Plantilla:

- `config/servers.example.json`

Ejemplo:

```json
{
  "servers": [
    {
      "name": "main-ubuntu",
      "host": "1.2.3.4",
      "user": "ubuntu",
      "port": 22,
      "protocol": "rsync",
      "paths": [
        "/home/ubuntu/melissa",
        "/home/ubuntu/nova-os",
        "/home/ubuntu/.nova",
        "/home/ubuntu/omni-core"
      ],
      "excludes": [".git", "__pycache__", "*.pyc", "node_modules"]
    }
  ]
}
```

Los snapshots remotos quedan en:

```text
data/servers/<server>/<ruta-remota-normalizada>/
```

## Instalación automática recomendada

```bash
cd /opt/omni-core
omni init --profile full-home
nano .env
nano config/repos.json
nano config/servers.json
./install.sh --compose --sync --timer
omni
```

## Flujo recomendado de restauración

1. clonar o copiar `omni-core`
2. correr `omni init --profile full-home` si quieres llevar todo `/home/ubuntu`
3. mover `bundle + secrets` al host nuevo
4. ejecutar `omni restore` o `omni migrate`
5. validar `omni doctor`
6. revisar `omni detect-ip`
7. si hace falta, ejecutar `omni rewrite-ip`
8. si quieres IA operativa en el host, ejecutar `omni agent`

## Liberar espacio

Cuando la máquina ya quedó reconstruida y quieres recuperar disco sin tocar los repos que puedes volver a clonar desde GitHub:

```bash
omni purge
omni purge --yes
```

Si además quieres eliminar secretos restaurados desde bundle:

```bash
omni purge --include-secrets --yes
```

Ese comando:

- elimina bundles, snapshots y logs locales de Omni
- elimina estado transferido que no está gestionado por Git
- limpia `node_modules`, `.venv`, `build`, `dist`, `tmp`, `output` y otros artefactos dentro de repos Git
- preserva por defecto los repos base clonados desde GitHub

## Simulación local

Si quieres probar una migración en la misma máquina sin tocar producción:

```bash
rsync -av --delete /opt/omni-core/ /opt/omni-core-test/
cd /opt/omni-core-test
mkdir -p data-test backups-test logs-test
docker compose -p omni-core-test -f docker-compose.test.yml up -d --build
docker compose -p omni-core-test -f docker-compose.test.yml ps
docker compose -p omni-core-test -f docker-compose.test.yml logs -f omni-core-test
```

Para tumbar la simulación:

```bash
docker compose -p omni-core-test -f docker-compose.test.yml down
```

## Notas operativas

- `omni sync` trae archivos remotos por `rsync` o `scp`
- para GitHub privado, el host necesita SSH o credenciales válidas
- el bundle de estado y el secrets pack deben viajar por caminos separados
- el wrapper PowerShell es el lanzador remoto; el bootstrap real sigue ocurriendo en Linux
- el objetivo es que una nueva instancia vuelva a un estado útil sin depender de restauraciones manuales una por una
