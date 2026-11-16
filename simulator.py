"""Deterministic validator misbehavior trace simulator (simulated data only).

Generates validation traces for a modelled 53-validator set over 120 ledgers,
then runs an explicit, numbered detector (rules R1-R7) over them.

Everything in this file is simulated. Nothing here measures the live network:
the traces are synthetic, built from the scenario configuration, and the
detector rules are a model of the postfiatd Byzantine detector described in
framework.md, not the postfiatd code itself.

Determinism rules (do not weaken them):
  - All randomness comes from random.Random(seed) instances. No global RNG.
  - All hashes come from hashlib.sha256 over fixed strings. No hash().
  - Every iteration that feeds output is sorted. No set iteration feeds output.
  - An injected second validation for the same sequence is always signed
    after the first validation for that sequence, so the detector's primary
    (earliest-signed validation per validator per sequence) is always the
    validator's first validation. The detector checks R1/R2 on the extra
    validations, R4/R6 on the primary only, and R5/R7 on primaries only.

Detector rules (thresholds match scenarios.json exactly):
  - R1 CONFLICTING: same validator, same sequence, two validations with
    different ledger hashes.
  - R2 MULTIPLE: same validator, same sequence, same ledger hash, different
    cookie.
  - R3 BADSEQ: validation sequence not greater than the largest sequence
    previously accepted from the same validator (and not already R1/R2).
  - R4 STALE: primary sign time more than 180 s before or more than 300 s
    after the ledger close time.
  - R5 LIVENESS: more than 10 missed validations inside any trailing window
    of 20 ledgers (signed below 50% of the window). Fires once per fault
    episode and re-arms only when the trailing window drops back to or
    below the threshold, so a validator that returns stays flagged until
    the window clears.
  - R6 LATE: primary sign time more than 20 s after the ledger close time.
  - R7 DIVERGENT: the validator's primary validation disagrees with the
    preferred (majority) ledger hash for 3 or more consecutive ledgers.
"""

import hashlib
import json
import random

VALIDATOR_COUNT = 53
LEDGERS_PER_RUN = 120
LEDGER_CLOSE_SECONDS = 4
QUORUM = 36  # max(ceil(53 * 0.67), ceil(53 * 0.6)) = 36

FRESHNESS_SECONDS = 20
STALE_EARLY_SECONDS = 180
STALE_WALL_SECONDS = 300
LIVENESS_WINDOW = 20
LIVENESS_MAX_MISSED = 10
DIVERGENT_CONSECUTIVE = 3


def validator_id(index):
    """Validator label, V000 to V052."""
    return "V%03d" % index


def ledger_hash(seed, seq, branch):
    """Deterministic 64-hex ledger identifier for a seed, sequence, branch."""
    text = "seed:%d:ledger:%d:branch:%s" % (seed, seq, branch)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def signing_hash(validator, seq, ledger_id, sign_time, cookie):
    """Deterministic 64-hex signing hash for one validation."""
    text = "val:%s:seq:%d:hash:%s:time:%d:cookie:%d" % (
        validator,
        seq,
        ledger_id,
        sign_time,
        cookie,
    )
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def cookie_for(seed, validator, seq):
    """Deterministic cookie for one validation (32-bit, from SHA-256)."""
    text = "seed:%d:cookie:%s:%d" % (seed, validator, seq)
    return int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:8], 16)


def make_validation(seed, validator, seq, ledger_id, sign_time, cookie):
    """One validation record with every field an evidence check needs."""
    return {
        "validator": validator,
        "seq": seq,
        "ledger_hash": ledger_id,
        "sign_time": sign_time,
        "seen_time": sign_time,
        "cookie": cookie,
        "full": True,
        "trusted": True,
        "signing_hash": signing_hash(
            validator, seq, ledger_id, sign_time, cookie
        ),
    }


def validation_ref(validation):
    """Evidence reference for one validation (full hashes, no truncation)."""
    return {
        "validator": validation["validator"],
        "seq": validation["seq"],
        "ledger_hash": validation["ledger_hash"],
        "sign_time": validation["sign_time"],
        "cookie": validation["cookie"],
        "signing_hash": validation["signing_hash"],
    }


def generate_trace(scenario, seed, config):
    """Generate one synthetic trace.

    Returns (validations, ground_truth). validations is a list of validation
    records sorted by (validator, seq, sign_time, ledger_hash, cookie).
    ground_truth is the scenario's ground-truth event list, copied verbatim
    from the scenario configuration.
    """
    model = config["model"]
    offenders = scenario.get("offenders", {})
    rng = random.Random(seed)
    close_seconds = model["ledger_close_seconds"]
    validations = []

    equiv = offenders.get("equivocation", {})
    equiv_validators = set(equiv.get("validators", []))
    equiv_ledgers = set(equiv.get("ledgers", []))
    multi = offenders.get("multiple_cookie", {})
    multi_validators = set(multi.get("validators", []))
    multi_ledgers = set(multi.get("ledgers", []))
    divergent = offenders.get("divergent_set", {})
    divergent_validators = set(divergent.get("validators", []))
    divergent_ledgers = set(divergent.get("ledgers", []))
    benign = offenders.get("benign_divergent", {})
    benign_validators = set(benign.get("validators", []))
    benign_ledgers = set(benign.get("ledgers", []))
    offline = offenders.get("offline", {})
    offline_validators = set(offline.get("validators", []))
    offline_ledgers = set(offline.get("ledgers", []))
    late = offenders.get("late", {})
    late_validators = set(late.get("validators", []))
    late_ledgers = set(late.get("ledgers", []))
    late_low, late_high = late.get("delay_seconds", [25, 45])

    for index in range(model["validator_count"]):
        validator = validator_id(index)
        for seq in range(1, model["ledgers_per_run"] + 1):
            close_time = seq * close_seconds
            if validator in offline_validators and seq in offline_ledgers:
                continue
            if validator in divergent_validators and seq in divergent_ledgers:
                branch = "fork"
            elif validator in benign_validators and seq in benign_ledgers:
                branch = "fork"
            else:
                branch = "main"
            ledger_id = ledger_hash(seed, seq, branch)
            if validator in late_validators and seq in late_ledgers:
                delay = rng.randint(late_low, late_high)
            else:
                delay = rng.randint(0, 2)
            sign_time = close_time + delay
            cookie = cookie_for(seed, validator, seq)
            primary = make_validation(
                seed, validator, seq, ledger_id, sign_time, cookie
            )
            validations.append(primary)
            if validator in equiv_validators and seq in equiv_ledgers:
                fork_id = ledger_hash(seed, seq, "fork")
                extra_delay = delay + rng.randint(1, 3)
                extra = make_validation(
                    seed,
                    validator,
                    seq,
                    fork_id,
                    close_time + extra_delay,
                    cookie,
                )
                validations.append(extra)
            if validator in multi_validators and seq in multi_ledgers:
                dup_delay = delay + rng.randint(1, 2)
                duplicate = make_validation(
                    seed,
                    validator,
                    seq,
                    ledger_id,
                    close_time + dup_delay,
                    cookie + 1,
                )
                validations.append(duplicate)

    validations.sort(
        key=lambda v: (
            v["validator"],
            v["seq"],
            v["sign_time"],
            v["ledger_hash"],
            v["cookie"],
        )
    )
    ground_truth = sorted(
        scenario.get("ground_truth_events", []),
        key=lambda e: (e["ledger_seq"], e["validator"], e["rule"]),
    )
    return validations, ground_truth


def _majority_hashes(validations, validator_count, ledgers):
    """Preferred (majority) ledger hash per sequence, from primaries only.

    The primary is the earliest-signed validation per validator per sequence.
    Ties in the majority count break toward the smallest hash, so the result
    is deterministic.
    """
    primaries = {}
    for validation in validations:
        key = (validation["validator"], validation["seq"])
        if key not in primaries:
            primaries[key] = validation
    majority = {}
    for seq in range(1, ledgers + 1):
        counts = {}
        for index in range(validator_count):
            validation = primaries.get((validator_id(index), seq))
            if validation is None:
                continue
            ledger_id = validation["ledger_hash"]
            counts[ledger_id] = counts.get(ledger_id, 0) + 1
        best_hash = None
        best_count = -1
        for ledger_id in sorted(counts):
            if counts[ledger_id] > best_count:
                best_count = counts[ledger_id]
                best_hash = ledger_id
        majority[seq] = (best_hash, best_count)
    return majority, primaries


def detect(validations, config):
    """Run detector rules R1-R7 over one trace.

    Returns (events, quorum_min). events is a list of detection events sorted
    by (ledger_seq, validator, rule). quorum_min is the smallest number of
    primary validations supporting the majority hash on any ledger.
    """
    model = config["model"]
    detector = config["detector"]
    validator_count = model["validator_count"]
    ledgers = model["ledgers_per_run"]
    close_seconds = model["ledger_close_seconds"]
    freshness = detector["freshness_seconds"]
    stale_early = detector["stale_early_seconds"]
    stale_wall = detector["stale_wall_seconds"]
    live_window = detector["liveness_window_ledgers"]
    live_max_missed = detector["liveness_max_missed"]
    divergent_needed = detector["divergent_consecutive_ledgers"]

    majority, primaries = _majority_hashes(
        validations, validator_count, ledgers
    )
    quorum_min = min(count for _, count in majority.values())

    by_validator_seq = {}
    for validation in validations:
        key = (validation["validator"], validation["seq"])
        by_validator_seq.setdefault(key, []).append(validation)

    events = []
    last_accepted = {}
    stored_primary = {}

    for key in sorted(by_validator_seq):
        validator, seq = key
        group = sorted(
            by_validator_seq[key],
            key=lambda v: (
                v["sign_time"],
                v["ledger_hash"],
                v["cookie"],
                v["signing_hash"],
            ),
        )
        close_time = seq * close_seconds
        accepted = last_accepted.get(validator, 0)
        if seq < accepted:
            for validation in group:
                events.append(
                    {
                        "ledger_seq": seq,
                        "validator": validator,
                        "rule": "R3",
                        "offense": "BADSEQ",
                        "evidence": [validation_ref(validation)],
                    }
                )
            continue
        if seq == accepted:
            primary = stored_primary[(validator, seq)]
            _check_extra(
                events, validator, seq, primary, group
            )
            continue
        primary = group[0]
        last_accepted[validator] = seq
        stored_primary[(validator, seq)] = primary
        if (
            primary["sign_time"] < close_time - stale_early
            or primary["sign_time"] > close_time + stale_wall
        ):
            events.append(
                {
                    "ledger_seq": seq,
                    "validator": validator,
                    "rule": "R4",
                    "offense": "STALE",
                    "evidence": [validation_ref(primary)],
                }
            )
        if primary["sign_time"] - close_time > freshness:
            events.append(
                {
                    "ledger_seq": seq,
                    "validator": validator,
                    "rule": "R6",
                    "offense": "LATE",
                    "evidence": [validation_ref(primary)],
                }
            )
        _check_extra(events, validator, seq, primary, group[1:])

    # R5 liveness: trailing window of live_window ledgers, missed > max.
    for index in range(validator_count):
        validator = validator_id(index)
        signed = set()
        for seq in range(1, ledgers + 1):
            if (validator, seq) in primaries:
                signed.add(seq)
        fired = False
        for end in range(1, ledgers + 1):
            start = max(1, end - live_window + 1)
            missed = [
                seq
                for seq in range(start, end + 1)
                if seq not in signed
            ]
            if len(missed) > live_max_missed:
                if not fired:
                    events.append(
                        {
                            "ledger_seq": end,
                            "validator": validator,
                            "rule": "R5",
                            "offense": "LIVENESS",
                            "evidence": [
                                {"ledger_seq": seq, "validator": validator}
                                for seq in missed
                            ],
                        }
                    )
                    fired = True
            else:
                fired = False

    # R7 divergent: primary disagrees with the majority hash for
    # divergent_needed or more consecutive ledgers.
    for index in range(validator_count):
        validator = validator_id(index)
        run = []
        for seq in range(1, ledgers + 1):
            primary = primaries.get((validator, seq))
            preferred = majority[seq][0]
            if primary is not None and primary["ledger_hash"] != preferred:
                run.append(seq)
                if len(run) == divergent_needed:
                    events.append(
                        {
                            "ledger_seq": seq,
                            "validator": validator,
                            "rule": "R7",
                            "offense": "DIVERGENT",
                            "evidence": [
                                validation_ref(primaries[(validator, s)])
                                for s in run
                            ],
                        }
                    )
            else:
                run = []

    events.sort(
        key=lambda e: (e["ledger_seq"], e["validator"], e["rule"])
    )
    return events, quorum_min


def _check_extra(events, validator, seq, primary, extras):
    """R1/R2 checks for extra validations of an already-seen sequence."""
    conflicting = None
    multiple = None
    for extra in extras:
        if extra["ledger_hash"] != primary["ledger_hash"]:
            if conflicting is None:
                conflicting = extra
        elif extra["cookie"] != primary["cookie"]:
            if multiple is None:
                multiple = extra
    if conflicting is not None:
        events.append(
            {
                "ledger_seq": seq,
                "validator": validator,
                "rule": "R1",
                "offense": "CONFLICTING",
                "evidence": [
                    validation_ref(primary),
                    validation_ref(conflicting),
                ],
            }
        )
    if multiple is not None:
        events.append(
            {
                "ledger_seq": seq,
                "validator": validator,
                "rule": "R2",
                "offense": "MULTIPLE",
                "evidence": [
                    validation_ref(primary),
                    validation_ref(multiple),
                ],
            }
        )


def event_key(event):
    """Matching key for one detection or ground-truth event."""
    return (event["validator"], event["ledger_seq"], event["rule"])


def score(events, ground_truth, opportunities):
    """Score detections against ground truth.

    Events are counted with multiplicity: the same (validator, ledger, rule)
    key occurring in several pooled seeds counts once per seed, so pooled
    totals are sums over seeds, not counts of distinct keys.
    opportunities is the number of validator-ledger pairs checked in the
    pooled runs. Non-offense opportunities are opportunities minus the
    pooled ground-truth event count. Precision and recall are defined as
    1.0 when their denominator is 0 (no detections and no ground truth
    means nothing was missed and nothing was falsely flagged).
    """
    from collections import Counter

    detected = Counter(event_key(e) for e in events)
    truth = Counter(event_key(e) for e in ground_truth)
    tp = 0
    fp = 0
    fn = 0
    for key in sorted(set(detected) | set(truth)):
        tp += min(detected[key], truth[key])
        fp += max(0, detected[key] - truth[key])
        fn += max(0, truth[key] - detected[key])
    truth_total = sum(truth.values())
    non_offense = opportunities - truth_total
    tn = non_offense - fp
    precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 1.0
    fpr = fp / non_offense if non_offense > 0 else 0.0
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "fpr": round(fpr, 4),
    }


def load_config(path):
    """Load scenarios.json (plain JSON, no comments)."""
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def canonical_json(data):
    """Canonical JSON: sorted keys, 2-space indent, trailing newline."""
    return json.dumps(data, sort_keys=True, indent=2) + "\n"
