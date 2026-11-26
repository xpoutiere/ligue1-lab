import type { Metadata } from "next";
import { BiasesView } from "@/components/views/pages";
import { getBiases } from "@/lib/data";

export const metadata: Metadata = { title: "Biais cognitifs" };

export default function Page() {
  return <BiasesView d={getBiases()} />;
}
