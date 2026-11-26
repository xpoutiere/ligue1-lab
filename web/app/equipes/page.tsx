import type { Metadata } from "next";
import { TeamsView } from "@/components/views/pages";
import { getTeams } from "@/lib/data";

export const metadata: Metadata = { title: "Équipes" };

export default function Page() {
  const t = getTeams();
  return <TeamsView teams={t.teams} season={t.season} home={t.home_advantage} />;
}
