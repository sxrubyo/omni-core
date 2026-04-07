"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.chatWithFallback = chatWithFallback;
const generative_ai_1 = require("@google/generative-ai");
const groq_sdk_1 = __importDefault(require("groq-sdk"));
async function chatWithFallback(systemPrompt, history, userMessage, tools) {
    // Intentar Gemini primero
    try {
        const genAI = new generative_ai_1.GoogleGenerativeAI(process.env.GEMINI_API_KEY);
        const model = genAI.getGenerativeModel({
            model: process.env.GEMINI_MODEL || "gemini-2.5-flash",
            systemInstruction: systemPrompt,
            tools: [{ functionDeclarations: tools }],
            generationConfig: { temperature: 0.7, maxOutputTokens: 2048 },
        });
        const chat = model.startChat({
            history: history.map(h => ({ role: h.role, parts: [{ text: h.text }] }))
        });
        const result = await chat.sendMessage(userMessage);
        const parts = result.response.candidates?.[0]?.content?.parts || [];
        const fnCalls = parts.filter((p) => p.functionCall);
        if (fnCalls.length > 0)
            return { text: "", toolCalls: fnCalls };
        return { text: result.response.text(), toolCalls: [] };
    }
    catch (e) {
        const err = e;
        if (err.status === 429 || err.status === 503) {
            console.log("[LLM] Gemini rate limit → fallback a Groq");
            // Groq fallback — sin tool calling, respuesta directa
            const groq = new groq_sdk_1.default({ apiKey: process.env.GROQ_API_KEY });
            const messages = [
                { role: "system", content: systemPrompt },
                ...history.map(h => ({ role: h.role === "model" ? "assistant" : "user", content: h.text })),
                { role: "user", content: userMessage }
            ];
            const res = await groq.chat.completions.create({
                model: "llama-3.3-70b-versatile",
                messages,
                max_tokens: 1024,
            });
            return { text: res.choices[0].message.content || "", toolCalls: [] };
        }
        throw e;
    }
}
