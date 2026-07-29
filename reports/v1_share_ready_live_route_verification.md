# v1 Share-Ready Live Route Verification

## Attempted deployment checks

- Primary and new public HTML routes: 16/16 returned successfully.
- Intended share resources: 8/8 returned successfully.
- Internal links checked: 30 unique live links.
- Broken links: 0.
- Serious or critical axe violations: 0.
- Console or request errors: 0.
- Horizontal-overflow failures: 0.
- Desktop rendering: PASS.
- Mobile rendering: PASS.
- Print flow: PASS.
- JSON export: PASS (`rh-research-hypothesis.json`).
- Markdown export: PASS (`rh-research-hypothesis.md`).
- Local analyst controls: PASS.
- Five-minute presentation mode: PASS.
- Ten-minute presentation mode: PASS.
- EFX financial-role rendering: PASS.
- Browser and social metadata: PASS.
- Public architecture diagram: PASS.

These checks passed before the public-packet hash failure triggered rollback. They do not override the failed integrity gate.

## Rollback verification

The live homepage reverted to the `61c50b0` copy, and `/demo/faq.html` returned 404 after the rollback propagated. Remote `gh-pages` resolves to `61c50b0b0f8d95ea9b39edd2a2b02d451ef9890f`.

Final route disposition: rollback verified.
