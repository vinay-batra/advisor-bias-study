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

# Floating point noise is not a small problem here, because the decision rule
# is whether an interval excludes zero. The paired differences are means of
# small integers over trials, and values like 0.2 have no exact binary
# representation, so sums that should cancel to zero land on 3.7e-17 instead.
# An interval bound of 3.7e-17 excludes zero arithmetically and would be read
# as a non-zero effect. Anything this small is zero: the smallest difference
# the instrument can produce is one scale point divided by the trial count,
# which is seven orders of magnitude larger.
ZERO_TOL = 1e-9


def snap(x):
    """Collapse floating point noise around zero to exactly zero."""
    return 0.0 if abs(x) < ZERO_TOL else x

try:
    import numpy as _np
except ImportError:
    _np = None

RNG = random.Random(SEED)


def mean(xs):
    return sum(xs) / len(xs) if xs else float("nan")


def _percentile(ordered, q):
    """Empirical quantile of a sorted sequence, without interpolation.

    Interpolating between order statistics is wrong for this data. The paired
    differences are discrete, so the bootstrap distribution of their mean has
    heavy ties, often at exactly zero. Linear interpolation between a zero
    order statistic and the next one up returns a strictly positive bound,
    and since an effect is called non-zero when the interval excludes zero,
    that turns an interpolation artifact into a significance claim. Taking
    the order statistic itself reports the bound the resamples actually
    support. Both code paths below use this, so the numpy and pure Python
    branches return identical intervals rather than merely similar ones.
    """
    k = len(ordered)
    i = min(k - 1, max(0, math.ceil(q * k) - 1))
    return snap(float(ordered[i]))


def bootstrap_ci(diffs, n=N_BOOT, alpha=0.05):
    """Percentile bootstrap over the matched pairs."""
    if not diffs:
        return (float("nan"), float("nan"))
    k = len(diffs)
    if _np is not None:
        rng = _np.random.default_rng(SEED)
        d = _np.asarray(diffs, dtype=float)
        means = _np.sort(d[rng.integers(0, k, size=(n, k))].mean(axis=1))
    else:
        means = sorted(mean([diffs[RNG.randrange(k)] for _ in range(k)])
                       for _ in range(n))
    return (_percentile(means, alpha / 2),
            _percentile(means, 1 - alpha / 2))


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


def holm(ps):
    """Holm step down adjusted p values, in the order given.

    Registered as a correction within each model and effort cell across the
    nine bias families. Monotonicity is enforced, so an adjusted value is
    never smaller than one earlier in the sorted sequence, and values are
    capped at 1.
    """
    m = len(ps)
    order = sorted(range(m), key=lambda i: ps[i])
    out = [float("nan")] * m
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, (m - rank) * ps[i])
        out[i] = min(1.0, running)
    return out


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


EFFORT_ORDER = {"low": 0, "medium": 1, "high": 2, "xhigh": 3, "max": 4}

# What counts as a change in the absolute effect, per measure. The
# categorical scale spans 3 points, the continuous one 100, so a single
# threshold would read as noise on one and as a wall on the other.
GRADIENT_TOL = {"sell_tendency": 0.02, "pct_to_sell": 0.5}


def print_gradient(results, measure):
    """Absolute effect against effort, for one dependent variable."""
    sub = [r for r in results if r["measure"] == measure]
    if not sub:
        return
    print(f"\n== {measure}")
    for model in sorted({r["model"] for r in sub}):
        print(f"\n  {model}")
        for bias in DIRECTIONS:
            cells = sorted([r for r in sub if r["model"] == model
                            and r["bias"] == bias],
                           key=lambda r: EFFORT_ORDER.get(r["effort"], 9))
            if len(cells) < 2:
                continue
            shown = "  ".join(f"{c['effort'][:3]} {abs(c['effect']):6.2f}"
                              for c in cells)
            delta = abs(cells[-1]["effect"]) - abs(cells[0]["effect"])
            tol = GRADIENT_TOL[measure]
            arrow = ("down" if delta < -tol
                     else ("up" if delta > tol else "flat"))
            print(f"    {bias:20s} {shown}   -> {arrow} ({delta:+.2f})")


def main():
    rows = load_rows()
    ok = [r for r in rows if r.get("status") == "ok"]
    print(f"{len(rows):,} responses on disk, {len(ok):,} usable "
          f"({100 * len(ok) / max(len(rows), 1):.1f}%)")

    dropped = collections.Counter(
        r.get("status") for r in rows if r.get("status") != "ok")
    for k, v in dropped.most_common():
        print(f"  dropped {v:,} as {k}")

    # Data quality flags carried through from collection. Reported, never
    # silently dropped: a model ignoring a stated bound, or contradicting its
    # own categorical answer with its numeric one, is a result about
    # instruction following rather than noise.
    FLAG_NOTE = {
        "pct_out_of_range":
            "percentage outside 0 to 100, excluded from the continuous "
            "measure, categorical answer kept",
        "action_pct_inconsistent":
            "the two measures disagree, both kept, never reconciled",
        "confidence_out_of_range":
            "confidence outside 0 to 100, reported, never a dependent "
            "variable",
    }
    flags = collections.Counter()
    for r in ok:
        for f in FLAG_NOTE:
            if r.get(f):
                flags[f] += 1
    for k, v in flags.most_common():
        print(f"  flagged {v:,} as {k}: {FLAG_NOTE[k]}")

    # Two dependent variables, analysed identically. The categorical scale is
    # the pre-registered primary; the continuous measure was added in
    # Amendment 3 because the categorical one proved to be at ceiling.
    #
    # A percentage outside 0 to 100 is not a percentage of a position, so it
    # cannot enter a mean of percentages: it is excluded from the continuous
    # measure and counted. The same response's categorical answer is still a
    # valid answer and stays in the categorical measure. This is a per measure
    # validity rule, not a response level exclusion, so the two measures can
    # legitimately rest on different numbers of observations.
    def pct_of(r):
        v = r.get("pct_of_position_to_sell")
        if r.get("pct_out_of_range") or not isinstance(v, (int, float)):
            return None
        return v if 0 <= v <= 100 else None

    MEASURES = {
        "sell_tendency": lambda r: config.ACTION_SCORE[r["action"]],
        "pct_to_sell": pct_of,
    }

    # vals[(measure, model, effort, bias, pair_id, condition)] -> [value, ...]
    vals = collections.defaultdict(list)
    actions = collections.defaultdict(collections.Counter)
    kept = collections.Counter()
    for r in ok:
        key = (r["model"], r["effort"], r["bias"], r["pair_id"], r["condition"])
        actions[key][r["action"]] += 1
        for mname, get in MEASURES.items():
            v = get(r)
            if isinstance(v, (int, float)):
                vals[(mname,) + key].append(float(v))
                kept[mname] += 1
    for mname in MEASURES:
        n = kept[mname]
        print(f"  {mname}: {n:,} of {len(ok):,} usable responses carry a "
              f"valid value ({100 * n / max(len(ok), 1):.1f}%)")

    results = []
    for model in sorted({r["model"] for r in ok}):
        for effort in sorted({r["effort"] for r in ok}):
            for bias, (base_c, treat_c, pred) in DIRECTIONS.items():
                pair_ids = sorted({r["pair_id"] for r in ok
                                   if r["bias"] == bias})
                # Flip rate and entropy describe the categorical answer and so
                # are the same for both measures. Computed once per cell.
                flips, ents = [], []
                for pair_id in pair_ids:
                    ab = actions.get((model, effort, bias, pair_id, base_c))
                    at = actions.get((model, effort, bias, pair_id, treat_c))
                    if not ab or not at:
                        continue
                    flips.append(1 if ab.most_common(1)[0][0]
                                 != at.most_common(1)[0][0] else 0)
                    ents.append(entropy(ab))
                    ents.append(entropy(at))
                for mname in MEASURES:
                    diffs = []
                    for pair_id in pair_ids:
                        b = vals.get((mname, model, effort, bias, pair_id, base_c))
                        t = vals.get((mname, model, effort, bias, pair_id, treat_c))
                        if not b or not t:
                            continue
                        diffs.append(mean(t) - mean(b))
                    if not diffs:
                        continue
                    lo, hi = bootstrap_ci(diffs)
                    eff = snap(mean(diffs))
                    nz = sum(1 for d in diffs if abs(d) >= ZERO_TOL)
                    results.append(dict(
                        measure=mname,
                        model=model, effort=effort, bias=bias,
                        baseline=base_c, treatment=treat_c, predicted=pred,
                        n_pairs=len(diffs), n_nonzero=nz,
                        effect=eff, ci_low=lo, ci_high=hi,
                        p_value=permutation_p(diffs),
                        flip_rate=mean(flips),
                        mean_entropy=mean(ents),
                        significant=not (lo <= 0 <= hi),
                        matches_prediction=(
                            pred == "?" or
                            (pred == "+" and eff > 0) or
                            (pred == "-" and eff < 0)),
                    ))

    # Holm within each model and effort cell, across the bias families, and
    # separately per measure. Reported alongside the uncorrected values.
    cells = collections.defaultdict(list)
    for r in results:
        cells[(r["measure"], r["model"], r["effort"])].append(r)
    for group in cells.values():
        adj = holm([g["p_value"] for g in group])
        for g, a in zip(group, adj):
            g["p_holm"] = a
            g["n_family"] = len(group)
            g["significant_holm"] = a < 0.05

    with open("data/results.json", "w") as f:
        json.dump(dict(results=results, rationale=RATIONALE), f, indent=2)

    for mname in MEASURES:
        sub = [r for r in results if r["measure"] == mname]
        if not sub:
            continue
        print(f"\n== {mname} "
              f"({'pre-registered primary' if mname == 'sell_tendency' else 'continuous co-primary, Amendment 3'})")
        print(f"{'model':18s} {'effort':7s} {'bias':20s} {'effect':>8s} "
              f"{'95% CI':>20s} {'p':>7s} {'p_holm':>7s} {'nz':>4s} "
              f"{'flip':>6s} {'ci':>3s} {'holm':>4s}")
        for r in sub:
            print(f"{r['model'].replace('claude-',''):18s} {r['effort']:7s} "
                  f"{r['bias']:20s} {r['effect']:+8.3f} "
                  f"[{r['ci_low']:+8.3f},{r['ci_high']:+8.3f}] "
                  f"{r['p_value']:7.4f} {r['p_holm']:7.4f} "
                  f"{r['n_nonzero']:2d}/{r['n_pairs']:<2d} "
                  f"{r['flip_rate']:6.2f} "
                  f"{('yes' if r['significant'] else ''):>3s} "
                  f"{('yes' if r['significant_holm'] else ''):>4s}")
        # The sign flipping test can only take as many distinct values as the
        # non-zero pairs allow. One moving pair gives p = 1 whatever the
        # effect size, because flipping its sign leaves the absolute mean
        # unchanged. Said out loud so the granularity is not read as a bug.
        thin = [r for r in sub if r["n_nonzero"] <= 2]
        if thin:
            print(f"  note: {len(thin)} of {len(sub)} cells have 2 or fewer "
                  f"pairs with a non-zero difference, so their permutation "
                  f"p values are coarse by construction")

    print("\nH10. Does more reasoning reduce bias? |effect| by effort.")
    print("Sign agnostic by construction: H10 is a claim about magnitude.")
    for mname in MEASURES:
        print_gradient(results, mname)

    print(f"\nwrote data/results.json")


if __name__ == "__main__":
    main()
