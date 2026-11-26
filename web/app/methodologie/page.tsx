import type { Metadata } from "next";
import { MethodView } from "@/components/views/method";

export const metadata: Metadata = { title: "Méthodologie et limites" };

export default function Page() {
  return <MethodView />;
}
