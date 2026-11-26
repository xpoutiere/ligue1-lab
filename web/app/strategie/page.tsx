import type { Metadata } from "next";
import { StrategyView } from "@/components/views/pages";
import { getStrategy } from "@/lib/data";

export const metadata: Metadata = { title: "Stratégie et risque" };

export default function Page() {
  return <StrategyView d={getStrategy()} />;
}
