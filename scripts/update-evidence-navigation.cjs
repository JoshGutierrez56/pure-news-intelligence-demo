const fs = require("node:fs");
const path = require("node:path");

const directory = path.resolve(__dirname, "..", "demo", "evidence_packets");
for (const file of fs.readdirSync(directory).filter((name) => /^0\d_.+\.html$/.test(name))) {
  const target = path.join(directory, file);
  let html = fs.readFileSync(target, "utf8");
  html = html
    .replace("<header>", '<header class="site-header">')
    .replace(
      /<div class="brand">Pure News Intelligence<small>[\s\S]*?<\/small><\/div>\s*<nav aria-label="Demo navigation">[\s\S]*?<\/nav>/,
      `<a class="brand" href="../../index.html">Pure News Intelligence<small>Evidence packet</small></a>
      <button class="nav-toggle secondary" type="button" aria-expanded="false" aria-controls="packet-nav">Menu</button>
      <nav class="primary-nav" id="packet-nav" aria-label="Primary navigation"><a href="../../index.html">Overview</a><a href="../professor_presentation.html">Professor Presentation</a><a href="../ranked_change_feed.html">Ranked Changes</a><a href="../case_studies.html">Case Studies</a><a href="../company_comparison.html">Comparisons</a><a href="../company_timeline.html">Timelines</a><a href="../research_results.html">Research Results</a><a href="../methodology.html">Methodology</a></nav>`
    )
    .replace('<script src="../assets/app.js"></script>', '<script src="../assets/site.js"></script>');
  fs.writeFileSync(target, html, "utf8");
}
console.log("Updated evidence-packet navigation.");
