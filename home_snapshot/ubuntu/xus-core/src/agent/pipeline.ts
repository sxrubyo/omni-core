import type { IncomingMessage } from "../types/index.js";
import { runCerebro } from "./cerebro.js";
import { getTimeContext } from "../utils/time.js";
import { sendText, sendAudio, sendTyping, sendReaction } from "../output/sender.js";

export async function processMessage(message: IncomingMessage): Promise<void> {
  console.log(`[Pipeline] ▶ ${message.type} | ${message.channel} | "${message.text?.slice(0,50)}"`);
  try {
    await sendTyping(message.channel, message.chatId);

    if (message.type === "audio" && !message.text) {
      const { transcribeAudio } = await import("./transcriber.js");
      const transcription = await transcribeAudio(message);
      if (transcription) { message.text = transcription; message.type = "text"; }
      else { await sendText(message.channel, message.chatId, "No pude entender el audio."); return; }
    }

    const timeCtx = getTimeContext();
    const output = await runCerebro(message, timeCtx);

    if (output.audioRequested) {
      const sent = await sendAudio(message.channel, message.chatId, output.text);
      if (!sent) await sendText(message.channel, message.chatId, output.text);
    } else {
      await sendText(message.channel, message.chatId, output.text);
    }

    const msgId = (message.raw as {message?: {message_id?: number}})?.message?.message_id;
    if (message.channel === "telegram" && msgId && Math.random() < 0.25) {
      const emojis = ["⚡","🎯","✅","🔥","💡"];
      await sendReaction(message.channel, message.chatId, msgId, emojis[Math.floor(Math.random() * emojis.length)]);
    }
  } catch (error) {
    console.error("[Pipeline] Error:", error);
    await sendText(message.channel, message.chatId, "Error interno. Revisando.").catch(() => {});
  }
}
