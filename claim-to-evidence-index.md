# Claim-to-Evidence Index

Every substantive claim in this pack, mapped to the primary source or
unedited log file and line that supports it. All results are simulated;
"evidence" here means the simulator output or the cited source file.
Pinned postfiatd commit for every source citation:
`0085a1ff885d6a446369cf73a4430f75af22be55` (accessed 2026-11-17).
File line numbers are file lines, verified against a local checkout of the pinned commit and cross-checked against the GitHub API blob for each file.

## PFTL source claims

| Claim | Evidence |
|---|---|
| postfiatd has no slashing mechanism; detection and logging only | Code search of postfiatd at the pinned commit for `equivocation`, `slash`, `conflicting`, `doubleSign` returned no slashing implementation. The complete detection mechanism is `src/xrpld/consensus/Validations.h` lines 623–707 and `src/xrpld/app/consensus/RCLValidations.cpp` lines 165–277. |
| `ValStatus` enum: `current`, `stale`, `badSeq`, `multiple`, `conflicting`, with `multiple` = same ledger and `conflicting` = different ledgers | `src/xrpld/consensus/Validations.h`, lines 169–180; `multiple` definition lines 176–177; `conflicting` definition lines 178–179 |
| `SeqEnforcer` returns false when the offered sequence is less than or equal to the largest seen, resetting after 10 minutes | `src/xrpld/consensus/Validations.h`, lines 99–135; `operator()` lines 118–128 |
| Validation timing parameters: CURRENT_WALL 5 min, CURRENT_LOCAL 3 min, CURRENT_EARLY 3 min, SET_EXPIRES 10 min, FRESHNESS 20 s | `src/xrpld/consensus/Validations.h`, lines 46–90; WALL line 56; LOCAL line 64; EARLY line 71; SET_EXPIRES line 79; FRESHNESS line 89 |
| `isCurrent` bounds: sign time after (now − 3 min) and before (now + 5 min) | `src/xrpld/consensus/Validations.h`, lines 149–166 |
| Byzantine branch order: different ledger ID → `conflicting`; same ledger, different sign time → `conflicting`; same seq+ledger, different cookie → `multiple`; otherwise `badSeq` | `src/xrpld/consensus/Validations.h`, lines 653–681; different-ledger lines 664–665; different-sign-time lines 671–672; different-cookie lines 676–677; `badSeq` line 680 |
| Tracked entry replaced when sign-time difference exceeds 5 minutes and the new sign time is later | `src/xrpld/consensus/Validations.h`, lines 644–650 |
| Validation evidence fields: ledger ID, sequence, sign time, seen time, signing key, node ID, trusted flag, full flag, load fee, cookie | `src/xrpld/app/consensus/RCLValidations.h`: `ledgerID()` line 61; `seq()` line 68; `signTime()` line 75; `seenTime()` line 82; `key()` line 89; `nodeID()` line 96; `trusted()` line 103; `setTrusted()`/`setUntrusted()` lines 109/115; `full()` line 122; `loadFee()` line 129; `cookie()` line 136 |
| Trusted validations have their vote recorded with the signing hash as proof, then `checkAccept(hash, seq)` is called | `src/xrpld/app/consensus/RCLValidations.cpp`, lines 216–222 (recordVote) and line 237 (checkAccept) |
| Trust marking from the validator list (UNL / listed key) | `src/xrpld/app/consensus/RCLValidations.cpp`, lines 177–185 |
| Problematic trusted validations are logged at the highest level and deliberately relayed so peers observe them | `src/xrpld/app/consensus/RCLValidations.cpp`, comment lines 243–251 |
| `conflicting` log line: "Byzantine Behavior Detector:... Conflicting validation for {seq}!" | `src/xrpld/app/consensus/RCLValidations.cpp`, lines 265–269 |
| `multiple` log line: "Byzantine Behavior Detector:... Multiple validations for {seq}/{hash}!" | `src/xrpld/app/consensus/RCLValidations.cpp`, lines 271–275 |
| `minCONSENSUS_PCT` = 67 | `src/xrpld/consensus/ConsensusParms.h`, line 79 |
| Consensus timing: `validationVALID_WALL` 5 min, `validationVALID_LOCAL` 3 min, `validationVALID_EARLY` 3 min, `proposeFRESHNESS` 20 s, `proposeINTERVAL` 12 s, `ledgerMIN_CONSENSUS` 1950 ms, `ledgerMAX_CONSENSUS` 15 s, `ledgerMIN_CLOSE` 2 s, `ledgerGRANULARITY` 1 s, `ledgerABANDON_CONSENSUS_FACTOR` 10, `ledgerABANDON_CONSENSUS` 120 s, `avMIN_CONSENSUS_TIME` 5 s; avalanche cutoffs 50% / 65% / 70% / 95%; `avCT_CONSENSUS_PCT` 75; `avMIN_ROUNDS` 2; `avSTALLED_ROUNDS` 4 | `src/xrpld/consensus/ConsensusParms.h`: lines 51, 59, 66, 69, 72, 86–87, 95–96, 99, 102, 105, 113–114, 126–127, 146–157, 160, 165, 169 |
| Quorum formula `max(ceil(effectiveUnlSize * 0.67), ceil(unlSize * 0.6))`; 67% comment citing Theorem 8 of arXiv 1802.07242; "Original XRPL uses 80%, but this fork uses 67% for devnet/testnet. For mainnet, this should be reverted to 80%." | `src/xrpld/app/misc/detail/ValidatorList.cpp`: formula lines 1933–1934; comment lines 1898–1903; `calculateQuorum` lines 1845–1935 |
| Quorum recomputed every round by `updateTrusted` | `src/xrpld/app/misc/detail/ValidatorList.cpp`, line 1938 (`updateTrusted`); `quorum_` assignment line 2109 |
| Command-line `minimumQuorum_` override with "potentially unsafe" warning; quorum disabled (`SIZE_MAX`) when too many publishers unavailable | `src/xrpld/app/misc/detail/ValidatorList.cpp`, lines 1851–1857 and 1894–1895 |
| A ledger is fully validated once trusted validations meet or exceed quorum; trusted-list size is 125% of quorum with multiple lists | `src/xrpld/app/misc/ValidatorList.h`, comment lines 492–496 and line 170 |
| Liveness machinery: `censorshipWarnInternal` = 15; `getQuorumKeys()`; `laggards(seq, trustedKeys)`; `proposersValidated(h)`; `proposersFinished(...)`; `validate(ledger, txns, proposing)` | `src/xrpld/app/consensus/RCLConsensus.h`: line 56; lines 151–152; lines 155–157; lines 244–245; lines 255–256; lines 413–417 |
| Censorship detector: `propose()` tracks proposed transactions; `check(accepted, pred)` removes accepted ones; censorship = proposed repeatedly but never accepted | `src/xrpld/app/consensus/RCLCensorshipDetector.h`: lines 81–97; lines 113–131; `reset()` lines 138–142 |
| Negative UNL accessors; validators excluded from the effective UNL when believed offline or malfunctioning | `src/xrpld/app/misc/ValidatorList.h`, lines 705–728 |
| `STValidation` declaration file lives at `include/xrpl/protocol/STValidation.h`, not `src/xrpl/protocol/STValidation.h` (404 at the pinned commit) | Stated in `framework.md`, section 3. No claim in this pack cites that file. |

## Reference-design claims (not PFTL rules)

| Claim | Evidence |
|---|---|
| Cosmos SDK `x/slashing`: double-signing slashed by `SlashFractionDoubleSign` and tombstoned; tombstone cap allows one slash per double-sign fault; liveness slashes do not tombstone | https://docs.cosmos.network/sdk/latest/modules/slashing/README (accessed 2026-11-17; page updated 2026-08-04), "Tombstone Caps" and "Liveness Tracking" sections |
| Cosmos liveness rule: `maxMissed` = `SignedBlocksWindow` − (`MinSignedPerWindow` × `SignedBlocksWindow`); slash by `SlashFractionDowntime`, jail for `DowntimeJailDuration` | Same page, "BeginBlock / Liveness Tracking" section |
| Cosmos example parameters: `SignedBlocksWindow` 100; `MinSignedPerWindow` 0.5; `DowntimeJailDuration` 600,000,000,000 ns; `SlashFractionDoubleSign` 0.05; `SlashFractionDowntime` 0.01 | Same page, "Parameters" table |
| Cosmos equivocation valid only if `Evidence.Timestamp >= block.Timestamp − MaxEvidenceAge`; slash applies to stake at infraction time | Same page, "Staking Tombstone" section; also https://devnet.docs.injective.dev/develop/modules/Core/evidence/begin_block/ (accessed 2026-11-17) |
| CometBFT `DuplicateVoteEvidence` rules: same validator address, height, round, type; different BlockIDs; validator in set at that height; valid signatures; chain ID binds the fault | https://docs.cosmos.network/cometbft/latest/spec/consensus/Evidence (accessed 2026-11-17; updated 2026-10-30) |
| CometBFT evidence expiry: expired if `CurrentHeight − MaxAgeNumBlocks > EvidenceHeight` AND `CurrentTime − MaxAgeDuration > EvidenceTime`; evidence takes strict priority over transactions; per-block size capped by `MaxBytes` | Same page, "Verification" section |
| Ethereum Casper FFG: double vote (same target epoch, different data) and surround vote (`source_1 < source_2` and `target_2 < target_1`) are slashable; proposer equivocation is two blocks for the same slot; minimum penalty 1/32 of effective balance plus a correlation penalty | https://notes.ethereum.org/@vbuterin/Sys3GLJbD (accessed 2026-11-17), `is_slashable_attestation_data` and `process_slashings` |
| XRPL standard quorum 80% of trusted validators; Negative UNL keeps quorum at ≥80% of effective UNL and ≥60% of configured UNL; 35 validators on default UNLs as of 2024-06-25 | https://xrpl.org/docs/concepts/consensus-protocol/negative-unl (accessed 2026-11-17) |

## Simulator claims

| Claim | Evidence |
|---|---|
| Detector rules R1–R7 with exact thresholds | `simulator.py`, module docstring; `scenarios.json`, `detector` object |
| Penalty-calibration table is model parameters, not a PFTL rule | `scenarios.json`, `penalty_model` object (note field); `framework.md`, section 12; `detection-table.md`, penalty table |
| 53-validator set and 120 ledgers per run are model parameters | `scenarios.json`, `model` object (note field); `framework.md`, section 6 |
| Quorum for the modelled set is 36 | `scenarios.json`, `model.quorum_rule`; computed from the ValidatorList.cpp formula in the source table above |
| Scoring definitions: pooled vs per-seed, multiplicity counting, precision/recall 1.0 convention for a zero denominator, FPR denominator | `simulator.py`, `score()` docstring; `detection-table.md`, "Definitions" |

## Measured (simulated) results

| Claim | Evidence |
|---|---|
| Pooled metrics, all six scenarios (TP/FP/FN/TN/precision/recall/FPR) | `logs/drill-run-1.log`, lines 9–14; `results.json`, `per_scenario` object |
| Per-seed metrics (identical across all five seeds per scenario) | `logs/drill-run-1.log`, lines 17–46 |
| Rule counts pooled (R1=100, R2=5 in equivocation; R7=15 in conflicting sets; R5=10 in liveness; R6=200 in late; zero R1 in conflicting sets; zero R3/R4 everywhere) | `logs/drill-run-1.log`, lines 49–54 |
| Quorum holds on every ledger (minimum majority support 50, quorum 36) | `logs/drill-run-1.log`, line 63; `results.json`, `quorum` object |
| Canonical results SHA-256 `d26cee1b0eed63a44b06b80a440a119fed5090e15e40c88a9c3913be28d20d7b` | `logs/drill-run-1.log`, line 74; recompute with `sha256sum results.json` |
| Per-event log SHA-256 values and event counts | `logs/drill-run-1.log`, lines 66–71 |
| Equivocation event example: V003, ledger 40, R1 CONFLICTING, two validations with different ledger hashes | `logs/events-equivocation_double_sign-seed1001.jsonl`, line 1 |
| Multiple event example: V017, ledger 45, R2 MULTIPLE, same ledger hash, different cookie | `logs/events-equivocation_double_sign-seed1001.jsonl`, line 13 |
| Divergent event example: V005, ledger 32, R7 DIVERGENT, 3 disagreeing validations as evidence | `logs/events-conflicting_validation_sets-seed1001.jsonl`, line 1 |
| Liveness event example: V007, ledger 60, R5 LIVENESS, 11 missed ledgers as evidence | `logs/events-liveness_offline-seed1001.jsonl`, line 1 |
| Late event example: V011, ledger 20, R6 LATE | `logs/events-late_validations-seed1001.jsonl`, line 1 |
| Baseline and benign-divergence logs contain zero events (empty files) | `logs/events-baseline_clean-seed1001.jsonl` and `logs/events-benign_divergence-seed1001.jsonl` (0 lines; SHA-256 of empty input `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`) |
| All drill checks passed, exit code 0 | `logs/drill-run-1.log`, line 99 ("ALL CHECKS PASSED"); `logs/drill-run-2.log` through `logs/drill-run-5.log` identical |
| All five drill logs byte-identical | `SHA256SUMS`; all five files hash to `0390c5371b7724f53686c78f09e92245fc5d492bb0dda0de3eefaa23bb322c0f` |
| Fresh-clone rerun byte-identical to drill-run-1 | `logs/fresh-clone-rerun.log`, SHA-256 `0390c5371b7724f53686c78f09e92245fc5d492bb0dda0de3eefaa23bb322c0f` |
| Output byte-identical across separate processes under different hash seeds | `logs/determinism-hashseed-check.log` (drill run under `PYTHONHASHSEED` 1, 2, 3, 42, 99, 777, all outputs diffed against the committed logs) |
