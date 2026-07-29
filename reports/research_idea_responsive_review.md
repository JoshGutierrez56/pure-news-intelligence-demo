# Research Idea Responsive Review

## Result

**PASS — the three Research Idea pages, ranked-feed integration, and all eight frozen packet details reflow without horizontal page overflow at the required sizes.**

This layout result is independent of the research gate. The frozen packet collection remains **HOLD_GROUNDING**, with zero publishable packets.

## Scope and matrix

Final browser checks ran on Microsoft Edge `151.0.4129.50` through Playwright `1.62.0` against the local static server.

| Viewport | Review surfaces | Packet-detail routes | Maximum page overflow | Runtime, console, or request failures |
|---|---:|---:|---:|---:|
| `1920×1080` | 5 | 8 | `0px` | 0 |
| `1440×900` | 5 | 8 | `0px` | 0 |
| `1024×768` | 5 | 8 | `0px` | 0 |
| `390×844` | 5 | 8 | `0px` | 0 |
| **Total** | **20 runs** | **32 runs** | **`0px`** | **0** |

The five frozen review surfaces were:

- strongest grounded hold (EFX)
- rejected packet (KHC)
- no-actionable-view hold (CHE)
- Idea Gallery
- Idea Methodology

The ranked feed was covered separately by the combined public-surface
responsive suite and exact-link checks.

All eight final packet states rendered twelve ordered detail sections, the required disclaimer, analyst controls, and their exact held or rejected state:

- Held: TFC, DLTR, EFX, CHE
- Rejected by skeptic: KHC, DVN, RH, FCX

## Layout behavior observed

### `1920×1080` and `1440×900`

- Full primary navigation remained visible.
- Detail evidence led the page, followed by interpretation, hypotheses, skeptical review, and analyst controls.
- Gallery cards used the wide multi-column layout and displayed all eight packets.
- Methodology used its wide workflow and trust-control grids.
- No clipped cards, controls, badges, source text, or page-level scrollbar appeared.

### `1024×768`

- Primary navigation collapsed to the labeled **Menu** control.
- Wide Research Idea grids reduced to two columns where appropriate.
- The gallery filter and card layouts remained readable without fixed-width assumptions.
- Keyboard activation opened the collapsed navigation and exposed **Overview** as the next focus stop.

### `390×844`

- Hero panels, filter controls, gallery cards, evidence comparisons, scenarios, skeptical-review content, and analyst controls collapsed to one column.
- Hero actions and disposition controls became full-width.
- The analyst notes field and save/export controls remained inside the viewport.
- All eight packet details had `0px` page overflow, including long evidence IDs and skeptical-review text.

## Mobile touch evidence

Using a touch-enabled `390×844` Edge context:

- The **Menu** target measured approximately `77.3×48px`; a touch tap opened the navigation and set `aria-expanded="true"`.
- Tapping and typing `KHC` into the issuer filter reduced the gallery to one card and retained `0px` overflow.
- The detail-page **Accept** target measured approximately `324×48px`; a touch tap set `aria-pressed="true"`.
- The temporary analyst state was removed after the test.

## Ranked-feed integration

Each bounded case was located by exact issuer and exact `data-record-id`. Every row produced one exact link to its frozen packet:

| Ticker | Change ID | Link result |
|---|---|---|
| TFC | `dbe75bc24f2888f4166a` | PASS |
| KHC | `8f5336b55618ffe68e8a` | PASS |
| DLTR | `339fae2941721ee094b0` | PASS |
| DVN | `4784f62ad001b2a12af4` | PASS |
| RH | `412b08746bb0ed5a7745` | PASS |
| FCX | `8d4598f4ea16f15c7048` | PASS |
| EFX | `279e7d4e407851a19548` | PASS |
| CHE | `2f22dc2216c9df31d377` | PASS |

The exact destination form was `research_idea.html?change_id=<change_id>`.

## Overflow regression and resolution

The final packet rerun exposed a real methodology-page overflow at
`1024×768`: the document measured `1140px` wide against a `1024px` viewport.
The cause was one unbroken evidence identifier inside the KHC guided example.

The narrow design-system fix is:

```css
.ri-guided-flow li { overflow-wrap: anywhere; }
```

The focused review suite then passed all five surfaces at all four required
sizes, and the permanent all-packet sweep passed all eight packet details at
all four sizes. Every final page measurement was `0px` overflow.

## Visual review

Twenty repository screenshots were inspected at the required sizes for:

- strongest grounded hold (EFX);
- rejected packet (KHC);
- no-actionable-view hold (CHE);
- gallery;
- methodology and guided example.

The screenshots showed clear one-column mobile reading order, visible
held/rejected badges, no overlapping controls, and no hidden primary action.
Their deterministic manifest SHA-256 is
`e15e8998c1e0a8f0f8625bcd03f142eb3c9f355a4871eef3f2a07e8aa2703198`.

## Limitations

- The matrix used Microsoft Edge only; Firefox and Safari were not tested.
- Touch behavior was emulated, not tested on physical devices.
- Landscape phone orientation, foldables, very small `320px` widths, browser zoom, OS font scaling, and print layout were not part of this run.
- Full external SEC pages and network conditions were outside scope.
- The responsive PASS does not override the feature-level `HOLD_GROUNDING` decision.

## Commands and execution

The site was served through the Playwright configuration. The final focused
Research Idea suite passed `15/15`; the combined public regression suite
passed `32/32`. The permanent matrix includes the 32 all-packet viewport
checks described above.

The final responsive classification is **PASS**. The feature-level research classification remains **HOLD_GROUNDING**.
