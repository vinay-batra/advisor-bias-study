"""Analyse the collected responses.

Output: data/results.json plus a printed table. Pre-registered analysis, run
unchanged over whatever rows exist on disk.

Each matched pair contributes one paired observation per cell: the mean sell
tendency across trials in the treatment condition minus the mean in the
baseline condition. The pair is the unit of analysis, which is why the test is
paired. Confidence intervals come from a bootstrap over pairs; p values come
from a sign flipping permutation test, which assumes nothing about the shape
of the distribution.

Usage:
    python analysis/analyze.py
"""

import collections
import json
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from analysis.directions import DIRECTIONS, RATIONALE

N_BOOT = 10000
N_PERM = 10000
SEED = 7

try:
    import numpy as _np
except ImportError:
    _np = None

RNG = random.Random(SEED)


def mean(xs):
    return sum(xs) / len(xs) if xs else float("nan")


def bootstrap_ci(diffs, n=N_BOOT, alpha=0.05):
    """Percentile bootstrap over the matched pairs."""
    if not diffs:
        return (float("nan"), float("nan"))
    k = len(diffs)
    if _np is not None:
        rng = _np.random.default_rng(SEED)
        d = _np.asarray(diffs, dtype=float)
        means = d[rng.integers(0, k, size=(n, k))].mean(axis=1)
        return (float(_np.quantile(means, alpha / 2)),
                float(_np.quantile(means, 1 - alpha / 2)))
    means = sorted(mean([diffs[RNG.randrange(k)] for _ in range(k)])
                   for _ in range(n))
    return (means[int(alpha / 2 * n)], means[int((1 - alpha / 2) * n)])


def permutation_p(diffs, n=N_PERM):
    """Two sided sign flipping test on the paired differences."""
    if not diffs:
        return float("nan")
    observed = abs(mean(diffs))
    if _np is not None:
        rng = _np.random.default_rng(SEED + 1)
        d = _np.asarray(diffs, dtype=float)
        signs = rng.choice([-1.0, 1.0], size=(n, len(d)))
        null = _np.abs((signs * d).mean(axis=1))
        return float((_np.count_nonzero(null >= observed - 1e-12) + 1) / (n + 1))
    hits = sum(
        1 for _ in range(n)
        if abs(mean([d if RNG.random() < 0.5 else -d for d in diffs]))
        >= observed - 1e-12)
    return (hits + 1) / (n + 1)


def entropy(counts):
    total = sum(counts.values())
    if total == 0:
        return 0.0
    h = 0.0
    for v in counts.values():
        if v:
            p = v / total
            h -= p * math.log(p, 2)
    return h


def load_rows():
    rows = []
    with open(config.RESPONSES_PATH) as f:
        for line in f:
            rows.append(json.loads(line))
    return rows


def main():
    rows = load_rows()
    ok = [r for r in rows if r.get("status") == "ok"]
    print(f"{len(rows):,} responses on disk, {len(ok):,} usable "
          f"({100 * len(ok) / max(len(rows), 1):.1f}%)")

    dropped = collections.Counter(
        r.get("status") for r in rows if r.get("status") != "ok")
    for k, v in dropped.most_common():
        print(f"  dropped {v:,} as {k}")

    # scores[(model, effort, bias, pair_id, condition)] -> [sell tendency, ...]
    scores = collections.defaultdict(list)
    actions = collections.defaultdict(collections.Counter)
    for r in ok:
        key = (r["model"], r["effort"], r["bias"], r["pair_id"], r["condition"])
        scores[key].append(config.ACTION_SCORE[r["action"]])
        actions[key][r["action"]] += 1

    results = []
    for model in sorted({r["model"] for r in ok}):
        for effort in sorted({r["effort"] for r in ok}):
            for bias, (base_c, treat_c, pred) in DIRECTIONS.items():
                diffs, flips, ents = [], [], []
                for pair_id in sorted({r["pair_id"] for r in ok
                                       if r["bias"] == bias}):
                    b = scores.get((model, effort, bias, pair_id, base_c))
                    t = scores.get((model, effort, bias, pair_id, treat_c))
                    if not b or not t:
                        continue
                    diffs.append(mean(t) - mean(b))
                    mb = actions[(model, effort, bias, pair_id, base_c)].most_common(1)[0][0]
                    mt = actions[(model, effort, bias, pair_id, treat_c)].most_common(1)[0][0]
                    flips.append(1 if mb != mt else 0)
                    ents.append(entropy(actions[(model, effort, bias, pair_id, base_c)]))
                    ents.append(entropy(actions[(model, effort, bias, pair_id, treat_c)]))
                if not diffs:
                    continue
                lo, hi = bootstrap_ci(diffs)
                results.append(dict(
                    model=model, effort=effort, bias=bias,
                    baseline=base_c, treatment=treat_c, predicted=pred,
                    n_pairs=len(diffs),
                    effect=mean(diffs), ci_low=lo, ci_high=hi,
                    p_value=permutation_p(diffs),
                    flip_rate=mean(flips),
                    mean_entropy=mean(ents),
                    significant=not (lo <= 0 <= hi),
                    matches_prediction=(
                        pred == "?" or
                        (pred == "+" and mean(diffs) > 0) or
                        (pred == "-" and mean(diffs) < 0)),
                ))

    with open("data/results.json", "w") as f:
        json.dump(dict(results=results, rationale=RATIONALE), f, indent=2)

    print(f"\n{'model':18s} {'effort':7s} {'bias':20s} {'effect':>7s} "
          f"{'95% CI':>16s} {'p':>7s} {'flip':>6s} {'sig':>4s}")
    for r in results:
        star = "yes" if r["significant"] else ""
        print(f"{r['model'].replace('claude-',''):18s} {r['effort']:7s} "
              f"{r['bias']:20s} {r['effect']:+7.3f} "
              f"[{r['ci_low']:+.2f},{r['ci_high']:+.2f}] {r['p_value']:7.4f} "
              f"{r['flip_rate']:6.2f} {star:>4s}")

    print("\nDoes more reasoning reduce bias? |effect| by effort:")
    order = {"low": 0, "medium": 1, "high": 2, "xhigh": 3, "max": 4}
    for model in sorted({r["model"] for r in results}):
        print(f"\n  {model}")
        for bias in DIRECTIONS:
            cells = sorted([r for r in results
                            if r["model"] == model and r["bias"] == bias],
                           key=lambda r: order.get(r["effort"], 9))
            if len(cells) < 2:
                continue
            vals = "  ".join(f"{c['effort'][:3]} {abs(c['effect']):.2f}"
                             for c in cells)
            delta = abs(cells[-1]["effect"]) - abs(cells[0]["effect"])
            arrow = "down" if delta < -0.02 else ("up" if delta > 0.02 else "flat")
            print(f"    {bias:20s} {vals}   -> {arrow} ({delta:+.2f})")

    print(f"\nwrote data/results.json")


if __name__ == "__main__":
    main()
