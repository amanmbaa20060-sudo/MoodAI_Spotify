import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const appRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const repoRoot = path.resolve(appRoot, "../..");
const src = path.join(repoRoot, "phases", "phase-3", "static");
const out = path.join(appRoot, "dist");
const apiUrl = process.env.MOODAI_API_URL || "";

if (!fs.existsSync(path.join(src, "index.html"))) {
  console.error(`Static source not found: ${src}`);
  process.exit(1);
}

fs.rmSync(out, { recursive: true, force: true });
fs.mkdirSync(path.join(out, "assets"), { recursive: true });
fs.copyFileSync(path.join(src, "index.html"), path.join(out, "index.html"));
fs.copyFileSync(path.join(src, "app.js"), path.join(out, "assets", "app.js"));
fs.writeFileSync(
  path.join(out, "config.js"),
  `window.__MOODAI_CONFIG__ = { apiBaseUrl: ${JSON.stringify(apiUrl)} };\n`
);

console.log(`MoodAI web build complete (API=${apiUrl || "same-origin"})`);
