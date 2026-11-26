export type Lang = "fr" | "en";

// Formatage SANS Intl : le rendu statique (Node du runner) et le navigateur peuvent embarquer
// des versions d'ICU différentes, ce qui provoquait une erreur d'hydratation React (#418).
export function fmt(x: number | null | undefined, digits = 3, lang: Lang = "fr"): string {
  if (x === null || x === undefined || Number.isNaN(x)) return "–";
  const [int, dec] = Math.abs(x).toFixed(digits).split(".");
  const grouped = int.replace(/\B(?=(\d{3})+(?!\d))/g, lang === "fr" ? " " : ",");
  const sign = x < 0 && Number(Math.abs(x).toFixed(digits)) !== 0 ? "-" : "";
  return sign + grouped + (dec ? (lang === "fr" ? "," : ".") + dec : "");
}

export function signed(x: number | null | undefined, digits = 3, lang: Lang = "fr"): string {
  if (x === null || x === undefined || Number.isNaN(x)) return "–";
  const s = fmt(Math.abs(x), digits, lang);
  return `${x > 0 ? "+" : x < 0 ? "−" : "±"}${s}`;
}

export function pct(x: number | null | undefined, digits = 1, lang: Lang = "fr"): string {
  if (x === null || x === undefined || Number.isNaN(x)) return "–";
  return `${fmt(x, digits, lang)} %`.replace(" %", lang === "fr" ? " %" : "%");
}

export function prob(x: number | null | undefined, lang: Lang = "fr"): string {
  if (x === null || x === undefined) return "–";
  return pct(100 * x, 0, lang);
}

export function ci(lo: number | null | undefined, hi: number | null | undefined, digits = 3, lang: Lang = "fr", sign = true) {
  const f = sign ? signed : fmt;
  return `[${f(lo, digits, lang)} ; ${f(hi, digits, lang)}]`;
}

const DAYS = { fr: ["dim.", "lun.", "mar.", "mer.", "jeu.", "ven.", "sam."], en: ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"] };
const MONTHS = {
  fr: ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."],
  en: ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
};

export function date(d: string, lang: Lang = "fr", withYear = true): string {
  const dt = new Date(`${d}T12:00:00Z`);
  const day = DAYS[lang][dt.getUTCDay()], m = MONTHS[lang][dt.getUTCMonth()], n = dt.getUTCDate();
  const y = withYear ? ` ${dt.getUTCFullYear()}` : "";
  return lang === "fr" ? `${day} ${n} ${m}${y}` : `${day} ${n} ${m}${y}`;
}

/** Horodatage ISO -> « 26 nov. 2026, 12:35 UTC » (sans Intl, identique serveur / navigateur). */
export function stamp(iso: string, lang: Lang = "fr"): string {
  const dt = new Date(iso);
  const hh = String(dt.getUTCHours()).padStart(2, "0"), mm = String(dt.getUTCMinutes()).padStart(2, "0");
  return `${dt.getUTCDate()} ${MONTHS[lang][dt.getUTCMonth()]} ${dt.getUTCFullYear()}, ${hh}:${mm} UTC`;
}

export function seasonLabel(code: string): string {
  return `20${code.slice(0, 2)}-${code.slice(2)}`;
}
