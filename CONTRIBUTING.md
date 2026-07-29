# Contributing

Contributions should strengthen evidence traceability, accessibility, reproducibility, or claim discipline.

## Before opening a change

1. Preserve frozen packets, source excerpts, offsets, research results, and receipts.
2. Do not introduce future outcomes into point-in-time artifacts.
3. Keep facts, interpretations, uncertainty, and hypotheses separate.
4. Add tests for changed behavior.
5. Run the Python and Playwright suites.
6. Explain any public claim change and cite its frozen source artifact.

Do not regenerate locked research packets, weaken publication gates, add personalized investment advice, or represent automated checks as human validation.

## Development

```powershell
npm install
npx playwright install
node tests/server.cjs
python -m unittest discover -s tests -p "test_*.py"
npm test
```

Use focused commits. Do not commit credentials, licensed article bodies, private reviewer notes, local paths, model chain-of-thought, or unpublished speculative packets.
