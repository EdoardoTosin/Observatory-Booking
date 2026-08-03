/**
 * Copy Leaflet's dist assets (JS/CSS/marker images) from node_modules into
 * app/static/vendor/leaflet/, so the app can self-host the map picker's
 * library instead of loading it from a CDN. Run automatically as part of
 * `npm run build`.
 */
const fs = require("fs");
const path = require("path");

const SRC_DIR = path.join(__dirname, "..", "node_modules", "leaflet", "dist");
const DEST_DIR = path.join(__dirname, "..", "app", "static", "vendor", "leaflet");

fs.mkdirSync(path.join(DEST_DIR, "images"), { recursive: true });

fs.copyFileSync(path.join(SRC_DIR, "leaflet.js"), path.join(DEST_DIR, "leaflet.js"));
fs.copyFileSync(path.join(SRC_DIR, "leaflet.css"), path.join(DEST_DIR, "leaflet.css"));

for (const file of fs.readdirSync(path.join(SRC_DIR, "images"))) {
  fs.copyFileSync(
    path.join(SRC_DIR, "images", file),
    path.join(DEST_DIR, "images", file)
  );
}

console.log("Vendored Leaflet assets into app/static/vendor/leaflet/");
