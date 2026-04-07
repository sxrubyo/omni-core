import { DateTime } from "luxon";
import type { TimeContext, InputClass } from "../types/index.js";

export function getTimeContext(): TimeContext {
  const tz = process.env.ARCHITECT_TIMEZONE || "America/Bogota";
  const now = DateTime.now().setZone(tz);
  const hour = now.hour;

  let period: TimeContext["period"];
  let energy: string;

  if (hour >= 0 && hour < 6) {
    period = "madrugada"; energy = "Modo silencioso — respuestas cortas";
  } else if (hour >= 6 && hour < 12) {
    period = "mañana"; energy = "Alta energía — modo GUERRA activo";
  } else if (hour >= 12 && hour < 19) {
    period = "tarde"; energy = "Ejecución — foco en resultados";
  } else {
    period = "noche"; energy = "Revisión y tribunal — auditoría del día";
  }

  return {
    hour,
    minutes: now.toFormat("mm"),
    period,
    energy,
    fullDate: now.toFormat("EEEE, dd 'de' MMMM yyyy", { locale: "es" }),
    isWeekend: now.weekday >= 6,
    isLateNight: hour >= 23 || hour < 5,
    shouldGreet: hour >= 5,
    timezone: tz,
  };
}

export function getSessionId(userId: string, channel: string): string {
  const date = DateTime.now()
    .setZone(process.env.ARCHITECT_TIMEZONE || "America/Bogota")
    .toFormat("yyyy-MM-dd");
  return `${channel}:${userId}:${date}`;
}

export function classifyInput(text: string): InputClass {
  if (!text) return "A_ARCHITECT";
  if (text.toUpperCase().startsWith("SCHEDULE_")) return "B_SCHEDULE";
  if (/^SON LAS \d{1,2}:\d{2}/.test(text)) return "B_SCHEDULE";
  if (text.startsWith("{") || text.startsWith("[")) return "C_CALLBACK";
  if (text.includes("REPORT:") || text.includes("RESULTADO:")) return "D_SUBREPORT";
  return "A_ARCHITECT";
}
