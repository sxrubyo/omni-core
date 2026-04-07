export type Channel = "telegram" | "whatsapp";
export type MessageType = "text" | "audio" | "image" | "callback" | "schedule";
export type InputClass = "A_ARCHITECT" | "B_SCHEDULE" | "C_CALLBACK" | "D_SUBREPORT";

export interface IncomingMessage {
  id: string;
  channel: Channel;
  type: MessageType;
  text?: string;
  audioBase64?: string;
  audioMimeType?: string;
  imageBase64?: string;
  chatId: string;
  userId?: string;
  username?: string;
  timestamp: Date;
  raw: Record<string, unknown>;
}

export interface TimeContext {
  hour: number;
  minutes: string;
  period: "madrugada" | "mañana" | "tarde" | "noche";
  energy: string;
  fullDate: string;
  isWeekend: boolean;
  isLateNight: boolean;
  shouldGreet: boolean;
  timezone: string;
}

export interface MemoryEntry {
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  channel: Channel;
  sessionId: string;
}

export interface LongTermMemory {
  victories: MemoryRecord[];
  failures: MemoryRecord[];
  patterns: MemoryRecord[];
  clients: ClientRecord[];
  lastUpdated: Date;
}

export interface MemoryRecord {
  type: "VICTORY" | "FAILURE" | "PATTERN" | "CLOSURE";
  content: string;
  date: string;
  data?: Record<string, unknown>;
}

export interface ClientRecord {
  name: string;
  amount?: number;
  closedDate?: string;
  status: string;
  notes?: string;
}

export interface AgentOutput {
  text: string;
  audioRequested: boolean;
  toolsUsed: string[];
  shouldUpdateLTM: boolean;
  ltmUpdate?: Partial<LongTermMemory>;
}

export interface ReflectionEntry {
  sessionId: string;
  userInput: string;
  agentOutput: string;
  toolsUsed: string[];
  quality: number;
  issues: string[];
  improvements: string[];
  timestamp: Date;
}

export interface SelfImprovementLog {
  totalSessions: number;
  avgQuality: number;
  topIssues: string[];
  appliedImprovements: string[];
  lastReflection: Date;
  instructionPatches: InstructionPatch[];
}

export interface InstructionPatch {
  id: string;
  description: string;
  applied: boolean;
  appliedAt?: Date;
  triggerCondition: string;
}
