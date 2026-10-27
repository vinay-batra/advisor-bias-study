"""The disposition aggregation the abstract leads with.

The registered analysis is per cell: one effect for each model, effort and
family, with twelve matched pairs behind it. The abstract instead states the
disposition effect once, over the whole study, because the reversal against
Odean's sign is a claim about these models rather than about one cell of the
design, and a reader should not have to read nine intervals to see it.

That aggregation is not a registered quantity. It pools across two factors
the design deliberately varies, so it cannot carry a confirmatory test, and
the paper labels it a secondary aggregation wherever it appears. What it can
do is place the direction, which is all the abstract asks of it.

It was computed by hand before this file existed, which left the paper's
first number the only one in it that no released script reproduced. That is
the defect this file closes. The statistical primitives are imported from
analyze rather than rewritten, so the bootstrap, the seed and the matched
pair definition are the registered ones; only the grouping is different. The
self check at the end recomputes every disposition cell and compares it
against the figures analyze.py printed, because the one risk in a second
script that reshapes the same data is that it reshapes it wrongly and agrees
with nothing.

Deterministic. Run from the repo root:

    .venv/bin/python analysis/aggregate.py
"""

import collections
import json
import re
import sys

sys.path.insert(0, ".")

import config
from analysis.analyze import (
    ZERO_TOL, bootstrap_ci, load_rows, mean, snap,
)
from analysis.directions import DIRECTIONS

FAMILY = "disposition"
CONFIRMATORY_OUTPUT = "analysis/confirmatory_output.txt"


def pct_of(r):
    """The continuous measure, with the same validity rule analyze.py uses.

    A percentage outside 0 to 100 is not a percentage of a position, so it
    cannot enter a mean of percentages. Dropping it from this measure alone
    keeps the row's categorical answer, which is still an answer.
    """
    v = r.get("pct_of_position_to_sell")
    if r.get("pct_out_of_range") or not isinstance(v, (int, float)):
        return None
    return v if 0 <= v <= 100 else None


MEASURES = {
    "sell_tendency": lambda r: config.ACTION_SCORE[r["action"]],
    "pct_to_sell": pct_of,
}


def pair_diffs(rows, measure, models=None, efforts=None):
    """Matched pair differences for one family, pooled over the cells kept.

    One difference per (model, effort, pair), which is the unit the
    registered bootstrap resamples. Pooling therefore widens the sample
    without changing what a draw is.

    The cells are sorted, and the order matters. bootstrap_ci draws indices
    from a fixed seed and reads them against this list, so permuting it
    leaves the mean untouched and moves the percentile bounds by Monte Carlo
    noise. The hand computation this file replaces built the list in a
    different order, which is why its point estimates and sign counts were
    exact and three of its eight intervals were off in the third decimal.
    """
    base_c, treat_c, _ = DIRECTIONS[FAMILY]
    get = MEASURES[measure]
    vals = collections.defaultdict(list)
    for r in rows:
        if r["bias"] != FAMILY:
            continue
        if models is not None and r["model"] not in models:
            continue
        if efforts is not None and r["effort"] not in efforts:
            continue
        v = get(r)
        if isinstance(v, (int, float)):
            key = (r["model"], r["effort"], r["pair_id"], r["condition"])
            vals[key].append(float(v))

    cells = sorted({(m, e, p) for m, e, p, _ in vals})
    diffs = []
    for model, effort, pair_id in cells:
        b = vals.get((model, effort, pair_id, base_c))
        t = vals.get((model, effort, pair_id, treat_c))
        if b and t:
            diffs.append(mean(t) - mean(b))
    return diffs


def describe(label, diffs):
    lo, hi = bootstrap_ci(diffs)
    eff = snap(mean(diffs))
    pos = sum(1 for d in diffs if d > ZERO_TOL)
    neg = sum(1 for d in diffs if d < -ZERO_TOL)
    print(f"  {label:<24} {eff:+8.3f} [{lo:+8.3f}, {hi:+8.3f}]"
          f"   {len(diffs):>3} pairs, {pos:>3} positive, {neg:>3} negative,"
          f" {len(diffs) - pos - neg:>3} zero")
    return dict(label=label, effect=eff, ci_low=lo, ci_high=hi,
                n_pairs=len(diffs), n_positive=pos, n_negative=neg)


def self_check(rows):
    """Every disposition cell, against what the registered script printed.

    A reshaping bug would move the aggregate without moving any cell, so the
    cells are where it would hide. Parsed from the committed output rather
    than recomputed by calling analyze.main, which prints 252 lines.
    """
    want = {}
    pat = re.compile(
        r"^(\S+)\s+(low|medium|high)\s+" + FAMILY + r"\s+([+-]\d+\.\d+)")
    measure = None
    for line in open(CONFIRMATORY_OUTPUT):
        if line.startswith("== "):
            measure = line.split()[1]
        m = pat.match(line.strip())
        if m and measure:
            model, effort, eff = m.groups()
            want[(measure, model.split("-5-5")[0], effort)] = float(eff)
    if not want:
        raise SystemExit(f"{CONFIRMATORY_OUTPUT}: parsed no {FAMILY} cells")

    bad = 0
    for (measure, model, effort), expect in sorted(want.items()):
        got = snap(mean(pair_diffs(
            rows, measure,
            models={m for m in {r["model"] for r in rows} if model in m},
            efforts={effort})))
        if abs(got - expect) > 5e-4:
            print(f"  MISMATCH {measure} {model} {effort}: "
                  f"this file {got:+.3f}, analyze.py {expect:+.3f}")
            bad += 1
    print(f"  {len(want)} cells checked against {CONFIRMATORY_OUTPUT}, "
          f"{bad} mismatched")
    return bad


def action_shares(rows):
    """How each model's categorical answers distribute.

    Quoted in the continuous measure appendix to explain why that measure was
    added: the four point scale is effectively three point, because no model
    ever returned BUY_MORE, and each model sits on one category. The
    registered script prints the per cell counts, not these whole-model
    shares, so they are produced here.
    """
    print("=" * 78)
    print("Categorical answer shares per model")
    print("=" * 78)
    out = []
    for model in sorted({r["model"] for r in rows}):
        mine = [r for r in rows if r["model"] == model]
        counts = collections.Counter(r["action"] for r in mine)
        total = len(mine)
        shares = {a: 100 * counts.get(a, 0) / total
                  for a in config.ACTION_SCORE}
        top = max(shares, key=shares.get)
        print(f"  {model:<20} n={total:>5}  " + "  ".join(
            f"{a} {shares[a]:.1f}%" for a in config.ACTION_SCORE))
        out.append(dict(model=model, n=total, shares=shares, modal=top))
    never = [a for a in config.ACTION_SCORE
             if not any(r["action"] == a for r in rows)]
    print(f"  never returned by any model at any effort: "
          f"{', '.join(never) if never else 'none'}")
    return out


def main():
    rows = [r for r in load_rows() if r.get("status") == "ok"]
    models = sorted({r["model"] for r in rows})

    print("=" * 78)
    print("Self check: the disposition cells of the registered analysis")
    print("=" * 78)
    bad = self_check(rows)

    print()
    shares = action_shares(rows)

    out = {"family": FAMILY, "registered": False, "aggregates": [],
           "action_shares": shares}
    for measure in MEASURES:
        print()
        print("=" * 78)
        print(f"Secondary aggregation, {measure}. Not a registered quantity:")
        print("it pools over model and effort, which the design varies.")
        print("=" * 78)
        out["aggregates"].append(
            describe("all nine cells", pair_diffs(rows, measure)))
        for model in models:
            out["aggregates"].append(describe(
                model, pair_diffs(rows, measure, models={model})))

    with open("analysis/aggregate_output.json", "w") as f:
        json.dump(out, f, indent=2)
    print("\nwrote analysis/aggregate_output.json")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
