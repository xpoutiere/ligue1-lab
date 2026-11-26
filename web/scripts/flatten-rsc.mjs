// Export statique Next 16 : le client précharge `route/__next.route.__PAGE__.txt`,
// mais l'export écrit `route/__next.route/__PAGE__.txt`. On copie le fichier au nom attendu
// pour éviter des 404 de préchargement sur un hébergeur statique (GitHub Pages).
import { copyFileSync, readdirSync, statSync } from "node:fs";
import path from "node:path";

function walk(dir) {
  for (const name of readdirSync(dir)) {
    const p = path.join(dir, name);
    if (!statSync(p).isDirectory()) continue;
    if (name.startsWith("__next.")) {
      for (const f of readdirSync(p)) {
        const src = path.join(p, f);
        if (statSync(src).isFile()) copyFileSync(src, path.join(dir, `${name}.${f}`));
      }
    }
    walk(p);
  }
}
walk("out");
