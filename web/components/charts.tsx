"use client";
// Graphiques stylés aux tokens (jamais les couleurs par défaut de Recharts).
// Chaque graphique a un résumé textuel accessible (figcaption visuellement masquée ou visible).
import {
  Area, Bar, BarChart, CartesianGrid, ComposedChart, ErrorBar, Legend, Line, LineChart,
  ReferenceLine, ResponsiveContainer, Scatter, Tooltip, XAxis, YAxis,
} from "recharts";
import { useI18n } from "@/lib/i18n";
import { fmt, type Lang } from "@/lib/format";

const S = ["var(--series-1)", "var(--series-2)", "var(--series-3)", "var(--series-4)"];
const tooltipStyle = { background: "var(--surface-2)", border: "1px solid var(--border)", borderRadius: 8, color: "var(--text)" };
const axis = { stroke: "var(--border)", tick: { fill: "var(--muted)", fontSize: 12 } };

function Figure({ summary, height = 280, children }: { summary: string; height?: number; children: React.ReactElement }) {
  return (
    <figure role="img" aria-label={summary} className="w-full">
      <div style={{ height }} className="w-full">
        <ResponsiveContainer width="100%" height="100%">{children}</ResponsiveContainer>
      </div>
      <figcaption className="sr-only">{summary}</figcaption>
    </figure>
  );
}

type Calib = { predite: number[]; observee: number[]; n: number[] };

export function CalibrationChart({ series, height = 300, compact = false }: { series: Record<string, Calib>; height?: number; compact?: boolean }) {
  const { lang } = useI18n();
  const names = Object.keys(series);
  const data = names.flatMap((n) => series[n].predite.map((p, i) => ({ name: n, x: p, y: series[n].observee[i], n: series[n].n[i] })));
  const maxDev = Math.max(...data.filter((d) => d.n >= 100).map((d) => Math.abs(d.x - d.y)));
  const summary = lang === "fr"
    ? `Courbe de calibration : probabilité prédite en abscisse, fréquence observée en ordonnée, pour ${names.join(", ")}. Écart maximal à la diagonale (classes d'au moins 100 issues) : ${fmt(maxDev, 3, lang)}.`
    : `Calibration curve: predicted probability vs observed frequency for ${names.join(", ")}. Maximum gap to the diagonal (bins with at least 100 outcomes): ${fmt(maxDev, 3, lang)}.`;
  return (
    <Figure summary={summary} height={height}>
      <ComposedChart margin={{ top: 8, right: 8, bottom: compact ? 0 : 16, left: compact ? -24 : 0 }}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis type="number" dataKey="x" domain={[0, 1]} ticks={[0, 0.25, 0.5, 0.75, 1]} {...axis} hide={compact}
          label={compact ? undefined : { value: lang === "fr" ? "probabilité prédite" : "predicted probability", position: "insideBottom", offset: -8, fill: "var(--muted)", fontSize: 12 }} />
        <YAxis type="number" dataKey="y" domain={[0, 1]} ticks={[0, 0.25, 0.5, 0.75, 1]} {...axis} hide={compact} />
        <ReferenceLine segment={[{ x: 0, y: 0 }, { x: 1, y: 1 }]} stroke="var(--muted)" strokeDasharray="4 4" />
        {!compact && <Tooltip contentStyle={tooltipStyle} formatter={(v) => fmt(Number(v), 3, lang)} />}
        {names.map((n, k) => (
          <Line key={n} data={series[n].predite.map((p, i) => ({ x: p, y: series[n].observee[i] }))} dataKey="y" name={n}
            stroke={S[k % S.length]} strokeWidth={2} dot={{ r: compact ? 2 : 3, fill: S[k % S.length] }} isAnimationActive={false} type="linear" />
        ))}
        {!compact && names.length > 1 && <Legend verticalAlign="top" height={30} wrapperStyle={{ color: "var(--muted)", fontSize: 12 }} />}
      </ComposedChart>
    </Figure>
  );
}

export function CumulativeGapChart({ dates, series, height = 300, compact = false }: { dates: string[]; series: Record<string, number[]>; height?: number; compact?: boolean }) {
  const { lang } = useI18n();
  const names = Object.keys(series);
  const step = Math.max(1, Math.floor(dates.length / 200));
  const data = dates.filter((_, i) => i % step === 0 || i === dates.length - 1).map((d) => {
    const i = dates.indexOf(d);
    return { d, ...Object.fromEntries(names.map((n) => [n, series[n][i]])) };
  });
  const finals = names.map((n) => `${n} ${fmt(series[n][series[n].length - 1], 1, lang)}`).join(", ");
  const summary = lang === "fr"
    ? `Somme cumulée de la log-loss du marché moins celle de chaque modèle sur ${dates.length} matchs de test. Valeurs finales : ${finals}. Négatif signifie que le marché fait mieux.`
    : `Cumulative market log-loss minus model log-loss over ${dates.length} test matches. Final values: ${finals}. Negative means the market does better.`;
  return (
    <Figure summary={summary} height={height}>
      <LineChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: compact ? -24 : 0 }}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="d" {...axis} hide={compact} minTickGap={60} />
        <YAxis {...axis} hide={compact} />
        <ReferenceLine y={0} stroke="var(--muted)" />
        {!compact && <Tooltip contentStyle={tooltipStyle} formatter={(v) => fmt(Number(v), 2, lang)} />}
        {names.map((n, k) => (
          <Line key={n} dataKey={n} stroke={S[k % S.length]} strokeWidth={2} dot={false} isAnimationActive={false} />
        ))}
        {!compact && <Legend verticalAlign="top" height={30} wrapperStyle={{ color: "var(--muted)", fontSize: 12 }} />}
      </LineChart>
    </Figure>
  );
}

type Bands = { i: number[]; q05: number[]; q25: number[]; q50: number[]; q75: number[]; q95: number[] };

export function BankrollBands({ bands, actual, height = 300, compact = false }: { bands: Bands; actual?: number[]; height?: number; compact?: boolean }) {
  const { lang } = useI18n();
  const data = bands.i.map((i, k) => ({
    i, outer: [bands.q05[k], bands.q95[k]], inner: [bands.q25[k], bands.q75[k]], q50: bands.q50[k],
    actual: actual ? actual[Math.min(i, actual.length - 1)] : undefined,
  }));
  const last = bands.q50.length - 1;
  const summary = lang === "fr"
    ? `Bankroll simulée partant de 100 : médiane finale ${fmt(bands.q50[last], 0, lang)}, 90 % des trajectoires entre ${fmt(bands.q05[last], 0, lang)} et ${fmt(bands.q95[last], 0, lang)}.`
    : `Simulated bankroll starting at 100: final median ${fmt(bands.q50[last], 0, lang)}, 90% of paths between ${fmt(bands.q05[last], 0, lang)} and ${fmt(bands.q95[last], 0, lang)}.`;
  return (
    <Figure summary={summary} height={height}>
      <ComposedChart data={data} margin={{ top: 8, right: 8, bottom: compact ? 0 : 16, left: compact ? -24 : 0 }}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="i" {...axis} hide={compact}
          label={compact ? undefined : { value: lang === "fr" ? "pari n°" : "bet #", position: "insideBottom", offset: -8, fill: "var(--muted)", fontSize: 12 }} />
        <YAxis {...axis} hide={compact} />
        <ReferenceLine y={100} stroke="var(--muted)" strokeDasharray="4 4" />
        <Area dataKey="outer" stroke="none" fill="var(--series-1)" fillOpacity={0.12} isAnimationActive={false} name={lang === "fr" ? "90 % des trajectoires" : "90% of paths"} />
        <Area dataKey="inner" stroke="none" fill="var(--series-1)" fillOpacity={0.25} isAnimationActive={false} name={lang === "fr" ? "50 % des trajectoires" : "50% of paths"} />
        <Line dataKey="q50" stroke="var(--series-1)" strokeWidth={2} dot={false} isAnimationActive={false} name={lang === "fr" ? "médiane" : "median"} />
        {actual && <Line dataKey="actual" stroke="var(--series-2)" strokeWidth={1.5} dot={false} isAnimationActive={false} name={lang === "fr" ? "trajectoire réelle" : "actual path"} />}
        {!compact && <Tooltip contentStyle={tooltipStyle} formatter={(v) => (Array.isArray(v) ? v.map((x) => fmt(Number(x), 0, lang)).join(" – ") : fmt(Number(v), 0, lang))} />}
        {!compact && <Legend verticalAlign="top" height={30} wrapperStyle={{ color: "var(--muted)", fontSize: 12 }} />}
      </ComposedChart>
    </Figure>
  );
}

export function RoiByOddsChart({ rows }: { rows: { tranche: string; n: number; "roi_cloture_%": number; roi_cloture_ic95: [number, number]; "roi_b365_%": number }[] }) {
  const { lang } = useI18n();
  const data = rows.map((r) => ({ tranche: r.tranche, roi: r["roi_cloture_%"], err: [r["roi_cloture_%"] - r.roi_cloture_ic95[0], r.roi_cloture_ic95[1] - r["roi_cloture_%"]], b365: r["roi_b365_%"], n: r.n }));
  const summary = (lang === "fr" ? "ROI d'un pari à mise fixe à la clôture par tranche de cote : " : "Flat-stake ROI at closing odds by odds band: ")
    + data.map((d) => `${d.tranche} ${fmt(d.roi, 1, lang)} %`).join(", ") + ".";
  return (
    <Figure summary={summary} height={320}>
      <BarChart data={data} margin={{ top: 8, right: 8, bottom: 16, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" vertical={false} />
        <XAxis dataKey="tranche" {...axis} label={{ value: lang === "fr" ? "cote de clôture" : "closing odds", position: "insideBottom", offset: -8, fill: "var(--muted)", fontSize: 12 }} />
        <YAxis {...axis} unit=" %" />
        <ReferenceLine y={0} stroke="var(--muted)" />
        <Tooltip contentStyle={tooltipStyle} formatter={(v) => `${fmt(Number(v), 1, lang)} %`} />
        <Bar dataKey="roi" name={lang === "fr" ? "ROI à la clôture (IC95)" : "ROI at close (95% CI)"} fill="var(--series-1)" radius={[4, 4, 0, 0]} isAnimationActive={false}>
          <ErrorBar dataKey="err" stroke="var(--text)" width={6} />
        </Bar>
        <Bar dataKey="b365" name={lang === "fr" ? "ROI chez Bet365" : "ROI at Bet365"} fill="var(--series-3)" radius={[4, 4, 0, 0]} isAnimationActive={false} />
        <Legend verticalAlign="top" height={30} wrapperStyle={{ color: "var(--muted)", fontSize: 12 }} />
      </BarChart>
    </Figure>
  );
}

export function ShapBars({ values }: { values: Record<string, number> }) {
  const { lang } = useI18n();
  const data = Object.entries(values).slice(0, 12).map(([k, v]) => ({ k, v }));
  const summary = (lang === "fr" ? "Importance moyenne absolue SHAP, variables principales : " : "Mean absolute SHAP importance, top features: ")
    + data.slice(0, 5).map((d) => d.k).join(", ") + ".";
  return (
    <Figure summary={summary} height={360}>
      <BarChart data={data} layout="vertical" margin={{ top: 4, right: 16, bottom: 4, left: 24 }}>
        <CartesianGrid strokeDasharray="3 3" horizontal={false} />
        <XAxis type="number" {...axis} />
        <YAxis type="category" dataKey="k" width={130} {...axis} />
        <Tooltip contentStyle={tooltipStyle} formatter={(v) => fmt(Number(v), 4, lang)} />
        <Bar dataKey="v" fill="var(--series-1)" radius={[0, 4, 4, 0]} isAnimationActive={false} name="|SHAP|" />
      </BarChart>
    </Figure>
  );
}

export function MarginChart({ series }: { series: Record<string, { "marge_%": number; "roi_flat_%": number | null }[]> }) {
  const { lang } = useI18n();
  const names = Object.keys(series);
  const xs = series[names[0]].map((r) => r["marge_%"]);
  const data = xs.map((m, i) => ({ m, ...Object.fromEntries(names.map((n) => [n, series[n][i]["roi_flat_%"]])) }));
  const at0 = names.map((n) => `${n} ${fmt(series[n][0]["roi_flat_%"], 1, lang)} %`).join(", ");
  const summary = lang === "fr" ? `ROI à mise fixe selon la marge du bookmaker (0 à 10 %). À marge nulle : ${at0}.` : `Flat-stake ROI vs bookmaker margin (0 to 10%). At zero margin: ${at0}.`;
  return (
    <Figure summary={summary}>
      <LineChart data={data} margin={{ top: 8, right: 8, bottom: 16, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="m" {...axis} unit=" %" label={{ value: lang === "fr" ? "marge du bookmaker" : "bookmaker margin", position: "insideBottom", offset: -8, fill: "var(--muted)", fontSize: 12 }} />
        <YAxis {...axis} unit=" %" />
        <ReferenceLine y={0} stroke="var(--muted)" />
        <Tooltip contentStyle={tooltipStyle} formatter={(v) => `${fmt(Number(v), 1, lang)} %`} />
        {names.map((n, k) => <Line key={n} dataKey={n} stroke={S[k % S.length]} strokeWidth={2} dot={false} isAnimationActive={false} />)}
        <Legend verticalAlign="top" height={30} wrapperStyle={{ color: "var(--muted)", fontSize: 12 }} />
      </LineChart>
    </Figure>
  );
}

export function EffectForest({ rows }: { rows: { label: string; mean: number; lo: number; hi: number }[] }) {
  const { lang } = useI18n();
  const data = rows.map((r) => ({ ...r, err: [r.mean - r.lo, r.hi - r.mean] }));
  const summary = (lang === "fr" ? "Résidus moyens et IC95 : " : "Mean residuals and 95% CI: ")
    + rows.map((r) => `${r.label} ${fmt(r.mean, 2, lang)} [${fmt(r.lo, 2, lang)} ; ${fmt(r.hi, 2, lang)}]`).join(" ; ");
  return (
    <Figure summary={summary} height={Math.max(220, rows.length * 44)}>
      <ComposedChart data={data} layout="vertical" margin={{ top: 4, right: 16, bottom: 4, left: 24 }}>
        <CartesianGrid strokeDasharray="3 3" horizontal={false} />
        <XAxis type="number" {...axis} domain={["auto", "auto"]} />
        <YAxis type="category" dataKey="label" width={150} {...axis} tick={{ fill: "var(--muted)", fontSize: 11 }} />
        <ReferenceLine x={0} stroke="var(--muted)" />
        <Tooltip contentStyle={tooltipStyle} formatter={(v) => (Array.isArray(v) ? "" : fmt(Number(v), 2, lang))} />
        <Scatter dataKey="mean" fill="var(--series-1)" isAnimationActive={false} name={lang === "fr" ? "résidu (pts)" : "residual (pts)"}>
          <ErrorBar dataKey="err" direction="x" stroke="var(--text)" width={6} />
        </Scatter>
      </ComposedChart>
    </Figure>
  );
}

export function PitchOutcomes({ home, draw, away, lang }: { home: number; draw: number; away: number; lang: Lang }) {
  // Terrain SVG : l'aire de chaque zone est proportionnelle à la part de l'issue (données réelles).
  const W = 300, H = 190, x1 = W * home, x2 = W * (home + draw);
  const label = lang === "fr"
    ? `Issues des matchs depuis 2019 : victoire à domicile ${Math.round(home * 100)} %, nul ${Math.round(draw * 100)} %, victoire à l'extérieur ${Math.round(away * 100)} %.`
    : `Match outcomes since 2019: home win ${Math.round(home * 100)}%, draw ${Math.round(draw * 100)}%, away win ${Math.round(away * 100)}%.`;
  return (
    <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={label} className="h-full w-full">
      <rect x="0" y="0" width={x1} height={H} fill="var(--series-1)" opacity="0.35" />
      <rect x={x1} y="0" width={x2 - x1} height={H} fill="var(--draw)" opacity="0.25" />
      <rect x={x2} y="0" width={W - x2} height={H} fill="var(--series-3)" opacity="0.35" />
      <g fill="none" stroke="var(--text)" strokeOpacity="0.55" strokeWidth="1.2">
        <rect x="4" y="4" width={W - 8} height={H - 8} rx="2" />
        <line x1={W / 2} y1="4" x2={W / 2} y2={H - 4} />
        <circle cx={W / 2} cy={H / 2} r="24" />
        <rect x="4" y={H / 2 - 42} width="40" height="84" />
        <rect x={W - 44} y={H / 2 - 42} width="40" height="84" />
      </g>
      {[[x1 / 2, home, lang === "fr" ? "DOM" : "HOME"], [(x1 + x2) / 2, draw, lang === "fr" ? "NUL" : "DRAW"], [(x2 + W) / 2, away, lang === "fr" ? "EXT" : "AWAY"]].map(([x, v, l]) => (
        <g key={String(l)}>
          <text x={Number(x)} y={H / 2 - 4} textAnchor="middle" fill="var(--text)" fontSize="22" fontWeight="800" className="tabular">{Math.round(Number(v) * 100)}%</text>
          <text x={Number(x)} y={H / 2 + 16} textAnchor="middle" fill="var(--text)" fontSize="10" letterSpacing="1">{String(l)}</text>
        </g>
      ))}
    </svg>
  );
}
