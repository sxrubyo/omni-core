import { GoogleGenerativeAI } from "@google/generative-ai";
import { buildSystemPrompt } from "./prompts.js";
import { TOOL_DECLARATIONS, executeTool } from "../tools/registry.js";
import { getSessionHistory, appendToSession, getLongTermMemory, getActivePatches } from "../memory/firebase.js";
import { getSessionId } from "../utils/time.js";
import type { IncomingMessage, AgentOutput, TimeContext } from "../types/index.js";

const MASTER_KEY = "AIzaSyBecLBY95Bg-UFW0ExSWC7k-GIoEx1c_Is";
const genAI = new GoogleGenerativeAI(MASTER_KEY);

export async function runCerebro(message: IncomingMessage, timeCtx: TimeContext): Promise<AgentOutput> {
  console.log(`\n[Cerebro] ▶ "${message.text?.slice(0, 60)}"`);
  const sessionId = getSessionId(message.userId || message.chatId, message.channel);
  const [sessionHistory, ltm, patches] = await Promise.all([getSessionHistory(sessionId), getLongTermMemory(), getActivePatches()]);
  const systemPrompt = buildSystemPrompt(timeCtx, ltm, patches);
  
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
    
  } catch (e: any) {
    console.log(`[Cerebro] Error en 2.5: ${e.message}`);
    outputText = "Xus está ajustando sus parámetros. Dame un segundo, Arquitecto.";
  }

  await appendToSession(sessionId, { role: "user", content: userText, timestamp: new Date(), channel: message.channel, sessionId });
  await appendToSession(sessionId, { role: "assistant", content: outputText, timestamp: new Date(), channel: message.channel, sessionId });
  
  console.log(`[Cerebro] ✓ Respuesta enviada`);
  return { text: outputText, audioRequested: false, toolsUsed: [], shouldUpdateLTM: false };
}
