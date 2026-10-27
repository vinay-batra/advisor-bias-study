"""Is H10's ten out of ten evidence, or is it the selection rule?

H10 as registered: "For any bias family where a non-zero effect is found at
`low`, the absolute effect at `high` will be smaller." It holds in all ten
qualifying cases, five on each measure, and the paper reports that ten of ten
has probability 2^-10 under a null that assigns each case an independent coin
flip.

That null is wrong, and it is wrong in the direction that flatters the
result. The hypothesis selects families on having a large, statistically
non-zero effect at `low`, and then asks whether a second, independent
measurement of the same quantity is smaller. Selection on a noisy baseline
guarantees shrinkage on re-measurement even when nothing has changed: the
cells that clear a significance filter are disproportionately the ones whose
noise happened to point away from zero. Under a true null of no effort
effect, the probability that a qualifying case shrinks is above one half, and
how far above is an empirical question about this design, not something that
can be reasoned out.

This file answers it by running the registered rule verbatim on data where
the effort label has been shuffled among the responses to the same item
within a model. That destroys any real effect of effort and leaves the
selection rule, the sample sizes, the item set and the noise structure
exactly as they are. The fraction of shuffles reaching ten of ten, and the
mean shrink rate among qualifying cases, are the honest null for the headline.

Not pre-registered. It does not change the registered analysis; it changes
what the registered result is worth.

Runtime is a few minutes with no numpy installed. Run from the repo root:
    python3 analysis/h10_placebo.py
"""

import collections
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from analysis.analyze import DIRECTIONS, load_rows, mean, snap
from analysis.robustness import VALUE, usable

MODELS = list(config.MODELS)
SHORT = {m: m.replace("claude-", "").replace("-5-5", "") for m in MODELS}
N_SHUFFLE = 400
N_BOOT = 600

# The pre-registration keeps the two exploratory families out of every
# pooled confirmatory statement. H10 is a confirmatory hypothesis, so the
# registered reading of it uses the seven confirmatory families only. The
# inclusive reading is reported beside it because the paper's first draft
# used it, and because leaving it out would hide the one case that fails.
EXPLORATORY = ("price_path", "brand_salience")
CONFIRMATORY = tuple(f for f in DIRECTIONS if f not in EXPLORATORY)
# The percentile bootstrap CI of a mean of twelve values cannot exclude zero
# when the mean is this small relative to its own standard error. Screening
# on it before bootstrapping cuts most of the work out of the placebo loop
# and cannot change a decision: every cell near the boundary is still
# bootstrapped. The threshold is deliberately well below the 1.96 that would
# make it a test in its own right.
T_SCREEN = 1.0


def effects(rows, measure, effort_of=None):
    """Family effect at each effort level, keyed (model, effort, family).

    Value is (mean difference over pairs, list of pair differences).
    """
    get = VALUE[measure]
    cells = collections.defaultdict(lambda: collections.defaultdict(list))
    for r in rows:
        eff = effort_of(r) if effort_of else r["effort"]
        key = (r["model"], eff, r["bias"], r["pair_id"])
        v = get(r)
        if v is not None:
            cells[key][r["condition"]].append(v)
    per_pair = collections.defaultdict(list)
    for key, byc in cells.items():
        base, treat, _ = DIRECTIONS[key[2]]
        if base in byc and treat in byc:
            per_pair[(key[0], key[1], key[2])].append(
                snap(mean(byc[treat]) - mean(byc[base])))
    return {k: (mean(v), v) for k, v in per_pair.items() if v}


def excludes_zero(ds, rng):
    """Percentile bootstrap over pairs, the registered decision rule."""
    n = len(ds)
    if n < 2:
        return False
    m = mean(ds)
    if m == 0.0:
        return False
    var = sum((d - m) ** 2 for d in ds) / (n - 1)
    if var <= 0:
        return True
    if abs(m) / math.sqrt(var / n) < T_SCREEN:
        return False
    draws = sorted(mean([ds[rng.randrange(n)] for _ in range(n)])
                   for _ in range(N_BOOT))
    lo = draws[int(0.025 * N_BOOT)]
    hi = draws[int(0.975 * N_BOOT) - 1]
    return (lo > 0 and hi > 0) or (lo < 0 and hi < 0)


def apply_h10(rows, rng, effort_of=None, families=None):
    """Run the registered rule. Returns (n_qualified, n_shrank, detail)."""
    families = list(DIRECTIONS) if families is None else list(families)
    nq = ns = 0
    detail = []
    for measure in ("cat", "pct"):
        eff = effects(rows, measure, effort_of=effort_of)
        for m in MODELS:
            for fam in families:
                lo = eff.get((m, "low", fam))
                hi = eff.get((m, "high", fam))
                if lo is None or hi is None:
                    continue
                if not excludes_zero(lo[1], rng):
                    continue
                nq += 1
                shrank = abs(hi[0]) < abs(lo[0])
                ns += 1 if shrank else 0
                detail.append((measure, m, fam, lo[0], hi[0], shrank))
    return nq, ns, detail


def observed_from_registered():
    """The observed qualifying set, read from the pre-registered output.

    data/results.json is what analysis/analyze.py wrote, so it carries the
    registered bootstrap with the registered seed. Recomputing the
    qualification here with a different seed moves borderline cells: one
    categorical cell, brand salience in Opus, has an interval upper bound of
    -0.017 and falls either side of the line depending on the draw. The
    observed counts quoted in the paper come from this file. The placebo
    below uses its own bootstrap for both arms of its comparison, which is
    what keeps it internally consistent.
    """
    import json
    path = os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "data", "results.json")
    R = json.load(open(path))["results"]
    by = {(r["measure"], r["model"], r["bias"], r["effort"]): r for r in R}
    out = []
    for (meas, mod, fam, eff), r in sorted(by.items()):
        if eff != "low":
            continue
        ex = ((r["ci_low"] > 0 and r["ci_high"] > 0)
              or (r["ci_low"] < 0 and r["ci_high"] < 0))
        if not ex:
            continue
        hi = by.get((meas, mod, fam, "high"))
        if hi is None:
            continue
        out.append((meas, mod, fam, r["effect"], hi["effect"],
                    abs(hi["effect"]) < abs(r["effect"]),
                    fam not in EXPLORATORY))
    return out


def main():
    rows = usable(load_rows())
    print(f"{len(rows):,} usable responses")
    rng = random.Random(97)

    print("\n" + "=" * 78)
    print("Observed, from data/results.json, the pre-registered output")
    print("=" * 78)
    obs = observed_from_registered()
    for meas, mod, fam, lo, hi, shrank, conf in obs:
        print(f"  {meas:13s} {SHORT[mod]:10s} {fam:20s} "
              f"low {lo:+8.3f} -> high {hi:+8.3f}  "
              f"{'smaller' if shrank else 'NOT SMALLER':11s} "
              f"{'confirmatory' if conf else 'exploratory'}")
    cf = [o for o in obs if o[6]]
    print(f"\n  confirmatory families only, which is the registered "
          f"reading: {sum(1 for o in cf if o[5])} of {len(cf)} shrink")
    print(f"  including the two exploratory families:          "
          f"{sum(1 for o in obs if o[5])} of {len(obs)} shrink")
    fails = [o for o in obs if not o[5]]
    for o in fails:
        print(f"  the case that fails: {o[0]} {SHORT[o[1]]} {o[2]}, "
              f"{o[3]:+.3f} to {o[4]:+.3f}")

    n_obs = {"confirmatory only": len(cf), "all nine families": len(obs)}

    nq, ns, _ = apply_h10(rows, rng)
    print(f"\n  recomputed here with an independent bootstrap: "
          f"{ns} of {nq} (see observed_from_registered)")

    print("\n" + "=" * 78)
    print(f"Placebo: {N_SHUFFLE} shuffles of the effort label among the")
    print("responses to the same item within a model. The rule, the sample")
    print("sizes and the item set are untouched; only the labels move.")
    print("=" * 78)

    groups = collections.defaultdict(list)
    for i, r in enumerate(rows):
        groups[(r["model"], r["item_id"])].append(i)

    prng = random.Random(1861)
    stats = {}
    for tag, fams in (("confirmatory only", CONFIRMATORY),
                      ("all nine families", list(DIRECTIONS))):
        quals, rates, allhit = [], [], 0
        for k in range(N_SHUFFLE):
            label = {}
            for g in groups.values():
                effs = [rows[i]["effort"] for i in g]
                prng.shuffle(effs)
                for i, e in zip(g, effs):
                    label[i] = e
            idx = {id(rows[i]): label[i] for i in label}
            eff_of = (lambda r, idx=idx: idx.get(id(r), r["effort"]))
            q, s, _ = apply_h10(rows, prng, effort_of=eff_of, families=fams)
            quals.append(q)
            if q:
                rates.append(s / q)
                if s == q:
                    allhit += 1
            if (k + 1) % 100 == 0:
                print(f"  {tag}: {k + 1}/{N_SHUFFLE}, running shrink rate "
                      f"{mean(rates):.3f}")
        stats[tag] = (mean(quals), min(quals), max(quals), mean(rates),
                      allhit / N_SHUFFLE)
        print()

    print("=" * 78)
    print("The null for H10")
    print("=" * 78)
    for tag, (mq, lo, hi, rate, allp) in stats.items():
        print(f"\n  {tag}")
        print(f"    qualifying cases per shuffle: mean {mq:.2f}, "
              f"range {lo} to {hi}")
        print(f"    a single qualifying case shrinks with probability "
              f"{rate:.4f}")
        print(f"    p(every qualifying case shrinks) = {allp:.4f}")
        # Two coin-flip comparisons, and only the first belongs in prose.
        # The paper's claim is about the cases it observed, so that is the
        # count its coin flip has to be evaluated at. The second line is a
        # property of the shuffled distribution, which qualifies more cases
        # than the real data does; quoting its ratio against a count the
        # study never observed is what made the appendix contradict itself.
        n = n_obs[tag]
        print(f"    the coin flip at the {n} observed cases says "
              f"{0.5 ** n:.4f}, which is wrong by "
              f"{allp / 0.5 ** n:.1f}x   <- the paper quotes this")
        print(f"    at the {round(mq)} cases a shuffle qualifies on average "
              f"it says {0.5 ** round(mq):.4f}, wrong by "
              f"{allp / max(0.5 ** round(mq), 1e-12):.0f}x (diagnostic only)")

    print("\n" + "=" * 78)
    print("What this does to the paper's claim")
    print("=" * 78)
    print("  Selecting families on a non-zero effect at low effort and then")
    print("  asking whether a second measurement is smaller shrinks on its")
    print("  own: the cells that clear the filter are the ones whose noise")
    print("  pointed away from zero. The null probability of a single case")
    print("  shrinking is about 0.69, not 0.5, so 2^-n overstates the")
    print("  evidence several fold at the counts observed. The pattern is")
    print("  still unlikely under the null, and that is what the paper")
    print("  should claim, with this number rather than the coin flip.")


if __name__ == "__main__":
    main()
