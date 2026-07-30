# Final Public Packet Integrity Repair

## Scope

Starting commit: `0e1e2e0fbb4e9c87d8a09bb39580c490e66b9669`

Repair commit: `4f884e92a5229519c229ae89c4d25fe4256cc7ad`

Only these public packet files were repaired:

- RH: `demo/data/research_ideas/v2/rh.json`
- DVN: `demo/data/research_ideas/v2/dvn.json`
- EFX rejection: `demo/data/research_ideas/v2/efx_rejection.json`

The canonical bytes were already present in the validated Windows working
tree and matched the hashes frozen in `manifest.json`. Git had previously
normalized those bytes to LF. The repair added exact `-text` rules and staged
the validated CRLF bytes. No JSON value changed.

## Byte inventory

| Packet | Bytes | Working tree | Index | Commit | Clean clone | Canonical |
|---|---:|---|---|---|---|---|
| RH | 13,622 | `684dfea02feaeb76d8a3de134118e18a8bfe192216757a8c127cf6fa5b1e5585` | same | same | same | same |
| DVN | 14,394 | `103b1894bba6fb1ed3ed82e907315e92f3c749262c65aeaed1a0a4b7db6db655` | same | same | same | same |
| EFX | 5,757 | `e92004321017a148b8f88df832d7b535ca90535e8e0b94c1e9988e96ba8d388c` | same | same | same | same |

## Semantic hashes

- RH: `7ad8dfa3c196950ca78ef18410b452c6256c90711077282ed7c020df0ebcf750`
- DVN: `9e9ae28abf9aaa27f7a206613bfb71756c25982d7ccf89ff7dc805d2e5982a9c`
- EFX: `a5229d3f4864b4ee61a66ca602a91308720dfc96bc9a6115c8665ee4fd1550d2`

## Attribute rules

```gitattributes
demo/data/research_ideas/v2/rh.json -text
demo/data/research_ideas/v2/dvn.json -text
demo/data/research_ideas/v2/efx_rejection.json -text
```

No wildcard rule was applied to the Research Idea directory and no global
normalization setting changed.

Final repair result: **PASS**.
