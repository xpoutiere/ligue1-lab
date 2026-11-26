import type { Metadata } from "next";
import { MatchesView } from "@/components/views/pages";
import { getMatches } from "@/lib/data";

export const metadata: Metadata = { title: "Matchs" };

export default function Page() {
  const m = getMatches();
  return <MatchesView upcoming={m.upcoming} recent={m.recent} modelName={m.model_name} />;
}
