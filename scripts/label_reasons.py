"""Draw the stratified sample that analysis/reasons.py is audited against.

A regex measure of what a sentence means is worth nothing unless someone has
read a sample of it, so this writes the sample and the detector's prediction
and leaves the label blank. Filling it in is a reading task, and the filled
file is committed so the audit can be rerun and disagreed with.

Stratified by family and by predicted label, not drawn at random over the
corpus. A random draw would be mostly silent reasons and would measure
almost nothing about the category the analysis actually rests on.

Two samples, and the distinction matters. The first, data/reason_labels.json,
is a development set: the detector's patterns were widened against it, so the
agreement it reports is a fit to its own tuning data and is not evidence the
measure works. The second, written with --heldout, is drawn under a different
seed from the reasons the first did not touch, and is labelled once after the
patterns are frozen. The held out agreement is the number the paper may quote.

Three rounds, each under its own seed and disjoint from the ones before it.
dev1, dev2 and dev3 are development data: the patterns were widened against
them, so their agreement is a fit to their own tuning data and is not
evidence the measure works. Each of dev2 and dev3 was drawn and labelled
while the patterns were frozen, so its first reading was an honest out of
sample score, and each score is recorded in its own file before it was spent.
Three rounds were needed because the first reading of each turned up a bug in
the patterns rather than a limit of the measure: whitespace stripped by
re.VERBOSE, then two broken character classes, then a marker matched against
the wrong grammatical subject. test is drawn after the patterns were frozen
for good and labelled once. Only the test agreement belongs in the paper.

    python scripts/label_reasons.py --round dev1
    python scripts/label_reasons.py --round dev2
    python scripts/label_reasons.py --round dev3
    python scripts/label_reasons.py --round test
    python scripts/label_reasons.py --check
"""

import argparse
import collections
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analysis.reasons import LABELS_PATH, NAMEABLE, classify

PER_LABEL = {"rejects": 4, "cites": 3, "silent": 3}

# Ordered. A round excludes every reason drawn by the rounds before it, so no
# row appears twice and the test set cannot contain anything the patterns were
# tuned on.
ROUNDS = (
    ("dev1", 41, LABELS_PATH,
     "development set, the patterns were tuned against it"),
    ("dev2", 907, "data/reason_labels_heldout.json",
     "second development round, honest out of sample when first read, "
     "then tuned against"),
    ("dev3", 2719, "data/reason_labels_test.json",
     "third development round. Honest out of sample when first read, at "
     "0.76 agreement with precision 24 of 24 and recall 24 of 35; reading "
     "it then exposed a broken character class and a marker whose subject "
     "was wrong, both of which were fixed, which spends it"),
    ("test", 5281, "data/reason_labels_final.json",
     "test set, drawn and labelled after the patterns were frozen for good; "
     "this is the agreement the paper quotes"),
)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--round", choices=[r[0] for r in ROUNDS], default="dev1")
    args = ap.parse_args()

    if args.check:
        bad = 0
        for name, _, path, role in ROUNDS:
            if not os.path.exists(path):
                print(f"{name:<5} {path}: not drawn yet")
                continue
            d = json.load(open(path))
            blank = [x for x in d["labels"] if x["label"] is None]
            print(f"{name:<5} {path}: {len(d['labels'])} sampled, "
                  f"{len(blank)} still unlabelled")
            bad += len(blank)
        return 0 if not bad else 1

    here = [r for r in ROUNDS if r[0] == args.round][0]
    _, seed, path, role = here
    spent = set()
    for name, _, earlier, _ in ROUNDS:
        if name == args.round:
            break
        if os.path.exists(earlier):
            spent |= {x["custom_id"]
                      for x in json.load(open(earlier))["labels"]}

    rows = [json.loads(l) for l in open("data/responses.jsonl")]
    rows = [r for r in rows
            if r.get("status") == "ok" and r.get("reason")
            and r["bias"] in NAMEABLE]
    rows = [r for r in rows if r["custom_id"] not in spent]
    pools = collections.defaultdict(list)
    for r in rows:
        pools[(r["bias"], classify(r["reason"], r["bias"]))].append(r)

    rng = random.Random(seed)
    out = []
    for fam in NAMEABLE:
        for pred, k in PER_LABEL.items():
            pool = sorted(pools[(fam, pred)], key=lambda r: r["custom_id"])
            for r in rng.sample(pool, min(k, len(pool))):
                out.append(dict(custom_id=r["custom_id"], bias=fam,
                                model=r["model"], effort=r["effort"],
                                predicted=pred, label=None,
                                reason=r["reason"]))
    existing = {}
    if os.path.exists(path):
        existing = {x["custom_id"]: x["label"]
                    for x in json.load(open(path))["labels"]}
    for x in out:
        x["label"] = existing.get(x["custom_id"])

    with open(path, "w") as f:
        json.dump({
            "what": "Hand labels for the cue reference measure in "
                    "analysis/reasons.py. label is what the reason actually "
                    "does with the family's manipulated cue: silent if it "
                    "never refers to it, cites if it refers to it as a "
                    "consideration, rejects if it refers to it and discounts "
                    "it. predicted is what the detector said, and is not "
                    "evidence about the label.",
            "round": args.round,
            "role": role,
            "excludes": f"{len(spent)} reasons drawn by earlier rounds",
            "sample": f"stratified by family and predicted label, seed {seed}",
            "labels": out}, f, indent=1)
    print(f"wrote {len(out)} sampled reasons to {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
