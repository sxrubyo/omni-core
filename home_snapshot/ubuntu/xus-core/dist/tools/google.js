"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.readCalendar = readCalendar;
exports.writeCalendar = writeCalendar;
exports.readSheets = readSheets;
exports.writeSheets = writeSheets;
exports.readEmail = readEmail;
exports.sendEmail = sendEmail;
const googleapis_1 = require("googleapis");
function getOAuth() {
    const auth = new googleapis_1.google.auth.OAuth2(process.env.GOOGLE_CLIENT_ID, process.env.GOOGLE_CLIENT_SECRET, process.env.GOOGLE_REDIRECT_URI);
    auth.setCredentials({ refresh_token: process.env.GOOGLE_REFRESH_TOKEN });
    return auth;
}
async function readCalendar(params) {
    try {
        const cal = googleapis_1.google.calendar({ version: "v3", auth: getOAuth() });
        const now = new Date();
        const end = new Date();
        end.setDate(end.getDate() + (params.days_ahead || 7));
        const res = await cal.events.list({ calendarId: "primary", timeMin: now.toISOString(), timeMax: end.toISOString(), singleEvents: true, orderBy: "startTime", maxResults: 20 });
        return { success: true, data: res.data.items?.map(e => ({ title: e.summary, start: e.start?.dateTime || e.start?.date, end: e.end?.dateTime || e.end?.date, id: e.id })) || [] };
    }
    catch (e) {
        return { success: false, error: e.message };
    }
}
async function writeCalendar(params) {
    try {
        const cal = googleapis_1.google.calendar({ version: "v3", auth: getOAuth() });
        const res = await cal.events.insert({ calendarId: "primary", requestBody: { summary: params.title, description: params.description, start: { dateTime: params.start }, end: { dateTime: params.end } } });
        return { success: true, data: { id: res.data.id, link: res.data.htmlLink } };
    }
    catch (e) {
        return { success: false, error: e.message };
    }
}
async function readSheets(params) {
    try {
        const sheets = googleapis_1.google.sheets({ version: "v4", auth: getOAuth() });
        const res = await sheets.spreadsheets.values.get({ spreadsheetId: params.sheet_id || process.env.GOOGLE_SHEETS_ID, range: params.range });
        return { success: true, data: { rows: res.data.values || [] } };
    }
    catch (e) {
        return { success: false, error: e.message };
    }
}
async function writeSheets(params) {
    try {
        const sheets = googleapis_1.google.sheets({ version: "v4", auth: getOAuth() });
        await sheets.spreadsheets.values.append({ spreadsheetId: params.sheet_id || process.env.GOOGLE_SHEETS_ID, range: params.range, valueInputOption: "USER_ENTERED", requestBody: { values: params.values } });
        return { success: true };
    }
    catch (e) {
        return { success: false, error: e.message };
    }
}
async function readEmail(params) {
    try {
        const gmail = googleapis_1.google.gmail({ version: "v1", auth: getOAuth() });
        const list = await gmail.users.messages.list({ userId: "me", maxResults: params.max_results || 10, q: params.query || "is:unread" });
        const messages = await Promise.all((list.data.messages || []).slice(0, 5).map(async (m) => {
            const msg = await gmail.users.messages.get({ userId: "me", id: m.id });
            const h = msg.data.payload?.headers || [];
            return { id: m.id, subject: h.find(x => x.name === "Subject")?.value, from: h.find(x => x.name === "From")?.value, snippet: msg.data.snippet };
        }));
        return { success: true, data: messages };
    }
    catch (e) {
        return { success: false, error: e.message };
    }
}
async function sendEmail(params) {
    try {
        const gmail = googleapis_1.google.gmail({ version: "v1", auth: getOAuth() });
        const raw = Buffer.from([`To: ${params.to}`, `Subject: ${params.subject}`, "Content-Type: text/plain; charset=utf-8", "", params.body].join("\n")).toString("base64url");
        await gmail.users.messages.send({ userId: "me", requestBody: { raw } });
        return { success: true, data: { sent: true } };
    }
    catch (e) {
        return { success: false, error: e.message };
    }
}
