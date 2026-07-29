# Pure News Intelligence

**Find what changed. Verify the evidence. Decide what to investigate.**

Pure News Intelligence is an evidence-linked disclosure research workflow for institutional analysts. It compares consecutive corporate filings, identifies meaningful changes, traces each change to exact source text, checks earlier context, and preserves a reviewable research record.

The project began by testing whether “pure news” in 10-K filings predicted returns. The locked studies did **not** support the original alpha thesis. That negative result changed the product: instead of claiming a trading signal, the project focused on a more defensible workflow problem—helping analysts prioritize information and resist unsupported narratives.

The core Disclosure Change Engine demonstrates 995 evidence-backed changes across 150 consecutive 10-K pairs, including 629 high-confidence changes and 1,990 verified excerpt offsets.

The secondary Experimental Research Idea Engine was tested on eight frozen cases. Two—RH and DVN—produced publishable, falsifiable research hypotheses with 1.00 evidence coverage. Six failed safely. EFX is the clearest negative fixture: full-prior evidence showed that a supposedly new $125 million term had already been disclosed, $346.7 million was a remaining balance rather than an exposure cap, and approximately $345 million was a cash deposit. Unsupported liquidity, reserve, and bondholder claims were removed. No actionable trade view survived.

**Validated bounded result:** 8 reviewed · 2 publishable hypotheses · 6 safe failures · 0 actionable trade views.

The public site runs no live model inference. It serves frozen public-safe packets, separates facts from inference and uncertainty, shows counterevidence, and leaves analyst disposition in browser-only local controls.

**Not validated:** Sharpe-ratio or information-coefficient improvement, return prediction, causality, analyst adoption, commercial value, or investment performance. Formal blinded human review remains pending, and the 60-case phase is blocked and not run.

**Recommended demo path:** Overview → Ranked Changes → Case Studies → Research Ideas → Research Results → Methodology.

Live demo: https://joshgutierrez56.github.io/pure-news-intelligence-demo/
