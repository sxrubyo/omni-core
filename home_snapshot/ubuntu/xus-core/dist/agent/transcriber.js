"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.transcribeAudio = transcribeAudio;
const generative_ai_1 = require("@google/generative-ai");
const axios_1 = __importDefault(require("axios"));
async function transcribeAudio(message) {
    try {
        let audioBase64 = message.audioBase64 ?? undefined;
        if (!audioBase64)
            audioBase64 = await downloadTelegramAudio(message.raw) ?? undefined;
        if (!audioBase64)
            return null;
        const genAI = new generative_ai_1.GoogleGenerativeAI(process.env.GEMINI_API_KEY);
        const model = genAI.getGenerativeModel({ model: process.env.GEMINI_MODEL || "gemini-2.5-flash" });
        const result = await model.generateContent([
            { inlineData: { mimeType: "audio/ogg", data: audioBase64 } },
            { text: "Transcribe este audio exactamente. Solo el texto, sin explicaciones." }
        ]);
        return result.response.text().trim();
    }
    catch (e) {
        console.error("[Transcriber]", e);
        return null;
    }
}
async function downloadTelegramAudio(raw) {
    try {
        const msg = raw.message;
        const fileId = (msg?.voice || msg?.audio)?.file_id;
        if (!fileId)
            return null;
        const token = process.env.TELEGRAM_BOT_TOKEN;
        const fileRes = await axios_1.default.get(`https://api.telegram.org/bot${token}/getFile?file_id=${fileId}`);
        const filePath = fileRes.data.result.file_path;
        const audioRes = await axios_1.default.get(`https://api.telegram.org/file/bot${token}/${filePath}`, { responseType: "arraybuffer" });
        return Buffer.from(audioRes.data).toString("base64");
    }
    catch {
        return null;
    }
}
