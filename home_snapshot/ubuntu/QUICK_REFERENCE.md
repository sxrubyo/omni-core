# 🚀 QUICK REFERENCE - Security Fixes Implementation

## 📋 Archivos Modificados

```bash
# Ver cambios
diff /home/ubuntu/melissa/.env /home/ubuntu/melissa/.env.backup
diff /home/ubuntu/whatsapp-bridge/.env /home/ubuntu/whatsapp-bridge/.env.backup

# Ver cambios en código
git diff /home/ubuntu/melissa/melissa.py  # Si está en git
```

## 🔑 Secretos Generados

```bash
# Melissa Webhook Secret
WEBHOOK_SECRET=eA4UKb5lW7jIZT4Gc7oCuxnIiDxM3eyUpSdfOHVlyNs

# Bridge Webhook Token
WEBHOOK_TOKEN=209e00bd628d72a4525594b6a11cd374c36587a7bae169da19de73bb1dd1f400

# MASTER_API_KEY (generar nuevo):
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

## ✅ Pre-Deployment Checklist

```bash
# 1. Validar sintaxis
python3 -m py_compile /home/ubuntu/melissa/melissa.py && echo "✓ OK"

# 2. Validar imports
python3 -c "from melissa import app; print('✓ Import OK')" 2>&1

# 3. Verificar configuración
echo "MELISSA:" && grep "WEBHOOK_SECRET\|MASTER_API_KEY" /home/ubuntu/melissa/.env
echo "" && echo "BRIDGE:" && grep "WEBHOOK_TOKEN\|WEBHOOK_URL" /home/ubuntu/whatsapp-bridge/.env

# 4. Backup antes de reiniciar
mkdir -p /home/ubuntu/melissa/.backup
cp /home/ubuntu/melissa/.env /home/ubuntu/melissa/.backup/.env.$(date +%s)
cp /home/ubuntu/whatsapp-bridge/.env /home/ubuntu/whatsapp-bridge/.backup/.env.$(date +%s)
```

## 🧪 Pruebas Post-Deployment

```bash
# 1. Health check
curl -s http://localhost:8001/health | jq .

# 2. Broadcast sin auth (debe fallar con 401)
curl -X POST http://localhost:8001/broadcast \
  -H "Content-Type: application/json" \
  -d '{"message":"test"}' \
  -w "\nStatus: %{http_code}\n"

# 3. Broadcast CON auth (necesita MASTER_API_KEY válida)
MASTER_KEY="YOUR_MASTER_API_KEY_HERE"
curl -X POST http://localhost:8001/broadcast \
  -H "X-Master-Key: $MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{"message":"test"}' \
  -w "\nStatus: %{http_code}\n"

# 4. Rate limiting (ejecutar 105 veces, últimas deben ser 429)
for i in {1..105}; do
  curl -s -o /dev/null -w "%{http_code}\n" \
    -X POST http://localhost:8001/webhook/eA4UKb5lW7jIZT4Gc7oCuxnIiDxM3eyUpSdfOHVlyNs \
    -H "Content-Type: application/json" \
    -d '{"ok":true}' | grep -q "429" && echo "✓ Rate limit active at request $i"
done

# 5. Bridge status
curl -s http://localhost:8002/status | jq '.connectionStatus'

# 6. Webhook communication test
# Enviar mensaje de prueba a través del bridge
# Verificar que Melissa lo reciba y responda
```

## 📊 Cambios Técnicos Detallados

### melissa.py

**Agregados:**
- Línea ~60: Imports para slowapi
- Línea ~10873: Limiter initialization
- Línea ~10909: @limiter.limit decorator
- Línea ~11656: _verify_master_key() function
- Línea ~11454: Auth check en /broadcast
- Línea ~11474: Auth check en /reset
- Línea ~10916, 11043, 11049: secrets.compare_digest() replacements

**Líneas aproximadas: +45 líneas nuevas**

### .env Files

**melissa/.env:**
```diff
- WEBHOOK_SECRET=melissa_2026
+ WEBHOOK_SECRET=eA4UKb5lW7jIZT4Gc7oCuxnIiDxM3eyUpSdfOHVlyNs
```

**whatsapp-bridge/.env:**
```diff
- WEBHOOK_URL=http://localhost:8001/webhook/melissa_2026
+ WEBHOOK_URL=http://localhost:8001/webhook/eA4UKb5lW7jIZT4Gc7oCuxnIiDxM3eyUpSdfOHVlyNs
- WEBHOOK_TOKEN=
+ WEBHOOK_TOKEN=209e00bd628d72a4525594b6a11cd374c36587a7bae169da19de73bb1dd1f400
```

## 🔐 Seguridad Post-Implementación

### ⚠️ CRÍTICO: Set MASTER_API_KEY

Antes de reiniciar Melissa, **DEBE** establecer MASTER_API_KEY en .env:

```bash
# Generar clave segura
MASTER_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")

# Agregar al .env
echo "MASTER_API_KEY=$MASTER_KEY" >> /home/ubuntu/melissa/.env

# Guardar en lugar seguro (password manager)
echo "Master Key: $MASTER_KEY"
```

### Monitoreo

```bash
# Ver logs en tiempo real
tail -f /home/ubuntu/melissa/logs/*.log

# Ver rate limit events
grep "rate" /home/ubuntu/melissa/logs/*.log

# Ver authentication failures
grep "Unauthorized\|401" /home/ubuntu/melissa/logs/*.log
```

## 🐛 Troubleshooting

**Problema**: Rate limiting bloquea todos los webhooks
```bash
# Solución: Aumentar límite en el código o resetear después de test
# Cambiar en melissa.py línea ~10909:
# @limiter.limit("100/minute")  # Aumentar número si es necesario
```

**Problema**: Broadcast/Reset retorna siempre 401
```bash
# Verificar MASTER_API_KEY:
grep "MASTER_API_KEY" /home/ubuntu/melissa/.env

# Verificar que está configurado (no vacío)
```

**Problema**: Bridge no conecta con Melissa
```bash
# Verificar URL y token:
grep "WEBHOOK_URL\|WEBHOOK_TOKEN" /home/ubuntu/whatsapp-bridge/.env

# Probar conectividad:
curl -v http://localhost:8001/health
```

## 📞 Contacto / Soporte

Para problemas o preguntas sobre estos fixes:
1. Revisar SECURITY_FIXES_APPLIED.md para contexto completo
2. Revisar logs de Melissa en ~/melissa/logs/
3. Revisar logs de Bridge en ~/whatsapp-bridge/logs/

---

**Última actualización**: 2026-03-19  
**Versión**: 1.0
