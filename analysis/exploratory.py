"""Exploratory analyses, none of them pre-registered.

Everything here was written after the confirmatory data was in hand, and
nothing in this file can change a pre-registered conclusion. It exists
because the registered analysis leaves four questions open that a reader
will ask, and because two of them bear directly on the competing claim the
design was registered against.

  1. Does length do the work, or does the label? The registered analysis
     compares effort levels. Hu and Wang's claim is that the parameter sets a
     ceiling on generation rather than driving how reasoning is allocated.
     Those two are only distinguishable by holding the label fixed and
     letting length vary, which the data allow because length varies a lot
     within a cell.
  2. Is the effort slope actually different across models? The headline
     reading of the registered table is that deliberation substitutes for
     capability. That is a statement about an interaction, and the registered
     analysis never tests one.
  3. Does the headline survive losing any single pair? Twelve pairs is few
     enough that one of them could be carrying the result.
  4. Is Sonnet's medium cell a real treatment level? Its generation length
     and its entropy both look like its low cell.

Usage:
    python analysis/exploratory.py
"""

import collections
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from analysis.analyze import (DIRECTIONS, bootstrap_ci, entropy, holm, load_rows,
                              mean, permutation_p, p_floor, snap)

MODELS = ["claude-haiku-5-5", "claude-sonnet-5-5", "claude-opus-5-5"]
EFFORTS = ["low", "medium", "high"]
SHORT = {m: m.replace("claude-", "") for m in MODELS}


def rank(xs):
    """Average ranks, ties shared. Used for Spearman."""
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    out = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        r = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            out[order[k]] = r
        i = j + 1
    return out


def pearson(xs, ys):
    n = len(xs)
    if n < 3:
        return float("nan")
    mx, my = mean(xs), mean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    dy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if dx == 0 or dy == 0:
        return float("nan")
    return num / (dx * dy)


def spearman(xs, ys):
    return pearson(rank(xs), rank(ys))


def perm_corr(xs, ys, n=10000, seed=11):
    """Two sided permutation test on a Spearman correlation."""
    import random
    rho = spearman(xs, ys)
    if math.isnan(rho):
        return rho, float("nan")
    rng = random.Random(seed)
    ry = list(ys)
    hits = 0
    for _ in range(n):
        rng.shuffle(ry)
        r = spearman(xs, ry)
        if not math.isnan(r) and abs(r) >= abs(rho) - 1e-12:
            hits += 1
    return rho, (hits + 1) / (n + 1)


def pair_table(ok):
    """Per pair differences, with the generation length that produced them.

    Keyed (model, effort, bias, pair_id). Carries the signed difference on
    both measures and the mean output tokens over every response in the pair,
    both conditions together, which is the pair's deliberation budget as
    actually spent rather than as requested.
    """
    cells = collections.defaultdict(lambda: collections.defaultdict(list))
    toks = collections.defaultdict(list)
    for r in ok:
        key = (r["model"], r["effort"], r["bias"], r["pair_id"])
        cells[key][r["condition"]].append(r)
        t = r.get("output_tokens")
        if isinstance(t, (int, float)):
            toks[key].append(float(t))
    out = {}
    for key, byc in cells.items():
        bias = key[2]
        base, treat, _ = DIRECTIONS[bias]
        if base not in byc or treat not in byc:
            continue
        def m(rows, f):
            vs = [f(x) for x in rows]
            vs = [v for v in vs if isinstance(v, (int, float))]
            return mean(vs) if vs else None
        cat_b = m(byc[base], lambda x: config.ACTION_SCORE[x["action"]])
        cat_t = m(byc[treat], lambda x: config.ACTION_SCORE[x["action"]])
        def pct(x):
            v = x.get("pct_of_position_to_sell")
            if x.get("pct_out_of_range") or not isinstance(v, (int, float)):
                return None
            return v if 0 <= v <= 100 else None
        pct_b = m(byc[base], pct)
        pct_t = m(byc[treat], pct)
        out[key] = dict(
            cat=snap(cat_t - cat_b) if None not in (cat_b, cat_t) else None,
            pct=snap(pct_t - pct_b) if None not in (pct_b, pct_t) else None,
            tokens=mean(toks[key]) if toks[key] else None,
            n=len(byc[base]) + len(byc[treat]),
        )
    return out


def q1_length_or_label(pairs):
    """Within a fixed effort label, does a longer answer carry less bias?

    The effort label is held constant inside every cell, so any relationship
    between length and bias here is not the label's doing. A negative
    correlation means the model's own choice to deliberate further on a
    particular item is associated with less bias on that item, which is the
    dial reading. A null means the label moved bias without length tracking
    it item by item, which is closer to the ceiling reading.
    """
    print("\n" + "=" * 78)
    print("Q1. Length or label? Pair level correlation between generation")
    print("    length and absolute bias, computed INSIDE each model x effort")
    print("    cell so the effort label cannot drive it.")
    print("=" * 78)
    print(f"{'model':14s} {'effort':7s} {'measure':8s} {'rho':>7s} "
          f"{'p':>8s}  {'pairs':>6s}  mean tokens")
    rows = []
    for mname in MODELS:
        for eff in EFFORTS:
            sub = [(v["tokens"], v) for k, v in pairs.items()
                   if k[0] == mname and k[1] == eff and v["tokens"] is not None]
            for measure in ("cat", "pct"):
                xs = [t for t, v in sub if v[measure] is not None]
                ys = [abs(v[measure]) for t, v in sub if v[measure] is not None]
                if len(xs) < 10:
                    continue
                rho, p = perm_corr(xs, ys)
                rows.append((mname, eff, measure, rho, p, len(xs)))
                print(f"{SHORT[mname]:14s} {eff:7s} {measure:8s} {rho:+7.3f} "
                      f"{p:8.4f}  {len(xs):6d}  {mean(xs):11.1f}")
    # Pooled across cells, with the cell mean removed from both variables so
    # that only within cell variation contributes. This is the test that
    # separates length from label: between cell differences, which is where
    # the label lives, are differenced out entirely.
    print("\n  Pooled, cell means removed from both variables, so only")
    print("  within cell variation contributes and the label is differenced out:")
    for measure in ("cat", "pct"):
        xs, ys = [], []
        for mname in MODELS:
            for eff in EFFORTS:
                sub = [v for k, v in pairs.items()
                       if k[0] == mname and k[1] == eff
                       and v["tokens"] is not None and v[measure] is not None]
                if len(sub) < 10:
                    continue
                mt = mean([v["tokens"] for v in sub])
                mb = mean([abs(v[measure]) for v in sub])
                xs += [v["tokens"] - mt for v in sub]
                ys += [abs(v[measure]) - mb for v in sub]
        rho, p = perm_corr(xs, ys)
        print(f"    {measure:8s} rho {rho:+.3f}  p {p:.4f}  over {len(xs)} pairs")
        rows.append(("POOLED", "within", measure, rho, p, len(xs)))
    return rows


def q2_interaction(pairs):
    """Is the effort slope different across models?

    The headline reading of the registered table is that deliberation
    substitutes for capability: the weakest model gains most from effort and
    the strongest gains nothing because it has nothing left to gain. That is
    an interaction claim and the registered analysis never tested one. The
    slope here is the change in absolute effect per effort step, fitted over
    the three levels by least squares, bootstrapped over pairs so the
    interval respects the pairing.
    """
    print("\n" + "=" * 78)
    print("Q2. Does the effort slope differ by model? Absolute effect per")
    print("    effort step, and the between model contrasts.")
    print("=" * 78)
    import random
    out = {}
    for measure in ("cat", "pct"):
        print(f"\n  {measure}")
        slopes = {}
        for mname in MODELS:
            # Slope of |effect| on effort coded 0, 1, 2, pooling families.
            by_eff = {}
            for i, eff in enumerate(EFFORTS):
                vals = [abs(v[measure]) for k, v in pairs.items()
                        if k[0] == mname and k[1] == eff
                        and v[measure] is not None]
                by_eff[i] = vals
            xs = sorted(by_eff)
            mx = mean(xs)
            ms = {i: mean(by_eff[i]) for i in xs}
            my = mean(list(ms.values()))
            num = sum((i - mx) * (ms[i] - my) for i in xs)
            den = sum((i - mx) ** 2 for i in xs)
            slope = num / den if den else float("nan")
            # Bootstrap the slope by resampling pairs within each effort
            # level. The seed is per model on purpose. Sharing one seed makes
            # every model resample the same pair indices, which correlates the
            # three bootstrap series and shrinks the variance of their
            # differences to almost nothing. A contrast built from that
            # excludes zero no matter what the data say.
            rng = random.Random(23 + 101 * MODELS.index(mname))
            boot = []
            for _ in range(2000):
                bs = {}
                for i in xs:
                    v = by_eff[i]
                    bs[i] = mean([v[rng.randrange(len(v))] for _ in range(len(v))])
                byb = mean(list(bs.values()))
                nb = sum((i - mx) * (bs[i] - byb) for i in xs)
                boot.append(nb / den if den else float("nan"))
            # Keep the draws in draw order and sort a copy for the
            # quantiles. Sorting in place and then differencing two models'
            # stored arrays compares order statistic to order statistic,
            # which is not a contrast at all: two sorted samples track each
            # other, so their difference has almost no spread and every
            # contrast comes out excluding zero.
            ordered = sorted(boot)
            lo = ordered[int(0.025 * len(ordered))]
            hi = ordered[int(0.975 * len(ordered)) - 1]
            slopes[mname] = (slope, lo, hi, boot)
            print(f"    {SHORT[mname]:14s} slope {slope:+8.3f} per effort step "
                  f"[{lo:+8.3f}, {hi:+8.3f}]  "
                  f"low {ms[0]:7.3f} -> high {ms[2]:7.3f}")
        # Contrasts. A difference of slopes whose interval excludes zero is
        # evidence that effort does different work in different models, which
        # is the substitution claim stated as something testable.
        print("    contrasts, difference of slopes:")
        for a, b in [("claude-haiku-5-5", "claude-opus-5-5"),
                     ("claude-haiku-5-5", "claude-sonnet-5-5"),
                     ("claude-sonnet-5-5", "claude-opus-5-5")]:
            # Paired across draw index, with independent seeds per model,
            # so this is the bootstrap distribution of the slope difference.
            d = sorted(x - y for x, y in zip(slopes[a][3], slopes[b][3]))
            lo, hi = d[int(0.025 * len(d))], d[int(0.975 * len(d)) - 1]
            diff = slopes[a][0] - slopes[b][0]
            flag = "excludes zero" if (lo > 0 or hi < 0) else ""
            print(f"      {SHORT[a]:12s} minus {SHORT[b]:12s} "
                  f"{diff:+8.3f} [{lo:+8.3f}, {hi:+8.3f}]  {flag}")
        out[measure] = {m: slopes[m][:3] for m in slopes}
    return out


def q2b_compression(pairs):
    """Does effort remove bias, or redistribute it across families?

    Haiku's pooled slope is flat while its disposition effect collapses by 36
    points, which can only happen if other families moved the other way. Two
    different mechanisms produce a flat pooled slope: effort does nothing, or
    effort pulls every family toward a common middle, taking the large
    effects down and pushing the small ones up. They are distinguished by
    the spread of the family level effects, not by their mean.

    Regression to the mean would produce part of this on its own, since the
    low effort estimate carries noise that the change then inherits with the
    opposite sign. The spread comparison is reported because it does not
    depend on the baseline level the way a change on level regression does.
    """
    print("\n" + "=" * 78)
    print("Q2b. Removal or redistribution? Spread of the nine family effects")
    print("     within each model, at each effort level.")
    print("=" * 78)
    for measure in ("cat", "pct"):
        print(f"\n  {measure}")
        print(f"    {'model':14s} {'low':>18s} {'medium':>18s} {'high':>18s}")
        for mname in MODELS:
            cells = []
            for eff in EFFORTS:
                fam = []
                for bias in DIRECTIONS:
                    ds = [v[measure] for k, v in pairs.items()
                          if k[0] == mname and k[1] == eff and k[2] == bias
                          and v[measure] is not None]
                    if ds:
                        fam.append(abs(mean(ds)))
                mu = mean(fam)
                sd = math.sqrt(mean([(x - mu) ** 2 for x in fam]))
                cells.append((mu, sd, max(fam), min(fam)))
            txt = "  ".join(f"mean {c[0]:5.2f} sd {c[1]:5.2f}" for c in cells)
            print(f"    {SHORT[mname]:14s} {txt}")
            rng_txt = "  ".join(f"max {c[2]:5.2f} min {c[3]:5.2f}"
                                for c in cells)
            print(f"    {'':14s} {rng_txt}")
        print("    A mean that holds while the sd falls is redistribution:")
        print("    large effects shrink and small ones grow.")
        # Bootstrap the change in spread from low to high. Resampling is over
        # pairs within each family and effort level, so the interval carries
        # the sampling error of the nine family estimates that the spread is
        # computed from, not just the spread of nine fixed numbers.
        import random
        print("    change in sd from low to high, bootstrapped over pairs:")
        for mname in MODELS:
            byef = {}
            for eff in ("low", "high"):
                byef[eff] = []
                for bias in DIRECTIONS:
                    ds = [v[measure] for k, v in pairs.items()
                          if k[0] == mname and k[1] == eff and k[2] == bias
                          and v[measure] is not None]
                    byef[eff].append(ds)
            def sd_of(sample):
                mags = [abs(mean(x)) for x in sample if x]
                mu = mean(mags)
                return math.sqrt(mean([(x - mu) ** 2 for x in mags]))
            obs = sd_of(byef["high"]) - sd_of(byef["low"])
            rng = random.Random(41 + MODELS.index(mname))
            draws = []
            for _ in range(2000):
                res = {}
                for eff in ("low", "high"):
                    res[eff] = [[x[rng.randrange(len(x))] for _ in range(len(x))]
                                if x else [] for x in byef[eff]]
                draws.append(sd_of(res["high"]) - sd_of(res["low"]))
            draws.sort()
            lo = draws[int(0.025 * len(draws))]
            hi = draws[int(0.975 * len(draws)) - 1]
            flag = "excludes zero" if (lo > 0 or hi < 0) else ""
            print(f"      {SHORT[mname]:14s} {obs:+8.3f} "
                  f"[{lo:+8.3f}, {hi:+8.3f}]  {flag}")


def q3_jackknife(pairs):
    """Does the headline survive losing any single pair?

    Twelve pairs is few enough that one could be carrying the result. This
    drops each in turn and refits. If every leave one out interval still
    excludes zero, no single item is responsible.
    """
    print("\n" + "=" * 78)
    print("Q3. Leave one pair out on the four cells that survived Holm.")
    print("=" * 78)
    targets = [("claude-haiku-5-5", "low", "disposition", "cat"),
               ("claude-haiku-5-5", "low", "disposition", "pct"),
               ("claude-opus-5-5", "high", "anchoring", "pct"),
               ("claude-opus-5-5", "high", "mental_accounting", "pct")]
    for mname, eff, bias, measure in targets:
        ds = [v[measure] for k, v in pairs.items()
              if k[0] == mname and k[1] == eff and k[2] == bias
              and v[measure] is not None]
        full = mean(ds)
        lo0, hi0 = bootstrap_ci(ds)
        worst = None
        n_excl = 0
        for i in range(len(ds)):
            sub = ds[:i] + ds[i + 1:]
            lo, hi = bootstrap_ci(sub)
            if lo > 0 or hi < 0:
                n_excl += 1
            if worst is None or abs(mean(sub)) < abs(worst[0]):
                worst = (mean(sub), lo, hi, i)
        print(f"  {SHORT[mname]:14s} {eff:6s} {bias:20s} {measure}")
        print(f"    full      {full:+8.3f} [{lo0:+8.3f}, {hi0:+8.3f}]  "
              f"{len(ds)} pairs")
        print(f"    weakest   {worst[0]:+8.3f} [{worst[1]:+8.3f}, "
              f"{worst[2]:+8.3f}]  dropping pair {worst[3]}")
        print(f"    {n_excl} of {len(ds)} leave one out intervals still "
              f"exclude zero")
    print()


def q4_sonnet_medium(ok):
    """Is Sonnet's medium cell a distinct treatment level?

    Its generation length and its entropy both resemble its low cell. If the
    model barely spends more on medium than on low, then medium is not a
    weaker version of high, it is a second copy of low, and the bias peak
    there is a cell where the treatment did not land rather than a genuine
    non-monotonicity.
    """
    print("=" * 78)
    print("Q4. Sonnet's medium cell. Is it distinguishable from its low cell?")
    print("=" * 78)
    import random
    def toks(m, e):
        return [float(r["output_tokens"]) for r in ok
                if r["model"] == m and r["effort"] == e
                and isinstance(r.get("output_tokens"), (int, float))]
    for mname in MODELS:
        print(f"\n  {SHORT[mname]}")
        for a, b in [("low", "medium"), ("medium", "high"), ("low", "high")]:
            xa, xb = toks(mname, a), toks(mname, b)
            obs = mean(xb) - mean(xa)
            pool = xa + xb
            rng = random.Random(29)
            na = len(xa)
            hits = 0
            for _ in range(2000):
                rng.shuffle(pool)
                if abs(mean(pool[na:]) - mean(pool[:na])) >= abs(obs) - 1e-9:
                    hits += 1
            p = (hits + 1) / 2001
            ratio = mean(xb) / mean(xa) if mean(xa) else float("nan")
            # With 1,080 observations a side, a three token difference clears
            # any significance threshold, so the p value answers a question
            # nobody asked. Cohen's d is reported instead, because the claim
            # is that one of these contrasts is negligible in size, not that
            # it is indistinguishable from zero.
            ma, mb_ = mean(xa), mean(xb)
            va = mean([(x - ma) ** 2 for x in xa])
            vb = mean([(x - mb_) ** 2 for x in xb])
            sd = math.sqrt((va + vb) / 2) or float("nan")
            d = (mb_ - ma) / sd
            size = ("negligible" if abs(d) < 0.2 else
                    "small" if abs(d) < 0.5 else
                    "medium" if abs(d) < 0.8 else "large")
            print(f"    tokens {a:6s} -> {b:6s}  {ma:7.1f} -> "
                  f"{mb_:7.1f}  {ratio:5.2f}x  d {d:+6.2f} {size:11s} "
                  f"p {p:.4f}")


def q5_study_wide(pairs):
    """Holm across every cell at once, not within effort cells.

    The registered correction is within each model and effort cell across the
    nine families, which is the right family for a claim about one cell. A
    reader asking what survives across the whole study is asking a different
    question, and it deserves an answer rather than a defence of the
    registered choice.
    """
    print("\n" + "=" * 78)
    print("Q5. Study wide Holm over all 81 cells per measure, alongside the")
    print("    registered within cell correction.")
    print("=" * 78)
    for measure in ("cat", "pct"):
        rows = []
        for mname in MODELS:
            for eff in EFFORTS:
                for bias in DIRECTIONS:
                    ds = [v[measure] for k, v in pairs.items()
                          if k[0] == mname and k[1] == eff and k[2] == bias
                          and v[measure] is not None]
                    if not ds:
                        continue
                    eff_sz = mean(ds)
                    lo, hi = bootstrap_ci(ds)
                    p = permutation_p(ds)
                    nz = sum(1 for d in ds if abs(d) > 1e-9)
                    rows.append([mname, eff, bias, eff_sz, lo, hi, p, nz])
        adj = holm([r[6] for r in rows])
        surv = [(r, a) for r, a in zip(rows, adj) if a < 0.05]
        ci_only = [r for r, a in zip(rows, adj)
                   if a >= 0.05 and (r[4] > 0 or r[5] < 0)]
        best = min(r[6] for r in rows)
        need = 0.05 / len(rows)
        print(f"\n  {measure}: {len(surv)} of {len(rows)} cells survive "
              f"study wide Holm; {len(ci_only)} more have a bootstrap "
              f"interval excluding zero")
        print(f"    smallest p anywhere in the study {best:.5f}; the most "
              f"significant of {len(rows)} tests needs p < {need:.6f}")
        print(f"    with 12 pairs the sign flipping test cannot return a p "
              f"below {p_floor(12):.5f}, so a study wide Holm survivor is "
              f"out of reach by arithmetic, at any effect size")
        for r, a in sorted(surv, key=lambda x: x[1]):
            print(f"    {SHORT[r[0]]:14s} {r[1]:6s} {r[2]:20s} "
                  f"{r[3]:+8.3f} [{r[4]:+7.3f}, {r[5]:+7.3f}]  "
                  f"p_holm_study {a:.4f}  {r[7]}/12 moving")


def q6_inconsistency(ok):
    """Where do the two measures disagree?

    A response whose categorical answer and whose percentage contradict each
    other is a result about instruction following, and it is only
    interpretable if it is not spread evenly. Concentration in a model or an
    effort level says something; uniformity says it is noise.
    """
    print("\n" + "=" * 78)
    print("Q6. The 86 responses whose two measures disagree.")
    print("=" * 78)
    flagged = [r for r in ok if r.get("action_pct_inconsistent")]
    print(f"  {len(flagged)} of {len(ok)} responses, "
          f"{100 * len(flagged) / len(ok):.2f}%")
    for label, keyf in [("model", lambda r: SHORT[r["model"]]),
                        ("effort", lambda r: r["effort"]),
                        ("bias", lambda r: r["bias"]),
                        ("action", lambda r: r["action"])]:
        c = collections.Counter(keyf(r) for r in flagged)
        tot = collections.Counter(keyf(r) for r in ok)
        print(f"\n  by {label}:")
        for k, v in c.most_common():
            print(f"    {k:22s} {v:4d} of {tot[k]:5d}  "
                  f"{100 * v / tot[k]:5.2f}%")


def q7_variance(ok):
    """How much of the response variance is within item rather than between?

    The paper reports within item entropy as a result because temperature
    cannot be set. This states the same thing in variance terms: if most of
    the variance is between items, the instrument is measuring the stimulus;
    if a large share is within item, repeated sampling was necessary rather
    than decorative.
    """
    print("\n" + "=" * 78)
    print("Q7. Variance decomposition of the continuous measure.")
    print("=" * 78)
    print(f"{'model':14s} {'effort':7s} {'within':>9s} {'between':>9s} "
          f"{'within share':>13s}  mean entropy")
    for mname in MODELS:
        for eff in EFFORTS:
            groups = collections.defaultdict(list)
            acts = collections.defaultdict(collections.Counter)
            for r in ok:
                if r["model"] != mname or r["effort"] != eff:
                    continue
                v = r.get("pct_of_position_to_sell")
                if r.get("pct_out_of_range") or not isinstance(v, (int, float)):
                    continue
                groups[r["item_id"]].append(float(v))
                acts[r["item_id"]][r["action"]] += 1
            if not groups:
                continue
            grand = mean([v for vs in groups.values() for v in vs])
            within = mean([mean([(v - mean(vs)) ** 2 for v in vs])
                           for vs in groups.values() if len(vs) > 1])
            between = mean([(mean(vs) - grand) ** 2 for vs in groups.values()])
            share = within / (within + between) if (within + between) else 0.0
            ent = mean([entropy(c) for c in acts.values()])
            print(f"{SHORT[mname]:14s} {eff:7s} {within:9.2f} {between:9.2f} "
                  f"{100 * share:12.1f}%  {ent:12.3f}")


def main():
    rows = load_rows()
    ok = [r for r in rows if r.get("status") == "ok"]
    print(f"{len(ok):,} usable responses")
    pairs = pair_table(ok)
    print(f"{len(pairs):,} matched pairs across "
          f"{len(MODELS)} models x {len(EFFORTS)} effort levels x "
          f"{len(DIRECTIONS)} families")

    q1 = q1_length_or_label(pairs)
    q2 = q2_interaction(pairs)
    q2b_compression(pairs)
    q3_jackknife(pairs)
    q4_sonnet_medium(ok)
    q5_study_wide(pairs)
    q6_inconsistency(ok)
    q7_variance(ok)

    with open("data/exploratory.json", "w") as f:
        json.dump(dict(length_vs_label=q1, effort_slopes=q2), f, indent=2)
    print("\nwrote data/exploratory.json")


if __name__ == "__main__":
    main()
