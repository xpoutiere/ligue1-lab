import Link from "next/link";

export default function NotFound() {
  return (
    <div className="py-24 text-center">
      <p className="font-display text-7xl font-extrabold text-accent-text">404</p>
      <p className="mt-4 text-muted">Page introuvable · Page not found</p>
      <Link href="/" className="mt-6 inline-block rounded-[8px] bg-accent px-4 py-2 font-bold text-on-accent">Accueil</Link>
    </div>
  );
}
