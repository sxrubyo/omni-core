# Eco Nova Mega Agent

## Objetivo

Construir `eco-nova` como un agente autonomo local con patron de gateway, onboarding guiado y enrutamiento fiel a la arquitectura de `Workflows-n8n`.

## Patrones adoptados de OpenClaw

- CLI con wizard de onboarding en lugar de depender de archivos sueltos.
- Gateway Telegram por long polling con validacion de token.
- Politicas de acceso para DM: `allowlist`, `pairing`, `open`.
- Estado persistente local para offsets, pairing y memoria de sesion.
- Separacion entre gateway, router, backend y arquitectura.

## Arquitectura heredada de Workflows-n8n

- Entrada: `XUS Begin v1.0 - Entrance & Schedules`
- Orquestador: `XUS Talking v1.0 - Main Orchestrator`
- Clusters principales:
  - `SISTEMA`
  - `NEGOCIO`
  - `VIDA`
  - `MULTIMEDIA`
- Salida: `XUS Output Engine v1.0`

## Implementacion actual

- Router local basado en los dominios y vocabulario del orquestador original.
- Descubrimiento automatico de clusters y subagentes reales desde `Workflows-n8n`.
- Backend configurable:
  - `openai`
  - `codex`
  - `auto`
- Memoria corta por sesion para mantener contexto entre mensajes.
- CLI simplificado inspirado en `nova-os`:
  - `eco start`
  - `eco status`
  - `eco chat ...`
  - `eco tg connect`
  - `eco tg start`
  - `eco see ...`
  - `eco listen ...`
- Layout runtime inspirado en `.openclaw`:
  - `~/.eco-nova/workspace`
  - `~/.eco-nova/logs`
  - `~/.eco-nova/memory`
  - `~/.eco-nova/channels/telegram`
  - `~/.eco-nova/credentials`
  - `~/.eco-nova/devices`

## Siguiente iteracion natural

- Conectar acciones reales por cluster:
  - `NEGOCIO` con CRM / outreach
  - `VIDA` con calendario y habitos
  - `MULTIMEDIA` con TV / Android
  - `SISTEMA` con n8n / Drive / reportes
- Añadir Webhooks de n8n para ejecucion real de subagentes.
