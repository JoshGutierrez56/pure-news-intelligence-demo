# Research Idea Engine V2 fixtures

`novelty_role_fixtures.json` freezes the expected retrieval, novelty,
financial-role, grounding, and fail-safe outcomes before the eight real cases
are rerun. The fixture inventory includes the EFX negative regression and the
fifteen additional patterns required by the V2 grounding-repair protocol.

The fixture file is an input contract. Tests may read it but generation scripts
must not rewrite it.
