const fs = require("node:fs");
const path = require("node:path");

const root = path.resolve(__dirname, "..");
const source = fs.readFileSync(path.join(root, "demo", "ranked_change_feed.html"), "utf8");
const match = source.match(/<script id="curated-change-data" type="application\/json">([\s\S]*?)<\/script>/);
if (!match) throw new Error("Embedded curated change data was not found.");
const records = JSON.parse(match[1]);
if (records.length !== 995) throw new Error(`Expected 995 records; found ${records.length}.`);
fs.writeFileSync(
  path.join(root, "demo", "data", "changes.json"),
  `${JSON.stringify({ schema: "pure-news-ranked-changes.v1", records })}\n`,
  "utf8"
);
console.log(`Extracted ${records.length} frozen records to demo/data/changes.json`);
