import { HomeView } from "@/components/views/home";
import { getMarket, getMatches, getModels, getStrategy, getSummary } from "@/lib/data";

export default function Home() {
  const s = getSummary();
  const market = getMarket();
  const models = getModels();
  const strat = getStrategy();
  const matches = getMatches();
  return (
    <HomeView
      summary={{ ...s, test_period: s.meta.test_period }}
      calib={market.calibration}
      bands={strat.models["Dixon-Coles"]?.mc?.bands ?? null}
      gap={models.cumulative_gap}
      recent={matches.upcoming.length ? matches.upcoming : matches.recent}
      modelName={matches.model_name}
    />
  );
}
