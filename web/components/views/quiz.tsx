"use client";
// « Ma calibration » : le visiteur estime des probabilités sur des matchs passés (issus du test),
// puis compare son score de Brier au modèle et au marché. Données locales uniquement.
import { useEffect, useMemo, useState } from "react";
import { Card, PageHeader, StatTile, TeamMonogram } from "@/components/ui";
import type { QuizMatch } from "@/lib/data";
import { date as fmtDate, fmt, prob } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import { Target, User, Landmark } from "lucide-react";

const OUT = ["H", "D", "A"];
const brier = (p: number[], r: string) => OUT.reduce((s, o, k) => s + (p[k] - (o === r ? 1 : 0)) ** 2, 0);

export function QuizView({ matches }: { matches: QuizMatch[] }) {
  const { t, lang } = useI18n();
  const [ans, setAns] = useState<Record<number, number[]>>({});
  const [done, setDone] = useState(false);
  useEffect(() => {
    try {
      const s = localStorage.getItem("quiz-answers");
      // eslint-disable-next-line react-hooks/set-state-in-effect -- reprise des réponses locales après hydratation
      if (s) setAns(JSON.parse(s));
    } catch {}
  }, []);
  const save = (next: Record<number, number[]>) => {
    setAns(next);
    try { localStorage.setItem("quiz-answers", JSON.stringify(next)); } catch {}
  };
  const setVal = (id: number, k: number, v: number) => {
    const cur = ans[id] ?? [40, 30, 30];
    const next = [...cur];
    next[k] = Math.max(0, Math.min(100, v));
    save({ ...ans, [id]: next });
  };
  const valid = (p?: number[]) => !!p && Math.abs(p.reduce((a, b) => a + b, 0) - 100) < 0.5;
  const answered = matches.filter((m) => valid(ans[m.id]));
  const scores = useMemo(() => {
    if (!answered.length) return null;
    const mean = (f: (m: QuizMatch) => number) => answered.reduce((s, m) => s + f(m), 0) / answered.length;
    return {
      you: mean((m) => brier(ans[m.id].map((x) => x / 100), m.result)),
      model: mean((m) => brier(m.model.map(Number), m.result)),
      market: mean((m) => brier(m.market.map(Number), m.result)),
    };
  }, [answered, ans]);
  const outcomes = [t.common.home, t.common.draw, t.common.away];
  return (
    <>
      <PageHeader title={t.quiz.title} lead={t.quiz.lead} />
      <div className="grid gap-4 md:grid-cols-2">
        {matches.map((m) => {
          const p = ans[m.id] ?? [40, 30, 30];
          const sum = p.reduce((a, b) => a + b, 0);
          return (
            <Card key={m.id}>
              <div className="flex items-center justify-between text-xs text-muted"><span>{fmtDate(m.date, lang)}</span>
                {done && <span className="font-semibold text-accent-text">{t.matches.result} : {outcomes[OUT.indexOf(m.result)]}</span>}</div>
              <div className="my-3 flex items-center justify-center gap-4">
                <TeamMonogram code={m.home.code} /><span className="font-display font-extrabold text-accent-text">{t.common.vs}</span><TeamMonogram code={m.away.code} />
              </div>
              <p className="mb-3 text-center text-sm">{m.home.name} – {m.away.name}</p>
              <fieldset className="grid grid-cols-3 gap-2">
                <legend className="sr-only">{`${m.home.name} – ${m.away.name}`}</legend>
                {outcomes.map((o, k) => (
                  <label key={o} className="text-center text-xs text-muted">
                    {o}
                    <input type="number" min={0} max={100} step={5} value={p[k]} disabled={done}
                      onChange={(e) => setVal(m.id, k, Number(e.target.value))}
                      className="mt-1 w-full rounded-[8px] border border-border bg-surface-2 px-2 py-2 text-center text-base font-bold text-text tabular" aria-label={`${o} (%)`} />
                  </label>
                ))}
              </fieldset>
              {Math.abs(sum - 100) >= 0.5 && <p className="mt-2 text-xs text-warn" role="status">{t.quiz.sumWarn} ({sum} %)</p>}
              {done && (
                <p className="mt-3 text-xs text-muted tabular">{t.common.model} {m.model.map((x) => prob(x, lang)).join(" / ")} · {t.common.market} {m.market.map((x) => prob(x, lang)).join(" / ")}</p>
              )}
            </Card>
          );
        })}
      </div>
      <div className="sticky bottom-4 mt-8 flex flex-wrap items-center gap-3 rounded-[14px] border border-border bg-surface p-4">
        <span className="text-sm text-muted">{answered.length} / {matches.length} {t.quiz.answered}</span>
        {!done ? (
          <button type="button" disabled={!answered.length} onClick={() => setDone(true)}
            className="rounded-[8px] bg-accent px-4 py-2 font-bold text-on-accent disabled:opacity-40">{t.quiz.start}</button>
        ) : (
          <button type="button" onClick={() => { setDone(false); save({}); }} className="rounded-[8px] border border-border px-4 py-2 font-semibold">{t.quiz.reset}</button>
        )}
      </div>
      {done && scores && (
        <section className="mt-8" aria-live="polite">
          <h2 className="mb-3 font-display text-2xl font-bold">{t.quiz.score}</h2>
          <div className="grid gap-3 md:grid-cols-3">
            <StatTile icon={<User size={20} />} label={t.quiz.you} value={fmt(scores.you, 3, lang)} />
            <StatTile icon={<Target size={20} />} label={t.common.model} value={fmt(scores.model, 3, lang)} />
            <StatTile icon={<Landmark size={20} />} label={t.common.market} value={fmt(scores.market, 3, lang)} />
          </div>
        </section>
      )}
    </>
  );
}
