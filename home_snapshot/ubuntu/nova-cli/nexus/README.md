# NEXUS STACK — Deploy Guide
# "Un comando. Servidor nuevo. Todo arriba."

## ESTRUCTURA
nexus/
├── docker-compose.yml     ← stack completo
├── .env.example           ← variables (renombrar a .env)
├── .env                   ← NO subir a Git
├── caddy/
│   └── Caddyfile          ← SSL + reverse proxy
└── README.md

## DEPLOY EN SERVIDOR NUEVO

### 1. Requisitos
- Ubuntu 22.04+ 
- Docker + Docker Compose instalados
- Puerto 80 y 443 abiertos en el firewall
- Dominio apuntando a la IP del servidor

### 2. Instalar Docker (si no está)
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker

### 3. Clonar / subir archivos
# Opción A — desde WinSCP: subir la carpeta nexus/ a /home/ubuntu/
# Opción B — desde Git:
# git clone https://github.com/tu-repo/nexus.git

### 4. Configurar variables
cd /home/ubuntu/nexus
cp .env.example .env
nano .env
# Cambiar todos los valores marcados con CAMBIAR_

### 5. Generar encryption key para n8n
openssl rand -hex 16
# Pegar el resultado en N8N_ENCRYPTION_KEY del .env

### 6. Reemplazar dominio en Caddyfile
nano caddy/Caddyfile
# Cambiar "tudominio.com" por tu dominio real

### 7. LANZAR TODO
docker compose up -d

### 8. Verificar
docker compose ps
# Todos deben aparecer como "healthy" o "running"

### 9. Ver logs si algo falla
docker compose logs -f nexus-n8n-main
docker compose logs -f nexus-caddy

## COMANDOS ÚTILES

# Ver estado
docker compose ps

# Reiniciar un servicio
docker compose restart nexus-n8n-main

# Actualizar n8n a la última versión
docker compose pull nexus-n8n-main nexus-n8n-worker
docker compose up -d nexus-n8n-main nexus-n8n-worker

# Backup de postgres
docker exec nexus-postgres pg_dump -U nexus nexus_db > backup_$(date +%Y%m%d).sql

# Apagar todo
docker compose down

# Apagar y borrar volúmenes (CUIDADO — borra datos)
docker compose down -v

## PROXY COLOMBIA (HP via Tailscale)
- El HP debe tener Tailscale activo (100.84.255.20)
- El proxy debe estar corriendo en el HP: puerto 808
- Verificar: curl --proxy http://100.84.255.20:808 https://ipinfo.io/ip
- Debe devolver: 181.51.32.10

## NOTAS
- SSL es automático via Caddy (Let's Encrypt)
- n8n corre en modo queue con worker separado
- Redis persiste datos en volumen
- Postgres persiste datos en volumen
- WhatsApp Bridge: escanear QR en los primeros 60 segundos
