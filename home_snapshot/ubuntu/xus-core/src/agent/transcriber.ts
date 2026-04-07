import { GoogleGenerativeAI } from "@google/generative-ai";
import axios from "axios";
import type { IncomingMessage } from "../types/index.js";

export async function transcribeAudio(message: IncomingMessage): Promise<string | null> {
  try {
    let audioBase64: string | undefined = message.audioBase64 ?? undefined;
    if (!audioBase64) audioBase64 = await downloadTelegramAudio(message.raw) ?? undefined;
    if (!audioBase64) return null;

    const genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY!);
    const model = genAI.getGenerativeModel({ model: process.env.GEMINI_MODEL || "gemini-2.5-flash" });
    const result = await model.generateContent([
      { inlineData: { mimeType: "audio/ogg", data: audioBase64 } },
      { text: "Transcribe este audio exactamente. Solo el texto, sin explicaciones." }
    ]);
    return result.response.text().trim();
  } catch (e) { console.error("[Transcriber]", e); return null; }
}

async function downloadTelegramAudio(raw: Record<string, unknown>): Promise<string | null> {
  try {
    const msg = raw.message as Record<string, unknown>;
    const fileId = ((msg?.voice || msg?.audio) as Record<string, unknown>)?.file_id as string;
    if (!fileId) return null;
    const token = process.env.TELEGRAM_BOT_TOKEN!;
    const fileRes = await axios.get(`https://api.telegram.org/bot${token}/getFile?file_id=${fileId}`);
    const filePath = fileRes.data.result.file_path;
    const audioRes = await axios.get(`https://api.telegram.org/file/bot${token}/${filePath}`, { responseType: "arraybuffer" });
    return Buffer.from(audioRes.data).toString("base64");
  } catch { return null; }
}
