"""Check a later wave of items before any of it is paid for.

A wave is worth about the same as the wave before it, so every property the
design depends on is asserted here rather than discovered in the analysis.
The checks are the ones that would quietly invalidate the extension:

- the wave is a wave, not a second study: same families, same conditions in
  the pre-registered order, same number of pairs in each;
- nothing collides with what is already collected, on item id, pair id or
  batch custom id, because the analysis pools the two waves by those keys;
- nothing is shared with wave 1 either, since a repeated prompt would make
  the replication partly a re-run;
- the matched pair still holds: both arms of a pair state the same account,
  the same cash need, the same share count and the same price, so the cue
  under test is the only thing that differs;
- the two arms are close in length, because a systematic length difference
  is a confound the design claims not to have.

Usage:
    python scripts/validate_wave.py 2
"""

import collections
import json
import os
import re
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from analysis.directions import DIRECTIONS
from battery.items import FAMILIES
from run.common import custom_id, wave as wave_paths

# Figures that must agree across the two arms of a pair. The cue under test
# is never one of these: it is the sentence the two arms differ in.
SHARED = {
    "account": r"retirement account of about \$([\d,]+)",
    "cash_need": r"needs to raise \$([\d,]+) in cash",
    "shares": r"under review is ([\d,]+) shares",
    "price": r"currently \$([\d.]+) a share",
    "weight": r"which is (\d+)% of the account",
}


def read(path):
    with open(path) as f:
        return [json.loads(line) for line in f]


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    w = wave_paths(n)
    items = read(w["items"])
    base = read(config.ITEMS_PATH)
    fail = []

    def check(ok, msg):
        print(f"  {'ok  ' if ok else 'FAIL'}  {msg}")
        if not ok:
            fail.append(msg)

    print(f"wave {n}: {len(items)} items from {w['items']}")
    print(f"wave 1: {len(base)} items from {config.ITEMS_PATH}\n")

    # 1. Shape.
    by_fam = collections.Counter(it["bias"] for it in items)
    check(sorted(by_fam) == sorted(f for f, _, _ in FAMILIES),
          f"all {len(FAMILIES)} families present")
    check(set(by_fam.values()) == {w["pairs"] * 2},
          f"every family has exactly {w['pairs']} pairs")

    pairs = collections.defaultdict(list)
    for it in items:
        pairs[it["pair_id"]].append(it)
    bad = [p for p, v in pairs.items() if len(v) != 2]
    check(not bad, f"{len(pairs)} pairs, every one with two arms")

    wrong = [p for p, v in pairs.items()
             if {x["condition"] for x in v} != set(DIRECTIONS[v[0]["bias"]][:2])]
    check(not wrong, "every pair's conditions match analysis/directions.py")

    # 2. Collisions with what is already collected.
    check(not (set(x["item_id"] for x in items)
               & set(x["item_id"] for x in base)), "no item_id collides with wave 1")
    check(not (set(x["pair_id"] for x in items)
               & set(x["pair_id"] for x in base)), "no pair_id collides with wave 1")

    cids = {custom_id(i + w["id_offset"], m, e, t)
            for i in range(len(items)) for m in range(len(config.MODELS))
            for e in config.EFFORTS for t in range(config.N_TRIALS)}
    old = {custom_id(i, m, e, t)
           for i in range(len(base)) for m in range(len(config.MODELS))
           for e in config.EFFORTS for t in range(config.N_TRIALS)}
    check(len(cids) == len(items) * len(config.MODELS) * len(config.EFFORTS)
          * config.N_TRIALS, f"{len(cids):,} custom_ids, all distinct")
    check(not (cids & old), "no custom_id collides with wave 1")

    # 3. Independence of the items themselves.
    shared = set(x["prompt"] for x in items) & set(x["prompt"] for x in base)
    check(not shared, "no prompt is shared with wave 1")
    check(len(set(x["prompt"] for x in items)) == len(items),
          "no prompt is repeated inside the wave")
    same_co = sum(1 for p, v in pairs.items()
                  if any(b["meta"]["company"] == v[0]["meta"]["company"]
                         and b["pair_id"].split("_w")[0] == v[0]["bias"]
                         and b["pair_id"].endswith(p.split("_")[-1])
                         for b in base))
    print(f"  note  {same_co} of {len(pairs)} pairs reuse wave 1's company "
          f"at the same index")

    # 4. The matched pair still holds.
    for name, pat in SHARED.items():
        off = []
        for p, v in sorted(pairs.items()):
            vals = {re.search(pat, x["prompt"]).group(1)
                    if re.search(pat, x["prompt"]) else None for x in v}
            if len(vals) != 1 or None in vals:
                off.append(p)
        check(not off, f"both arms state the same {name}"
              + (f" (off: {off[:3]})" if off else ""))

    # 5. Length balance. Not an assertion about any one pair: the cue
    #    sentences are not the same length and cannot be. What would be a
    #    confound is a family whose arms differ systematically, so the
    #    signed difference is what is reported.
    print("\n  within-pair length difference, characters (treatment - baseline):")
    for fam, _, _ in FAMILIES:
        b, t = DIRECTIONS[fam][:2]
        d = []
        for p, v in sorted(pairs.items()):
            if v[0]["bias"] != fam:
                continue
            got = {x["condition"]: len(x["prompt"]) for x in v}
            d.append(got[t] - got[b])
        print(f"    {fam:22} mean {statistics.mean(d):+7.1f}  "
              f"max |d| {max(abs(x) for x in d):4}")

    print()
    if fail:
        print(f"{len(fail)} check(s) failed. Do not submit.")
        return 1
    print(f"wave {n} is ready: {len(cids):,} requests across "
          f"{len(config.MODELS) * len(config.EFFORTS)} cells.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
