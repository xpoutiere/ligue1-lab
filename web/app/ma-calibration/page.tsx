import type { Metadata } from "next";
import { QuizView } from "@/components/views/quiz";
import { getQuiz } from "@/lib/data";

export const metadata: Metadata = { title: "Ma calibration" };

export default function Page() {
  return <QuizView matches={getQuiz().matches} />;
}
