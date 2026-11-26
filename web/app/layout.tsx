import type { Metadata, Viewport } from "next";
import { Inter, Inter_Tight } from "next/font/google";
import { Footer, Navbar, ResponsibleBanner } from "@/components/chrome";
import { getSummary } from "@/lib/data";
import { LangProvider } from "@/lib/i18n";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter", display: "swap" });
const interTight = Inter_Tight({ subsets: ["latin"], weight: ["700", "800"], variable: "--font-inter-tight", display: "swap" });

export const metadata: Metadata = {
  title: { default: "Ligue 1 Lab : le marché des paris est-il battable ?", template: "%s · Ligue 1 Lab" },
  description: "Étude statistique honnête de la Ligue 1 : modèles Elo, Dixon-Coles et machine learning face aux cotes de clôture. Projet éducatif, aucune garantie de gain.",
};

export const viewport: Viewport = {
  themeColor: [{ media: "(prefers-color-scheme: dark)", color: "#0a0a0a" }, { media: "(prefers-color-scheme: light)", color: "#eaf3fb" }],
};

// Thème posé avant le premier rendu (préférence enregistrée, sinon prefers-color-scheme).
const themeScript = `(function(){try{var t=localStorage.getItem('theme');if(!t){t=matchMedia('(prefers-color-scheme: light)').matches?'light':'dark'}document.documentElement.dataset.theme=t}catch(e){document.documentElement.dataset.theme='dark'}})()`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const s = getSummary();
  return (
    <html lang="fr" data-theme="dark" className={`${inter.variable} ${interTight.variable}`} suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body className="min-h-screen">
        <LangProvider>
          <a href="#contenu" className="skip-link">Aller au contenu</a>
          <ResponsibleBanner />
          <Navbar />
          <main id="contenu" className="mx-auto max-w-[1280px] px-4 md:px-8">{children}</main>
          <Footer generatedAt={s.meta.generated_at} version={s.meta.model_version} />
        </LangProvider>
      </body>
    </html>
  );
}
