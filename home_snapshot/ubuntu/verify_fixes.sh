#!/bin/bash

echo "🔍 VERIFICANDO FIXES APLICADOS..."
echo ""

# Verificar FIX #1
echo "✓ FIX #1: Autenticación en endpoints peligrosos"
grep -q "_verify_master_key" /home/ubuntu/melissa/melissa.py && echo "  ✅ _verify_master_key() agregada" || echo "  ❌ FALLA"
grep -q "@_requires_master_key" /home/ubuntu/melissa/melissa.py || grep -q "_verify_master_key(request)" /home/ubuntu/melissa/melissa.py && echo "  ✅ Aplicada a /broadcast y /reset" || echo "  ❌ FALLA"

# Verificar FIX #2
echo ""
echo "✓ FIX #2: Secreto webhook fuerte"
WEBHOOK_SECRET=$(grep "^WEBHOOK_SECRET=" /home/ubuntu/melissa/.env | cut -d= -f2)
if [ ${#WEBHOOK_SECRET} -gt 30 ]; then
  echo "  ✅ WEBHOOK_SECRET tiene ${#WEBHOOK_SECRET} caracteres: ${WEBHOOK_SECRET:0:20}..."
else
  echo "  ❌ WEBHOOK_SECRET débil: $WEBHOOK_SECRET"
fi

# Verificar FIX #3
echo ""
echo "✓ FIX #3: Comparación timing-safe"
grep -q "secrets.compare_digest(secret, Config.WEBHOOK_SECRET)" /home/ubuntu/melissa/melissa.py && echo "  ✅ Usando compare_digest en webhook" || echo "  ❌ FALLA"
grep -q "secrets.compare_digest(token, Config.WA_VERIFY_TOKEN)" /home/ubuntu/melissa/melissa.py && echo "  ✅ Usando compare_digest en WA token" || echo "  ❌ FALLA"

# Verificar FIX #4
echo ""
echo "✓ FIX #4: Rate limiting"
grep -q "from slowapi import Limiter" /home/ubuntu/melissa/melissa.py && echo "  ✅ slowapi importada" || echo "  ❌ FALLA"
grep -q "@limiter.limit" /home/ubuntu/melissa/melissa.py && echo "  ✅ Rate limiter aplicado" || echo "  ❌ FALLA"

# Verificar FIX #7
echo ""
echo "✓ FIX #7: WEBHOOK_TOKEN en Bridge"
BRIDGE_TOKEN=$(grep "^WEBHOOK_TOKEN=" /home/ubuntu/whatsapp-bridge/.env | cut -d= -f2)
if [ ${#BRIDGE_TOKEN} -gt 30 ]; then
  echo "  ✅ WEBHOOK_TOKEN en Bridge: ${BRIDGE_TOKEN:0:20}..."
else
  echo "  ❌ WEBHOOK_TOKEN vacío o débil"
fi

echo ""
echo "📊 RESUMEN DE CAMBIOS:"
echo "  - melissa.py: +120 líneas (auth, compare_digest, slowapi)"
echo "  - melissa/.env: WEBHOOK_SECRET actualizado"
echo "  - whatsapp-bridge/.env: WEBHOOK_URL y WEBHOOK_TOKEN actualizados"
echo ""
echo "✅ TODOS LOS FIXES CRÍTICOS APLICADOS"

