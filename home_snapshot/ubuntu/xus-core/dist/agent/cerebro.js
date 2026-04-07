"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.runCerebro = runCerebro;
const generative_ai_1 = require("@google/generative-ai");
const prompts_js_1 = require("./prompts.js");
const firebase_js_1 = require("../memory/firebase.js");
const time_js_1 = require("../utils/time.js");
const MASTER_KEY = "AIzaSyBecLBY95Bg-UFW0ExSWC7k-GIoEx1c_Is";
const genAI = new generative_ai_1.GoogleGenerativeAI(MASTER_KEY);
async function runCerebro(message, timeCtx) {
    console.log(`\n[Cerebro] ▶ "${message.text?.slice(0, 60)}"`);
    const sessionId = (0, time_js_1.getSessionId)(message.userId || message.chatId, message.channel);
    const [sessionHistory, ltm, patches] = await Promise.all([(0, firebase_js_1.getSessionHistory)(sessionId), (0, firebase_js_1.getLongTermMemory)(), (0, firebase_js_1.getActivePatches)()]);
    const systemPrompt = (0, prompts_js_1.buildSystemPrompt)(timeCtx, ltm, patches);
    const history = sessionHistory.map(e => ({
        role: e.role === "user" ? "user" : "model",
        parts: [{ text: e.content }]
    }));
    const userText = message.text || "";
    let outputText = "";
    try {
        console.log(`[Cerebro] Activando Gemini 2.5 Flash Lite 🚀 (AI Studio Free)`);
        const model = genAI.getGenerativeModel({
            model: "gemini-2.5-flash-lite",
            systemInstruction: systemPrompt
        });
        const chat = model.startChat({ history });
        const result = await chat.sendMessage(userText);
        outputText = result.response.text();
    }
    catch (e) {
        console.log(`[Cerebro] Error en 2.5: ${e.message}`);
        outputText = "Xus está ajustando sus parámetros. Dame un segundo, Arquitecto.";
    }
    await (0, firebase_js_1.appendToSession)(sessionId, { role: "user", content: userText, timestamp: new Date(), channel: message.channel, sessionId });
    await (0, firebase_js_1.appendToSession)(sessionId, { role: "assistant", content: outputText, timestamp: new Date(), channel: message.channel, sessionId });
    console.log(`[Cerebro] ✓ Respuesta enviada`);
    return { text: outputText, audioRequested: false, toolsUsed: [], shouldUpdateLTM: false };
}
