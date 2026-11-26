"use client";
import { Activity, BarChart3, Brain, Gauge, Percent, Scale, Sigma, Target } from "lucide-react";
import Link from "next/link";
import { BankrollBands, CalibrationChart, CumulativeGapChart, PitchOutcomes } from "@/components/charts";
import { MatchCard } from "@/components/match-card";
import { CountUp, Pill, Reveal, SectionTitle, StatTile } from "@/components/ui";
import { ci, fmt, signed } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import type { MatchItem } from "@/lib/data";

type Props = {
  summary: {
    n_test: number; market_log_loss: number; market_ll_ci: [number, number]; best_model: string;
    lgbm_delta: number; lgbm_delta_ci: [number, number]; pinnacle_margin_pct: number;
    b365_margin_pct: number; outcome_shares: [number, number, number]; n_matches: number;
    test_period: [string, string];
  };
  calib: { predite: number[]; observee: number[]; n: number[] };
  bands: { i: number[]; q05: number[]; q25: number[]; q50: number[]; q75: number[]; q95: number[] } | null;
  gap: { dates: string[]; series: Record<string, number[]> };
  recent: MatchItem[];
  modelName: string;
};

export function HomeView({ summary: s, calib, bands, gap, recent, modelName }: Props) {
  const { t, lang } = useI18n();
  const h = t.home;
  const icons = [<BarChart3 key="a" size={20} />, <Brain key="b" size={20} />, <Activity key="c" size={20} />];
  return (
    <>
      <section className="pb-12 pt-10 md:pt-16" aria-labelledby="hero-title">
        <h1 id="hero-title" className="font-display font-extrabold leading-[0.95]" style={{ fontSize: "clamp(2.75rem, 8vw, 7rem)" }}>
          {h.title1} {h.title2} <span className="text-accent-text">{h.accent}</span>{h.title3}
        </h1>
        <div className="mt-6 flex flex-wrap gap-3">
          {h.pills.map((p, i) => <Pill key={p} icon={icons[i]}>{p}</Pill>)}
        </div>
        <p className="mt-6 max-w-3xl text-lg text-muted">{h.lead}</p>

        <Reveal className="mt-10 grid gap-3 md:grid-cols-4 md:grid-rows-2" delay={0.05}>
          <div className="card overflow-hidden p-4 md:col-span-2 md:row-span-2">
            <p className="smallcaps text-muted">{h.mosaic.calib}</p>
            <CalibrationChart series={{ [t.common.market]: calib }} height={300} compact />
          </div>
          <div className="card overflow-hidden p-4 md:col-span-2">
            <p className="smallcaps text-muted">{h.mosaic.gap}</p>
            <CumulativeGapChart dates={gap.dates} series={{ LightGBM: gap.series["LightGBM"], "Dixon-Coles": gap.series["Dixon-Coles"] }} height={130} compact />
          </div>
          <div className="card overflow-hidden p-4">
            <p className="smallcaps text-muted">{h.mosaic.bankroll}</p>
            {bands && <BankrollBands bands={bands} height={130} compact />}
          </div>
          <div className="card overflow-hidden p-4">
            <p className="smallcaps text-muted">{h.mosaic.pitch}</p>
            <div className="h-[130px]"><PitchOutcomes home={s.outcome_shares[0]} draw={s.outcome_shares[1]} away={s.outcome_shares[2]} lang={lang} /></div>
          </div>
        </Reveal>
      </section>

      <Reveal>
        <section className="card mb-12 border-l-4 p-6 md:p-8" style={{ borderLeftColor: "var(--accent)" }} aria-labelledby="verdict">
          <p id="verdict" className="smallcaps text-accent-text">{h.verdictTitle}</p>
          <p className="mt-2 font-display text-2xl font-bold md:text-3xl">{h.verdict(s.best_model)}</p>
        </section>
      </Reveal>

      <section className="mb-16 grid gap-3 sm:grid-cols-2 lg:grid-cols-4" aria-label="Chiffres clés">
        <StatTile icon={<Target size={20} />} label={h.tiles.market} value={<CountUp value={s.market_log_loss} format={(v) => fmt(v, 3, lang)} />}
          sub={`${t.common.ci} ${ci(s.market_ll_ci[0], s.market_ll_ci[1], 3, lang, false)}`} />
        <StatTile icon={<Scale size={20} />} label={h.tiles.gap} value={signed(s.lgbm_delta, 3, lang)}
          sub={`${t.common.ci} ${ci(s.lgbm_delta_ci[0], s.lgbm_delta_ci[1], 3, lang)} · ${t.common.lower}`} />
        <StatTile icon={<Percent size={20} />} label={h.tiles.margin} value={<CountUp value={s.pinnacle_margin_pct} format={(v) => `${fmt(v, 2, lang)} %`} />}
          sub={`Bet365 ${fmt(s.b365_margin_pct, 2, lang)} %`} />
        <StatTile icon={<Sigma size={20} />} label={h.tiles.tested} value={<CountUp value={s.n_test} format={(v) => fmt(v, 0, lang)} />}
          sub={`${s.test_period[0]} → ${s.test_period[1]}`} />
      </section>

      <section className="mb-16" aria-labelledby="findings">
        <SectionTitle id="findings">{h.sections.findings}</SectionTitle>
        <div className="grid gap-3 md:grid-cols-2">
          {h.findings.map((f, i) => (
            <Reveal key={f.t} delay={i * 0.05}>
              <article className="card flex h-full gap-4 p-5">
                <span className="mt-1 text-accent-text" aria-hidden><Gauge size={22} /></span>
                <div>
                  <h3 className="font-display text-lg font-bold">{f.t}</h3>
                  <p className="mt-1 text-muted">{f.d}</p>
                </div>
              </article>
            </Reveal>
          ))}
        </div>
      </section>

      <section className="mb-8" aria-labelledby="recent">
        <SectionTitle id="recent" sub={t.matches.recentNote}>{h.sections.recent}</SectionTitle>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {recent.slice(0, 3).map((m) => <MatchCard key={`${m.date}${m.home.code}`} m={m} modelName={modelName} />)}
        </div>
        <Link href="/matchs/" className="mt-6 inline-block font-semibold text-accent-text underline-offset-4 hover:underline">{h.more} →</Link>
      </section>
    </>
  );
}
