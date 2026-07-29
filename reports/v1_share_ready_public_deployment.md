# v1 Share-Ready Public Deployment

Deployment attempt: 2026-07-29 18:49:50 EDT  
Authorized source: `2c1d92517600587d74ee36a6f10d38cb25f9dcbf`  
Prior and rollback commit: `61c50b0b0f8d95ea9b39edd2a2b02d451ef9890f`

## Result

The exact authorized commit was fast-forwarded to `gh-pages`. All pre-deployment tests passed, the public routes rendered, the manifest itself retained its required byte hash, and the initial live browser audit passed.

The deployment then failed a public-data integrity check: the raw live public packet bytes did not match the SHA-256 values recorded in the public manifest.

- `dvn.json` manifest hash: `103b1894bba6fb1ed3ed82e907315e92f3c749262c65aeaed1a0a4b7db6db655`
- `dvn.json` live/Git-blob hash: `8bf5dbafdf508c789bbd7f6003060979072a4fcac00c768510c928c270d8708a`

The cause is line-ending normalization of the packet JSON files. The path-specific `.gitattributes` rule protects only `manifest.json`; it does not protect `rh.json`, `dvn.json`, or `efx_rejection.json`. The manifest therefore records CRLF working-tree hashes while GitHub Pages serves LF Git blobs.

Per the mandatory rollback rule, `gh-pages` was restored to `61c50b0` at 2026-07-29 18:53:58 EDT. The rollback was verified live by the restored homepage copy and the absence of the newly added FAQ route.

## Classification

`ROLLBACK_REQUIRED`

No research result, packet, source artifact, or feature-branch implementation was changed.
