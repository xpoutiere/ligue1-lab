export type Lang = "fr" | "en";

const loc = (lang: Lang) => (lang === "fr" ? "fr-FR" : "en-GB");

export function fmt(x: number | null | undefined, digits = 3, lang: Lang = "fr"): string {
  if (x === null || x === undefined || Number.isNaN(x)) return "–";
  return x.toLocaleString(loc(lang), { minimumFractionDigits: digits, maximumFractionDigits: digits });
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

export function date(d: string, lang: Lang = "fr", withYear = true): string {
  const dt = new Date(`${d}T12:00:00Z`);
  return dt.toLocaleDateString(loc(lang), {
    weekday: "short", day: "numeric", month: "short", ...(withYear ? { year: "numeric" } : {}),
  });
}

export function seasonLabel(code: string): string {
  return `20${code.slice(0, 2)}-${code.slice(2)}`;
}
