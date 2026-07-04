/**
 * Vercel static build — copies UI from phases/phase-3/static into dist/.
 * Set MOODAI_API_URL on Vercel to your Render API URL (no trailing slash).
 */
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const src = path.join(repoRoot, "phases", "phase-3", "static");
const out = path.join(repoRoot, "dist");
const apiUrl = (process.env.MOODAI_API_URL || "").replace(/\/$/, "");

const indexPath = path.join(src, "index.html");
if (!fs.existsSync(indexPath)) {
  console.error(`Static UI not found at ${src}`);
  process.exit(1);
}

fs.rmSync(out, { recursive: true, force: true });
fs.mkdirSync(path.join(out, "assets"), { recursive: true });
fs.copyFileSync(indexPath, path.join(out, "index.html"));
fs.copyFileSync(path.join(src, "app.js"), path.join(out, "assets", "app.js"));
fs.writeFileSync(
  path.join(out, "config.js"),
  `window.__MOODAI_CONFIG__ = { apiBaseUrl: ${JSON.stringify(apiUrl)} };\n`
);

console.log(`MoodAI Vercel build OK → dist/ (API=${apiUrl || "NOT SET — add MOODAI_API_URL"})`);
