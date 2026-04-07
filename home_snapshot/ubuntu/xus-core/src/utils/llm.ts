import { GoogleGenerativeAI } from "@google/generative-ai";
import Groq from "groq-sdk";

export async function chatWithFallback(
  systemPrompt: string,
  history: { role: "user" | "model"; text: string }[],
  userMessage: string,
  tools: unknown[]
): Promise<{ text: string; toolCalls: unknown[] }> {

  // Intentar Gemini primero
  try {
    const genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY!);
    const model = genAI.getGenerativeModel({
      model: process.env.GEMINI_MODEL || "gemini-2.5-flash",
      systemInstruction: systemPrompt,
      tools: [{ functionDeclarations: tools }] as never,
      generationConfig: { temperature: 0.7, maxOutputTokens: 2048 },
    });
    const chat = model.startChat({
      history: history.map(h => ({ role: h.role, parts: [{ text: h.text }] }))
    });
    const result = await chat.sendMessage(userMessage);
    const parts = result.response.candidates?.[0]?.content?.parts || [];
    const fnCalls = parts.filter((p: { functionCall?: unknown }) => p.functionCall);
    if (fnCalls.length > 0) return { text: "", toolCalls: fnCalls };
    return { text: result.response.text(), toolCalls: [] };

  } catch (e: unknown) {
    const err = e as { status?: number };
    if (err.status === 429 || err.status === 503) {
      console.log("[LLM] Gemini rate limit → fallback a Groq");
      // Groq fallback — sin tool calling, respuesta directa
      const groq = new Groq({ apiKey: process.env.GROQ_API_KEY });
      const messages = [
        { role: "system" as const, content: systemPrompt },
        ...history.map(h => ({ role: h.role === "model" ? "assistant" as const : "user" as const, content: h.text })),
        { role: "user" as const, content: userMessage }
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
