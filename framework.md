# Validator Slashing and Misbehavior Evidence Pack — Framework

## 1. Scope and reading guide

[FAKTA] This pack is a reproducible, simulated study of validator misbehavior
detection for the PFTL ledger. Every number in the detection tables comes
from the simulator in `simulator.py`, run over synthetic traces defined in
`scenarios.json`. No number in this pack is a measurement of the live PFTL
network.

[FAKTA] The primary sources for the framework below are postfiatd source
files at pinned commit `0085a1ff885d6a446369cf73a4430f75af22be55`, read
2026-11-17. All file paths are relative to the postfiatd repository root.
Line numbers are file lines (the raw-file display is 0-indexed, so file
line = displayed line + 1).

[ANALISIS] Labels used on every substantive claim in this pack:
`[FAKTA]` — verified fact with a source, a date, and evidence;
`[ESTIMASI]` — a modelled or reported number, never a measured fact;
`[ANALISIS]` — an interpretation of what a fact implies. A claim carries
exactly one label.

[FAKTA] Comparable proof-of-stake designs (Cosmos SDK, CometBFT evidence,
Ethereum Casper FFG, XRPL) appear only in section 9, kept separate from
PFTL claims and labelled as references. Nothing in section 9 is a PFTL
rule.

## 2. What postfiatd does today: detection without slashing

[FAKTA] postfiatd has no slashing mechanism. A code search of the
postfiatd repository at the pinned commit for `equivocation`, `slash`,
`conflicting`, and `doubleSign` returned no slashing implementation, and
the consensus and validator sources below contain detection and logging
only — no stake penalty, no jailing, no tombstoning.

[FAKTA] What postfiatd does have is a Byzantine behavior detector. The
generic `Validations::add()` in
`src/xrpld/consensus/Validations.h` (lines 1197–1248) runs the detector
when a validation violates the increasing-sequence invariant, and
`RCLValidations::handleNewValidation` in
`src/xrpld/app/consensus/RCLValidations.cpp` (lines 304–513) logs
problematic validations from trusted validators at the highest level and
deliberately relays them so peers observe them too (comment, lines
449–463).

[ANALISIS] The honest reading of the source is therefore: postfiatd can
*detect* equivocation and *record* it, but cannot *punish* it. Any
slashing rule for PFTL is a proposal to be designed, not a description of
existing behavior. The penalty table in section 12 is a calibration
model, not a network rule.

## 3. Validation anatomy: the evidence fields

[FAKTA] A validation is a signed statement by one validator about one
ledger. The fields an evidence package needs are the fields the
`RCLValidation` wrapper exposes in
`src/xrpld/app/consensus/RCLValidations.h`:
ledger ID (`ledgerID()`, line 106), ledger sequence (`seq()`, line 119),
signing time (`signTime()`, line 132), first-seen time (`seenTime()`,
line 145), signing key (`key()`, line 158), node ID (`nodeID()`, line
171), trusted flag (`trusted()`, line 184, with `setTrusted()` /
`setUntrusted()` at lines 195/206), full/partial flag (`full()`, line
219), load fee (`loadFee()`, line 232), and cookie (`cookie()`, line
245).

[FAKTA] `RCLValidations::handleNewValidation` records a trusted,
current validation's vote through `ValidatorVoteTracker.recordVote`,
using the validation's signing hash as proof (RCLValidations.cpp,
lines 362–410), and then calls `checkAccept(hash, seq)` (line 438).

[ANALISIS] The signing hash is therefore the natural evidence
identifier: two validations from the same validator for the same
sequence with different signing hashes are two distinct signed
statements, and that is exactly what an equivocation proof consists
of. The simulator's evidence references carry the full signing hash
for this reason.

[ANALISIS] Note on a path corrected during verification: the `STValidation` declaration
file lives at `include/xrpl/protocol/STValidation.h` in the pinned tree, not at
`src/xrpl/protocol/STValidation.h` (that path returns 404 at the pinned commit),
so this framework cites the
`RCLValidation` accessor fields above instead of `STValidation` field
declarations. No claim in this pack depends on that file.

## 4. The Byzantine detector in `Validations.h`

[FAKTA] The detector works on three inputs per validation: the
validator's identity, the ledger sequence, and the ledger ID. Its
statuses are defined by the `ValStatus` enum in
`src/xrpld/consensus/Validations.h` (lines 307–329): `current` (new,
added), `stale` (not current or older), `badSeq` (violates the
increasing-sequence requirement), `multiple` ("Multiple validations by
a validator for the same ledger", lines 321–323), and `conflicting`
("Multiple validations by a validator for different ledgers", lines
325–327).

[FAKTA] The increasing-sequence invariant is enforced by `SeqEnforcer`
(lines 175–244): `operator()` returns false when the offered sequence
is less than or equal to the largest sequence seen from that validator
(lines 211–231), except that the stored sequence resets to 0 when more
than `validationSET_EXPIRES` (10 minutes) has passed.

[FAKTA] When the invariant fails and the new validation is for the same
sequence as the one tracked, `Validations::add()` checks it closely
(lines 1208–1248), in this order:

1. Different ledger ID for the same sequence → `conflicting` (lines
   1219–1221). The comment (lines 1212–1216) says this "could be the
   result of misconfiguration but it can also mean a Byzantine
   validator."
2. Same ledger, different signing time → `conflicting` (lines
   1232–1234), with the same comment (lines 1223–1229).
3. Same sequence and ledger, different cookie → `multiple` (lines
   1241–1243). The comment (lines 1236–1238) says this is "probably
   accidental misconfiguration."
4. Otherwise → `badSeq` (line 1248).

[FAKTA] A tracked entry is replaced when the sign-time difference
exceeds `validationCURRENT_WALL` (5 minutes) and the new validation's
sign time is later (lines 1188–1192). The detector therefore forgets
old duplicates and only compares validations signed within 5 minutes
of each other.

[ANALISIS] Two consequences follow for any slashing design. First, the
detector distinguishes *equivocation* (cases 1–2, different ledger or
different sign time) from *duplication* (case 3, same ledger, different
cookie) — and only the first two are candidate slashable offenses; the
third is explicitly treated as probable misconfiguration. Second, the
detector only fires on the *second* validation for a sequence: a
validator that persistently validates a different ledger, one
validation per sequence, never triggers it. Persistent divergence is a
different signal and needs its own rule (R7 in this pack).

## 5. What happens after detection

[FAKTA] `handleNewValidation` (RCLValidations.cpp, lines 304–513)
marks trust from the validator list: a signing key is trusted if it is
in the UNL (`app.validators().getTrustedKey(signingKey)`) and listed if
it is on a validator list (`getListedKey`) (lines 329–341). Only
validations that are `current` and trusted have their vote recorded
(lines 362–410).

[FAKTA] The two detector outcomes are logged as: `conflicting` →
"Byzantine Behavior Detector:... Conflicting validation for {seq}!"
(lines 490–498); `multiple` → "Byzantine Behavior Detector:...
Multiple validations for {seq}/{hash}!" (lines 501–509).

[ANALISIS] Detection is therefore local and informational: each node
logs and relays the offending validation, but no node removes the
validator, reduces its standing, or records a penalty. A slashing
design must add three things postfiatd lacks: an evidence-gossip and
aggregation step (so one node's observation becomes network knowledge),
a decision rule (how much evidence, from whom, within what age), and a
penalty execution step. Section 10 proposes the evidence format; the
other two are design decisions, not source facts.

## 6. Quorum, UNL, and the 67% rule

[FAKTA] A ledger is considered fully validated once the number of
received trusted validations meets or exceeds a quorum value
(`src/xrpld/app/misc/ValidatorList.h`, comment lines 492–496). The
trusted-list size is 125% of quorum when multiple lists are configured
(line 170). The quorum itself is recomputed every round by
`updateTrusted` (`src/xrpld/app/misc/detail/ValidatorList.cpp`, line
4002: `quorum_ = calculateQuorum(unlSize, effectiveUnlSize, seenSize)`).

[FAKTA] `calculateQuorum` (ValidatorList.cpp, lines 3491–3669) uses a
67% quorum: "Use a 67% quorum to balance fork safety, liveness, and
required UNL overlap. Note: Original XRPL uses 80%, but this fork uses
67% for devnet/testnet. For mainnet, this should be reverted to 80%."
(lines 3595–3599, citing Theorem 8 of arXiv 1802.07242, Analysis of
the XRP Ledger Consensus Protocol). The formula (lines 3665–3667) is
`max(ceil(effectiveUnlSize * 0.67), ceil(unlSize * 0.6))`, where the
0.6 floor is the Negative UNL AbsoluteMinimumQuorum. A command-line
`minimumQuorum_` overrides it, with a "potentially unsafe" warning
(lines 3501–3514); if too many publishers are unavailable, quorum is
disabled (`SIZE_MAX`, lines 3588–3590).

[FAKTA] The consensus-layer constant agrees: `minCONSENSUS_PCT` = 67
(`src/xrpld/consensus/ConsensusParms.h`, line 139).

[ESTIMASI] For the modelled 53-validator set used by this pack,
quorum = max(ceil(53 × 0.67), ceil(53 × 0.6)) = max(36, 32) = **36**.
The 53-validator size is a model parameter chosen for this pack; it is
not a live measurement of the network in this session.

[ANALISIS] The 67% quorum is what makes the misbehavior scenarios in
this pack survivable: with 36 of 53 validations required, up to 17
validators can misbehave or go offline before a ledger fails to
validate. All six scenarios keep at least 50 validators on the
majority hash, so quorum holds on every ledger in every run (see
`detection-table.md`). A slashing design must reckon with the other
direction too: if slashing removes validators faster than the UNL
adapts, quorum itself is at risk — which is why the modelled penalties
in section 12 jail liveness offenders temporarily but only tombstone
equivocators, and why no modelled penalty removes a validator
instantly on a single late or divergent validation.

## 7. Timing parameters and staleness

[FAKTA] `ValidationParms` (`src/xrpld/consensus/Validations.h`, lines
82–161) sets: `validationCURRENT_WALL` = 5 minutes (line 100),
`validationCURRENT_LOCAL` = 3 minutes (line 114),
`validationCURRENT_EARLY` = 3 minutes (line 126),
`validationSET_EXPIRES` = 10 minutes (line 140), and
`validationFRESHNESS` = 20 seconds (line 159). The freshness comment
(lines 142–155) says 20 seconds should be "sufficiently higher than
ledgerMAX_CONSENSUS such that validators who are waiting for laggards
are not considered offline."

[FAKTA] `isCurrent` (lines 267–302) requires the sign time to be after
(now − 3 minutes) and before (now + 5 minutes), and the seen time to
be before (now + 3 minutes).

[FAKTA] The consensus parameters (`src/xrpld/consensus/ConsensusParms.h`)
set `validationVALID_WALL` 5 minutes (line 91), `validationVALID_LOCAL`
3 minutes (line 105), `validationVALID_EARLY` 3 minutes (line 117),
`proposeFRESHNESS` 20 seconds (line 122), `proposeINTERVAL` 12 seconds
(line 127), `ledgerMIN_CONSENSUS` 1950 ms (lines 151–153),
`ledgerMAX_CONSENSUS` 15 seconds (lines 168–170), `ledgerMIN_CLOSE` 2
seconds (line 175), `ledgerGRANULARITY` 1 second (line 180),
`ledgerABANDON_CONSENSUS_FACTOR` 10 (line 185),
`ledgerABANDON_CONSENSUS` 120 seconds (lines 200–202), and
`avMIN_CONSENSUS_TIME` 5 seconds (lines 224–226). Avalanche cutoffs
(lines 269–283) are 50% initially, 65% after 50% of the time, 70%
after 85% of the time, and 95% after 200% of the time;
`avCT_CONSENSUS_PCT` = 75 (line 290), `avMIN_ROUNDS` = 2 (line 299),
`avSTALLED_ROUNDS` = 4 (line 306).

[ANALISIS] The 20-second freshness value is the natural threshold for
a "late validation" warning: a validation signed more than 20 seconds
after its ledger's close time no longer represents the validator's most
recent view, but it is still current for 5 minutes, so lateness is a
performance signal, not an offense. The simulator's R6 uses exactly
this 20-second threshold, and R4 uses the 3-minute early / 5-minute
wall bounds.

## 8. Liveness machinery

[FAKTA] `RCLConsensus` exposes `laggards(seq, trustedKeys)` (lines
155–156), `getQuorumKeys()` (line 152),
`proposersValidated(h)` (line 245), and
`proposersFinished(...)` (line 256) in
`src/xrpld/app/consensus/RCLConsensus.h`, and `validate(ledger, txns,
proposing)` (lines 414–417). `censorshipWarnInternal` = 15 (line 56):
a transaction proposed 15 times without acceptance triggers a
censorship warning.

[FAKTA] `RCLCensorshipDetector` (`src/xrpld/app/consensus/RCLCensorshipDetector.h`)
tracks proposed transactions with their round sequence (`propose()`,
lines 82–97) and removes accepted ones (`check(accepted, pred)`,
lines 114–131): censorship is a transaction proposed repeatedly but
never accepted.

[FAKTA] The Negative UNL lets servers adjust their effective UNL by
excluding validators believed offline or malfunctioning
(`ValidatorList.h`, lines 705–728). XRPL's documentation states the
same mechanism and adds that each server tracks a validator by the
percentage of the last 256 ledgers where its vote matched consensus
(xrpl.org, Negative UNL, accessed 2026-11-17).

[ANALISIS] postfiatd already has the *measurement* side of liveness:
which validators are lagging, which are missing, and which can be
excluded from the effective UNL. What it lacks is a *penalty* side:
exclusion from the effective UNL is temporary and reputation-free, and
nothing burns stake or bars re-entry. The simulator's R5 models the
penalty-side trigger (missed validations over a sliding window) while
the framework keeps the two sides distinct: measurement is sourced,
penalty is modelled.

## 9. Reference designs (not PFTL rules)

Everything in this section describes other networks. It is included so
a PFTL slashing design can be compared against proven designs; no
statement here is a claim about postfiatd.

### 9.1 Cosmos SDK slashing

[FAKTA] The Cosmos SDK `x/slashing` module penalizes two infraction
classes: double-signing (equivocation) and downtime (liveness)
(Cosmos SDK docs, `x/slashing`, accessed 2026-11-17; page updated
2026-08-04). Double-signing slashes by `SlashFractionDoubleSign` and
tombstones the validator (permanent jail, `JailedUntil = MAX_TIME`,
cannot unjail). A tombstone cap allows a validator to be slashed only
once per double-sign fault, so a misconfigured key that double-signs
many blocks is punished for the first fault only. Liveness slashes do
NOT tombstone.

[FAKTA] Liveness tracking uses a sliding window: `maxMissed` =
`SignedBlocksWindow` − (`MinSignedPerWindow` × `SignedBlocksWindow`).
If the current block is past the minimum height and a validator's
`MissedBlocksCounter` exceeds `maxMissed`, it is slashed by
`SlashFractionDowntime`, jailed for `DowntimeJailDuration`, and its
counters reset. The module's example parameters are:
`SignedBlocksWindow` 100, `MinSignedPerWindow` 0.5,
`DowntimeJailDuration` 600,000,000,000 ns (600 seconds),
`SlashFractionDoubleSign` 0.05 (5%), `SlashFractionDowntime` 0.01
(1%).

[FAKTA] Evidence reaches the state machine through CometBFT: an
equivocation is valid only if `Evidence.Timestamp >= block.Timestamp
− MaxEvidenceAge`, and the slash applies to the stake at infraction
time, not discovery time.

### 9.2 CometBFT evidence handling

[FAKTA] CometBFT's evidence system detects and gossips Byzantine
faults (CometBFT evidence spec, accessed 2026-11-17; updated
2026-10-30). Valid `DuplicateVoteEvidence` requires: the same
validator address, height, round, and vote type for both votes;
different BlockIDs; the validator in the validator set at that height;
and correctly signed votes (the chain ID binds the fault to the
chain). Evidence is valid only once (uniqueness) and only within a
period from the fault (timeliness), defined by `EvidenceParams`
`MaxAgeNumBlocks` and `MaxAgeDuration`: if `CurrentHeight −
MaxAgeNumBlocks > EvidenceHeight` AND `CurrentTime − MaxAgeDuration >
EvidenceTime`, the evidence is expired and ignored. Evidence takes
strict priority over regular transactions in a block, and its size per
block is capped by `EvidenceParams.MaxBytes`.

### 9.3 Ethereum Casper FFG slashing conditions

[FAKTA] Ethereum's consensus layer defines two slashable attestation
contradictions in `is_slashable_attestation_data` (Vitalik Buterin,
annotated Ethereum 2.0 spec, accessed 2026-11-17): a **double vote**
(two different attestations with the same target epoch) and a
**surround vote** (`data_1.source.epoch < data_2.source.epoch` and
`data_2.target.epoch < data_1.target.epoch`). A third condition is
**proposer equivocation**: signing two different blocks for the same
slot. A slashed validator loses at least 1/32 of its effective
balance immediately, plus a correlation penalty proportional to how
many other validators were slashed around the same time, and is then
force-exited over several weeks.

### 9.4 XRPL contrast

[FAKTA] XRPL's standard quorum is 80% of trusted validators, and the
Negative UNL keeps quorum at at least 80% of the effective UNL and at
least 60% of the configured UNL (xrpl.org, Negative UNL, accessed
2026-11-17). As of 2024-06-25 there were 35 validators on the default
UNLs, so the network would stop making progress if 8 or more went
offline. XRPL has no staking and no slashing.

[ANALISIS] The contrast matters: PFTL's 67% quorum (section 6) is
more liveness-friendly than XRPL's 80% but tolerates less collusion,
and a PFTL slashing design cannot copy Cosmos or Ethereum penalties
directly because PFTL has no staking module in postfiatd at the pinned
commit — there is no stake to slash. Any PFTL penalty would need a
staking or bond mechanism first, or would have to be expressed as
exclusion (UNL removal, Negative UNL listing) rather than a burn.

## 10. Proposed evidence format

[ANALISIS] The following format is a proposal modelled on the sources
above, not a description of any existing PFTL format. An equivocation
evidence package must contain, at minimum:

1. The validator's identity: node ID and signing key (the fields in
   section 3).
2. Both conflicting validations in full: ledger sequence, ledger hash,
   signing time, cookie, load fee, and signing hash for each — the
   pair that `Validations::add()` would classify `conflicting`.
3. The detector's classification: which branch fired (different ledger
   ID, or same ledger with different sign time), with the source lines
   cited (section 4).
4. An age bound: the evidence's ledger sequence and the sequence at
   which it was submitted, so an expiry rule in the style of CometBFT's
   `MaxAgeNumBlocks` / `MaxAgeDuration` can be applied.
5. A uniqueness guard: the signing-hash pair must not have been used
   in an earlier penalty, in the style of the Cosmos tombstone cap.

[ANALISIS] A liveness evidence package must contain: the validator's
identity, the sliding-window parameters used, the list of missed
ledger sequences inside the window, and the threshold crossed. The
simulator's R5 events carry exactly this: the missed ledger list is
in the event's evidence field.

[ANALISIS] A divergence evidence package must contain: the validator's
identity, the run of consecutive ledgers where its validation
disagreed with the preferred ledger, and the preferred ledger's hash
and support count per ledger — so a reviewer can tell a fork-support
run from a one-off stale view. The simulator's R7 events carry the
three disagreeing validations as evidence.

## 11. Detector rules R1–R7 (simulator)

[FAKTA] The simulator implements seven numbered rules. Thresholds are
taken from the sources in sections 4, 6, and 7, except where marked as
model choices:

- **R1 CONFLICTING** — same validator, same ledger sequence, two
  validations with different ledger hashes. Mirrors
  `Validations.h` lines 1219–1221. Slashable in the model.
- **R2 MULTIPLE** — same validator, same ledger sequence, same ledger
  hash, different cookie. Mirrors `Validations.h` lines 1241–1243.
  Not slashable in the model (probable misconfiguration).
- **R3 BADSEQ** — validation sequence not greater than the largest
  sequence previously accepted from the same validator. Mirrors
  `SeqEnforcer` (`Validations.h` lines 211–231) and the `badSeq`
  branch (line 1248). Validation dropped, no penalty in the model.
- **R4 STALE** — primary sign time more than 180 seconds before or
  more than 300 seconds after the ledger close time. Mirrors
  `validationCURRENT_EARLY` (3 minutes) and `validationCURRENT_WALL`
  (5 minutes) (`Validations.h` lines 100, 126). Validation dropped,
  no penalty in the model.
- **R5 LIVENESS** — more than 10 missed validations inside any
  trailing window of 20 ledgers (signed below 50% of the window).
  Modelled on the Cosmos rule (`maxMissed` = window − min-signed ×
  window, section 9.1) with the window scaled to the 120-ledger run.
  Fires once per fault episode and re-arms only when the trailing
  window drops back to or below the threshold.
- **R6 LATE** — primary sign time more than 20 seconds after the
  ledger close time. Mirrors `validationFRESHNESS` (20 seconds)
  (`Validations.h` line 159). Warning only, no penalty in the model.
- **R7 DIVERGENT** — the validator's primary validation disagrees with
  the preferred (majority) ledger hash for 3 or more consecutive
  ledgers. Model choice: the 3-ledger threshold is arbitrary and is
  stated as such; it exists to separate a persistent fork-support run
  from a one- or two-ledger stale view. Warning plus investigation,
  not slashable in the model.

[FAKTA] The detector evaluates only the validator's *first* (earliest-
signed) validation per sequence for R4–R7. Extra validations for the
same sequence are handled by R1/R2 only, so an equivocating validator
is never also flagged divergent for its own second validation. The
preferred ledger per sequence is the majority hash among first
validations; majority ties break toward the smallest hash.

## 12. Penalty calibration (model parameters, not a PFTL rule)

[ANALISIS] The table below is a calibration proposal. postfiatd has no
slashing mechanism (section 2) and no staking module at the pinned
commit, so these numbers are model parameters for discussion, not
network rules. The reference column shows where each number is
borrowed from; the model column is the choice made for this pack.

| Offense | Rule | Modelled slash (share of stake) | Modelled jail | Tombstone | Reference |
|---|---|---|---|---|---|
| Equivocation (conflicting) | R1 | 5% | none (permanent exclusion instead) | yes | Cosmos `SlashFractionDoubleSign` 0.05 |
| Multiple (same ledger, different cookie) | R2 | 0% | none | no | postfiatd treats as probable misconfiguration (`Validations.h` lines 1236–1238) |
| Bad sequence | R3 | 0% | none | no | validation dropped |
| Stale | R4 | 0% | none | no | validation dropped |
| Liveness fault | R5 | 1% | 600 s | no | Cosmos `SlashFractionDowntime` 0.01, `DowntimeJailDuration` 600 s |
| Late validation | R6 | 0% | none | no | warning only |
| Persistent divergence | R7 | 0% | none | no | warning plus investigation; not slashable alone |

[ANALISIS] The calibration is deliberately asymmetric: equivocation is
the only offense that ends a validator's career in the model, because
it is the only offense that is cryptographic proof of contradiction
(two signed statements that cannot both be honest). Everything else is
either a likely accident (R2), a dropped message (R3, R4), a
performance signal (R6), or a signal that needs human investigation
before any penalty (R5, R7). The 1% liveness slash is small on purpose:
in a 53-validator set with a 36-validator quorum, jailing several
validators at once for a shared outage (for example a datacenter
failure) must not itself break quorum.

## 13. Assumptions, limitations, and what was not verified

[ANALISIS] Assumptions built into the simulator:

- All 53 validators are trusted and in the UNL, with equal weight.
  Real UNLs weight by trust, not equally, and the effective UNL
  changes as validators go offline (Negative UNL).
- Ledger close time is a fixed 4 seconds per ledger. Real close times
  vary (see `ledgerMIN_CLOSE` 2 seconds, section 7).
- Honest validators sign 0–2 seconds after close; late validators
  sign 25–45 seconds after close. These delays are model choices.
- An injected second validation for the same sequence is always
  signed after the first. A real equivocator could sign in any order;
  the detector's primary selection (earliest-signed) would then pick
  whichever came first, but R1 still fires because it compares hashes,
  not order.
- The R5 window (20 ledgers) and the R7 threshold (3 consecutive
  ledgers) are model choices scaled to a 120-ledger run, not sourced
  values. The Cosmos reference window is 100 blocks; the R7 threshold
  has no reference at all.
- The R5 rule stays armed until the trailing window clears: a
  validator that returns after a 30-ledger outage is not eligible for
  a second liveness event until the window no longer contains more
  than 10 misses (9 ledgers after its return in the modelled
  scenario). This mirrors the Cosmos property that a validator cannot
  commit a second liveness fault until it unjails, but the exact
  re-arm timing is a property of the window, not a sourced rule.

[ANALISIS] Limitations of the measured results:

- The detector is tested only against the injected offenses in
  `scenarios.json`. It has not been tested against adversarial
  orderings (for example a second validation signed *before* the
  first), clock skew beyond the modelled delays, or a validator that
  equivocates on a minority fork that later becomes preferred.
- Precision and recall are 1.0000 in every scenario because the
  injected offenses are clean and the thresholds are set to match
  them. Real traffic would be messier; these numbers measure the
  detector against its own specification, not against the live
  network.
- The benign-divergence scenario (2 ledgers) and the conflicting-set
  scenario (30 ledgers) differ only in duration. The 3-ledger R7
  threshold is what separates them; a 2-ledger fork-support run and a
  3-ledger stale view would be classified by duration alone, which is
  a weak discriminator and is flagged here as a limitation, not a
  strength.

[FAKTA] What was not verified live in this session:

- The `STValidation` declaration file lives at `include/xrpl/protocol/STValidation.h`, not `src/xrpl/protocol/STValidation.h` (section 3).
- The 53-validator testnet size is a model parameter, not a live
  measurement taken in this session.
- No live PFTL network observation was made; all detection numbers are
  simulated.

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

Reference sources (accessed 2026-11-17):

- Cosmos SDK `x/slashing` module —
  https://docs.cosmos.network/sdk/latest/modules/slashing/README
  (page updated 2026-08-04)
- CometBFT evidence specification —
  https://docs.cosmos.network/cometbft/latest/spec/consensus/Evidence
  (page updated 2026-10-30)
- Vitalik Buterin, annotated Ethereum 2.0 specification (Casper FFG
  slashing conditions) —
  https://notes.ethereum.org/@vbuterin/Sys3GLJbD
- XRPL Negative UNL —
  https://xrpl.org/docs/concepts/consensus-protocol/negative-unl
- XRPL consensus introduction —
  https://learn.xrpl.org/course/intro-to-the-xrpl/lesson/how-the-xrp-ledger-works/
