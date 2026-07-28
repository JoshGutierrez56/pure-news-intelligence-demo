# Pure News Intelligence v2 critical audit

Audit date: 2026-07-28  
Starting deployed commit: `1a8399dbded190197cd466a4d6643b4b361eabfc`  
Audit status: complete before implementation

## Scope

The deployed site was rendered in Microsoft Edge at 1920×1080, 1440×900, 1024×768, and 390×844. The audit covered the overview, professor presentation, ranked feed, case-study gallery, comparisons, timelines, research results, methodology, experimental workspace, presentation redirect, and all eight evidence packets. This produced 72 route-and-viewport captures. All 10 presentation screens were also inspected in presentation mode at 1440×900.

The review used five perspectives:

1. Innovation professor: Can the innovation logic be understood without narration?
2. Buy-side analyst: Can a relevant change be found, verified, and retained?
3. Head of Research: Is the workflow benefit specific and pilotable?
4. CTO or Head of Data: Are trust, governance, integration, and boundaries credible?
5. First-time visitor: Is the product understandable in under one minute?

Baseline technical findings:

- Public routes tested: 18
- Route-and-viewport renders: 72
- Presentation screens inspected: 10
- Console errors: 0
- Responsive overflows: 10
- Frozen disclosure-change records preserved: 995
- Evidence packets preserved: 8

## Ten highest-impact remaining weaknesses

### 1. The presentation sequence does not yet tell the requested innovation story

The current deck opens well, but it moves from the customer problem directly to interviews, pivot, workflow, metrics, case, and research. It lacks distinct screens for what current tools do well, the original hypothesis, and the negative result. The audience must reconstruct the causal chain.

Impact:

- Professor: the hypothesis-test-learn-pivot logic is less explicit than the class framework.
- First-time visitor: the pivot can feel like a positioning change instead of a disciplined experiment.
- Presentation coach: several screens contain two messages and cannot be summarized in one sentence.

Required response: rebuild the 10-screen order around problem → tool gap → interviews → hypothesis → result → pivot → workflow and case → claim boundary → pilot.

### 2. Presentation mode is visually clean but not presenter-ready

The deck has slide numbers, progress, and arrow controls, but no speaker prompts, notes toggle, full-screen keyboard shortcut, five-minute path, ten-minute path, jump-to-demo control, print layout, or explicit transition cues. The opening screen also overflows vertically in presentation mode because the innovation-frame card extends below the viewport.

Impact:

- Professor: the deck still depends on Josh knowing the narration from memory.
- Presenter: no recovery cues during live delivery.
- Projector use: dense screens create a temptation to read instead of explain.

Required response: add 15–30 second notes per screen; `N`, `F`, timing modes, print support, and next-idea cues.

### 3. Customer discovery is credible but too generic

The six names and perspectives are visible, but each card contains only one broad implication. The page does not systematically show the workflow problem, trust requirement, product implication, or remaining unvalidated assumption for each interview.

Impact:

- Professor: the evidence-to-design connection is weaker than it could be.
- Head of Research: it is unclear which findings came from users versus buyers or gatekeepers.
- CTO: security, integration, auditability, and governance appear as a combined sentence rather than explicit requirements.

Required response: use a structured six-interview synthesis and a three-column “users / buyers and gatekeepers / product changes” visual.

### 4. The pivot is stated but not memorable

The current before-and-after comparison is clear, but it compresses the empirical test, null result, customer discovery, working product, and next pilot into two columns. It does not create a memorable innovation journey.

Impact:

- Professor: the discipline of rejecting the original hypothesis is underplayed.
- First-time visitor: the relationship between research and product opportunity is easy to forget.
- Product narrative: the null result can still read as defensive language instead of useful evidence.

Required response: create one seven-stage visual with the caption “Evidence changed the project rather than being tuned away.”

### 5. The ranked feed behaves like a polished dataset, not a complete analyst workflow

The feed has strong cards, filters, sorting, pagination, and evidence links. It lacks first-use guidance, a persistent classification legend, expandable excerpts, a guided example, a save-for-discussion action, and a visible shortlist. “Why it may matter” is often too long for fast scanning.

Impact:

- Analyst: can find records but cannot complete the full find → verify → retain workflow.
- Head of Research: the collaboration and institutional-memory proposition is not demonstrated.
- First-time visitor: ten filters arrive before the user knows the recommended path.

Required response: add dismissible onboarding, a default frozen example, concise cards with expandable evidence, local-only saving, shortlist export, and a persistent legend.

### 6. Case studies feel like packets, not teaching stories

The gallery is outcome-independent and accurate, but the eight cases are not grouped by learning purpose. Confidence is missing from the gallery. The packet pages do not consistently lead with analyst question → change → prior disclosure → relevance → what the evidence cannot prove.

Impact:

- Professor: the cases do not teach why novelty classification changes the analyst task.
- Analyst: long extracts appear before a clear diligence question.
- First-time visitor: the gallery looks like eight parallel records rather than a curated curriculum.

Required response: group cases by purpose, add confidence, standardize the five-part structure, and create a two-case contrast walkthrough.

### 7. Research results are still too technical and have a real responsive defect

The page leads with a useful plain-language headline, but the first study still exposes information coefficient abbreviations in the main reading path. The large `INSUFFICIENT_EVIDENCE` label causes horizontal overflow at 1440×900 and 1024×768.

Impact:

- Professor: statistical detail competes with the decision lesson.
- First-time visitor: abbreviations can make the page feel like an archive report.
- Accessibility: clipped content is a concrete responsive failure.

Required response: lead each study with Question / What was tested / Result / Decision / Lesson, move metrics into details, and add a neutral research decision tree.

### 8. The class framework and pilot are implied instead of inspectable

Target user, buyer, gatekeeper, value proposition, and pilot appear across several pages, but there is no one-page innovation framework or complete pilot plan with measurement definitions and go/revise/stop rules.

Impact:

- Professor: class deliverables require navigation and inference.
- Head of Research: no ready artifact exists for deciding whether to sponsor a pilot.
- CTO: architecture and gatekeeping considerations are not consolidated.

Required response: add dedicated innovation-framework and pilot-plan pages.

### 9. Calls to action and downloadable materials are incomplete

The site offers “View presentation,” “Explore,” and “Open case,” but the final requested action is not consistent. There is no professor-materials hub, no downloadable pilot plan, and no feedback worksheet.

Impact:

- Professor: no compact handoff packet after the meeting.
- Potential sponsor: unclear whether the ask is feedback, an introduction, enterprise requirements, or pilot participation.
- Josh: the live demo does not naturally convert into a next conversation.

Required response: add “Help test the next version” and deterministic HTML downloads.

### 10. Mobile evidence packets and some language still expose internal research mechanics

All eight evidence packets overflow horizontally at 390×844 because hashes and long technical strings do not wrap. Terms such as “corpus-bounded,” “point-in-time,” and “expected-language representation” remain prominent outside technical details. The experimental workspace is a 10,878-word surface and still feels archive-like if opened.

Impact:

- Mobile visitor: evidence pages require horizontal scrolling.
- Professor: internal terminology adds cognitive load.
- CTO: a prototype laboratory can be mistaken for the primary product unless its secondary status stays unmistakable.

Required response: wrap provenance strings, simplify primary language, retain exact terms in methodology, and keep the laboratory out of the main story.

## What already works and should be preserved

- The customer problem is visible on the first screen.
- The institutional visual system is credible and restrained.
- Product value and unsupported alpha claims are clearly separated.
- The current feed keeps every record linked to source evidence.
- The case-selection boundary is explicit and outcome-independent.
- The research conclusion remains visible rather than hidden.
- Primary routes have semantic headings, focus styles, labeled controls, and zero console errors.
- Large SEC and headline archives remain secondary and lazy-loaded.

## Audit decision

Proceed with a focused v2 polish, not a ground-up redesign.

Priority order:

1. Rebuild the presentation narrative and presenter controls.
2. Complete the analyst workflow in the ranked feed.
3. Strengthen interview synthesis and the pivot visual.
4. Add innovation-framework, pilot-plan, and professor-materials artifacts.
5. Restructure cases and research results for teaching clarity.
6. Fix all responsive overflows and complete accessibility validation.
