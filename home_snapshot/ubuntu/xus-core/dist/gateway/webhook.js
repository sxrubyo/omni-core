"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.registerTelegramWebhook = registerTelegramWebhook;
exports.registerWhatsAppWebhook = registerWhatsAppWebhook;
const pipeline_js_1 = require("../agent/pipeline.js");
function registerTelegramWebhook(app) {
    app.post(`/telegram/${process.env.WEBHOOK_SECRET}`, async (req, reply) => {
        reply.send({ ok: true });
        const message = normalizeTelegram(req.body);
        if (message)
            await (0, pipeline_js_1.processMessage)(message).catch(console.error);
    });
    console.log("[Gateway] Telegram ✓");
}
function registerWhatsAppWebhook(app) {
    app.post("/whatsapp/webhook", async (req, reply) => {
        reply.send({ ok: true });
        const message = normalizeWA(req.body);
        if (message)
            await (0, pipeline_js_1.processMessage)(message).catch(console.error);
    });
    console.log("[Gateway] WhatsApp ✓");
}
function normalizeTelegram(body) {
    if (body.callback_query) {
        const cb = body.callback_query;
        const cbMsg = cb.message;
        return { id: String(cb.id), channel: "telegram", type: "callback",
            text: String(cb.data || ""), chatId: String(cbMsg?.chat?.id || ""),
            userId: String(cb.from?.id || ""), timestamp: new Date(), raw: body };
    }
    const msg = body.message;
    if (!msg)
        return null;
    const chat = msg.chat;
    const from = msg.from;
    const base = { channel: "telegram", chatId: String(chat?.id || ""),
        userId: String(from?.id || ""), username: String(from?.username || from?.first_name || ""),
        timestamp: new Date(Number(msg.date) * 1000), raw: body };
    if (msg.voice || msg.audio)
        return { ...base, id: String(msg.message_id), type: "audio", text: "" };
    if (msg.text)
        return { ...base, id: String(msg.message_id), type: "text", text: String(msg.text) };
    return null;
}
function normalizeWA(body) {
    if (body.event !== "message.received")
        return null;
    const from = String(body.from || "");
    if (Boolean(body.isGroup))
        return null;
    const base = { channel: "whatsapp", chatId: from,
        userId: String(body.phone || from), username: String(body.pushName || ""),
        timestamp: new Date(Number(body.timestamp) || Date.now()), raw: body };
    if (body.isAudio && body.audioBase64)
        return { ...base, id: String(body.messageId), type: "audio", text: "",
            audioBase64: String(body.audioBase64), audioMimeType: String(body.audioMime || "audio/ogg") };
    const text = String(body.text || "");
    if (!text)
        return null;
    return { ...base, id: String(body.messageId), type: "text", text };
}
