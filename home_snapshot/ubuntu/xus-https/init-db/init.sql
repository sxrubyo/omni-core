#!/bin/bash
# =============================================================================
# Script de inicializacion de PostgreSQL
# Crea la base de datos "evolution" para Evolution API
# SOLO se ejecuta en la PRIMERA inicializacion de PostgreSQL
# Ruta: /home/ubuntu/xus-https/init-db/create-evolution-db.sh
# =============================================================================
set -e

echo ">>> Creando base de datos 'evolution' para Evolution API..."

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- Crear la base de datos para Evolution API
    CREATE DATABASE evolution;

    -- Otorgar permisos completos al usuario n8n sobre la DB evolution
    GRANT ALL PRIVILEGES ON DATABASE evolution TO $POSTGRES_USER;
EOSQL

# Conectarse a la DB evolution y otorgar permisos en el schema public
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "evolution" <<-EOSQL
    GRANT ALL ON SCHEMA public TO $POSTGRES_USER;
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO $POSTGRES_USER;
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO $POSTGRES_USER;
EOSQL

echo ">>> Base de datos 'evolution' creada exitosamente."
