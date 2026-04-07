import axios from "axios";
import FormData from "form-data";
import type { Channel } from "../types/index.js";

const TG = () => `https://api.telegram.org/bot${process.env.TELEGRAM_BOT_TOKEN}`;
const WA = () => process.env.WA_BRIDGE_URL || "http://localhost:3000";

export async function sendTyping(channel: Channel, chatId: string): Promise<void> {
  if (channel === "telegram") {
    await axios.post(`${TG()}/sendChatAction`, { chat_id: chatId, action: "typing" }).catch(() => {});
  } else {
    await axios.post(`${WA()}/typing`, { to: chatId, duration: 8000 }).catch(() => {});
  }
}

export async function sendText(channel: Channel, chatId: string, text: string): Promise<void> {
  if (channel === "telegram") {
    const chunks = text.length <= 4000 ? [text] : text.match(/.{1,4000}/gs) || [text];
    for (const chunk of chunks)
      await axios.post(`${TG()}/sendMessage`, { chat_id: chatId, text: chunk, parse_mode: "Markdown" });
  } else {
    const clean = text.replace(/\*\*(.+?)\*\*/g, "*$1*").replace(/#{1,6}\s/g, "").replace(/`{3}[\s\S]*?`{3}/g, "").replace(/`(.+?)`/g, "$1");
    await axios.post(`${WA()}/send`, { to: chatId, message: clean });
  }
}

export async function sendAudio(channel: Channel, chatId: string, text: string): Promise<boolean> {
  try {
    const res = await axios.post(
      `https://api.elevenlabs.io/v1/text-to-speech/${process.env.ELEVENLABS_VOICE_ID}`,
      { text: text.slice(0, 500), model_id: "eleven_multilingual_v2", voice_settings: { stability: 0.5, similarity_boost: 0.8 } },
      { headers: { "xi-api-key": process.env.ELEVENLABS_API_KEY!, "Content-Type": "application/json", Accept: "audio/mpeg" }, responseType: "arraybuffer" }
    );
    const buf = Buffer.from(res.data);
    if (channel === "telegram") {
      const form = new FormData();
      form.append("chat_id", chatId);
      form.append("voice", buf, { filename: "xus.ogg", contentType: "audio/ogg" });
      await axios.post(`${TG()}/sendVoice`, form, { headers: form.getHeaders() });
    } else {
      await axios.post(`${WA()}/recording`, { to: chatId, duration: 4000 }).catch(() => {});
      await axios.post(`${WA()}/send-audio`, { to: chatId, audioBase64: buf.toString("base64"), mimeType: "audio/mpeg" });
    }
    return true;
  } catch { return false; }
}

export async function sendReaction(channel: Channel, chatId: string, messageId: string | number, emoji: string): Promise<void> {
  if (channel === "telegram") {
    await axios.post(`${TG()}/setMessageReaction`, { chat_id: chatId, message_id: messageId, reaction: [{ type: "emoji", emoji }] }).catch(() => {});
  } else {
    await axios.post(`${WA()}/react`, { to: chatId, messageId: String(messageId), emoji }).catch(() => {});
  }
}
