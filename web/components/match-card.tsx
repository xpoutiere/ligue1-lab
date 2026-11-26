"use client";
// MatchCard : pastilles, équipes (monogrammes), forme, stade, bloc « Modèle vs Marché »,
// cotes, et « Mon pronostic » stocké uniquement dans localStorage. Aucun score prédit.
import { Clock, MapPin } from "lucide-react";
import { useEffect, useState } from "react";
import { date as fmtDate, fmt, prob, type Lang } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import type { MatchItem } from "@/lib/data";
import { Chip, FormBadges, TeamMonogram } from "./ui";

const OUT = ["H", "D", "A"] as const;

export function ProbBars({ model, market, lang, labels }: { model: (number | null)[]; market: (number | null)[]; lang: Lang; labels: { model: string; market: string; outcomes: string[]; diff: string } }) {
  return (
    <div className="grid grid-cols-3 gap-3">
      {OUT.map((_, k) => {
        const m = model[k] ?? 0, q = market[k] ?? 0, d = 100 * (m - q);
        return (
          <div key={k} className="min-w-0">
            <div className="mb-1 text-center text-xs font-semibold text-muted">{labels.outcomes[k]}</div>
            {[[labels.model, m, "var(--series-1)"], [labels.market, q, "var(--series-2)"]].map(([lab, v, c]) => (
              <div key={String(lab)} className="mb-1">
                <div className="flex justify-between text-[11px] text-muted"><span>{String(lab)}</span><span className="tabular text-text">{prob(Number(v), lang)}</span></div>
                <div className="h-1.5 rounded-full bg-surface-2" role="presentation">
                  <div className="h-1.5 rounded-full" style={{ width: `${Math.round(Number(v) * 100)}%`, background: String(c) }} />
                </div>
              </div>
            ))}
            <div className="text-center text-[11px] tabular text-muted" title={labels.diff}>
              {d >= 0 ? "+" : "−"}{fmt(Math.abs(d), 0, lang)} {lang === "fr" ? "pts" : "pts"}
            </div>
          </div>
        );
      })}
    </div>
  );
}

export function MatchCard({ m, modelName }: { m: MatchItem; modelName: string }) {
  const { t, lang } = useI18n();
  const key = `pick:${m.date}:${m.home.code}:${m.away.code}`;
  const [pick, setPick] = useState<string | null>(null);
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- lecture d'un choix local après hydratation
    try { setPick(localStorage.getItem(key)); } catch {}
  }, [key]);
  const choose = (o: string) => {
    const next = pick === o ? null : o;
    setPick(next);
    try { if (next) localStorage.setItem(key, next); else localStorage.removeItem(key); } catch {}
  };
  const outcomes = [t.common.home, t.common.draw, t.common.away];
  const resultIdx = m.result ? OUT.indexOf(m.result as (typeof OUT)[number]) : -1;
  return (
    <article className="card flex flex-col gap-4 p-5 transition-transform duration-200 hover:-translate-y-0.5"
      aria-label={`${m.home.name} ${t.common.vs} ${m.away.name}, ${fmtDate(m.date, lang)}`}>
      <div className="flex items-center justify-between gap-2">
        <div className="flex gap-2"><Chip>{t.common.ligue1}</Chip>{m.market_source && <Chip>{t.common.source} {m.market_source}</Chip>}</div>
        <span className="inline-flex items-center gap-1 text-xs text-muted tabular">
          <Clock size={14} aria-hidden /> {fmtDate(m.date, lang, false)}{m.time ? `, ${m.time}` : ""}
        </span>
      </div>

      <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-2 text-center">
        {[m.home, null, m.away].map((side, i) => side ? (
          <div key={i} className="flex min-w-0 flex-col items-center gap-1">
            <TeamMonogram code={side.code} />
            <span className="font-display text-lg font-extrabold">{side.code}</span>
            <span className="truncate text-xs text-muted">{side.name}</span>
            <FormBadges form={side.form} lang={lang} label={`${t.common.form} ${side.name}`} />
          </div>
        ) : (
          <div key={i} className="flex flex-col items-center">
            <span className="font-display text-2xl font-extrabold text-accent-text">{m.score ? `${m.score[0]}–${m.score[1]}` : t.common.vs}</span>
            {m.score && <span className="text-[11px] text-muted">{t.matches.result}</span>}
          </div>
        ))}
      </div>

      {m.home.stadium && (
        <p className="flex items-center justify-center gap-1 text-xs text-muted"><MapPin size={14} aria-hidden /> {m.home.stadium}</p>
      )}

      <div className="rounded-[12px] bg-surface-2 p-3">
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted">{t.matches.modelVsMarket} <span className="normal-case">({modelName})</span></p>
        <ProbBars model={m.model} market={m.market} lang={lang} labels={{ model: t.common.model, market: t.common.market, outcomes, diff: t.matches.diff }} />
      </div>

      <div className="grid grid-cols-3 text-center">
        {outcomes.map((o, k) => (
          <div key={o}>
            <div className="text-[11px] text-muted">{o}</div>
            <div className={`font-bold tabular ${k === resultIdx ? "text-accent-text" : ""}`}>{fmt(m.odds[k], 2, lang)}</div>
          </div>
        ))}
      </div>

      <div>
        <p className="mb-1 text-xs text-muted" id={`${key}-lbl`}>{t.matches.myPick}</p>
        <div className="grid grid-cols-3 gap-2" role="group" aria-labelledby={`${key}-lbl`}>
          {OUT.map((o, k) => (
            <button key={o} type="button" onClick={() => choose(o)} aria-pressed={pick === o}
              className={`rounded-[8px] border px-2 py-2 text-xs font-semibold transition-colors ${pick === o ? "border-accent bg-accent text-on-accent" : "border-border bg-surface-2 text-text hover:border-accent"}`}>
              {outcomes[k]}
            </button>
          ))}
        </div>
      </div>
    </article>
  );
}
