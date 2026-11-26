"use client";
// Navbar, bandeau jeu responsable, pied de page, interrupteurs thème / langue.
import { Code2 as Github, Languages, Menu, Moon, ShieldAlert, Sun, X } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { useI18n } from "@/lib/i18n";
import { Logo } from "./ui";

export const GITHUB_URL = process.env.NEXT_PUBLIC_GITHUB_URL || "https://github.com/xpoutiere/ligue1-lab";

const LINKS = [
  ["/", "home"], ["/matchs/", "matches"], ["/modeles/", "models"], ["/strategie/", "strategy"],
  ["/biais/", "biases"], ["/equipes/", "teams"], ["/journal/", "journal"],
  ["/ma-calibration/", "quiz"], ["/methodologie/", "method"],
] as const;

export function ThemeToggle() {
  const { t } = useI18n();
  const [theme, setTheme] = useState<"dark" | "light">("dark");
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- synchronisation avec le thème posé avant le rendu
    setTheme((document.documentElement.dataset.theme as "dark" | "light") || "dark");
  }, []);
  const toggle = () => {
    const next = theme === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    try { localStorage.setItem("theme", next); } catch {}
    setTheme(next);
  };
  return (
    <button type="button" onClick={toggle} className="rounded-[8px] border border-border p-2 text-text hover:bg-surface-2"
      aria-label={theme === "dark" ? t.theme.toLight : t.theme.toDark}>
      {theme === "dark" ? <Sun size={18} aria-hidden /> : <Moon size={18} aria-hidden />}
    </button>
  );
}

export function LangToggle() {
  const { lang, setLang, t } = useI18n();
  return (
    <button type="button" onClick={() => setLang(lang === "fr" ? "en" : "fr")}
      className="inline-flex items-center gap-1 rounded-[8px] border border-border px-2 py-2 text-xs font-semibold text-text hover:bg-surface-2"
      aria-label={t.lang} lang={lang === "fr" ? "en" : "fr"}>
      <Languages size={16} aria-hidden /> {lang === "fr" ? "EN" : "FR"}
    </button>
  );
}

export function Navbar() {
  const { t } = useI18n();
  const path = usePathname();
  const [open, setOpen] = useState(false);
  const isActive = (href: string) => (href === "/" ? path === "/" : path?.startsWith(href.replace(/\/$/, "")));
  return (
    <header className="sticky top-0 z-40 border-b border-border bg-[color-mix(in_srgb,var(--bg)_88%,transparent)] backdrop-blur">
      <nav className="mx-auto flex max-w-[1280px] items-center justify-between gap-4 px-4 py-3 md:px-8" aria-label="Navigation principale">
        <Link href="/" className="shrink-0" aria-label="Ligue 1 Lab, accueil"><Logo /></Link>
        <ul className="hidden items-center gap-5 xl:flex">
          {LINKS.map(([href, key]) => (
            <li key={href}>
              <Link href={href} aria-current={isActive(href) ? "page" : undefined}
                className={`smallcaps hover:text-text ${isActive(href) ? "text-accent-text" : "text-muted"}`}>
                {t.nav[key]}
              </Link>
            </li>
          ))}
        </ul>
        <div className="flex items-center gap-2">
          <LangToggle />
          <ThemeToggle />
          <a href={GITHUB_URL} target="_blank" rel="noopener noreferrer"
            className="hidden items-center gap-2 rounded-[8px] bg-accent px-3 py-2 text-sm font-bold text-on-accent sm:inline-flex">
            <Github size={16} aria-hidden /> {t.github}
          </a>
          <button type="button" className="rounded-[8px] border border-border p-2 xl:hidden" onClick={() => setOpen(!open)}
            aria-expanded={open} aria-controls="mobile-menu" aria-label={open ? t.close : t.menu}>
            {open ? <X size={18} aria-hidden /> : <Menu size={18} aria-hidden />}
          </button>
        </div>
      </nav>
      {open && (
        <ul id="mobile-menu" className="border-t border-border px-4 pb-4 xl:hidden">
          {LINKS.map(([href, key]) => (
            <li key={href}>
              <Link href={href} onClick={() => setOpen(false)} aria-current={isActive(href) ? "page" : undefined}
                className={`block py-3 font-display text-lg font-bold ${isActive(href) ? "text-accent-text" : "text-text"}`}>
                {t.nav[key]}
              </Link>
            </li>
          ))}
          <li>
            <a href={GITHUB_URL} target="_blank" rel="noopener noreferrer" className="mt-2 inline-flex items-center gap-2 rounded-[8px] bg-accent px-3 py-2 text-sm font-bold text-on-accent">
              <Github size={16} aria-hidden /> {t.github}
            </a>
          </li>
        </ul>
      )}
    </header>
  );
}

export function ResponsibleBanner() {
  const { t } = useI18n();
  return (
    <div role="note" className="border-b border-border bg-surface px-4 py-2 text-center text-xs text-muted md:text-sm">
      <ShieldAlert size={14} className="mr-1 inline align-[-2px] text-warn" aria-hidden />
      {t.banner}
    </div>
  );
}

export function Footer({ generatedAt, version }: { generatedAt: string; version: string }) {
  const { t, lang } = useI18n();
  const d = new Date(generatedAt).toLocaleString(lang === "fr" ? "fr-FR" : "en-GB", { dateStyle: "long", timeStyle: "short" });
  return (
    <footer className="mt-24 border-t border-border">
      <div className="mx-auto grid max-w-[1280px] gap-6 px-4 py-10 text-sm text-muted md:grid-cols-[1fr_2fr] md:px-8">
        <div>
          <Logo />
          <p className="mt-3">{t.footer.built} {d} · {t.footer.version} <span className="tabular">{version}</span></p>
        </div>
        <div className="space-y-2">
          <p>{t.footer.noAdvice}</p>
          <p>{t.banner}</p>
          <p>{t.footer.rights}</p>
        </div>
      </div>
    </footer>
  );
}
