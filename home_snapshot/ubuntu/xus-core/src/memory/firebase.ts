import admin from "firebase-admin";
import type { MemoryEntry, LongTermMemory, ReflectionEntry, InstructionPatch } from "../types/index.js";

let db: admin.firestore.Firestore;

export function initFirebase(): void {
  if (admin.apps.length > 0) return;
  admin.initializeApp({
    credential: admin.credential.cert({
      projectId: process.env.FIREBASE_PROJECT_ID,
      privateKey: process.env.FIREBASE_PRIVATE_KEY?.replace(/\\n/g, "\n"),
      clientEmail: process.env.FIREBASE_CLIENT_EMAIL,
    } as admin.ServiceAccount),
  });
  db = admin.firestore();
  console.log("[XUS Memory] Firebase ✓");
}

function getDb() {
  if (!db) throw new Error("Firebase not initialized");
  return db;
}

export async function getSessionHistory(sessionId: string): Promise<MemoryEntry[]> {
  try {
    const doc = await getDb().collection("sessions").doc(sessionId).get();
    if (!doc.exists) return [];
    const data = doc.data()!;
    const lastUpdate = data.updatedAt?.toDate() as Date;
    if (lastUpdate && (Date.now() - lastUpdate.getTime()) / 3600000 > 24) {
      await clearSession(sessionId);
      return [];
    }
    return data.messages || [];
  } catch { return []; }
}

export async function appendToSession(sessionId: string, entry: MemoryEntry): Promise<void> {
  const ref = getDb().collection("sessions").doc(sessionId);
  const doc = await ref.get();
  let messages: MemoryEntry[] = doc.exists ? doc.data()!.messages || [] : [];
  messages.push(entry);
  if (messages.length > 50) messages = messages.slice(-50);
  await ref.set({ messages, updatedAt: admin.firestore.FieldValue.serverTimestamp(), sessionId }, { merge: true });
}

export async function clearSession(sessionId: string): Promise<void> {
  await getDb().collection("sessions").doc(sessionId).delete();
}

export async function getLongTermMemory(): Promise<LongTermMemory> {
  try {
    const doc = await getDb().collection("memory").doc("xus_ltm_main").get();
    if (!doc.exists) return { victories: [], failures: [], patterns: [], clients: [], lastUpdated: new Date() };
    return doc.data() as LongTermMemory;
  } catch { return { victories: [], failures: [], patterns: [], clients: [], lastUpdated: new Date() }; }
}

export async function updateLongTermMemory(updates: Partial<LongTermMemory>): Promise<void> {
  await getDb().collection("memory").doc("xus_ltm_main").set(
    { ...updates, lastUpdated: admin.firestore.FieldValue.serverTimestamp() },
    { merge: true }
  );
}

export async function appendToLTM(type: "victories"|"failures"|"patterns"|"clients", entry: Record<string, unknown>): Promise<void> {
  await getDb().collection("memory").doc("xus_ltm_main").update({
    [type]: admin.firestore.FieldValue.arrayUnion(entry),
    lastUpdated: admin.firestore.FieldValue.serverTimestamp(),
  });
}

export async function logReflection(entry: ReflectionEntry): Promise<void> {
  await getDb().collection("reflections").add({ ...entry, timestamp: admin.firestore.FieldValue.serverTimestamp() });
}

export async function getActivePatches(): Promise<InstructionPatch[]> {
  try {
    const doc = await getDb().collection("system").doc("instruction_patches").get();
    if (!doc.exists) return [];
    return (doc.data()!.patches || []).filter((p: InstructionPatch) => p.applied);
  } catch { return []; }
}

export async function applyInstructionPatch(patch: InstructionPatch): Promise<void> {
  await getDb().collection("system").doc("instruction_patches").set(
    { patches: admin.firestore.FieldValue.arrayUnion({ ...patch, applied: true, appliedAt: new Date().toISOString() }) },
    { merge: true }
  );
}

export async function getSelfImprovementLog() {
  try {
    const doc = await getDb().collection("system").doc("self_improvement").get();
    if (!doc.exists) return { totalSessions: 0, avgQuality: 0, topIssues: [], appliedImprovements: [], lastReflection: new Date(), instructionPatches: [] };
    return doc.data()!;
  } catch { return { totalSessions: 0, avgQuality: 0, topIssues: [], appliedImprovements: [], lastReflection: new Date(), instructionPatches: [] }; }
}

export async function updateSelfImprovementLog(updates: Record<string, unknown>): Promise<void> {
  await getDb().collection("system").doc("self_improvement").set(updates, { merge: true });
}
