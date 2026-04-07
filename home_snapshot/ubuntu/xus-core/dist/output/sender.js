"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.sendTyping = sendTyping;
exports.sendText = sendText;
exports.sendAudio = sendAudio;
exports.sendReaction = sendReaction;
const axios_1 = __importDefault(require("axios"));
const form_data_1 = __importDefault(require("form-data"));
const TG = () => `https://api.telegram.org/bot${process.env.TELEGRAM_BOT_TOKEN}`;
const WA = () => process.env.WA_BRIDGE_URL || "http://localhost:3000";
async function sendTyping(channel, chatId) {
    if (channel === "telegram") {
        await axios_1.default.post(`${TG()}/sendChatAction`, { chat_id: chatId, action: "typing" }).catch(() => { });
    }
    else {
        await axios_1.default.post(`${WA()}/typing`, { to: chatId, duration: 8000 }).catch(() => { });
    }
}
async function sendText(channel, chatId, text) {
    if (channel === "telegram") {
        const chunks = text.length <= 4000 ? [text] : text.match(/.{1,4000}/gs) || [text];
        for (const chunk of chunks)
            await axios_1.default.post(`${TG()}/sendMessage`, { chat_id: chatId, text: chunk, parse_mode: "Markdown" });
    }
    else {
        const clean = text.replace(/\*\*(.+?)\*\*/g, "*$1*").replace(/#{1,6}\s/g, "").replace(/`{3}[\s\S]*?`{3}/g, "").replace(/`(.+?)`/g, "$1");
        await axios_1.default.post(`${WA()}/send`, { to: chatId, message: clean });
    }
}
async function sendAudio(channel, chatId, text) {
    try {
        const res = await axios_1.default.post(`https://api.elevenlabs.io/v1/text-to-speech/${process.env.ELEVENLABS_VOICE_ID}`, { text: text.slice(0, 500), model_id: "eleven_multilingual_v2", voice_settings: { stability: 0.5, similarity_boost: 0.8 } }, { headers: { "xi-api-key": process.env.ELEVENLABS_API_KEY, "Content-Type": "application/json", Accept: "audio/mpeg" }, responseType: "arraybuffer" });
        const buf = Buffer.from(res.data);
        if (channel === "telegram") {
            const form = new form_data_1.default();
            form.append("chat_id", chatId);
            form.append("voice", buf, { filename: "xus.ogg", contentType: "audio/ogg" });
            await axios_1.default.post(`${TG()}/sendVoice`, form, { headers: form.getHeaders() });
        }
        else {
            await axios_1.default.post(`${WA()}/recording`, { to: chatId, duration: 4000 }).catch(() => { });
            await axios_1.default.post(`${WA()}/send-audio`, { to: chatId, audioBase64: buf.toString("base64"), mimeType: "audio/mpeg" });
        }
        return true;
    }
    catch {
        return false;
    }
}
async function sendReaction(channel, chatId, messageId, emoji) {
    if (channel === "telegram") {
        await axios_1.default.post(`${TG()}/setMessageReaction`, { chat_id: chatId, message_id: messageId, reaction: [{ type: "emoji", emoji }] }).catch(() => { });
    }
    else {
        await axios_1.default.post(`${WA()}/react`, { to: chatId, messageId: String(messageId), emoji }).catch(() => { });
    }
}
