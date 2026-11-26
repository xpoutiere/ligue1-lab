import type { Metadata } from "next";
import { ModelsView } from "@/components/views/pages";
import { getModels } from "@/lib/data";

export const metadata: Metadata = { title: "Modèles" };

export default function Page() {
  return <ModelsView d={getModels()} />;
}
