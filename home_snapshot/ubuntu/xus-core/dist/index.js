"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
require("dotenv/config");
const fastify_1 = __importDefault(require("fastify"));
const firebase_js_1 = require("./memory/firebase.js");
const webhook_js_1 = require("./gateway/webhook.js");
const app = (0, fastify_1.default)({ logger: false });
app.get("/health", async () => ({ status: "operational", agent: "XUS v2.0", timestamp: new Date().toISOString() }));
async function boot() {
    console.log("\n╔══════════════════════════════════╗");
    console.log("║      XUS CORE v2.0 — BOOT        ║");
    console.log("╚══════════════════════════════════╝\n");
    const required = ["GEMINI_API_KEY", "TELEGRAM_BOT_TOKEN", "FIREBASE_PROJECT_ID", "FIREBASE_PRIVATE_KEY", "FIREBASE_CLIENT_EMAIL"];
    const missing = required.filter(k => !process.env[k]);
    if (missing.length) {
        console.error("✗ Missing env vars:", missing.join(", "));
        process.exit(1);
    }
    (0, firebase_js_1.initFirebase)();
    console.log("[Boot] ✓ Firebase");
    (0, webhook_js_1.registerTelegramWebhook)(app);
    (0, webhook_js_1.registerWhatsAppWebhook)(app);
    console.log("[Boot] ✓ Webhooks");
    const port = Number(process.env.PORT) || 4000;
    await app.listen({ port, host: "0.0.0.0" });
    console.log(`[Boot] ✓ XUS escuchando en puerto ${port}`);
    console.log(`[Boot] ✓ Telegram: /telegram/${process.env.WEBHOOK_SECRET}`);
    console.log("\n[XUS] Sistema operativo activo. Esperando al Arquitecto.\n");
}
boot().catch(err => { console.error("Fatal:", err); process.exit(1); });
