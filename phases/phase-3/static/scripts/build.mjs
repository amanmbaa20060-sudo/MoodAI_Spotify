import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const staticRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const out = path.join(staticRoot, "dist");
const apiUrl = process.env.MOODAI_API_URL || "";

fs.rmSync(out, { recursive: true, force: true });
fs.mkdirSync(path.join(out, "assets"), { recursive: true });
fs.copyFileSync(path.join(staticRoot, "index.html"), path.join(out, "index.html"));
fs.copyFileSync(path.join(staticRoot, "app.js"), path.join(out, "assets", "app.js"));
fs.writeFileSync(
  path.join(out, "config.js"),
  `window.__MOODAI_CONFIG__ = { apiBaseUrl: ${JSON.stringify(apiUrl)} };\n`
);

console.log(`MoodAI static build complete (API=${apiUrl || "same-origin"})`);
