import type { FastifyInstance, FastifyRequest, FastifyReply } from "fastify";
import type { IncomingMessage } from "../types/index.js";
import { processMessage } from "../agent/pipeline.js";

export function registerTelegramWebhook(app: FastifyInstance): void {
  app.post(`/telegram/${process.env.WEBHOOK_SECRET}`, async (req: FastifyRequest, reply: FastifyReply) => {
    reply.send({ ok: true });
    const message = normalizeTelegram(req.body as Record<string, unknown>);
    if (message) await processMessage(message).catch(console.error);
  });
  console.log("[Gateway] Telegram ✓");
}

export function registerWhatsAppWebhook(app: FastifyInstance): void {
  app.post("/whatsapp/webhook", async (req: FastifyRequest, reply: FastifyReply) => {
    reply.send({ ok: true });
    const message = normalizeWA(req.body as Record<string, unknown>);
    if (message) await processMessage(message).catch(console.error);
  });
  console.log("[Gateway] WhatsApp ✓");
}

function normalizeTelegram(body: Record<string, unknown>): IncomingMessage | null {
  if (body.callback_query) {
    const cb = body.callback_query as Record<string, unknown>;
    const cbMsg = cb.message as Record<string, unknown>;
    return { id: String(cb.id), channel: "telegram", type: "callback",
      text: String(cb.data || ""), chatId: String((cbMsg?.chat as Record<string, unknown>)?.id || ""),
      userId: String((cb.from as Record<string, unknown>)?.id || ""), timestamp: new Date(), raw: body };
  }
  const msg = body.message as Record<string, unknown>;
  if (!msg) return null;
  const chat = msg.chat as Record<string, unknown>;
  const from = msg.from as Record<string, unknown>;
  const base = { channel: "telegram" as const, chatId: String(chat?.id || ""),
    userId: String(from?.id || ""), username: String(from?.username || from?.first_name || ""),
    timestamp: new Date(Number(msg.date) * 1000), raw: body };
  if (msg.voice || msg.audio) return { ...base, id: String(msg.message_id), type: "audio", text: "" };
  if (msg.text) return { ...base, id: String(msg.message_id), type: "text", text: String(msg.text) };
  return null;
}

function normalizeWA(body: Record<string, unknown>): IncomingMessage | null {
  if (body.event !== "message.received") return null;
  const from = String(body.from || "");
  if (Boolean(body.isGroup)) return null;
  const base = { channel: "whatsapp" as const, chatId: from,
    userId: String(body.phone || from), username: String(body.pushName || ""),
    timestamp: new Date(Number(body.timestamp) || Date.now()), raw: body };
  if (body.isAudio && body.audioBase64)
    return { ...base, id: String(body.messageId), type: "audio", text: "",
      audioBase64: String(body.audioBase64), audioMimeType: String(body.audioMime || "audio/ogg") };
  const text = String(body.text || "");
  if (!text) return null;
  return { ...base, id: String(body.messageId), type: "text", text };
}
