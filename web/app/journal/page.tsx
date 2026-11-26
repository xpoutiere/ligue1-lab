import type { Metadata } from "next";
import { JournalView } from "@/components/views/pages";
import { getPaper } from "@/lib/data";

export const metadata: Metadata = { title: "Journal de paper trading" };

export default function Page() {
  return <JournalView entries={getPaper().entries} />;
}
