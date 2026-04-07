"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.processMessage = processMessage;
const cerebro_js_1 = require("./cerebro.js");
const time_js_1 = require("../utils/time.js");
const sender_js_1 = require("../output/sender.js");
async function processMessage(message) {
    console.log(`[Pipeline] ▶ ${message.type} | ${message.channel} | "${message.text?.slice(0, 50)}"`);
    try {
        await (0, sender_js_1.sendTyping)(message.channel, message.chatId);
        if (message.type === "audio" && !message.text) {
            const { transcribeAudio } = await import("./transcriber.js");
            const transcription = await transcribeAudio(message);
            if (transcription) {
                message.text = transcription;
                message.type = "text";
            }
            else {
                await (0, sender_js_1.sendText)(message.channel, message.chatId, "No pude entender el audio.");
                return;
            }
        }
        const timeCtx = (0, time_js_1.getTimeContext)();
        const output = await (0, cerebro_js_1.runCerebro)(message, timeCtx);
        if (output.audioRequested) {
            const sent = await (0, sender_js_1.sendAudio)(message.channel, message.chatId, output.text);
            if (!sent)
                await (0, sender_js_1.sendText)(message.channel, message.chatId, output.text);
        }
        else {
            await (0, sender_js_1.sendText)(message.channel, message.chatId, output.text);
        }
        const msgId = message.raw?.message?.message_id;
        if (message.channel === "telegram" && msgId && Math.random() < 0.25) {
            const emojis = ["⚡", "🎯", "✅", "🔥", "💡"];
            await (0, sender_js_1.sendReaction)(message.channel, message.chatId, msgId, emojis[Math.floor(Math.random() * emojis.length)]);
        }
    }
    catch (error) {
        console.error("[Pipeline] Error:", error);
        await (0, sender_js_1.sendText)(message.channel, message.chatId, "Error interno. Revisando.").catch(() => { });
    }
}
