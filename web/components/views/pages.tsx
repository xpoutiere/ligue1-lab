"use client";
// Vues client des pages (le texte suit la langue choisie ; les données viennent des artefacts).
import { BankrollBands, CalibrationChart, CumulativeGapChart, EffectForest, MarginChart, RoiByOddsChart, ShapBars } from "@/components/charts";
import { MatchCard } from "@/components/match-card";
import { Card, EmptyState, FormBadges, PageHeader, Reveal, SectionTitle, StatTile, TeamMonogram } from "@/components/ui";
import type { Biases, MatchItem, Metric, Models, Strategy, TeamRow } from "@/lib/data";
import { ci, date as fmtDate, fmt, pct, prob, seasonLabel, signed } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import { AlertTriangle, LineChart, Shield, TrendingDown } from "lucide-react";

function Table({ head, rows, caption }: { head: string[]; rows: (string | number | React.ReactNode)[][]; caption?: string }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[640px] text-left text-sm">
        {caption && <caption className="sr-only">{caption}</caption>}
        <thead>
          <tr className="border-b border-border text-xs uppercase tracking-wide text-muted">
            {head.map((h) => <th key={h} scope="col" className="px-3 py-2 font-semibold">{h}</th>)}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i} className="border-b border-border last:border-0">
              {r.map((c, j) => j === 0
                ? <th key={j} scope="row" className="px-3 py-2 font-semibold">{c}</th>
                : <td key={j} className="px-3 py-2 tabular">{c}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/* ------------------------------------------------------------------ Matchs */
export function MatchesView({ upcoming, recent, modelName }: { upcoming: MatchItem[]; recent: MatchItem[]; modelName: string }) {
  const { t } = useI18n();
  return (
    <>
      <PageHeader title={t.matches.title} lead={t.matches.lead} />
      <section className="mb-14" aria-labelledby="up">
        <SectionTitle id="up">{t.matches.upcoming}</SectionTitle>
        {upcoming.length ? (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {upcoming.map((m) => <MatchCard key={`${m.date}${m.home.code}`} m={m} modelName={modelName} />)}
          </div>
        ) : <EmptyState>{t.matches.noUpcoming}</EmptyState>}
      </section>
      <section aria-labelledby="rec">
        <SectionTitle id="rec" sub={`${t.matches.recentNote} ${t.matches.myPickNote}`}>{t.matches.recent}</SectionTitle>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {recent.map((m) => <MatchCard key={`${m.date}${m.home.code}`} m={m} modelName={modelName} />)}
        </div>
      </section>
    </>
  );
}

/* ------------------------------------------------------------------ Modèles */
function metricRows(ms: Metric[], lang: "fr" | "en", withP = true) {
  return ms.map((m) => [
    m["modèle"],
    fmt(m.log_loss, 4, lang),
    ci(m.ll_ic95_bas, m.ll_ic95_haut, 3, lang, false),
    m["modèle"] === "Marché" ? "–" : `${signed(m["delta_vs_marché"], 4, lang)} ${ci(m.delta_ic95_bas, m.delta_ic95_haut, 3, lang)}`,
    fmt(m.brier, 4, lang),
    pct(m["accuracy_%"], 1, lang),
    ...(withP ? [m.p_holm === null || m.p_holm === undefined ? "–" : fmt(m.p_holm, 2, lang)] : []),
  ]);
}

export function ModelsView({ d }: { d: Models }) {
  const { t, lang } = useI18n();
  const p = d.protocol;
  const head = [t.common.model, t.common.logloss, t.common.ci, lang === "fr" ? "Écart au marché [IC95]" : "Gap to market [95% CI]", t.common.brier, t.common.accuracy];
  const seasons = (xs: string[]) => xs.map(seasonLabel).join(", ");
  return (
    <>
      <PageHeader title={t.models.title} lead={t.models.lead} />
      <div className="mb-10 grid gap-3 md:grid-cols-3">
        <StatTile icon={<Shield size={20} />} label={lang === "fr" ? "Apprentissage" : "Training"} value={fmt(p.n_train, 0, lang)} sub={seasons(p.train)} />
        <StatTile icon={<LineChart size={20} />} label="Validation" value={fmt(p.n_valid, 0, lang)} sub={seasons(p.valid)} />
        <StatTile icon={<TrendingDown size={20} />} label={lang === "fr" ? "Test final (une seule fois)" : "Final test (once)"} value={fmt(p.n_test, 0, lang)} sub={`${p.test_period[0]} → ${p.test_period[1]}`} />
      </div>

      <Reveal><Card title={t.models.table} desc={`${t.common.lower}. p Holm : ${lang === "fr" ? "p-valeur corrigée de « meilleur que le marché »" : "corrected p-value of “better than market”"}.`} className="mb-6">
        <Table head={[...head, "p Holm"]} rows={metricRows(d.metrics, lang)} caption={t.models.table} />
      </Card></Reveal>

      <Reveal><Card title={t.models.pinnacle} desc={`${fmt(p.n_test_pinnacle, 0, lang)} ${lang === "fr" ? "matchs dont la baseline est Pinnacle clôture (référence la plus stricte)" : "matches with Pinnacle closing baseline (strictest reference)"}`} className="mb-6">
        <Table head={head} rows={metricRows(d.metrics_pinnacle_only, lang, false)} caption={t.models.pinnacle} />
      </Card></Reveal>

      <div className="mb-6 grid gap-6 lg:grid-cols-2">
        <Card title={t.models.calib}><CalibrationChart series={Object.fromEntries(Object.entries(d.calibration).filter(([k]) => k !== "LightGBM calibré"))} /></Card>
        <Card title={t.models.cum} desc={t.models.cumNote}><CumulativeGapChart dates={d.cumulative_gap.dates} series={d.cumulative_gap.series} /></Card>
      </div>

      <Reveal><Card title={t.models.enc} desc={t.models.encNote} className="mb-6">
        <Table head={[t.common.model, "a (" + t.common.market.toLowerCase() + ")", "b (" + t.common.model.toLowerCase() + ")", t.common.ci, "p"]}
          rows={Object.entries(d.encompassing).map(([k, e]) => [k, fmt(e.a_marche, 2, lang), signed(e.b_modele, 2, lang), ci(e.b_ic95[0], e.b_ic95[1], 2, lang), fmt(e.p_value, 3, lang)])} />
      </Card></Reveal>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card title={t.models.shap}><ShapBars values={d.shap_top} /></Card>
        <Card title={t.models.choices}>
          <ul className="space-y-2 text-sm">
            <li><span className="text-muted">{lang === "fr" ? "Logistique, régularisation C" : "Logistic, regularisation C"} :</span> <span className="tabular">{d.choices.logit_C}</span></li>
            <li><span className="text-muted">LightGBM :</span> <span className="tabular">{Object.entries(d.choices.lgbm.params).map(([k, v]) => `${k}=${v}`).join(", ")}, {d.choices.lgbm.n_estimators} {lang === "fr" ? "arbres" : "trees"}</span></li>
            <li><span className="text-muted">{lang === "fr" ? "Calibration retenue" : "Calibration chosen"} :</span> {d.choices.calibration} <span className="text-muted tabular">({Object.entries(d.choices.calibration_scores).map(([k, v]) => `${k} ${fmt(v, 4, lang)}`).join(", ")})</span></li>
            <li><span className="text-muted">{lang === "fr" ? "Poids de la combinaison" : "Pool weights"} :</span> <span className="tabular">{Object.entries(d.choices.pool_weights).map(([k, v]) => `${k} ${fmt(v, 2, lang)}`).join(", ")}</span></li>
          </ul>
        </Card>
      </div>
    </>
  );
}

/* ------------------------------------------------------------------ Stratégie */
export function StrategyView({ d }: { d: Strategy }) {
  const { t, lang } = useI18n();
  const names = Object.keys(d.models);
  return (
    <>
      <PageHeader title={t.strategy.title} lead={t.strategy.lead} />
      <div className="mb-8 grid gap-3 md:grid-cols-3">
        {names.map((n) => {
          const s = d.models[n].test;
          return <StatTile key={n} icon={<TrendingDown size={20} />} label={`${t.strategy.clv} · ${n}`} value={`${signed(s["clv_moy_%"], 2, lang)} %`}
            sub={`${t.common.ci} ${ci(s["clv_ic95_%"]?.[0], s["clv_ic95_%"]?.[1], 2, lang)} · ${s.paris} ${lang === "fr" ? "paris" : "bets"}`} />;
        })}
      </div>
      <p className="mb-10 text-muted">{t.strategy.random} : <span className="tabular text-text">{signed(d["clv_random_bet_b365_%"], 2, lang)} %</span>.</p>

      <Card title={lang === "fr" ? "Résultats sur le test" : "Test results"} className="mb-6">
        <Table head={[t.common.model, lang === "fr" ? "Seuil (validation)" : "Threshold (validation)", lang === "fr" ? "Paris" : "Bets", "ROI [IC95]", "CLV [IC95]", lang === "fr" ? "Bankroll 100 →" : "Bankroll 100 →", "Drawdown max", t.strategy.ruin]}
          rows={names.map((n) => {
            const m = d.models[n], s = m.test;
            return [n, pct(100 * m.edge, 0, lang), s.paris, `${signed(s["roi_flat_%"], 1, lang)} % ${ci(s["roi_ic95_%"]?.[0], s["roi_ic95_%"]?.[1], 1, lang)}`,
              `${signed(s["clv_moy_%"], 2, lang)} % ${ci(s["clv_ic95_%"]?.[0], s["clv_ic95_%"]?.[1], 2, lang)}`, fmt(s.bankroll_finale, 0, lang),
              pct(s["drawdown_max_%"], 0, lang), m.mc ? pct(m.mc["p_ruine_%"], 0, lang) : "–"];
          })} />
      </Card>

      <div className="mb-6 grid gap-6 lg:grid-cols-2">
        {names.map((n) => d.models[n].mc && (
          <Card key={n} title={`${t.strategy.bankroll} · ${n}`}
            desc={`${t.strategy.ruin} : ${pct(d.models[n].mc!["p_ruine_%"], 0, lang)} · ${t.strategy.perte} : ${pct(d.models[n].mc!["p_perte_%"], 0, lang)}`}>
            <BankrollBands bands={d.models[n].mc!.bands} actual={d.models[n].bankroll.bankroll} />
          </Card>
        ))}
      </div>
      <Card title={t.strategy.margin} desc={t.strategy.marginNote}>
        <MarginChart series={Object.fromEntries(names.map((n) => [n, d.models[n].margin]))} />
      </Card>
    </>
  );
}

/* ------------------------------------------------------------------ Biais */
export function BiasesView({ d }: { d: Biases }) {
  const { t, lang } = useI18n();
  return (
    <>
      <PageHeader title={t.biases.title} lead={t.biases.lead} />
      <Card title={t.biases.byOdds} desc={`${fmt(d.n_matchs, 0, lang)} ${lang === "fr" ? "matchs" : "matches"}, ${d.periode[0]} → ${d.periode[1]}`} className="mb-6">
        <RoiByOddsChart rows={d.par_tranche_de_cote} />
      </Card>
      <Card title={t.biases.effect} desc={t.biases.note} className="mb-6">
        <EffectForest rows={d.tests.map((x) => ({ label: x.label, mean: x.resid_pts.moyenne, lo: x.resid_pts.ic95[0], hi: x.resid_pts.ic95[1] }))} />
      </Card>
      <div className="grid gap-4 md:grid-cols-2">
        {d.tests.map((x) => (
          <Reveal key={x.label}>
            <article className="card h-full p-5">
              <h3 className="font-display text-lg font-bold">{x.label}</h3>
              <p className="mt-1 text-sm text-muted">{t.biases.hyp} : {x.hypothese}</p>
              <dl className="mt-3 grid grid-cols-2 gap-2 text-sm">
                <dt className="text-muted">n</dt><dd className="tabular">{fmt(x.resid_pts.n, 0, lang)}</dd>
                <dt className="text-muted">{lang === "fr" ? "Résidu" : "Residual"}</dt><dd className="tabular">{signed(x.resid_pts.moyenne, 2, lang)} pts {ci(x.resid_pts.ic95[0], x.resid_pts.ic95[1], 2, lang)}</dd>
                <dt className="text-muted">p / Holm / BH</dt><dd className="tabular">{fmt(x.resid_pts.p, 3, lang)} / {fmt(x.p_holm, 2, lang)} / {fmt(x.p_bh, 2, lang)}</dd>
                <dt className="text-muted">ROI Bet365</dt><dd className="tabular">{signed(x["roi_b365_%"].moyenne, 1, lang)} % {ci(x["roi_b365_%"].ic95[0], x["roi_b365_%"].ic95[1], 1, lang)}</dd>
              </dl>
              <p className="mt-3 flex items-start gap-2 text-sm"><AlertTriangle size={16} className="mt-0.5 shrink-0 text-warn" aria-hidden /><span><strong>{x.verdict}</strong> · {x.exploitable}</span></p>
            </article>
          </Reveal>
        ))}
      </div>
    </>
  );
}

/* ------------------------------------------------------------------ Équipes */
export function TeamsView({ teams, season, home }: { teams: TeamRow[]; season: string; home: number }) {
  const { t, lang } = useI18n();
  return (
    <>
      <PageHeader title={`${t.teams.title} · ${seasonLabel(season)}`} lead={`${t.teams.lead} ${lang === "fr" ? "Avantage du terrain estimé" : "Estimated home advantage"} : ${fmt(home, 3, lang)} log-buts.`} />
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {teams.map((r) => (
          <article key={r.code} className="card flex items-center gap-4 p-4 transition-transform hover:-translate-y-0.5">
            <span className="w-6 text-right font-display text-xl font-extrabold tabular text-muted">{r.rank}</span>
            <TeamMonogram code={r.code} size={48} />
            <div className="min-w-0 flex-1">
              <h2 className="truncate font-display text-lg font-bold">{r.name}</h2>
              <p className="text-xs text-muted tabular">{r.pts} {t.teams.pts} · {r.j} {t.teams.played} · {t.teams.gd} {r.bp - r.bc >= 0 ? "+" : ""}{r.bp - r.bc}</p>
              <div className="mt-1"><FormBadges form={r.form} lang={lang} label={t.common.form} /></div>
            </div>
            <dl className="grid grid-cols-[auto_auto] gap-x-2 text-right text-xs">
              <dt className="text-muted">{t.teams.elo}</dt><dd className="tabular font-semibold">{fmt(r.elo, 0, lang)}</dd>
              <dt className="text-muted">{t.teams.attack}</dt><dd className="tabular">{signed(r.attack, 2, lang)}</dd>
              <dt className="text-muted">{t.teams.defense}</dt><dd className="tabular">{signed(r.defense, 2, lang)}</dd>
            </dl>
          </article>
        ))}
      </div>
    </>
  );
}

/* ------------------------------------------------------------------ Journal */
export function JournalView({ entries }: { entries: Record<string, string | number | null>[] }) {
  const { t, lang } = useI18n();
  const settled = entries.filter((e) => e.FTR);
  const brier = (e: Record<string, string | number | null>, pre: string) => {
    const y = ["H", "D", "A"].map((o) => (e.FTR === o ? 1 : 0));
    return ["H", "D", "A"].reduce((s, o, k) => s + (Number(e[`${pre}${o}`]) - y[k]) ** 2, 0);
  };
  const mean = (xs: number[]) => xs.reduce((a, b) => a + b, 0) / Math.max(1, xs.length);
  return (
    <>
      <PageHeader title={t.journal.title} lead={t.journal.lead} />
      {entries.length === 0 ? <EmptyState>{t.journal.empty}</EmptyState> : (
        <>
          {settled.length > 0 && (
            <div className="mb-6 grid gap-3 md:grid-cols-3">
              <StatTile icon={<LineChart size={20} />} label={lang === "fr" ? "Matchs joués" : "Settled matches"} value={settled.length} />
              <StatTile icon={<LineChart size={20} />} label={`Brier ${t.common.model}`} value={fmt(mean(settled.map((e) => brier(e, "m_"))), 3, lang)} />
              <StatTile icon={<LineChart size={20} />} label={`Brier ${t.common.market}`} value={fmt(mean(settled.map((e) => brier(e, "mkt_"))), 3, lang)} />
            </div>
          )}
          <Card>
            <Table head={[t.journal.match, t.journal.predictedAt, `${t.common.model} H/N/A`, `${t.common.market} H/N/A`, t.matches.result]}
              rows={entries.map((e) => [`${e.HomeTeam} – ${e.AwayTeam} (${fmtDate(String(e.Date), lang, false)})`, String(e.predicted_at),
                [e.m_H, e.m_D, e.m_A].map((v) => prob(Number(v), lang)).join(" / "),
                [e.mkt_H, e.mkt_D, e.mkt_A].map((v) => prob(Number(v), lang)).join(" / "),
                e.FTR ? `${e.FTHG}–${e.FTAG}` : "…"])} />
          </Card>
        </>
      )}
    </>
  );
}
