import type { Metadata } from "next";
import { DesignView } from "@/components/views/design";
import { getMarket, getMatches } from "@/lib/data";

export const metadata: Metadata = { title: "Design", robots: { index: false } };

export default function Page() {
  return <DesignView match={getMatches().recent[0]} calib={getMarket().calibration} />;
}
