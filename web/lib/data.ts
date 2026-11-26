// Lecture et validation (zod) des artefacts produits par `python make_artifacts.py`.
// Exécuté au build (export statique) : si un artefact ne respecte pas le schéma, le build échoue.
import "server-only";
import { readFileSync } from "node:fs";
import path from "node:path";
import { z } from "zod";

const num = z.number().nullable();
const triple = z.tuple([num, num, num]);

const Meta = z.object({
  generated_at: z.string(),
  model_version: z.string(),
  data_period: z.tuple([z.string(), z.string()]),
  test_period: z.tuple([z.string(), z.string()]),
  source: z.string(),
});
export type Meta = z.infer<typeof Meta>;

const Team = z.object({ name: z.string(), code: z.string(), stadium: z.string().nullable() });

const Summary = z.object({
  meta: Meta,
  n_matches: z.number(),
  n_test: z.number(),
  market_log_loss: z.number(),
  market_ll_ci: z.tuple([z.number(), z.number()]),
  best_model: z.string(),
  best_model_delta: z.number(),
  best_model_delta_ci: z.tuple([z.number(), z.number()]),
  lgbm_log_loss: z.number(),
  lgbm_delta: z.number(),
  lgbm_delta_ci: z.tuple([z.number(), z.number()]),
  pinnacle_margin_pct: z.number(),
  b365_margin_pct: z.number(),
  clv_pct: z.record(z.string(), num),
  n_bias_tests: z.number(),
  n_bias_significant: z.number(),
  accuracy_market_pct: z.number(),
  outcome_shares: z.tuple([z.number(), z.number(), z.number()]),
});

const Metric = z.object({
  "modèle": z.string(),
  log_loss: z.number(),
  ll_ic95_bas: z.number(),
  ll_ic95_haut: z.number(),
  "delta_vs_marché": z.number(),
  delta_ic95_bas: z.number(),
  delta_ic95_haut: z.number(),
  brier: z.number(),
  "accuracy_%": z.number(),
  "p_mieux_que_marché": num.optional(),
  p_holm: num.optional(),
});
export type Metric = z.infer<typeof Metric>;

const Calib = z.object({ predite: z.array(z.number()), observee: z.array(z.number()), n: z.array(z.number()) });

const Models = z.object({
  meta: Meta,
  protocol: z.object({
    burn_in: z.array(z.string()),
    train: z.array(z.string()),
    valid: z.array(z.string()),
    test: z.array(z.string()),
    n_train: z.number(),
    n_valid: z.number(),
    n_test: z.number(),
    n_test_pinnacle: z.number(),
    test_period: z.tuple([z.string(), z.string()]),
  }),
  choices: z.object({
    logit_C: z.number(),
    calibration: z.string(),
    calibration_scores: z.record(z.string(), z.number()),
    pool_weights: z.record(z.string(), z.number()),
    lgbm: z.object({ params: z.record(z.string(), z.number()), n_estimators: z.number(), cv_log_loss: z.number() }),
  }).passthrough(),
  metrics: z.array(Metric),
  metrics_pinnacle_only: z.array(Metric),
  encompassing: z.record(z.string(), z.object({
    a_marche: z.number(), b_modele: z.number(), b_ic95: z.tuple([z.number(), z.number()]),
    lr_stat: z.number(), p_value: z.number(),
  })),
  calibration: z.record(z.string(), Calib),
  shap_top: z.record(z.string(), z.number()),
  cumulative_gap: z.object({ dates: z.array(z.string()), series: z.record(z.string(), z.array(z.number())) }),
});
export type Models = z.infer<typeof Models>;

const Band = z.object({ i: z.array(z.number()), q05: z.array(z.number()), q25: z.array(z.number()),
  q50: z.array(z.number()), q75: z.array(z.number()), q95: z.array(z.number()) });
const MC = z.object({
  n_paths: z.number(), "p_ruine_%": z.number(), "p_perte_%": z.number(),
  bankroll_finale_q: z.record(z.string(), z.number()),
  "drawdown_max_q_%": z.record(z.string(), z.number()), bands: Band,
}).nullable();
const StratModel = z.object({
  edge: z.number(),
  validation: z.array(z.object({ edge: z.number(), paris: z.number().nullable(), "roi_flat_%": num, "clv_moy_%": num })),
  test: z.object({
    paris: z.number(), "roi_flat_%": z.number().optional(), "roi_ic95_%": z.tuple([z.number(), z.number()]).optional(),
    "clv_moy_%": z.number().optional(), "clv_ic95_%": z.tuple([z.number(), z.number()]).optional(),
    "part_clv_positive_%": z.number().optional(), bankroll_finale: z.number().optional(),
    "drawdown_max_%": z.number().optional(), cote_moy: z.number().optional(),
  }),
  mc: MC, mc_null: MC,
  margin: z.array(z.object({ "marge_%": z.number(), paris: z.number(), "roi_flat_%": num, "roi_ic95_%": z.tuple([num, num]).nullable().optional() })),
  bankroll: z.object({ Date: z.array(z.string()), bankroll: z.array(z.number()) }).partial(),
});
const Strategy = z.object({
  meta: Meta,
  config: z.object({ kelly_frac: z.number(), cap: z.number(), ruin_level: z.number(), exec: z.string(), closing: z.string() }).passthrough(),
  models: z.record(z.string(), StratModel),
  "market_margin_b365_%": z.number(),
  "clv_random_bet_b365_%": z.number(),
});
export type Strategy = z.infer<typeof Strategy>;

const Boot = z.object({ n: z.number(), moyenne: z.number(), ic95: z.tuple([z.number(), z.number()]), p: z.number() });
const Biases = z.object({
  meta: Meta,
  n_matchs: z.number(),
  periode: z.tuple([z.string(), z.string()]),
  tests: z.array(z.object({
    label: z.string(), hypothese: z.string(), sens_attendu: z.number(),
    resid_pts: Boot, "roi_cloture_%": Boot, "roi_b365_%": Boot,
    p_implicite_moy: z.number(), frequence: z.number(), p_holm: z.number(), p_bh: z.number(),
    verdict: z.string(), exploitable: z.string(),
  })),
  par_tranche_de_cote: z.array(z.object({
    tranche: z.string(), n: z.number(), p_implicite: z.number(), frequence: z.number(),
    "roi_cloture_%": z.number(), roi_cloture_ic95: z.tuple([z.number(), z.number()]),
    "roi_b365_%": z.number(), roi_b365_ic95: z.tuple([z.number(), z.number()]),
  })),
  groupes: z.object({ populaires: z.array(z.string()), mediatises: z.array(z.string()) }),
});
export type Biases = z.infer<typeof Biases>;

const Market = z.object({
  meta: Meta,
  per_season: z.array(z.object({ Season: z.string(), matchs: z.number(), source: z.string(), log_loss: z.number(), brier: z.number(), "marge_moy_%": z.number() })),
  margins: z.array(z.record(z.string(), z.union([z.string(), z.number(), z.null()]))),
  calibration: Calib,
  n_matches: z.number(),
  sources: z.record(z.string(), z.number()),
});
export type Market = z.infer<typeof Market>;

const TeamRow = Team.extend({
  elo: z.number(), attack: z.number(), defense: z.number(), form: z.array(z.string()),
  j: z.number(), pts: z.number(), bp: z.number(), bc: z.number(), rank: z.number(),
});
const Teams = z.object({ meta: Meta, season: z.string(), teams: z.array(TeamRow), home_advantage: z.number(), rho: z.number() });
export type TeamRow = z.infer<typeof TeamRow>;

const Side = Team.extend({ form: z.array(z.string()) });
const MatchItem = z.object({
  date: z.string(), time: z.string().nullable(), home: Side, away: Side,
  model: triple, market: triple, odds: triple, market_source: z.string().nullable(),
  result: z.string().optional(), score: z.tuple([z.number(), z.number()]).optional(),
});
export type MatchItem = z.infer<typeof MatchItem>;
const Matches = z.object({ meta: Meta, model_name: z.string(), upcoming: z.array(MatchItem), recent: z.array(MatchItem) });

const Paper = z.object({ meta: Meta, entries: z.array(z.record(z.string(), z.union([z.string(), z.number(), z.null()]))) });
const Quiz = z.object({
  meta: Meta,
  matches: z.array(z.object({ id: z.number(), date: z.string(), home: Team, away: Team, model: triple, market: triple, result: z.string() })),
});
export type QuizMatch = z.infer<typeof Quiz>["matches"][number];

function load<T>(name: string, schema: z.ZodType<T>): T {
  const file = path.join(process.cwd(), "public", "data", `${name}.json`);
  const raw = JSON.parse(readFileSync(file, "utf-8"));
  const parsed = schema.safeParse(raw);
  if (!parsed.success) {
    throw new Error(`Artefact ${name}.json invalide : ${parsed.error.message}`);
  }
  return parsed.data;
}

export const getSummary = () => load("summary", Summary);
export const getModels = () => load("models", Models);
export const getStrategy = () => load("strategy", Strategy);
export const getBiases = () => load("biases", Biases);
export const getMarket = () => load("market", Market);
export const getTeams = () => load("teams", Teams);
export const getMatches = () => load("matches", Matches);
export const getPaper = () => load("paper_trading", Paper);
export const getQuiz = () => load("quiz", Quiz);
