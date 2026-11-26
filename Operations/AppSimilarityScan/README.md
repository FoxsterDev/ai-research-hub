# App Similarity Scan

A static self-check for iOS app bundles that answers one question before you submit:
**how much of this binary is the same as other apps you (or anyone in your corpus) ship?**

App Store Review Guideline 4.3(a) rejects apps that share "a similar binary, metadata,
and/or concept" with other apps "with only minor differences". Apple does not publish how
it measures this. This tool is a transparent reconstruction for self-checks. It
fingerprints every layer of a bundle, weights each feature by how rare it is in a
background corpus, and scores a build against peer builds. It does not predict review
outcomes, and it does not cover store-listing text or screenshots.

Standard library only (Python 3.9+). Unity-aware (IL2CPP metadata, UnityFS bundles), but
it also works on any arm64 iOS app.

## Quick start

```bash
python3 appsim.py index MyGame.ipa --out idx/mygame.json --label MyGame-2.0
python3 appsim.py index Other.xcarchive --out idx/other.json --label Other-1.4
python3 appsim.py index EmptyUnity.app --out idx/engine.json --label empty-unity
python3 appsim.py score idx/mygame.json --peers idx/other.json --background idx/engine.json \
  --previous idx/mygame-1.9.json --group 'studio=^(MyStudio|Shared)\.' --group-rest third-party \
  --out-md report.md --out-json report.json
python3 appsim.py scan idx/*.json --background idx/engine.json
```

`score` exits with code `2` when the level is `high`, so you can use it as a CI gate.

## Inputs

| Input | Accepted forms |
|---|---|
| Bundle to index | `.ipa`, `.xcarchive`, or an `.app` folder; signed or unsigned, symbols stripped or not |
| Peers | indexes of other apps you want to compare against: your other titles, a previous version, competitors you legally have |
| Background | indexes of **unrelated** apps and engine-only builds (an empty project built with the same engine version). Features found there are discounted. The bigger and more varied the background, the closer the weights get to "how common is this in the store" |
| Previous | index of the same app's previous approved build. It enables the *identity shift* check |

Indexes contain hashes, sizes, assembly, framework and ObjC class names, and `Info.plist`
key names. String literals, C strings, plist values and file contents are stored only as
hashes.

## What is compared

| Layer | Features | Comparison |
|---|---|---|
| Code | ARM64 `__text` and stubs; address and offset immediates (`B/BL`, `B.cond`, `CBZ/TBZ`, `ADR(P)`, `LDR literal`, `ADD/LDR/STR imm`) are masked, so the same source linked into another binary still matches | content-defined chunks (~2 KB), byte containment |
| Assets | everything under `Data/` and resource files; UnityFS `data.unity3d` (LZ4/LZ4HC or uncompressed) is unpacked first | content-defined chunks (~8 KB), byte containment |
| Names | ObjC class and selector names; IL2CPP identifiers (types, namespaces, methods, fields, parameters, properties, events) and assembly names | set containment |
| Strings | Mach-O C strings, IL2CPP string literals | set containment |
| Packaging | embedded frameworks, `Info.plist` key=value pairs (build-volatile keys excluded), privacy manifest | set containment |
| Icon | 64-bit dHash of `AppIcon*.png` (Apple CgBI PNGs decoded) | Hamming distance |
| Binary data | other Mach-O sections (relocation-heavy, low signal) | chunks, low weight |

Feature weight (`--background-mode rarity`, default): `floor + (1 - floor) * (1 - df/N)^2`,
where `df/N` is the share of background apps containing the feature (weight 1 if absent).
With a small background use `--background-mode presence --floor 0` instead: anything found
in any background index is excluded. A good way to "take public SDKs out of the
equation" is to build an **SDK-only reference**: the same project, the same package
manifest, `link.xml` and player settings, the game's own folder removed, one empty scene.
Then pass it as background. Frameworks matching the
built-in third-party name list (`--third-party` adds globs) get a further ×0.25.

Overall score: the weighted mean of the layer containments (code 0.30, assets 0.20,
names 0.20, strings 0.10, packaging 0.10, icon 0.05, binary data 0.05). Containment is
asymmetric: it is the share of the *query* found in the peer. `scan` links two apps into
a cluster only if both directions pass the threshold.

## Output

- Peer table with overall and per-layer scores; sub-layer detail for the nearest peer.
- **Uniqueness**: weighted share of the query found in no peer. This is the measurable
  side of "only minor differences".
- **Identity shift** flag: the build is closer to another app than to its own previous
  build. This is typical of an update that rebuilds an existing app on a shared template.
- **Who owns the shared IL2CPP identifiers**: every identifier is attributed to the
  assemblies that declare it. `--group LABEL=REGEX` buckets your own assemblies, and
  engine/.NET assemblies are grouped automatically. This shows how much of the
  similarity comes from your shared code versus the engine and SDKs everybody ships.
- Level: `low` / `medium` (nearest peer ≥ 35%) / `high` (nearest peer ≥ 50% and low
  uniqueness or several close peers). The thresholds were calibrated on a small corpus of
  shared-template games against unrelated and pre-template builds. Treat the level as a
  similarity measure, not a review verdict: apps that already passed review can sit in a
  high cluster.

## Limits

- Weights are only as good as the background corpus. With just engine-only builds,
  common Unity UI/TMP and popular SDK code still weigh as "rare".
- Statically linked SDKs inside one framework binary can only be told apart from your
  own code through names (ObjC, IL2CPP), not through bytes.
- Not covered: store metadata (title, description, keywords, screenshots), runtime
  behavior, server-driven content.

## Tests

```bash
python3 -m unittest discover -s tests
```

The tests build synthetic Mach-O, UnityFS, IL2CPP metadata v31 and CgBI PNG fixtures. No
real app binaries are needed.
