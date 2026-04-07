# Home Snapshot For GitHub

Este repositorio ahora maneja dos capas de respaldo para migracion:

1. [`home_snapshot/`](/home/ubuntu/omni-core/home_snapshot)
   Snapshot publico-seguro, saneado y restaurable rapido.
2. [`home_private_snapshot/`](/home/ubuntu/omni-core/home_private_snapshot)
   Overlay privado cifrado con estado oculto, logs y runtime util.

## Capa Publica

`home_snapshot/` no es un respaldo crudo de `/home/ubuntu`. Es un snapshot saneado y publicable:

- Incluye codigo fuente, scripts, docs y configuracion util.
- Incluye un inventario de todo el top-level de `/home/ubuntu`.
- Excluye secretos y runtime pesado: `.env`, `.ssh`, `.git-credentials`, `node_modules`, `venv`, bases `.db`, `sessions`, `vendor`, caches y backups gigantes.

Motivo:

- `/home/ubuntu` pesa decenas de GB.
- GitHub no es un destino realista para subir 42G crudos en texto plano.
- El repo puede alternar entre publico y privado durante migraciones.

## Refrescar solo la capa publica

```bash
cd /home/ubuntu/omni-core
./scripts/refresh_home_snapshot.sh
```

## Refrescar ambas capas

```bash
cd /home/ubuntu/omni-core
HOME_PRIVATE_SNAPSHOT_PASSPHRASE='tu-passphrase' ./scripts/refresh_home_snapshot.sh --mode private
```

Si no defines passphrase, el script genera una local en `backups/home_private_snapshot.passphrase` y no la sube a Git.

## Archivos clave

Publicos:

- [`home_snapshot/inventory/top_level_entries.tsv`](/home/ubuntu/omni-core/home_snapshot/inventory/top_level_entries.tsv)
- [`home_snapshot/inventory/top_level_sizes.txt`](/home/ubuntu/omni-core/home_snapshot/inventory/top_level_sizes.txt)
- [`home_snapshot/inventory/omitted_top_level.tsv`](/home/ubuntu/omni-core/home_snapshot/inventory/omitted_top_level.tsv)
- [`home_snapshot/inventory/snapshot_scope.txt`](/home/ubuntu/omni-core/home_snapshot/inventory/snapshot_scope.txt)
- [`home_snapshot/inventory/snapshot_size.txt`](/home/ubuntu/omni-core/home_snapshot/inventory/snapshot_size.txt)

Privados:

- [`home_private_snapshot/inventory/archive_manifest.tsv`](/home/ubuntu/omni-core/home_private_snapshot/inventory/archive_manifest.tsv)
- [`home_private_snapshot/inventory/archive_files.txt`](/home/ubuntu/omni-core/home_private_snapshot/inventory/archive_files.txt)
- [`home_private_snapshot/inventory/omitted_targets.tsv`](/home/ubuntu/omni-core/home_private_snapshot/inventory/omitted_targets.tsv)
- [`home_private_snapshot/inventory/archive_size.txt`](/home/ubuntu/omni-core/home_private_snapshot/inventory/archive_size.txt)

## Restauracion rapida

1. clonar `omni-core`
2. copiar o mover el contenido de `home_snapshot/ubuntu/`
3. restaurar el overlay cifrado
4. reinstalar dependencias y servicios

Ejemplo:

```bash
cd /home/ubuntu/omni-core
rsync -a home_snapshot/ubuntu/ /home/ubuntu/
HOME_PRIVATE_SNAPSHOT_PASSPHRASE='tu-passphrase' ./scripts/restore_home_private_snapshot.sh /home/ubuntu
```

La capa privada incluye chats, logs, `.n8n`, `.pm2`, `.codex` y otros estados utiles para migracion. Los secretos crudos siguen fuera del repo en texto plano.
