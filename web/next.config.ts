import type { NextConfig } from "next";

// Export statique : aucun serveur à maintenir (Vercel, GitHub Pages ou tout hébergeur statique).
// BASE_PATH permet un déploiement sous-dossier (ex. GitHub Pages : /ligue1-lab).
const nextConfig: NextConfig = {
  output: "export",
  trailingSlash: true,
  images: { unoptimized: true },
  basePath: process.env.BASE_PATH || undefined,
  poweredByHeader: false,
};

export default nextConfig;
