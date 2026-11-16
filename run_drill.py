"""One-command drill for the validator misbehavior evidence pack.

Runs every scenario over all configured seeds, scores the detector against
ground truth, writes the canonical results file and the per-event logs for
the first seed, and prints a fixed-format report to stdout.

Usage (from the directory holding this file):
    python3 run_drill.py

Exit code 0 only if every check passes. The report contains no timestamps
and no filesystem paths, so repeated runs produce byte-identical output.
All results in this drill are simulated.
"""

import hashlib
import json
import os
import sys

import simulator

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(HERE, "scenarios.json")
RESULTS_PATH = os.path.join(HERE, "results.json")
LOGS_DIR = os.path.join(HERE, "logs")
FIRST_SEED_INDEX = 0
RULES = ["R1", "R2", "R3", "R4", "R5", "R6", "R7"]


def sha256_hex(data):
    """Full 64-hex SHA-256 of bytes."""
    return hashlib.sha256(data).hexdigest()


def rule_counts(events):
    """Count detections per rule, with every rule present (zero if absent)."""
    counts = {rule: 0 for rule in RULES}
    for event in events:
        counts[event["rule"]] += 1
    return counts


def main():
    config = simulator.load_config(CONFIG_PATH)
    model = config["model"]
    seeds = model["seeds"]
    scenarios = config["scenarios"]
    opportunities_per_seed = (
        model["validator_count"] * model["ledgers_per_run"]
    )

    per_scenario = {}
    quorum_min_overall = None
    all_events_seed1 = {}
    checks = []

    for scenario in scenarios:
        name = scenario["name"]
        pooled_events = []
        pooled_truth = []
        per_seed_rows = []
        validations_total = 0
        scenario_quorum_min = None
        for seed in seeds:
            validations, truth = simulator.generate_trace(
                scenario, seed, config
            )
            events, quorum_min = simulator.detect(validations, config)
            validations_total += len(validations)
            if scenario_quorum_min is None or quorum_min < scenario_quorum_min:
                scenario_quorum_min = quorum_min
            pooled_events.extend(events)
            pooled_truth.extend(truth)
            per_seed_rows.append(
                simulator.score(
                    events, truth, opportunities_per_seed
                )
            )
            per_seed_rows[-1]["seed"] = seed
            if seed == seeds[FIRST_SEED_INDEX]:
                all_events_seed1[name] = events
        if (
            quorum_min_overall is None
            or scenario_quorum_min < quorum_min_overall
        ):
            quorum_min_overall = scenario_quorum_min
        metrics = simulator.score(
            pooled_events,
            pooled_truth,
            opportunities_per_seed * len(seeds),
        )
        per_scenario[name] = {
            "ground_truth_events_per_seed": len(
                scenario.get("ground_truth_events", [])
            ),
            "metrics_pooled": metrics,
            "per_seed": [
                {
                    "seed": row["seed"],
                    "tp": row["tp"],
                    "fp": row["fp"],
                    "fn": row["fn"],
                    "precision": row["precision"],
                    "recall": row["recall"],
                }
                for row in per_seed_rows
            ],
            "quorum_min": scenario_quorum_min,
            "rule_counts_pooled": rule_counts(pooled_events),
            "validations_pooled": validations_total,
        }

    # Determinism self-check: regenerate the first seed twice in-process
    # and compare the canonical event JSON byte for byte.
    deterministic = True
    for scenario in scenarios:
        name = scenario["name"]
        first_seed = seeds[FIRST_SEED_INDEX]
        validations_a, _ = simulator.generate_trace(
            scenario, first_seed, config
        )
        events_a, _ = simulator.detect(validations_a, config)
        validations_b, _ = simulator.generate_trace(
            scenario, first_seed, config
        )
        events_b, _ = simulator.detect(validations_b, config)
        text_a = simulator.canonical_json(events_a)
        text_b = simulator.canonical_json(events_b)
        if text_a != text_b:
            deterministic = False

    results = {
        "config": {
            "ledgers_per_run": model["ledgers_per_run"],
            "quorum": model["quorum"],
            "seeds": seeds,
            "validator_count": model["validator_count"],
        },
        "per_scenario": per_scenario,
        "quorum": {
            "holds": quorum_min_overall >= model["quorum"],
            "min_primary_validations_for_majority": quorum_min_overall,
            "quorum": model["quorum"],
        },
    }
    results_text = simulator.canonical_json(results)
    with open(RESULTS_PATH, "w", encoding="utf-8") as handle:
        handle.write(results_text)
    results_sha = sha256_hex(results_text.encode("utf-8"))

    os.makedirs(LOGS_DIR, exist_ok=True)
    events_shas = {}
    for scenario in scenarios:
        name = scenario["name"]
        filename = "events-%s-seed%d.jsonl" % (
            name,
            seeds[FIRST_SEED_INDEX],
        )
        path = os.path.join(LOGS_DIR, filename)
        lines = [
            json.dumps(event, sort_keys=True)
            for event in all_events_seed1[name]
        ]
        text = "\n".join(lines)
        if lines:
            text += "\n"
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
        events_shas[filename] = sha256_hex(text.encode("utf-8"))

    # Checks. Every check must pass for exit code 0.
    def pooled(name):
        return per_scenario[name]["metrics_pooled"]

    def check(label, passed):
        checks.append((label, passed))

    check(
        "equivocation recall 1.0000 and precision 1.0000",
        pooled("equivocation_double_sign")["recall"] == 1.0
        and pooled("equivocation_double_sign")["precision"] == 1.0,
    )
    check(
        "conflicting sets recall 1.0000 and precision 1.0000",
        pooled("conflicting_validation_sets")["recall"] == 1.0
        and pooled("conflicting_validation_sets")["precision"] == 1.0,
    )
    check(
        "conflicting sets produce zero R1 flags",
        per_scenario["conflicting_validation_sets"]["rule_counts_pooled"]["R1"]
        == 0,
    )
    check(
        "liveness recall 1.0000 and precision 1.0000",
        pooled("liveness_offline")["recall"] == 1.0
        and pooled("liveness_offline")["precision"] == 1.0,
    )
    check(
        "late recall 1.0000 and precision 1.0000",
        pooled("late_validations")["recall"] == 1.0
        and pooled("late_validations")["precision"] == 1.0,
    )
    check(
        "benign divergence false positives 0",
        pooled("benign_divergence")["fp"] == 0,
    )
    check(
        "baseline false positives 0",
        pooled("baseline_clean")["fp"] == 0,
    )
    check(
        "quorum holds on every ledger (min >= 36)",
        quorum_min_overall >= model["quorum"],
    )
    for scenario in scenarios:
        name = scenario["name"]
        counts = per_scenario[name]["rule_counts_pooled"]
        check(
            "%s has zero R3 flags" % name,
            counts["R3"] == 0,
        )
        check(
            "%s has zero R4 flags" % name,
            counts["R4"] == 0,
        )
    check(
        "determinism self-check (seed 1001 regenerated twice)",
        deterministic,
    )

    # Fixed-format report. No timestamps, no paths. Floats fixed to 4 dp.
    print("VALIDATOR MISBEHAVIOR DRILL (SIMULATED DATA)")
    print("validators: %d" % model["validator_count"])
    print("ledgers per run: %d" % model["ledgers_per_run"])
    print("seeds: %s" % ", ".join(str(s) for s in seeds))
    print("quorum: %d" % model["quorum"])
    print("")
    print("POOLED METRICS (5 seeds pooled; precision/recall/FPR as defined")
    print("in simulator.score; FPR denominator is non-offense opportunities)")
    for scenario in scenarios:
        name = scenario["name"]
        metrics = pooled(name)
        print(
            "%s: tp=%d fp=%d fn=%d tn=%d precision=%.4f recall=%.4f "
            "fpr=%.4f"
            % (
                name,
                metrics["tp"],
                metrics["fp"],
                metrics["fn"],
                metrics["tn"],
                metrics["precision"],
                metrics["recall"],
                metrics["fpr"],
            )
        )
    print("")
    print("PER-SEED METRICS (tp/fp/fn/precision/recall per seed)")
    for scenario in scenarios:
        name = scenario["name"]
        for row in per_scenario[name]["per_seed"]:
            print(
                "%s seed=%d: tp=%d fp=%d fn=%d precision=%.4f recall=%.4f"
                % (
                    name,
                    row["seed"],
                    row["tp"],
                    row["fp"],
                    row["fn"],
                    row["precision"],
                    row["recall"],
                )
            )
    print("")
    print("RULE COUNTS POOLED (detections per rule across 5 seeds)")
    for scenario in scenarios:
        name = scenario["name"]
        counts = per_scenario[name]["rule_counts_pooled"]
        print(
            "%s: %s"
            % (
                name,
                " ".join(
                    "%s=%d" % (rule, counts[rule]) for rule in RULES
                ),
            )
        )
    print("")
    print("QUORUM AND VOLUME")
    for scenario in scenarios:
        name = scenario["name"]
        print(
            "%s: quorum_min=%d validations_pooled=%d"
            % (
                name,
                per_scenario[name]["quorum_min"],
                per_scenario[name]["validations_pooled"],
            )
        )
    print(
        "quorum holds on every ledger: %s (min=%d, quorum=%d)"
        % (
            "yes" if quorum_min_overall >= model["quorum"] else "no",
            quorum_min_overall,
            model["quorum"],
        )
    )
    print("")
    print("PER-EVENT LOGS (seed 1001) SHA-256")
    for scenario in scenarios:
        name = scenario["name"]
        filename = "events-%s-seed%d.jsonl" % (
            name,
            seeds[FIRST_SEED_INDEX],
        )
        print(
            "%s: %d events sha256=%s"
            % (
                filename,
                len(all_events_seed1[name]),
                events_shas[filename],
            )
        )
    print("")
    print("CANONICAL RESULTS SHA-256")
    print("results.json sha256=%s" % results_sha)
    print("")
    print("CHECKS")
    failed = 0
    for label, passed in checks:
        print("%s: %s" % ("PASS" if passed else "FAIL", label))
        if not passed:
            failed += 1
    print("")
    if failed == 0:
        print("ALL CHECKS PASSED")
        return 0
    print("CHECKS FAILED: %d" % failed)
    return 1


if __name__ == "__main__":
    sys.exit(main())
