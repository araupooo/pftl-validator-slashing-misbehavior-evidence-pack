# Measured Detection and Penalty Tables (Simulated Data)

[FAKTA] All numbers below are simulated. They come from the simulator in
`simulator.py`, run by `run_drill.py` over the synthetic traces defined
in `scenarios.json`. Nothing here is a measurement of the live PFTL
network.

## Definitions (read before the tables)

[FAKTA] Each scenario is run over 5 seeds (1001, 1002, 1003, 1004, 1005).
Each run covers 53 validators × 120 ledgers = 6,360 validator-ledger
pairs, so each scenario's pooled opportunity count is 31,800 pairs.

[FAKTA] A detection event matches a ground-truth event when validator,
ledger sequence, and rule all match. TP, FP, and FN are counted with
multiplicity: the same (validator, ledger, rule) key occurring in
several pooled seeds counts once per seed.

[FAKTA] Precision = TP / (TP + FP); recall = TP / (TP + FN). Both are
defined as 1.0000 when their denominator is 0 (no detections and no
ground truth means nothing was missed and nothing was falsely
flagged). FPR = FP / non-offense opportunities, where non-offense
opportunities = 31,800 − pooled ground-truth events. TN = non-offense
opportunities − FP.

[FAKTA] "Pooled" means summed across all 5 seeds. "Per-seed" means one
seed's run alone. The two are never mixed in a single table without
saying which one it is.

## Pooled metrics (5 seeds pooled)

[FAKTA] Source: `results.json` (canonical results SHA-256
`d26cee1b0eed63a44b06b80a440a119fed5090e15e40c88a9c3913be28d20d7b`)
and `logs/drill-run-1.log`, lines 9–14.

| Scenario | TP | FP | FN | TN | Precision | Recall | FPR |
|---|---:|---:|---:|---:|---:|---:|---:|
| baseline_clean | 0 | 0 | 0 | 31800 | 1.0000 | 1.0000 | 0.0000 |
| equivocation_double_sign | 105 | 0 | 0 | 31695 | 1.0000 | 1.0000 | 0.0000 |
| conflicting_validation_sets | 15 | 0 | 0 | 31785 | 1.0000 | 1.0000 | 0.0000 |
| liveness_offline | 10 | 0 | 0 | 31790 | 1.0000 | 1.0000 | 0.0000 |
| late_validations | 200 | 0 | 0 | 31600 | 1.0000 | 1.0000 | 0.0000 |
| benign_divergence | 0 | 0 | 0 | 31800 | 1.0000 | 1.0000 | 0.0000 |

[ANALISIS] Precision and recall are 1.0000 in every scenario because
the injected offenses are clean and the detector thresholds are set to
match them. These numbers measure the detector against its own
specification, not against live network traffic.

## Per-seed metrics

[FAKTA] Source: `logs/drill-run-1.log`, lines 17–46. Per-seed TP, FP,
and FN are identical across all five seeds for every scenario, because
the offenders and offense ledgers are fixed in `scenarios.json` and
only the signing-time jitter varies by seed. Precision and recall are
1.0000 on every seed of every scenario.

| Scenario | TP per seed | FP per seed | FN per seed | Precision per seed | Recall per seed |
|---|---:|---:|---:|---:|---:|
| baseline_clean | 0 | 0 | 0 | 1.0000 | 1.0000 |
| equivocation_double_sign | 21 | 0 | 0 | 1.0000 | 1.0000 |
| conflicting_validation_sets | 3 | 0 | 0 | 1.0000 | 1.0000 |
| liveness_offline | 2 | 0 | 0 | 1.0000 | 1.0000 |
| late_validations | 40 | 0 | 0 | 1.0000 | 1.0000 |
| benign_divergence | 0 | 0 | 0 | 1.0000 | 1.0000 |

[FAKTA] The 21 per-seed equivocation events are 20 R1 CONFLICTING
events (2 validators × 10 ledgers) plus 1 R2 MULTIPLE event (1
validator, 1 ledger). The 40 per-seed late events are 2 validators ×
20 ledgers. The 3 per-seed divergent events are 3 validators flagged
once each at ledger 32. The 2 per-seed liveness events are 2
validators flagged once each at ledger 60.

## Rule counts (detections per rule, 5 seeds pooled)

[FAKTA] Source: `logs/drill-run-1.log`, lines 49–54.

| Scenario | R1 | R2 | R3 | R4 | R5 | R6 | R7 |
|---|---:|---:|---:|---:|---:|---:|---:|
| baseline_clean | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| equivocation_double_sign | 100 | 5 | 0 | 0 | 0 | 0 | 0 |
| conflicting_validation_sets | 0 | 0 | 0 | 0 | 0 | 0 | 15 |
| liveness_offline | 0 | 0 | 0 | 0 | 10 | 0 | 0 |
| late_validations | 0 | 0 | 0 | 0 | 0 | 200 | 0 |
| benign_divergence | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

[FAKTA] The discrimination checks hold: the conflicting-set scenario
produces zero R1 flags (persistent divergence is not equivocation),
the equivocation scenario produces zero R7 flags (a second validation
for the same sequence never feeds the divergence rule), and no
scenario produces any R3 (bad sequence) or R4 (stale) flag.

## Quorum and volume

[FAKTA] Source: `logs/drill-run-1.log`, lines 56–63, and
`results.json` (`quorum` object). Quorum for the modelled 53-validator
set is 36 (see `framework.md`, section 6).

| Scenario | Minimum primary validations for the majority hash (any ledger, any seed) | Validations generated (5 seeds pooled) |
|---|---:|---:|
| baseline_clean | 53 | 31800 |
| equivocation_double_sign | 53 | 31905 |
| conflicting_validation_sets | 50 | 31800 |
| liveness_offline | 51 | 31500 |
| late_validations | 53 | 31800 |
| benign_divergence | 51 | 31800 |

[FAKTA] Quorum holds on every ledger in every scenario and every
seed: the smallest majority support observed is 50, against a quorum
of 36 (`logs/drill-run-1.log`, line 63).

[ANALISIS] The volume column is a consistency check, not a result: the
equivocation scenario has 105 extra validations (100 conflicting
second validations + 5 duplicate-cookie validations), and the
liveness scenario has 300 fewer (2 validators × 30 ledgers × 5
seeds). Both match the scenario definitions exactly.

## Per-event logs (seed 1001)

[FAKTA] Source: the files in `logs/`, one line per detection event.
SHA-256 values are printed in `logs/drill-run-1.log`, lines 66–71.

| Log file | Events | SHA-256 |
|---|---|---|
| `logs/events-baseline_clean-seed1001.jsonl` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `logs/events-equivocation_double_sign-seed1001.jsonl` | 21 | `194c9bd30229dfc94786dbeb89921cc4fa3e4c9851dacf3ba9067269ed659286` |
| `logs/events-conflicting_validation_sets-seed1001.jsonl` | 3 | `a75a54ac2d2ec69c18da185932c92de31e921933124e7eea0f9c44d40becbdff` |
| `logs/events-liveness_offline-seed1001.jsonl` | 2 | `b87a2011b0a19b631dba8a9381610fbab417cd942255207c073563457754b1fc` |
| `logs/events-late_validations-seed1001.jsonl` | 40 | `dbb18af7b7da6d1c7d9aced6f459a82d6c9599fcd88f417592bbae8c973f76fa` |
| `logs/events-benign_divergence-seed1001.jsonl` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |

[FAKTA] The two 0-event files are empty (SHA-256 of empty input).
Each event line carries the validator, ledger sequence, rule,
offense, and full evidence references (ledger hash, signing hash,
sign time, cookie) so a cited line can be checked by eye.

## Penalty-calibration table (model parameters, not a PFTL rule)

[ANALISIS] postfiatd has no slashing mechanism and no staking module
at the pinned commit, so this table is a calibration proposal for
discussion. The reference column shows where each number is borrowed
from; the model column is the choice made for this pack. See
`framework.md`, section 12, for the reasoning.

| Offense | Rule | Modelled slash (share of stake) | Modelled jail | Tombstone | Reference |
|---|---|---|---|---|---|
| Equivocation (conflicting) | R1 | 5% | none (permanent exclusion instead) | yes | Cosmos `SlashFractionDoubleSign` 0.05 |
| Multiple (same ledger, different cookie) | R2 | 0% | none | no | postfiatd treats as probable misconfiguration |
| Bad sequence | R3 | 0% | none | no | validation dropped |
| Stale | R4 | 0% | none | no | validation dropped |
| Liveness fault | R5 | 1% | 600 s | no | Cosmos `SlashFractionDowntime` 0.01, `DowntimeJailDuration` 600 s |
| Late validation | R6 | 0% | none | no | warning only |
| Persistent divergence | R7 | 0% | none | no | warning plus investigation; not slashable alone |
