"use client";
// Page interne /design : la bibliothèque de composants, sur des données réelles.
import { BarChart3, Percent, Target } from "lucide-react";
import { CalibrationChart } from "@/components/charts";
import { MatchCard } from "@/components/match-card";
import { Card, Chip, EmptyState, FormBadges, Logo, PageHeader, Pill, SectionTitle, Skeleton, StatTile, TeamMonogram } from "@/components/ui";
import type { MatchItem } from "@/lib/data";
import { useI18n } from "@/lib/i18n";

const TOKENS = ["--bg", "--surface", "--surface-2", "--border", "--text", "--muted", "--accent", "--info", "--warn", "--win", "--draw", "--loss"];

export function DesignView({ match, calib }: { match: MatchItem; calib: { predite: number[]; observee: number[]; n: number[] } }) {
  const { t } = useI18n();
  return (
    <>
      <PageHeader title={t.design.title} lead="Tokens, typographie et composants (page interne, non liée dans la navigation)." />
      <SectionTitle>Tokens</SectionTitle>
      <div className="mb-10 grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-6">
        {TOKENS.map((v) => (
          <div key={v} className="card p-3 text-xs">
            <div className="mb-2 h-10 rounded-[8px] border border-border" style={{ background: `var(${v})` }} />
            <code>{v}</code>
          </div>
        ))}
      </div>
      <SectionTitle>Typographie</SectionTitle>
      <div className="mb-10 space-y-2">
        <p className="font-display text-6xl font-extrabold">Titre <span className="text-accent-text">accent</span></p>
        <p className="font-display text-3xl font-bold">Titre de section</p>
        <p>Corps de texte Inter. <span className="tabular">0,9658 · 1,0037 · 54,4 %</span> (chiffres tabulaires)</p>
        <p className="smallcaps text-muted">Petites capitales</p>
      </div>
      <SectionTitle>Éléments</SectionTitle>
      <div className="mb-10 flex flex-wrap items-center gap-4">
        <Logo /><Pill icon={<BarChart3 size={18} />}>Statistiques</Pill><Chip>Ligue 1</Chip>
        <TeamMonogram code="PSG" /><FormBadges form={["V", "N", "D", "V", "V"]} />
        <button className="rounded-[8px] bg-accent px-4 py-2 font-bold text-on-accent">Bouton principal</button>
        <button className="rounded-[8px] border border-border px-4 py-2 font-semibold">Bouton secondaire</button>
      </div>
      <div className="mb-10 grid gap-3 md:grid-cols-3">
        <StatTile icon={<Target size={20} />} value="0,966" label="StatTile" sub="IC95 [0,932 ; 1,000]" />
        <StatTile icon={<Percent size={20} />} value="2,77 %" label="Marge" />
        <Skeleton className="h-24" />
      </div>
      <div className="mb-10 grid gap-4 lg:grid-cols-2">
        <MatchCard m={match} modelName="Dixon-Coles" />
        <Card title="Graphique"><CalibrationChart series={{ Marché: calib }} /></Card>
      </div>
      <EmptyState title="État vide">Message explicatif quand il n&apos;y a rien à afficher.</EmptyState>
    </>
  );
}
