"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.evaluateAndPatch = evaluateAndPatch;
exports.installCapability = installCapability;
exports.getSystemStatus = getSystemStatus;
const generative_ai_1 = require("@google/generative-ai");
const firebase_js_1 = require("../memory/firebase.js");
// ─── Auto-evaluación de respuesta ─────────────────────────────────────────────
async function evaluateAndPatch(params) {
    try {
        const genAI = new generative_ai_1.GoogleGenerativeAI(process.env.GEMINI_API_KEY);
        const model = genAI.getGenerativeModel({ model: process.env.GEMINI_MODEL || "gemini-2.5-flash" });
        const prompt = `Eres el evaluador interno de XUS. Analiza esta interacción:

USUARIO: ${params.user_input}
XUS RESPONDIÓ: ${params.agent_output}
TOOLS USADAS: ${params.tools_used.join(", ") || "ninguna"}

LEYES DE XUS:
1. No anuncia acciones, reporta resultados
2. Habla en primera persona
3. Siempre en español
4. Nunca JSON crudo
5. Tono JARVIS: frío, preciso
6. Nunca dice "Por supuesto", "Claro que sí", "Con gusto"

Responde SOLO en JSON válido:
{
  "score": <0-10>,
  "issues": ["problema1"],
  "improvements": ["mejora concreta"],
  "patch": "instrucción adicional para el system prompt si score < 7, null si no"
}`;
        const result = await model.generateContent(prompt);
        const text = result.response.text().trim().replace(/```json|```/g, "");
        const evaluation = JSON.parse(text);
        // Loggear reflexión
        await (0, firebase_js_1.logReflection)({
            sessionId: `eval_${Date.now()}`,
            userInput: params.user_input,
            agentOutput: params.agent_output,
            toolsUsed: params.tools_used,
            quality: evaluation.score,
            issues: evaluation.issues || [],
            improvements: evaluation.improvements || [],
            timestamp: new Date(),
        });
        // Si calidad baja → aplicar patch automático
        if (evaluation.score < 7 && evaluation.patch) {
            await (0, firebase_js_1.applyInstructionPatch)({
                id: `patch_${Date.now()}`,
                description: evaluation.patch,
                applied: true,
                appliedAt: new Date(),
                triggerCondition: evaluation.issues?.[0] || "low_quality",
            });
            console.log(`[Self-Improve] 🔧 Patch aplicado: ${evaluation.patch.slice(0, 80)}`);
        }
        // Actualizar estadísticas globales
        const log = await (0, firebase_js_1.getSelfImprovementLog)();
        const newTotal = (log.totalSessions || 0) + 1;
        const newAvg = ((log.avgQuality || 0) * (log.totalSessions || 0) + evaluation.score) / newTotal;
        await (0, firebase_js_1.updateSelfImprovementLog)({ totalSessions: newTotal, avgQuality: Math.round(newAvg * 10) / 10, lastReflection: new Date() });
        return { success: true, data: { score: evaluation.score, issues: evaluation.issues, patched: evaluation.score < 7 } };
    }
    catch (e) {
        return { success: false, error: e.message };
    }
}
// ─── Instalar nueva capacidad (auto-tool-installer) ───────────────────────────
async function installCapability(params) {
    try {
        // XUS puede pedirse a sí mismo instalar una nueva herramienta
        // Genera el código del tool, lo guarda en Firebase como patch
        const genAI = new generative_ai_1.GoogleGenerativeAI(process.env.GEMINI_API_KEY);
        const model = genAI.getGenerativeModel({ model: process.env.GEMINI_MODEL || "gemini-2.5-flash" });
        const prompt = `Genera una función TypeScript para XUS que implemente: ${params.description}
${params.api_endpoint ? `API endpoint: ${params.api_endpoint}` : ""}
${params.api_key_env ? `API key env var: ${params.api_key_env}` : ""}

La función debe:
1. Llamarse ${params.capability_name}
2. Retornar { success: boolean, data?: unknown, error?: string }
3. Usar axios para HTTP
4. Manejar errores con try/catch
5. Ser TypeScript válido

Responde SOLO con el código de la función, sin imports ni explicaciones.`;
        const result = await model.generateContent(prompt);
        const code = result.response.text().trim().replace(/```typescript|```ts|```/g, "");
        // Guardar como capability en Firebase para revisión
        const { getDb } = await import("../memory/firebase.js");
        await (0, firebase_js_1.applyInstructionPatch)({
            id: `capability_${params.capability_name}_${Date.now()}`,
            description: `Nueva capacidad instalada: ${params.capability_name} — ${params.description}`,
            applied: true,
            appliedAt: new Date(),
            triggerCondition: "auto_install",
        });
        console.log(`[Self-Improve] ⚡ Nueva capacidad generada: ${params.capability_name}`);
        return { success: true, data: { name: params.capability_name, code_preview: code.slice(0, 200), status: "generated" } };
    }
    catch (e) {
        return { success: false, error: e.message };
    }
}
// ─── Ver estado del sistema ───────────────────────────────────────────────────
async function getSystemStatus(_params) {
    try {
        const [log, patches] = await Promise.all([(0, firebase_js_1.getSelfImprovementLog)(), (0, firebase_js_1.getActivePatches)()]);
        const logData = log;
        return {
            success: true,
            data: {
                totalInteractions: logData.totalSessions || 0,
                avgQuality: logData.avgQuality || 0,
                activePatches: patches.length,
                lastReflection: logData.lastReflection,
                uptime: Math.floor(process.uptime() / 3600) + "h",
                memory: Math.round(process.memoryUsage().heapUsed / 1024 / 1024) + "MB",
            }
        };
    }
    catch (e) {
        return { success: false, error: e.message };
    }
}
