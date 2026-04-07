# Home Snapshot For GitHub

Este repositorio incluye un plan B llamado [`home_snapshot/`](/home/ubuntu/omni-core/home_snapshot) pensado para GitHub.

No es un respaldo crudo de `/home/ubuntu`. Es un snapshot saneado y publicable:

- Incluye codigo fuente, scripts, docs y configuracion util.
- Incluye un inventario de todo el top-level de `/home/ubuntu`.
- Excluye secretos y runtime pesado: `.env`, `.ssh`, `.git-credentials`, `node_modules`, `venv`, bases `.db`, `sessions`, `vendor`, caches y backups gigantes.

Motivo:

- `/home/ubuntu` pesa decenas de GB.
- GitHub no es un destino realista para subir 42G crudos.
- El repo es publico o puede volver a ser publico durante una migracion.

## Refrescar el snapshot

```bash
cd /home/ubuntu/omni-core
./scripts/refresh_home_snapshot.sh
```

## Archivos clave

- [`home_snapshot/inventory/top_level_entries.tsv`](/home/ubuntu/omni-core/home_snapshot/inventory/top_level_entries.tsv)
- [`home_snapshot/inventory/top_level_sizes.txt`](/home/ubuntu/omni-core/home_snapshot/inventory/top_level_sizes.txt)
- [`home_snapshot/inventory/omitted_top_level.tsv`](/home/ubuntu/omni-core/home_snapshot/inventory/omitted_top_level.tsv)
- [`home_snapshot/inventory/snapshot_scope.txt`](/home/ubuntu/omni-core/home_snapshot/inventory/snapshot_scope.txt)
- [`home_snapshot/inventory/snapshot_size.txt`](/home/ubuntu/omni-core/home_snapshot/inventory/snapshot_size.txt)

## Restauracion rapida

El snapshot permite recuperar codigo y estructura de trabajo rapido:

1. clonar `omni-core`
2. copiar o mover el contenido de `home_snapshot/ubuntu/`
3. restaurar secretos por separado
4. reinstalar dependencias y servicios

Los secretos y datos voluminosos siguen yendo por otro canal.
