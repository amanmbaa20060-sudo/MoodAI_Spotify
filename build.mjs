/**
 * Vercel build — writes MOODAI_API_URL into public/config.js.
 * Copies latest UI from phases/phase-3/static when that folder is present.
 */
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const root = path.dirname(fileURLToPath(import.meta.url));
const src = path.join(root, "phases", "phase-3", "static");
const out = path.join(root, "public");
const apiUrl = (process.env.MOODAI_API_URL || "").replace(/\/$/, "");

fs.mkdirSync(path.join(out, "assets"), { recursive: true });

const indexSrc = path.join(src, "index.html");
const appSrc = path.join(src, "app.js");
const indexOut = path.join(out, "index.html");
const appOut = path.join(out, "assets", "app.js");

if (fs.existsSync(indexSrc) && fs.existsSync(appSrc)) {
  fs.copyFileSync(indexSrc, indexOut);
  fs.copyFileSync(appSrc, appOut);
} else if (!fs.existsSync(indexOut) || !fs.existsSync(appOut)) {
  console.error("Missing UI files in phases/phase-3/static and public/");
  process.exit(1);
}

fs.writeFileSync(
  path.join(out, "config.js"),
  `window.__MOODAI_CONFIG__ = { apiBaseUrl: ${JSON.stringify(apiUrl)} };\n`
);

console.log(`Vercel build OK → public/ (API=${apiUrl || "NOT SET — add MOODAI_API_URL"})`);
