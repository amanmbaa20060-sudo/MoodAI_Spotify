import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const src = path.join(root, "phases", "phase-3", "static");
const out = path.join(root, "dist");
const apiUrl = process.env.MOODAI_API_URL || "";

fs.rmSync(out, { recursive: true, force: true });
fs.mkdirSync(path.join(out, "assets"), { recursive: true });
fs.copyFileSync(path.join(src, "index.html"), path.join(out, "index.html"));
fs.copyFileSync(path.join(src, "app.js"), path.join(out, "assets", "app.js"));
fs.writeFileSync(
  path.join(out, "config.js"),
  `window.__MOODAI_CONFIG__ = { apiBaseUrl: ${JSON.stringify(apiUrl)} };\n`
);

console.log(`Vercel build complete: dist/ (API=${apiUrl || "same-origin"})`);
