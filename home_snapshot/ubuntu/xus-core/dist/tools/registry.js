"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.TOOL_DECLARATIONS = void 0;
exports.executeTool = executeTool;
const google_js_1 = require("./google.js");
const self_improve_js_1 = require("./self_improve.js");
const axios_1 = __importDefault(require("axios"));
exports.TOOL_DECLARATIONS = [
    { name: "search_web", description: "Buscar información actualizada en internet",
        parameters: { type: "object", properties: { query: { type: "string" }, num_results: { type: "number" } }, required: ["query"] } },
    { name: "read_calendar", description: "Leer eventos de Google Calendar",
        parameters: { type: "object", properties: { days_ahead: { type: "number" } } } },
    { name: "write_calendar", description: "Crear evento en Google Calendar",
        parameters: { type: "object", properties: { title: { type: "string" }, start: { type: "string" }, end: { type: "string" }, description: { type: "string" } }, required: ["title", "start", "end"] } },
    { name: "read_sheets", description: "Leer Google Sheets",
        parameters: { type: "object", properties: { sheet_id: { type: "string" }, range: { type: "string" } }, required: ["range"] } },
    { name: "write_sheets", description: "Escribir en Google Sheets",
        parameters: { type: "object", properties: { range: { type: "string" }, values: { type: "array" } }, required: ["range", "values"] } },
    { name: "read_email", description: "Leer correos de Gmail",
        parameters: { type: "object", properties: { max_results: { type: "number" }, query: { type: "string" } } } },
    { name: "send_email", description: "Enviar correo via Gmail",
        parameters: { type: "object", properties: { to: { type: "string" }, subject: { type: "string" }, body: { type: "string" } }, required: ["to", "subject", "body"] } },
    { name: "read_ltm", description: "Leer memoria de largo plazo",
        parameters: { type: "object", properties: {} } },
    { name: "write_ltm", description: "Escribir en memoria de largo plazo — usar en silencio al detectar victoria, fracaso, patrón o cierre",
        parameters: { type: "object", properties: { type: { type: "string", enum: ["VICTORY", "FAILURE", "PATTERN", "CLOSURE"] }, content: { type: "string" }, data: { type: "object" } }, required: ["type", "content"] } },
    { name: "send_whatsapp", description: "Enviar mensaje de WhatsApp",
        parameters: { type: "object", properties: { to: { type: "string" }, message: { type: "string" } }, required: ["to", "message"] } },
    { name: "evaluate_and_patch", description: "Auto-evaluar calidad de respuesta y aplicar mejoras. Usar al final de interacciones complejas.",
        parameters: { type: "object", properties: { user_input: { type: "string" }, agent_output: { type: "string" }, tools_used: { type: "array", items: { type: "string" } } }, required: ["user_input", "agent_output", "tools_used"] } },
    { name: "install_capability", description: "Instalar una nueva capacidad en XUS. XUS puede pedirse a sí mismo nuevas herramientas.",
        parameters: { type: "object", properties: { capability_name: { type: "string" }, description: { type: "string" }, api_endpoint: { type: "string" }, api_key_env: { type: "string" } }, required: ["capability_name", "description"] } },
    { name: "exec_command", description: "Ejecutar comando en la terminal del servidor. Usar con precaución.", parameters: { type: "object", properties: { command: { type: "string", description: "Comando bash a ejecutar" } }, required: ["command"] } },
    { name: "get_system_status", description: "Ver estado del sistema: uptime, calidad promedio, patches activos",
        parameters: { type: "object", properties: {} } },
];
async function executeTool(name, params) {
    console.log(`[Tools] ▶ ${name}`);
    try {
        switch (name) {
            case "search_web": {
                const res = await axios_1.default.get("https://api.search.brave.com/res/v1/web/search", { headers: { "X-Subscription-Token": process.env.BRAVE_API_KEY }, params: { q: params.query, count: params.num_results || 5 } });
                return { success: true, data: res.data.web?.results?.map((r) => ({ title: r.title, url: r.url, snippet: r.description })) || [] };
            }
            case "read_calendar": return await (0, google_js_1.readCalendar)(params);
            case "write_calendar": return await (0, google_js_1.writeCalendar)(params);
            case "read_sheets": return await (0, google_js_1.readSheets)(params);
            case "write_sheets": return await (0, google_js_1.writeSheets)(params);
            case "read_email": return await (0, google_js_1.readEmail)(params);
            case "send_email": return await (0, google_js_1.sendEmail)(params);
            case "read_ltm": {
                const { getLongTermMemory } = await import("../memory/firebase.js");
                return { success: true, data: await getLongTermMemory() };
            }
            case "write_ltm": {
                const { appendToLTM } = await import("../memory/firebase.js");
                const map = { VICTORY: "victories", FAILURE: "failures", PATTERN: "patterns", CLOSURE: "clients" };
                await appendToLTM(map[String(params.type)], { content: String(params.content), date: new Date().toISOString(), ...params.data });
                return { success: true };
            }
            case "send_whatsapp": {
                await axios_1.default.post(`${process.env.WA_BRIDGE_URL}/send`, { to: params.to, message: params.message });
                return { success: true };
            }
            case "evaluate_and_patch": return await (0, self_improve_js_1.evaluateAndPatch)(params);
            case "install_capability": return await (0, self_improve_js_1.installCapability)(params);
            case "get_system_status": return await (0, self_improve_js_1.getSystemStatus)(params);
            case "exec_command": {
                const { execSync } = await import("child_process");
                try {
                    const out = execSync(String(params.command), { timeout: 10000, encoding: "utf8" });
                    return { success: true, data: { output: out.trim() } };
                }
                catch (ex) {
                    return { success: false, error: ex.message };
                }
            }
            default: return { success: false, error: `Tool desconocida: ${name}` };
        }
    }
    catch (e) {
        console.error(`[Tools] ✗ ${name}:`, e.message);
        return { success: false, error: e.message };
    }
}
// Esta línea no hace nada — el tool exec_command ya está en el switch
