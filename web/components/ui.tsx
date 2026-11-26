"use client";
// Petits composants réutilisables (documentés sur /design).
import { motion, useInView, useReducedMotion } from "motion/react";
import { useEffect, useRef, useState, type ReactNode } from "react";

export function Logo({ compact = false }: { compact?: boolean }) {
  return (
    <span className="flex items-center gap-2 font-display font-extrabold">
      <span className="rounded-[6px] bg-accent px-1.5 py-0.5 text-sm text-on-accent">L1</span>
      {!compact && <span className="text-lg uppercase tracking-tight text-text">Lab</span>}
    </span>
  );
}

export function Pill({ icon, children }: { icon?: ReactNode; children: ReactNode }) {
  return (
    <span className="inline-flex items-center gap-2 rounded-full bg-surface-2 px-4 py-2 font-display text-sm font-bold uppercase text-text md:text-base">
      {icon && <span className="text-accent-text" aria-hidden>{icon}</span>}
      {children}
    </span>
  );
}

export function Chip({ children }: { children: ReactNode }) {
  return (
    <span className="inline-flex items-center rounded-full border border-border bg-surface-2 px-2.5 py-0.5 text-xs font-semibold text-muted">
      {children}
    </span>
  );
}

export function SectionTitle({ children, sub, id }: { children: ReactNode; sub?: ReactNode; id?: string }) {
  return (
    <div className="mb-6">
      <h2 id={id} className="font-display text-3xl font-extrabold text-accent-text md:text-4xl">{children}</h2>
      {sub && <p className="mt-2 max-w-3xl text-muted">{sub}</p>}
    </div>
  );
}

export function PageHeader({ title, lead }: { title: string; lead?: string }) {
  return (
    <header className="mb-10 pt-6">
      <h1 className="font-display text-4xl font-extrabold leading-[1.02] md:text-6xl">{title}</h1>
      {lead && <p className="mt-4 max-w-3xl text-lg text-muted">{lead}</p>}
    </header>
  );
}

export function CountUp({ value, format }: { value: number; format: (v: number) => string }) {
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true });
  const reduce = useReducedMotion();
  const [v, setV] = useState(value);
  useEffect(() => {
    if (!inView || reduce) return;
    let raf = 0;
    const t0 = performance.now();
    const step = (t: number) => {
      const k = Math.min(1, (t - t0) / 900);
      setV(value * (1 - Math.pow(1 - k, 3)));
      if (k < 1) raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [inView, reduce, value]);
  return <span ref={ref} className="tabular">{format(inView && !reduce ? v : value)}</span>;
}

export function StatTile({ icon, value, label, sub }: { icon: ReactNode; value: ReactNode; label: string; sub?: ReactNode }) {
  return (
    <div className="card flex items-start gap-3 p-5">
      <span className="mt-1 text-accent-text" aria-hidden>{icon}</span>
      <div>
        <div className="font-display text-3xl font-extrabold tabular">{value}</div>
        <div className="text-sm text-muted">{label}</div>
        {sub && <div className="mt-1 text-xs text-muted tabular">{sub}</div>}
      </div>
    </div>
  );
}

export function Reveal({ children, delay = 0, className = "" }: { children: ReactNode; delay?: number; className?: string }) {
  const reduce = useReducedMotion();
  if (reduce) return <div className={className}>{children}</div>;
  return (
    <motion.div className={className} initial={{ opacity: 0, y: 16 }} whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-40px" }} transition={{ duration: 0.45, delay, ease: "easeOut" }}>
      {children}
    </motion.div>
  );
}

export function TeamMonogram({ code, size = 44 }: { code: string; size?: number }) {
  return (
    <span aria-hidden className="inline-flex shrink-0 items-center justify-center rounded-full border border-border bg-surface-2 font-display font-extrabold text-text"
      style={{ width: size, height: size, fontSize: size * (code.length > 3 ? 0.26 : 0.32) }}>
      {code}
    </span>
  );
}

const FORM_STYLE: Record<string, string> = {
  V: "bg-[var(--win-bg)] text-win", N: "bg-[var(--draw-bg)] text-draw", D: "bg-[var(--loss-bg)] text-loss",
  W: "bg-[var(--win-bg)] text-win", L: "bg-[var(--loss-bg)] text-loss",
};

export function FormBadges({ form, lang = "fr", label }: { form: string[]; lang?: "fr" | "en"; label?: string }) {
  const map = lang === "en" ? { V: "W", N: "D", D: "L" } as Record<string, string> : {};
  return (
    <span className="inline-flex gap-1" aria-label={label ? `${label} : ${form.map((f) => map[f] ?? f).join(" ")}` : undefined}>
      {form.map((f, i) => (
        <span key={i} className={`inline-flex h-5 w-5 items-center justify-center rounded text-[11px] font-bold ${FORM_STYLE[f] ?? ""}`}>
          {map[f] ?? f}
        </span>
      ))}
    </span>
  );
}

export function EmptyState({ title, children }: { title?: string; children: ReactNode }) {
  return (
    <div className="card border-dashed p-8 text-center">
      {title && <p className="font-display text-xl font-bold">{title}</p>}
      <p className="mx-auto mt-2 max-w-xl text-muted">{children}</p>
    </div>
  );
}

export function Skeleton({ className = "h-40" }: { className?: string }) {
  return <div className={`animate-pulse rounded-[14px] bg-surface-2 ${className}`} aria-hidden />;
}

export function Card({ children, className = "", title, desc }: { children: ReactNode; className?: string; title?: string; desc?: ReactNode }) {
  return (
    <section className={`card p-5 md:p-6 ${className}`}>
      {title && <h3 className="font-display text-xl font-bold">{title}</h3>}
      {desc && <p className="mt-1 text-sm text-muted">{desc}</p>}
      <div className={title || desc ? "mt-4" : ""}>{children}</div>
    </section>
  );
}
