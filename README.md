# PFTL Validator Slashing and Misbehavior Evidence Pack

A public, reproducible evidence pack for validator misbehavior detection
on the PFTL ledger: a primary-source framework grounded in postfiatd
validator and consensus code, a configurable trace simulator, measured
detection and penalty tables, unedited drill and per-event logs, and a
claim-to-evidence index. **All results in this pack are simulated.**
Nothing here is a measurement of the live PFTL network.

## Headline results (simulated)

Detector rules R1–R7 (see `framework.md`, section 11) run over six
scenarios, 5 seeds each (1001–1005), 53 validators × 120 ledgers per
run (31,800 validator-ledger pairs pooled per scenario). Precision and
recall are pooled across the 5 seeds; FPR uses non-offense
opportunities as its denominator.

| Scenario | TP | FP | FN | Precision | Recall | FPR |
|---|---:|---:|---:|---:|---:|---:|
| baseline_clean | 0 | 0 | 0 | 1.0000 | 1.0000 | 0.0000 |
| equivocation_double_sign | 105 | 0 | 0 | 1.0000 | 1.0000 | 0.0000 |
| conflicting_validation_sets | 15 | 0 | 0 | 1.0000 | 1.0000 | 0.0000 |
| liveness_offline | 10 | 0 | 0 | 1.0000 | 1.0000 | 0.0000 |
| late_validations | 200 | 0 | 0 | 1.0000 | 1.0000 | 0.0000 |
| benign_divergence | 0 | 0 | 0 | 1.0000 | 1.0000 | 0.0000 |

Key discrimination results: the conflicting-set scenario produces
zero R1 (equivocation) flags — persistent divergence is not
equivocation; the equivocation scenario produces zero R7 (divergent)
flags; no scenario produces any R3 (bad sequence) or R4 (stale) flag;
the baseline and benign-divergence scenarios produce zero flags of
any kind. Quorum holds on every ledger in every scenario: the smallest
majority support observed is 50 validations, against a quorum of 36
for the modelled 53-validator set.

Canonical results SHA-256: `d26cee1b0eed63a44b06b80a440a119fed5090e15e40c88a9c3913be28d20d7b`
(`results.json`).

## What postfiatd does today

[FAKTA] postfiatd has **no slashing mechanism**. It has a Byzantine
behavior detector (`Validations::add()`, `RCLValidations::handleNewValidation`)
that logs and relays conflicting validations, but no stake penalty, no
jailing, and no tombstoning. The penalty table in this pack is therefore
a **calibration proposal**, not a network rule. The framework
(`framework.md`) documents the detector in full, with file and line
citations at pinned commit
`0085a1ff885d6a446369cf73a4430f75af22be55`, and compares it against
Cosmos SDK slashing, CometBFT evidence handling, and Ethereum Casper
FFG (kept separate, labelled as references).

## Contents

- [framework.md](framework.md) — primary-source framework: the
  postfiatd Byzantine detector, validation anatomy, quorum and the 67%
  rule, timing parameters, liveness machinery, reference PoS designs,
  proposed evidence format, detector rules R1–R7, penalty calibration,
  assumptions and limitations, full source list.
- [simulator.py](simulator.py) — deterministic trace simulator and
  detector (pure Python standard library, seeded, no timestamps).
- [run_drill.py](run_drill.py) — one-command drill: runs all scenarios
  over all seeds, scores the detector, writes `results.json` and the
  per-event logs, prints the report. Exit code 0 only if every check
  passes.
- [scenarios.json](scenarios.json) — scenario configurations (offenders,
  ledgers, thresholds), detector parameters, and the penalty model.
- [results.json](results.json) — canonical drill results (SHA-256
  `d26cee1b0eed63a44b06b80a440a119fed5090e15e40c88a9c3913be28d20d7b`).
- [detection-table.md](detection-table.md) — measured detection tables
  (pooled and per-seed), rule counts, quorum and volume, per-event log
  hashes, penalty-calibration table.
- [claim-to-evidence-index.md](claim-to-evidence-index.md) — every
  substantive claim mapped to a primary source or an unedited log file
  and line.
- [SHA256SUMS](SHA256SUMS) — SHA-256 for every file in the pack except
  itself.

## Logs (unedited)

Drill logs (all five byte-identical, SHA-256
`0390c5371b7724f53686c78f09e92245fc5d492bb0dda0de3eefaa23bb322c0f`):

- [logs/drill-run-1.log](logs/drill-run-1.log)
- [logs/drill-run-2.log](logs/drill-run-2.log)
- [logs/drill-run-3.log](logs/drill-run-3.log)
- [logs/drill-run-4.log](logs/drill-run-4.log)
- [logs/drill-run-5.log](logs/drill-run-5.log)

Fresh-clone rerun log (byte-identical to `drill-run-1.log`, same
SHA-256):

- [logs/fresh-clone-rerun.log](logs/fresh-clone-rerun.log)

Determinism check log (drill run under `PYTHONHASHSEED` 1, 2, 3, 42,
99, 777; all outputs byte-identical to the committed logs):

- [logs/determinism-hashseed-check.log](logs/determinism-hashseed-check.log)

Per-event logs (seed 1001, one JSON line per detection event, full
evidence references on every line):

- [logs/events-baseline_clean-seed1001.jsonl](logs/events-baseline_clean-seed1001.jsonl) — 0 events
- [logs/events-equivocation_double_sign-seed1001.jsonl](logs/events-equivocation_double_sign-seed1001.jsonl) — 21 events
- [logs/events-conflicting_validation_sets-seed1001.jsonl](logs/events-conflicting_validation_sets-seed1001.jsonl) — 3 events
- [logs/events-liveness_offline-seed1001.jsonl](logs/events-liveness_offline-seed1001.jsonl) — 2 events
- [logs/events-late_validations-seed1001.jsonl](logs/events-late_validations-seed1001.jsonl) — 40 events
- [logs/events-benign_divergence-seed1001.jsonl](logs/events-benign_divergence-seed1001.jsonl) — 0 events

## Reproduction

Requires Python 3.8 or later, standard library only. From the directory
holding these files:

```
python3 run_drill.py > logs/drill-run-1.log
```

The drill regenerates `results.json` and the six per-event logs for
seed 1001, prints the full report to stdout, and exits 0 only if every
check passes. Expected output is byte-identical to
[logs/drill-run-1.log](logs/drill-run-1.log) (SHA-256
`0390c5371b7724f53686c78f09e92245fc5d492bb0dda0de3eefaa23bb322c0f`).

Fresh-clone reproduction (the check this pack was verified with):

```
mkdir fresh-clone
cp simulator.py run_drill.py scenarios.json fresh-clone/
cd fresh-clone
python3 run_drill.py
```

The stdout must be byte-identical to
[logs/fresh-clone-rerun.log](logs/fresh-clone-rerun.log). The rerun log
in this pack was produced exactly this way, from a clean copy of only
the code and configuration files.

Verify file integrity at any time with:

```
sha256sum -c SHA256SUMS
```

## Sources

Primary sources (postfiatd, pinned commit
`0085a1ff885d6a446369cf73a4430f75af22be55`, accessed 2026-11-17):

- `src/xrpld/consensus/Validations.h` —
  https://raw.githubusercontent.com/postfiatorg/postfiatd/0085a1ff885d6a446369cf73a4430f75af22be55/src/xrpld/consensus/Validations.h
- `src/xrpld/app/consensus/RCLValidations.h` —
  https://raw.githubusercontent.com/postfiatorg/postfiatd/0085a1ff885d6a446369cf73a4430f75af22be55/src/xrpld/app/consensus/RCLValidations.h
- `src/xrpld/app/consensus/RCLValidations.cpp` —
  https://raw.githubusercontent.com/postfiatorg/postfiatd/0085a1ff885d6a446369cf73a4430f75af22be55/src/xrpld/app/consensus/RCLValidations.cpp
- `src/xrpld/consensus/ConsensusParms.h` —
  https://raw.githubusercontent.com/postfiatorg/postfiatd/0085a1ff885d6a446369cf73a4430f75af22be55/src/xrpld/consensus/ConsensusParms.h
- `src/xrpld/app/consensus/RCLConsensus.h` —
  https://raw.githubusercontent.com/postfiatorg/postfiatd/0085a1ff885d6a446369cf73a4430f75af22be55/src/xrpld/app/consensus/RCLConsensus.h
- `src/xrpld/app/consensus/RCLCensorshipDetector.h` —
  https://raw.githubusercontent.com/postfiatorg/postfiatd/0085a1ff885d6a446369cf73a4430f75af22be55/src/xrpld/app/consensus/RCLCensorshipDetector.h
- `src/xrpld/app/misc/ValidatorList.h` —
  https://raw.githubusercontent.com/postfiatorg/postfiatd/0085a1ff885d6a446369cf73a4430f75af22be55/src/xrpld/app/misc/ValidatorList.h
- `src/xrpld/app/misc/detail/ValidatorList.cpp` —
  https://raw.githubusercontent.com/postfiatorg/postfiatd/0085a1ff885d6a446369cf73a4430f75af22be55/src/xrpld/app/misc/detail/ValidatorList.cpp

Reference sources (accessed 2026-11-17; kept separate from PFTL claims):

- Cosmos SDK `x/slashing` module —
  https://docs.cosmos.network/sdk/latest/modules/slashing/README
- CometBFT evidence specification —
  https://docs.cosmos.network/cometbft/latest/spec/consensus/Evidence
- Vitalik Buterin, annotated Ethereum 2.0 specification (Casper FFG) —
  https://notes.ethereum.org/@vbuterin/Sys3GLJbD
- XRPL Negative UNL —
  https://xrpl.org/docs/concepts/consensus-protocol/negative-unl
- XRPL consensus introduction —
  https://learn.xrpl.org/course/intro-to-the-xrpl/lesson/how-the-xrp-ledger-works/

## Labels

Every substantive claim in this pack carries exactly one label:
`[FAKTA]` (verified fact with source, date, and evidence),
`[ESTIMASI]` (modelled or reported number), `[ANALISIS]`
(interpretation). Simulated results are labelled simulated wherever
they appear.
