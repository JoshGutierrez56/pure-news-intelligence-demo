# v1 Share-Ready Live Public-Data Audit

## Passed checks

- No credentials or API keys detected.
- No local machine paths detected in public V2 packet payloads.
- No private reviewer notes or chain-of-thought exposed.
- No licensed article bodies added.
- No future outcome fields added.
- No unpublished speculative packets added.
- Manifest JSON parsed and retained approved research boundaries.

## Failed check

The public packet byte hashes did not match the hashes declared by the manifest. This is a public-data integrity failure even though the packet JSON semantics were unchanged.

Observed:

- `dvn.json` live SHA-256: `8bf5dbafdf508c789bbd7f6003060979072a4fcac00c768510c928c270d8708a`
- Declared SHA-256: `103b1894bba6fb1ed3ed82e907315e92f3c749262c65aeaed1a0a4b7db6db655`

The same packaging risk applies to `rh.json` and `efx_rejection.json`, whose Git blobs are LF-normalized while the manifest records working-tree hashes.

Final public-data result: FAIL. Rollback completed.
