import makeWASocket, {
  useMultiFileAuthState, DisconnectReason, fetchLatestBaileysVersion,
  jidDecode, getContentType, downloadMediaMessage,
} from '@whiskeysockets/baileys';
import qrcode from 'qrcode-terminal';
import express from 'express';
import axios from 'axios';
import pino from 'pino';
import { Boom } from '@hapi/boom';
import { mkdir } from 'fs/promises';

// ─── CONFIG ───────────────────────────────────────────────────────────────────
const CONFIG = {
  PORT:              parseInt(process.env.PORT || '3000'),
  SESSION_DIR:       process.env.SESSION_DIR || './sessions/default',
  WEBHOOK_URL:       process.env.WEBHOOK_URL || '',
  WEBHOOK_TOKEN:     process.env.WEBHOOK_TOKEN || '',
  PHONE_NUMBER:      process.env.PHONE_NUMBER || '',
  LOG_LEVEL:         process.env.LOG_LEVEL || 'info',
  PRESENCE_TIMEOUT:  parseInt(process.env.PRESENCE_TIMEOUT || '1800000'), // 30 min
  KEEP_ALIVE_MS:     parseInt(process.env.KEEP_ALIVE_MS || '300000'),     // 5 min
  MAX_RETRIES:       parseInt(process.env.MAX_RETRIES || '3'),
  RETRY_BASE_MS:     parseInt(process.env.RETRY_BASE_MS || '2000'),
  TYPING_DEFAULT_MS: parseInt(process.env.TYPING_DEFAULT_MS || '8000'),   // 8 seg
  // Cola de salida: tiempo máximo que un mensaje espera en cola (ms)
  OUTQUEUE_TTL_MS:   parseInt(process.env.OUTQUEUE_TTL_MS || '30000'),    // 30s
  // Tiempo máximo esperando reconexión antes de responder error al caller
  OUTQUEUE_WAIT_MS:  parseInt(process.env.OUTQUEUE_WAIT_MS || '20000'),   // 20s
};

const logger = pino(
  { level: CONFIG.LOG_LEVEL },
  pino.transport({ target: 'pino-pretty', options: { colorize: true } })
);

// ─── STATE ────────────────────────────────────────────────────────────────────
let sock = null;
let qrString = null;
let connectionStatus = 'disconnected';
let pairingCodeShown = false;
let presenceTimer = null;
let keepAliveTimer = null;
let reconnectTimer = null;
let bridgeStartInFlight = false;
let messageQueue = [];
let isProcessingQueue = false;
let messageStats = { sent: 0, received: 0, failed: 0, retried: 0 };

// Mapa de timers de composing por JID para poder cancelarlos al enviar
const composingTimers = new Map();

// ─── COLA DE SALIDA (outgoing queue) ─────────────────────────────────────────
// Cuando el bridge está reconectando, los /send se encolan aquí.
// Al volver la conexión, se drena automáticamente.
// Cada item: { jid, message, resolve, reject, expiresAt }
const outgoingQueue = [];

async function drainOutgoingQueue() {
  if (connectionStatus !== 'open' || outgoingQueue.length === 0) return;
  const now = Date.now();
  while (outgoingQueue.length > 0) {
    const item = outgoingQueue.shift();
    if (now > item.expiresAt) {
      item.reject(new Error('Mensaje expirado en cola — bridge tardó demasiado en reconectar'));
      continue;
    }
    try {
      await stopComposing(item.jid);
      await new Promise(r => setTimeout(r, 350));
      const result = await sock.sendMessage(item.jid, { text: item.message });
      messageStats.sent++;
      logger.info({ to: item.jid, msgId: result?.key?.id }, '✅ Mensaje enviado (desde cola)');
      item.resolve({ ok: true, messageId: result?.key?.id, queued: true });
    } catch (err) {
      messageStats.failed++;
      logger.error({ to: item.jid, err: err.message }, '❌ Error enviando desde cola');
      item.reject(err);
    }
    // Pequeña pausa anti-ban entre mensajes de la cola
    if (outgoingQueue.length > 0) await new Promise(r => setTimeout(r, 400));
  }
}

/**
 * Enviar mensaje con resiliencia a reconexión.
 * Si está conectado → envía directo.
 * Si está reconectando → espera hasta OUTQUEUE_WAIT_MS y reintenta.
 */
async function sendWithQueue(jid, message) {
  if (connectionStatus === 'open') {
    // Conexión activa — enviar directo
    await stopComposing(jid);
    await new Promise(r => setTimeout(r, 350));
    const result = await sock.sendMessage(jid, { text: message });
    messageStats.sent++;
    logger.info({ to: jid, msgId: result?.key?.id }, '✅ Mensaje enviado');
    return { ok: true, messageId: result?.key?.id };
  }

  // Reconectando — encolar y esperar
  logger.warn({ to: jid }, '⏳ Bridge reconectando — mensaje encolado');
  return new Promise((resolve, reject) => {
    const expiresAt = Date.now() + CONFIG.OUTQUEUE_TTL_MS;
    outgoingQueue.push({ jid, message, resolve, reject, expiresAt });

    // Timeout de seguridad: si no reconecta en OUTQUEUE_WAIT_MS, falla
    setTimeout(() => {
      const idx = outgoingQueue.findIndex(i => i.resolve === resolve);
      if (idx !== -1) {
        outgoingQueue.splice(idx, 1);
        reject(new Error(`Bridge no reconectó en ${CONFIG.OUTQUEUE_WAIT_MS}ms`));
      }
    }, CONFIG.OUTQUEUE_WAIT_MS);
  });
}

async function stopComposing(jid) {
  const t = composingTimers.get(jid);
  if (t) {
    clearInterval(t.interval);
    clearTimeout(t.timeout);
    composingTimers.delete(jid);
  }
  try { await sock.sendPresenceUpdate('paused', jid); } catch (_) {}
}

// ─── UTILS ────────────────────────────────────────────────────────────────────

// FIX: normaliza cualquier formato de JID a s.whatsapp.net
// @c.us es el formato viejo de Baileys — los envíos fallan silenciosamente con él
const toJid = (to) => {
  if (!to) return '';
  // Si ya tiene @g.us (grupo) lo dejamos tal cual
  if (to.includes('@g.us')) return to;
  // Extraer solo el número y forzar @s.whatsapp.net
  const number = to.includes('@') ? to.split('@')[0] : to;
  return `${number}@s.whatsapp.net`;
};

const randomDelay = (min = 800, max = 3000) =>
  new Promise(r => setTimeout(r, Math.floor(Math.random() * (max - min + 1)) + min));

async function fireWebhook(payload, retries = CONFIG.MAX_RETRIES) {
  if (!CONFIG.WEBHOOK_URL) return;
  for (let attempt = 1; attempt <= retries; attempt++) {
    try {
      const headers = { 'Content-Type': 'application/json' };
      if (CONFIG.WEBHOOK_TOKEN) headers['Authorization'] = `Bearer ${CONFIG.WEBHOOK_TOKEN}`;
      await axios.post(CONFIG.WEBHOOK_URL, payload, { headers, timeout: 15000 });
      logger.info({ event: payload.event }, '📤 Webhook enviado OK');
      return;
    } catch (err) {
      messageStats.retried++;
      const wait = CONFIG.RETRY_BASE_MS * Math.pow(2, attempt - 1);
      logger.warn({ attempt, wait, err: err.message }, `⚠️ Webhook falló — reintento ${attempt}/${retries}`);
      if (attempt < retries) await new Promise(r => setTimeout(r, wait));
      else {
        messageStats.failed++;
        logger.error({ payload: payload.event }, '❌ Webhook falló definitivamente');
      }
    }
  }
}

// ─── PRESENCE MANAGER ─────────────────────────────────────────────────────────

async function setPresence(status) {
  try {
    await sock.sendPresenceUpdate(status);
    logger.info({ status }, '👁️ Presencia global actualizada');
  } catch (e) {
    logger.error({ err: e.message }, '❌ Error actualizando presencia');
  }
}

function schedulePresenceOff(timeout = CONFIG.PRESENCE_TIMEOUT) {
  if (presenceTimer) clearTimeout(presenceTimer);
  presenceTimer = setTimeout(async () => {
    await setPresence('unavailable');
    presenceTimer = null;
    logger.info('⏰ Presencia expirada → offline automático');
  }, timeout);
}

async function goOnline(timeoutMs = CONFIG.PRESENCE_TIMEOUT) {
  await setPresence('available');
  schedulePresenceOff(timeoutMs);
}

// ─── KEEP-ALIVE ───────────────────────────────────────────────────────────────

function startKeepAlive() {
  if (keepAliveTimer) clearInterval(keepAliveTimer);
  keepAliveTimer = setInterval(async () => {
    if (connectionStatus !== 'open') {
      logger.warn('💔 Keep-alive detectó desconexión silenciosa — reconectando...');
      clearInterval(keepAliveTimer);
      await startBridge();
      return;
    }
    try {
      if (sock?.ws?.readyState === 1) sock.ws.ping?.();
      logger.debug('💚 Keep-alive ping OK');
    } catch (e) {
      logger.warn({ err: e.message }, '⚠️ Keep-alive ping falló');
    }
  }, CONFIG.KEEP_ALIVE_MS);
  logger.info({ interval: CONFIG.KEEP_ALIVE_MS }, '💓 Keep-alive iniciado');
}

// ─── BRIDGE CORE ──────────────────────────────────────────────────────────────

async function startBridge() {
  if (bridgeStartInFlight) {
    logger.warn('⏳ startBridge ignorado: ya hay un arranque en curso');
    return;
  }
  bridgeStartInFlight = true;
  if (reconnectTimer) {
    clearTimeout(reconnectTimer);
    reconnectTimer = null;
  }
  await mkdir(CONFIG.SESSION_DIR, { recursive: true });
  try {
    const { state, saveCreds } = await useMultiFileAuthState(CONFIG.SESSION_DIR);
    const { version } = await fetchLatestBaileysVersion();
    logger.info({ version }, 'Iniciando Baileys v' + version.join('.'));

    sock = makeWASocket({
      version, auth: state,
      logger: pino({ level: 'silent' }),
      printQRInTerminal: false,
      browser: ['WhatsApp Bridge', 'Chrome', '120.0.0'],
      syncFullHistory: false,
      markOnlineOnConnect: false,
      // FIX: getMessage es requerido para que Baileys envíe delivery receipts
      // Sin esto los mensajes enviados muestran un solo chulo gris permanentemente
      // porque WA espera que el "dispositivo" confirme que recibió el mensaje
      getMessage: async (key) => {
        return { conversation: '' };
      },
    });

  // ── Connection Update ──────────────────────────────────────
    sock.ev.on('connection.update', async (update) => {
      const { connection, lastDisconnect, qr } = update;

      if (qr) {
        qrString = qr;
        logger.info('QR generado — escanea con WhatsApp:');
        qrcode.generate(qr, { small: true });

        if (CONFIG.PHONE_NUMBER && !pairingCodeShown) {
          pairingCodeShown = true;
          try {
            const code = await sock.requestPairingCode(CONFIG.PHONE_NUMBER);
            console.log('\n╔══════════════════════════════╗');
            console.log(`║  PAIRING CODE:  ${code.padEnd(12)} ║`);
            console.log('╚══════════════════════════════╝\n');
          } catch (err) { logger.error({ err }, 'Error con Pairing Code'); }
        }
      }

      if (connection === 'open') {
        connectionStatus = 'open';
        qrString = null;
        if (reconnectTimer) {
          clearTimeout(reconnectTimer);
          reconnectTimer = null;
        }
        logger.info('✅ WhatsApp conectado');
        startKeepAlive();
        await setPresence('unavailable');

        // ── CRÍTICO: drenar cola de mensajes pendientes ──────────
        if (outgoingQueue.length > 0) {
          logger.info({ pending: outgoingQueue.length }, '📬 Drenando cola de mensajes pendientes...');
          // Pequeña pausa para que WA estabilice la conexión antes de enviar
          await new Promise(r => setTimeout(r, 800));
          await drainOutgoingQueue();
        }
      }

      if (connection === 'connecting') { connectionStatus = 'connecting'; }

      if (connection === 'close') {
        const code = lastDisconnect?.error instanceof Boom
          ? lastDisconnect.error.output.statusCode : 0;
        const reason = lastDisconnect?.error?.message || 'unknown';
        connectionStatus = 'disconnected';
        pairingCodeShown = false;
        if (keepAliveTimer) clearInterval(keepAliveTimer);
        logger.warn({ code, reason }, '🔌 WhatsApp cerrado');
        if (code !== DisconnectReason.loggedOut) {
          if (!reconnectTimer) {
            logger.info('Reconectando en 5s...');
            reconnectTimer = setTimeout(() => {
              reconnectTimer = null;
              startBridge().catch(err => logger.error({ err: err.message }, '❌ Error en reconexión programada'));
            }, 5000);
          }
        } else {
          logger.warn('Sesión cerrada. Borra el volumen y reinicia.');
        }
      }
    });

    sock.ev.on('creds.update', saveCreds);

    // ── Messages Received ──────────────────────────────────────
    sock.ev.on('messages.upsert', async ({ messages, type }) => {
    if (type !== 'notify') return;

    for (const msg of messages) {
      if (msg.key.fromMe) continue;

      messageStats.received++;
      // NOTE: NO llamamos goOnline() global aquí — aparecería online para todos los contactos.
      // La presencia la maneja Melissa por JID específico via /typing antes de cada respuesta.
      // Solo marcamos presencia activa para el remitente específico:
      const senderJid = msg.key.remoteJid;
      if (senderJid && !senderJid.endsWith('@g.us')) {
        try {
          await sock.sendPresenceUpdate('available', senderJid);
        } catch (_) {}
      }

      const jid = msg.key.remoteJid ?? '';
      const decoded = jidDecode(jid) ?? {};
      const contentType = getContentType(msg.message ?? {});

      const text = msg.message?.conversation
        ?? msg.message?.extendedTextMessage?.text
        ?? msg.message?.imageMessage?.caption
        ?? msg.message?.videoMessage?.caption
        ?? '';

      // ── Descarga de audio ──────────────────────────────────
      let audioBase64 = null;
      let audioMime = null;
      const isAudio = contentType === 'audioMessage' || contentType === 'pttMessage';

      if (isAudio) {
        try {
          logger.info({ contentType }, '🎵 Descargando audio...');
          const buffer = await downloadMediaMessage(
            msg, 'buffer', {},
            { logger, reuploadRequest: sock.updateMediaMessage }
          );
          audioBase64 = buffer.toString('base64');
          audioMime = msg.message?.audioMessage?.mimetype || 'audio/ogg; codecs=opus';
          logger.info({ bytes: buffer.length, mime: audioMime }, '✅ Audio descargado OK');
        } catch (err) {
          logger.error({ err: err.message }, '❌ Error descargando audio');
        }
      }

      // ── Descarga de imagen ─────────────────────────────────
      let imageBase64 = null;
      let imageMime = null;
      const isImage = contentType === 'imageMessage';
      if (isImage) {
        try {
          const buffer = await downloadMediaMessage(
            msg, 'buffer', {},
            { logger, reuploadRequest: sock.updateMediaMessage }
          );
          imageBase64 = buffer.toString('base64');
          imageMime = msg.message?.imageMessage?.mimetype || 'image/jpeg';
          logger.info({ bytes: buffer.length }, '🖼️ Imagen descargada OK');
        } catch (err) {
          logger.warn({ err: err.message }, '⚠️ No se pudo descargar imagen');
        }
      }

      // ── Descarga de documento ──────────────────────────────
      let docBase64 = null;
      let documentMime = null;
      let documentName = null;
      const isDocument = contentType === 'documentMessage';
      if (isDocument) {
        try {
          const buffer = await downloadMediaMessage(
            msg, 'buffer', {},
            { logger, reuploadRequest: sock.updateMediaMessage }
          );
          docBase64 = buffer.toString('base64');
          documentMime = msg.message?.documentMessage?.mimetype || 'application/octet-stream';
          documentName = msg.message?.documentMessage?.fileName || 'document.bin';
          logger.info({ bytes: buffer.length, filename: documentName }, '📄 Documento descargado OK');
        } catch (err) {
          logger.warn({ err: err.message }, '⚠️ No se pudo descargar documento');
        }
      }

      const payload = {
        event:       'message.received',
        timestamp:   Date.now(),
        // FIX: decoded.server puede ser 'c.us' (formato viejo) o 's.whatsapp.net'
        // Baileys moderno usa s.whatsapp.net — forzamos siempre ese formato
        // para que Melissa pueda responder al JID correcto
        from:        decoded.user ? `${decoded.user}@s.whatsapp.net` : jid,
        phone:       decoded.user ?? jid.split('@')[0],
        isGroup:     jid.endsWith('@g.us'),
        pushName:    msg.pushName ?? '',
        messageId:   msg.key.id,
        messageType: contentType ?? 'unknown',
        text,
        key:         msg.key,
        remoteJid:   jid,
        channel:     'whatsapp',
        isAudio, audioBase64, audioMime,
        isImage, imageBase64, imageMime,
        isDocument, docBase64, documentMime, documentName,
      };

      logger.info({ from: payload.from, type: payload.messageType, isAudio, isImage, isDocument }, '📨 Mensaje recibido');
      await fireWebhook(payload);
    }
    });

    // ── Message Status Update ──────────────────────────────────
    sock.ev.on('message-receipt.update', async (updates) => {
    for (const update of updates) {
      const typeMap = { 2: 'delivered', 3: 'read', 4: 'played' };
      const status = typeMap[update.receipt?.type] || 'sent';

      await fireWebhook({
        event:     'message.status',
        messageId: update.key?.id,
        remoteJid: update.key?.remoteJid,
        status,
        timestamp: Date.now(),
        channel:   'whatsapp',
      });

      logger.info({ messageId: update.key?.id, status }, '📬 Status actualizado');
    }
    });
  } finally {
    bridgeStartInFlight = false;
  }
}

// ─── API REST ─────────────────────────────────────────────────────────────────
const app = express();
app.use(express.json({ limit: '100mb' }));

const requireConnected = (req, res, next) => {
  if (connectionStatus !== 'open')
    return res.status(503).json({ error: 'WhatsApp no conectado', status: connectionStatus });
  next();
};

// ── GET /status ──────────────────────────────────────────────────────────────
app.get('/status', (req, res) => res.json({
  status: connectionStatus,
  jid: sock?.user?.id ?? null,
  name: sock?.user?.name ?? null,
  stats: messageStats,
  queueLength: messageQueue.length,
  outgoingQueueLength: outgoingQueue.length,
  presenceActive: presenceTimer !== null,
}));

// ── GET /health ──────────────────────────────────────────────────────────────
app.get('/health', (req, res) => res.json({
  ok: connectionStatus === 'open',
  status: connectionStatus,
  outgoingQueue: outgoingQueue.length,
  uptime: Math.floor(process.uptime()),
}));

// ── GET /qr ──────────────────────────────────────────────────────────────────
app.get('/qr', (req, res) => {
  if (connectionStatus === 'open') return res.json({ connected: true });
  if (!qrString) return res.status(404).json({ error: 'QR aún no disponible' });
  res.json({ qr: qrString });
});

// ── GET /stats ───────────────────────────────────────────────────────────────
app.get('/stats', (req, res) => res.json({
  connection: connectionStatus,
  messages: messageStats,
  queue: { pending: messageQueue.length, processing: isProcessingQueue },
  outgoingQueue: outgoingQueue.length,
  uptime: Math.floor(process.uptime()),
  memory: process.memoryUsage(),
}));

// ── POST /send — texto (con cola de resiliencia) ──────────────────────────────
app.post('/send', async (req, res) => {
  const { to, message } = req.body;
  if (!to || !message) return res.status(400).json({ error: 'Faltan: to, message' });
  try {
    const jid = toJid(to);
    const result = await sendWithQueue(jid, message);
    res.json(result);
  } catch (err) {
    messageStats.failed++;
    logger.error({ to, err: err.message }, '❌ Error enviando mensaje');
    res.status(500).json({ error: err.message });
  }
});

// ── POST /send-audio ─────────────────────────────────────────────────────────
app.post('/send-audio', requireConnected, async (req, res) => {
  const { to, audioBase64, mimeType = 'audio/mpeg' } = req.body;
  if (!to || !audioBase64) return res.status(400).json({ error: 'Faltan: to, audioBase64' });
  try {
    const buffer = Buffer.from(audioBase64, 'base64');
    const result = await sock.sendMessage(toJid(to), {
      audio: buffer,
      mimetype: mimeType,
      ptt: mimeType.includes('ogg'),
    });
    messageStats.sent++;
    res.json({ ok: true, messageId: result?.key?.id });
  } catch (err) {
    messageStats.failed++;
    res.status(500).json({ error: err.message });
  }
});

// ── POST /send-image ─────────────────────────────────────────────────────────
app.post('/send-image', requireConnected, async (req, res) => {
  const { to, imageBase64, mimeType = 'image/jpeg', caption = '' } = req.body;
  if (!to || !imageBase64) return res.status(400).json({ error: 'Faltan: to, imageBase64' });
  try {
    const buffer = Buffer.from(imageBase64, 'base64');
    const result = await sock.sendMessage(toJid(to), {
      image: buffer, mimetype: mimeType, caption,
    });
    messageStats.sent++; 
    res.json({ ok: true, messageId: result?.key?.id });
  } catch (err) {
    messageStats.failed++;
    res.status(500).json({ error: err.message });
  }
});

// ── POST /send-document ──────────────────────────────────────────────────────
app.post('/send-document', requireConnected, async (req, res) => {
  const { to, docBase64, mimeType = 'application/pdf', filename = 'document.pdf', caption = '' } = req.body;
  if (!to || !docBase64) return res.status(400).json({ error: 'Faltan: to, docBase64' });
  try {
    const buffer = Buffer.from(docBase64, 'base64');
    const result = await sock.sendMessage(toJid(to), {
      document: buffer, mimetype: mimeType, fileName: filename, caption,
    });
    messageStats.sent++;
    res.json({ ok: true, messageId: result?.key?.id });
  } catch (err) {
    messageStats.failed++;
    res.status(500).json({ error: err.message });
  }
});

// ── POST /send-location ──────────────────────────────────────────────────────
app.post('/send-location', requireConnected, async (req, res) => {
  const { to, latitude, longitude, name = '', address = '' } = req.body;
  if (!to || latitude == null || longitude == null)
    return res.status(400).json({ error: 'Faltan: to, latitude, longitude' });
  try {
    const result = await sock.sendMessage(toJid(to), {
      location: {
        degreesLatitude:  parseFloat(latitude),
        degreesLongitude: parseFloat(longitude),
        name, address,
      }
    });
    messageStats.sent++;
    res.json({ ok: true, messageId: result?.key?.id });
  } catch (err) {
    messageStats.failed++;
    res.status(500).json({ error: err.message });
  }
});

// ── POST /send-contact ───────────────────────────────────────────────────────
app.post('/send-contact', requireConnected, async (req, res) => {
  const { to, contactName, contactPhone, organization = '' } = req.body;
  if (!to || !contactName || !contactPhone)
    return res.status(400).json({ error: 'Faltan: to, contactName, contactPhone' });
  try {
    const phone = contactPhone.replace(/\D/g, '');
    const vcard = [
      'BEGIN:VCARD', 'VERSION:3.0',
      `FN:${contactName}`,
      `ORG:${organization}`,
      `TEL;type=CELL;type=VOICE;waid=${phone}:+${phone}`,
      'END:VCARD'
    ].join('\n');

    const result = await sock.sendMessage(toJid(to), {
      contacts: { displayName: contactName, contacts: [{ vcard }] }
    });
    messageStats.sent++;
    res.json({ ok: true, messageId: result?.key?.id });
  } catch (err) {
    messageStats.failed++;
    res.status(500).json({ error: err.message });
  }
});

// ── POST /bulk-send ──────────────────────────────────────────────────────────
app.post('/bulk-send', requireConnected, async (req, res) => {
  const { messages } = req.body;
  if (!Array.isArray(messages) || messages.length === 0)
    return res.status(400).json({ error: 'messages debe ser un array no vacío' });

  logger.info({ count: messages.length }, '📦 Bulk send iniciado');
  res.json({ ok: true, total: messages.length, status: 'processing' });

  ;(async () => {
    for (let i = 0; i < messages.length; i++) {
      const { to, message, delayMin = 1500, delayMax = 5000 } = messages[i];
      try {
        const jid = toJid(to);
        await sock.sendPresenceUpdate('composing', jid);
        const typingMs = Math.min(message.length * 40, 6000);
        await new Promise(r => setTimeout(r, typingMs));
        await sock.sendPresenceUpdate('paused', jid);
        await sock.sendMessage(jid, { text: message });
        messageStats.sent++;
        logger.info({ to, index: i + 1, total: messages.length }, '✅ Bulk enviado');
      } catch (err) {
        messageStats.failed++;
        logger.error({ to, err: err.message }, '❌ Bulk error');
      }
      if (i < messages.length - 1) {
        const delay = Math.floor(Math.random() * (delayMax - delayMin + 1)) + delayMin;
        await new Promise(r => setTimeout(r, delay));
      }
    }
    logger.info({ total: messages.length }, '🎉 Bulk send completado');
  })();
});

// ── POST /typing ─────────────────────────────────────────────────────────────
app.post('/typing', requireConnected, async (req, res) => {
  const { to, duration = CONFIG.TYPING_DEFAULT_MS } = req.body;
  if (!to) return res.status(400).json({ error: 'Falta: to' });
  try {
    const jid = toJid(to);
    await sock.sendPresenceUpdate('composing', jid);

    const prev = composingTimers.get(jid);
    if (prev) { clearInterval(prev.interval); clearTimeout(prev.timeout); }

    const REFRESH_MS = 4500;
    let elapsed = 0;
    const interval = setInterval(async () => {
      elapsed += REFRESH_MS;
      if (elapsed < duration) {
        await sock.sendPresenceUpdate('composing', jid).catch(() => {});
      } else {
        clearInterval(interval);
        composingTimers.delete(jid);
      }
    }, REFRESH_MS);

    const timeout = setTimeout(async () => {
      clearInterval(interval);
      composingTimers.delete(jid);
      await sock.sendPresenceUpdate('paused', jid).catch(() => {});
    }, duration);

    composingTimers.set(jid, { interval, timeout });
    res.json({ ok: true, duration });
  } catch (err) { res.status(500).json({ error: err.message }); }
});

// ── POST /recording ──────────────────────────────────────────────────────────
app.post('/recording', requireConnected, async (req, res) => {
  const { to, duration = 5000 } = req.body;
  if (!to) return res.status(400).json({ error: 'Falta: to' });
  try {
    const jid = toJid(to);
    await sock.sendPresenceUpdate('recording', jid);

    const REFRESH_MS = 4500;
    let elapsed = 0;
    const interval = setInterval(async () => {
      elapsed += REFRESH_MS;
      if (elapsed < duration) {
        await sock.sendPresenceUpdate('recording', jid).catch(() => {});
      } else {
        clearInterval(interval);
      }
    }, REFRESH_MS);

    setTimeout(async () => {
      clearInterval(interval);
      await sock.sendPresenceUpdate('paused', jid).catch(() => {});
    }, duration);

    res.json({ ok: true, duration });
  } catch (err) { res.status(500).json({ error: err.message }); }
});

// ── POST /read ────────────────────────────────────────────────────────────────
app.post('/read', requireConnected, async (req, res) => {
  const { to, messageId } = req.body;
  if (!to || !messageId) return res.status(400).json({ error: 'Faltan: to, messageId' });
  try {
    const jid = toJid(to);
    await sock.readMessages([{ remoteJid: jid, id: messageId, fromMe: false }]);
    res.json({ ok: true });
  } catch (err) { res.status(500).json({ error: err.message }); }
});

// ── POST /react ───────────────────────────────────────────────────────────────
app.post('/react', requireConnected, async (req, res) => {
  const { to, messageId, emoji } = req.body;
  if (!to || !messageId || !emoji)
    return res.status(400).json({ error: 'Faltan: to, messageId, emoji' });
  try {
    const jid = toJid(to);
    await sock.sendMessage(jid, {
      react: { text: emoji, key: { remoteJid: jid, id: messageId, fromMe: false } }
    });
    res.json({ ok: true });
  } catch (err) { res.status(500).json({ error: err.message }); }
});

// ── POST /presence ────────────────────────────────────────────────────────────
app.post('/presence', requireConnected, async (req, res) => {
  const { status = 'available', timeout = CONFIG.PRESENCE_TIMEOUT } = req.body;
  if (!['available', 'unavailable'].includes(status))
    return res.status(400).json({ error: 'status debe ser: available | unavailable' });
  try {
    if (status === 'available') {
      await goOnline(timeout);
    } else {
      if (presenceTimer) clearTimeout(presenceTimer);
      presenceTimer = null;
      await setPresence('unavailable');
    }
    res.json({ ok: true, status, timeout });
  } catch (err) { res.status(500).json({ error: err.message }); }
});

// ── POST /logout ──────────────────────────────────────────────────────────────
app.post('/logout', async (req, res) => {
  try { await sock?.logout(); res.json({ ok: true }); }
  catch (err) { res.status(500).json({ error: err.message }); }
});

// ─── BOOT ─────────────────────────────────────────────────────────────────────
app.listen(CONFIG.PORT, () =>
  logger.info(`🌐 XUS WhatsApp Bridge v2.1 — http://0.0.0.0:${CONFIG.PORT}`)
);

await startBridge();
