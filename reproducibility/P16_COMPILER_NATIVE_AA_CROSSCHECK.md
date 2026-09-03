# Reviewer revision P16 — Compiler-native amplitude-amplification cross-check

Date: 2026-09-02
Status: COMPLETE — independent Qiskit compiler-native configuration cross-check

## Reviewer risk addressed
P14 showed that the executable threshold-oracle circuit can be far deeper than the analytical ripple-style bookkeeping template. A natural follow-up concern is whether the manuscript's zero-fixed-overhead `k*=0` configuration conclusion is merely an artefact of the analytical cost model. P16 therefore re-evaluates amplitude-amplification depth selection directly in compiler-native resource coordinates.

## Locked provenance
- GitHub Actions run: `33596371482` — **success**.
- Branch: `compiler-native-aa-v1.1`.
- Head SHA: `8f9ef9294f393bc3aa0b6ceefde07472a0d2a74c`.
- Artifact: `compiler-native-aa-qiskit-2.4.2`, artifact ID `9833538936`.
- Artifact digest: `sha256:b97c18dc5fc2860719312eb14442d2b1e82f4f68d193b5e4a74e73093d965cc5`.
- Qiskit: `2.4.2`; Python: `3.12.14`.
- Basis: `rz`, `sx`, `x`, `cx`; optimization level 1; `seed_transpiler=20260901`.

## Design
Nine representative primary instances are used: seed 17 for every `n={8,10,12}` x density `{0.25,0.50,0.75}` cell at operational `lambda=0.40`. For each instance:
1. The same executable reversible weighted-threshold oracle as P14 is basis-decomposed.
2. Uniform superposition preparation on the data register is compiled in the same basis.
3. A standard data-register Grover diffusion circuit is compiled in the same basis while retaining the oracle work-register width.
4. Exact Tier-I `rho_tau` is used only as retrospective marked-fraction ground truth for the cross-check.
5. `k=0..64` is exhaustively selected under two separate compiler-native scores: ideal Grover hit probability divided by total compiled instruction count, and ideal Grover hit probability divided by compiled serial depth.

No coupling map is imposed in the P16 selection layer. This intentionally isolates locked-basis synthesis from routing; P14 retains the separate line-routing stress evidence.

## Results
- Rows: **9**.
- All 9/9 select `k*=0` using compiled instruction count.
- All 9/9 select `k*=0` using compiled depth.
- Median compiled iteration size (oracle + diffusion): **147,848** basis instructions.
- Median compiled iteration depth (oracle + diffusion): **110,391**.
- The executable oracle dominates diffusion: median oracle/diffusion ratio is **684.5x** by instruction count and **1444.7x** by depth.
- The exact fixed-per-trial break-even, normalized by one compiler-native iteration cost, has median **0.1475** for instruction count and **0.1477** for depth. The observed ranges are approximately 0.0495--0.2455 and 0.0496--0.2460, respectively.

## Interpretation boundary
P16 supports a qualitative robustness statement: on these nine exact representatives, the zero-fixed-overhead no-amplification configuration survives replacement of the analytical resource coordinate by direct locked-basis compiler instruction/depth coordinates. It does **not** validate the analytical gate formulas, identify compiler instruction count with physical execution time, or establish hardware advantage. The compiler-native fixed-overhead ratios use a different denominator from the analytical `C_fixed/G_O` coordinate, so their numerical proximity is not treated as metric equivalence.

## Canonical evidence
- `src/compiler_native_aa_crosscheck.py`
- `.github/workflows/compiler-native-aa.yml`
- `results/compiler_native_aa_crosscheck.csv`
- `results/compiler_native_aa_summary.json`
- `reproducibility/P16_COMPILER_NATIVE_AA_CROSSCHECK.md`
