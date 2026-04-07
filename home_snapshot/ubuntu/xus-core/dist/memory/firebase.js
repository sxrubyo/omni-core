"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.initFirebase = initFirebase;
exports.getSessionHistory = getSessionHistory;
exports.appendToSession = appendToSession;
exports.clearSession = clearSession;
exports.getLongTermMemory = getLongTermMemory;
exports.updateLongTermMemory = updateLongTermMemory;
exports.appendToLTM = appendToLTM;
exports.logReflection = logReflection;
exports.getActivePatches = getActivePatches;
exports.applyInstructionPatch = applyInstructionPatch;
exports.getSelfImprovementLog = getSelfImprovementLog;
exports.updateSelfImprovementLog = updateSelfImprovementLog;
const firebase_admin_1 = __importDefault(require("firebase-admin"));
let db;
function initFirebase() {
    if (firebase_admin_1.default.apps.length > 0)
        return;
    firebase_admin_1.default.initializeApp({
        credential: firebase_admin_1.default.credential.cert({
            projectId: process.env.FIREBASE_PROJECT_ID,
            privateKey: process.env.FIREBASE_PRIVATE_KEY?.replace(/\\n/g, "\n"),
            clientEmail: process.env.FIREBASE_CLIENT_EMAIL,
        }),
    });
    db = firebase_admin_1.default.firestore();
    console.log("[XUS Memory] Firebase ✓");
}
function getDb() {
    if (!db)
        throw new Error("Firebase not initialized");
    return db;
}
async function getSessionHistory(sessionId) {
    try {
        const doc = await getDb().collection("sessions").doc(sessionId).get();
        if (!doc.exists)
            return [];
        const data = doc.data();
        const lastUpdate = data.updatedAt?.toDate();
        if (lastUpdate && (Date.now() - lastUpdate.getTime()) / 3600000 > 24) {
            await clearSession(sessionId);
            return [];
        }
        return data.messages || [];
    }
    catch {
        return [];
    }
}
async function appendToSession(sessionId, entry) {
    const ref = getDb().collection("sessions").doc(sessionId);
    const doc = await ref.get();
    let messages = doc.exists ? doc.data().messages || [] : [];
    messages.push(entry);
    if (messages.length > 50)
        messages = messages.slice(-50);
    await ref.set({ messages, updatedAt: firebase_admin_1.default.firestore.FieldValue.serverTimestamp(), sessionId }, { merge: true });
}
async function clearSession(sessionId) {
    await getDb().collection("sessions").doc(sessionId).delete();
}
async function getLongTermMemory() {
    try {
        const doc = await getDb().collection("memory").doc("xus_ltm_main").get();
        if (!doc.exists)
            return { victories: [], failures: [], patterns: [], clients: [], lastUpdated: new Date() };
        return doc.data();
    }
    catch {
        return { victories: [], failures: [], patterns: [], clients: [], lastUpdated: new Date() };
    }
}
async function updateLongTermMemory(updates) {
    await getDb().collection("memory").doc("xus_ltm_main").set({ ...updates, lastUpdated: firebase_admin_1.default.firestore.FieldValue.serverTimestamp() }, { merge: true });
}
async function appendToLTM(type, entry) {
    await getDb().collection("memory").doc("xus_ltm_main").update({
        [type]: firebase_admin_1.default.firestore.FieldValue.arrayUnion(entry),
        lastUpdated: firebase_admin_1.default.firestore.FieldValue.serverTimestamp(),
    });
}
async function logReflection(entry) {
    await getDb().collection("reflections").add({ ...entry, timestamp: firebase_admin_1.default.firestore.FieldValue.serverTimestamp() });
}
async function getActivePatches() {
    try {
        const doc = await getDb().collection("system").doc("instruction_patches").get();
        if (!doc.exists)
            return [];
        return (doc.data().patches || []).filter((p) => p.applied);
    }
    catch {
        return [];
    }
}
async function applyInstructionPatch(patch) {
    await getDb().collection("system").doc("instruction_patches").set({ patches: firebase_admin_1.default.firestore.FieldValue.arrayUnion({ ...patch, applied: true, appliedAt: new Date().toISOString() }) }, { merge: true });
}
async function getSelfImprovementLog() {
    try {
        const doc = await getDb().collection("system").doc("self_improvement").get();
        if (!doc.exists)
            return { totalSessions: 0, avgQuality: 0, topIssues: [], appliedImprovements: [], lastReflection: new Date(), instructionPatches: [] };
        return doc.data();
    }
    catch {
        return { totalSessions: 0, avgQuality: 0, topIssues: [], appliedImprovements: [], lastReflection: new Date(), instructionPatches: [] };
    }
}
async function updateSelfImprovementLog(updates) {
    await getDb().collection("system").doc("self_improvement").set(updates, { merge: true });
}
