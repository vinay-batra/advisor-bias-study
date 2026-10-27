"""Wave 2 against wave 1: did the result hold on items it had never seen?

Wave 2 doubles the design, twelve further matched pairs per family on top of
wave 1's twelve, and the reason it exists is power: at twelve pairs most cells
cannot reach a corrected p below 0.05 no matter how large the effect, because
the permutation test over twelve signs has a floor above it. Pooling to
twenty four lowers that floor.

Pooling is also the move a reader should be most suspicious of, which is what
this file is for. Wave 2 was decided after wave 1 had been read, and its items
are new rather than repeats, so the two waves differ in two ways at once:
sampling noise, and the items themselves. That makes wave 2 a test of whether
the finding survives a different draw of scenarios, which is a stronger thing
to pass than a repeat measurement and a weaker thing to interpret, because a
disagreement cannot be attributed to noise alone.

So the waves are reported apart before they are reported together. Three
readings, in the order a sceptical reader wants them:

  wave 1 alone     the registered result, unchanged
  wave 2 alone     the out-of-sample reading, on items chosen after the fact
  pooled           twenty four pairs, the only reading with the power the
                   design wanted

and then the agreement between the first two: sign agreement, the rank
correlation of the cell effects, how many of wave 1's significant cells come
back significant and same signed, and how many cells differ between waves by
more than a two sample bootstrap can explain. That last count is the one to
watch. Under a true replication it should sit near five percent of cells. Far
above, and the item set is doing work the paper would be attributing to the
model.

Nothing here is a registered quantity. The registered analysis is wave 1, and
reproducing it is the regression test in analyze.py.

Deterministic. Run from the repo root, after both waves are collected:

    .venv/bin/python analysis/replication.py
"""

import collections
import json
import math
import os
import statistics
import sys

sys.path.insert(0, ".")

import config
from analysis.analyze import (
    N_BOOT, ZERO_TOL, bootstrap_ci, holm, load_rows, mean, p_floor,
    permutation_p, snap,
)
from analysis.directions import DIRECTIONS
from analysis.exploratory import perm_corr, spearman

# A seed of its own, so the two sample bootstrap below cannot be confused
# with the registered one sample bootstrap that produced the paper's
# intervals.
DIFF_SEED = 4201
# The slope below resamples cells rather than pairs, which is a third kind of
# draw, so it gets a third seed rather than borrowing either of the others.
# It stays on the pure Python generator whether or not numpy is installed,
# because 54 cells is small enough that there is nothing to gain and a second
# code path would be a second thing to trust.
SLOPE_SEED = 9901
OUT_JSON = "analysis/replication_output.json"


def pct_of(r):
    v = r.get("pct_of_position_to_sell")
    if r.get("pct_out_of_range") or not isinstance(v, (int, float)):
        return None
    return v if 0 <= v <= 100 else None


MEASURES = {
    "sell_tendency": lambda r: config.ACTION_SCORE[r["action"]],
    "pct_to_sell": pct_of,
}


def diffs_by_cell(rows):
    """Per pair differences, keyed by measure, model, effort and family.

    The same matched pair definition the registered analysis uses: a pair
    contributes one difference, the treatment condition's mean minus the
    baseline condition's, and a pair missing either side contributes nothing.
    Pair ids carry a wave tag, so a pooled call simply has twice as many of
    them in each cell.
    """
    vals = collections.defaultdict(list)
    for r in rows:
        if r.get("status") != "ok":
            continue
        for mname, get in MEASURES.items():
            v = get(r)
            if isinstance(v, (int, float)):
                vals[(mname, r["model"], r["effort"], r["bias"],
                      r["pair_id"], r["condition"])].append(float(v))

    out = collections.defaultdict(list)
    seen = {(m, mo, e, b, p) for m, mo, e, b, p, _ in vals}
    for mname, model, effort, bias, pair_id in sorted(seen):
        base_c, treat_c, _ = DIRECTIONS[bias]
        b = vals.get((mname, model, effort, bias, pair_id, base_c))
        t = vals.get((mname, model, effort, bias, pair_id, treat_c))
        if b and t:
            out[(mname, model, effort, bias)].append(mean(t) - mean(b))
    return out


def complete_cells(diffs, pairs_expected):
    """Drop any cell that is not complete, and say which and why.

    Amendment 6. Wave 2 collection stopped partway when the API credit ran
    out, which left the three Opus efforts with roughly a third of their
    pairs and that third spread unevenly across the families, from seven
    pairs in one down to two in another. A cell resting on two pairs is not
    an estimate, and a reading in which one model rests on a different and
    much smaller item set than the others is not a comparison between models.

    The rule keys on completeness rather than on anything a cell says, and it
    was written down before any effect from the partial data was computed.
    Nothing is deleted: the responses stay on disk, and this is the only
    place that decides what they are used for.
    """
    keep, dropped = {}, []
    for k, ds in diffs.items():
        if len(ds) >= pairs_expected:
            keep[k] = ds
        else:
            dropped.append((k, len(ds)))
    return keep, dropped


def report_dropped(dropped, pairs_expected, label):
    if not dropped:
        return
    by_cell = collections.defaultdict(list)
    for (measure, model, effort, bias), n in dropped:
        by_cell[(model, effort)].append(n)
    print(f"  {label}: {len(dropped)} cells excluded under Amendment 6, "
          f"fewer than {pairs_expected} complete pairs")
    n_families = len(DIRECTIONS)
    for (model, effort), ns in sorted(by_cell.items()):
        # The pair total is what the exclusion rests on, so it is printed
        # rather than left to be summed from the range. Both measures drop
        # the same cells, so the per measure total is half the list.
        held = sum(ns) // len(MEASURES)
        print(f"    {model.replace('claude-', ''):<14} {effort:<7} "
              f"{len(ns):>2} cells, {min(ns)} to {max(ns)} pairs, "
              f"{held} of {pairs_expected * n_families} pairs held both "
              f"conditions")


def cell_rows(diffs, label):
    """One summary row per cell, with Holm applied the registered way.

    Holm runs within each measure, model and effort, across the nine
    families, which is the correction the pre-registration specifies. It has
    to be recomputed per reading rather than carried over, because the family
    of tests is the same size in each reading but the p values in it are not.
    """
    rows = []
    for (mname, model, effort, bias), ds in sorted(diffs.items()):
        if not ds:
            continue
        lo, hi = bootstrap_ci(ds)
        nz = sum(1 for d in ds if abs(d) >= ZERO_TOL)
        rows.append(dict(
            reading=label, measure=mname, model=model, effort=effort,
            bias=bias, n_pairs=len(ds), n_nonzero=nz, p_floor=p_floor(nz),
            effect=snap(mean(ds)), ci_low=lo, ci_high=hi,
            p_value=permutation_p(ds),
            significant=not (lo <= 0 <= hi),
        ))
    groups = collections.defaultdict(list)
    for r in rows:
        groups[(r["measure"], r["model"], r["effort"])].append(r)
    for g in groups.values():
        for r, a in zip(g, holm([x["p_value"] for x in g])):
            r["p_holm"] = a
            r["significant_holm"] = a < 0.05
    return rows


def diff_ci(a, b, n=N_BOOT, alpha=0.05):
    """Interval on the difference of two cells' mean differences.

    Each wave is resampled independently, with replacement, at its own size,
    and the difference of the two resampled means is recorded. It is the
    two sample analogue of the registered interval, and it answers the only
    question that matters here: whether the gap between the waves is larger
    than the pairs within them can account for.

    Numpy when present, because this runs for every cell in the design and
    the pure python path is slow enough to notice.
    """
    if not a or not b:
        return float("nan"), float("nan")
    try:
        import numpy as _np
        rng = _np.random.default_rng(DIFF_SEED)
        aa, bb = _np.asarray(a, float), _np.asarray(b, float)
        da = rng.integers(0, len(aa), size=(n, len(aa)))
        db = rng.integers(0, len(bb), size=(n, len(bb)))
        draws = bb[db].mean(axis=1) - aa[da].mean(axis=1)
        lo, hi = _np.quantile(draws, [alpha / 2, 1 - alpha / 2])
        return float(lo), float(hi)
    except ImportError:
        import random
        rng = random.Random(DIFF_SEED)
        draws = sorted(
            mean([rng.choice(b) for _ in b]) - mean([rng.choice(a) for _ in a])
            for _ in range(n))
        k = max(0, min(n - 1, int(round(alpha / 2 * (n - 1)))))
        return draws[k], draws[n - 1 - k]


def inference_cost(waves):
    """What the whole study consumed, for the ethics statement.

    The statement used to carry a dollar figure taken from a billing page,
    which no script reproduced and which stopped being true when the second
    wave ran. Tokens are in the released data, so they are reported instead
    and a reader can price them at whatever the list rates are when they
    read this.
    """
    print()
    print("=" * 78)
    print("What the study consumed")
    print("=" * 78)
    # Distinct custom_ids, not lines. Five requests were retried, so the
    # file holds five more rows than the design has items; the paper counts
    # items and the token totals count what was actually billed, which
    # includes the retries.
    n = tin = tout = 0
    for w in sorted(waves):
        rows = [json.loads(l) for l in open(config.WAVES[w]["responses"])]
        ids = {r.get("custom_id") for r in rows if r.get("custom_id")}
        i = sum(r["input_tokens"] for r in rows
                if isinstance(r.get("input_tokens"), int))
        o = sum(r["output_tokens"] for r in rows
                if isinstance(r.get("output_tokens"), int))
        print(f"  wave {w}  {len(ids):>6,} requests   "
              f"input {i:>12,}   output {o:>11,}"
              f"   ({len(rows) - len(ids)} retried)")
        n += len(ids); tin += i; tout += o
    print(f"  total  {n:>6,} requests   input {tin:>12,}   "
          f"output {tout:>11,}")
    print(f"  as the ethics statement quotes them: {tin / 1e6:.1f} million "
          f"input tokens and {tout / 1e6:.1f} million output tokens")
    return dict(requests=n, input_tokens=tin, output_tokens=tout)


def shrinkage_slope(x, y, n=10000):
    """The slope of wave 2 on wave 1, with an interval over cells.

    Galton's regression, stated in the paper's own units. If every wave 1
    estimate were the truth, wave 2 would scatter about the identity line and
    the slope would be one. Regression to the mean predicts a slope below
    one, and the slope is then the fraction of a wave 1 effect that was
    signal rather than a favourable item draw, measured on items wave 1 never
    saw. The quartile split is the same fact counted; this is it measured, and
    the interval is what decides whether a slope below one is more than noise.

    The resampling unit is the cell, because a cell is what the two waves
    pair up. Draws in which every resampled cell carries the same wave 1
    effect leave the slope undefined and are dropped rather than counted as
    zero, which would pull the interval toward it.
    """
    import random

    def fit(xs, ys):
        mx, my = mean(xs), mean(ys)
        sxx = sum((v - mx) ** 2 for v in xs)
        if sxx <= 0:
            return None
        b = sum((p - mx) * (q - my) for p, q in zip(xs, ys)) / sxx
        return b, my - b * mx

    k = len(x)
    whole = fit(x, y) if k >= 3 else None
    if not whole:
        nan = float("nan")
        return nan, (nan, nan), nan

    rng = random.Random(SLOPE_SEED)
    draws = []
    for _ in range(n):
        idx = [rng.randrange(k) for _ in range(k)]
        got = fit([x[i] for i in idx], [y[i] for i in idx])
        if got:
            draws.append(got[0])
    draws.sort()
    return (snap(whole[0]),
            (_pct(draws, 0.025), _pct(draws, 0.975)),
            snap(whole[1]))


def _pct(ordered, q):
    """The same percentile convention the registered bootstrap uses."""
    i = min(len(ordered) - 1, max(0, math.ceil(q * len(ordered)) - 1))
    return snap(float(ordered[i]))


def regression_to_mean(agree):
    """How much of a large wave 1 cell was the item draw rather than the model.

    The design-wide question first: across every cell both waves carry, does
    wave 2 come in smaller? If attenuation were a property of the second
    wave, most cells would shrink. The count is reported before anything is
    conditioned on, because a general attenuation and regression to the mean
    predict the same thing for the largest cells and opposite things here.

    Then the conditional question. Regression to the mean says the cells that
    shrink are the ones whose wave 1 estimate was largest, because a large
    estimate at twelve pairs is partly a large true effect and partly a
    favourable item draw, and only the first half comes back. That is a
    correlation between the wave 1 magnitude and the change in magnitude, and
    it is measured here rather than argued for: the items are new, so nothing
    about wave 1's draw is shared with wave 2's.

    The quartile split is the same fact in the units a reader uses. It is
    reported as a mean change rather than a ratio because a ratio of two
    noisy small numbers in the lower quartiles is unstable and says nothing.

    Not pre-registered. It could not have been: it needs a second wave.
    """
    print()
    print("=" * 78)
    print("Is the difference between the waves regression to the mean?")
    print("=" * 78)
    print("Not pre-registered. The items are new, so wave 1's draw is not "
          "shared with wave 2's.")
    out = {}
    for mname in MEASURES:
        sub = [a for a in agree if a["measure"] == mname]
        big = [abs(a["w1_effect"]) for a in sub]
        change = [abs(a["w2_effect"]) - abs(a["w1_effect"]) for a in sub]
        shrank = sum(1 for c in change if c < 0)
        rho, p_rho = perm_corr(big, change)
        order = sorted(range(len(sub)), key=lambda i: -big[i])
        q = max(len(order) // 4, 1)
        top, rest = order[:q], order[q:]
        t_mean = mean([change[i] for i in top])
        r_mean = mean([change[i] for i in rest])
        t_shrank = sum(1 for i in top if change[i] < 0)
        r_shrank = sum(1 for i in rest if change[i] < 0)
        print()
        print(f"  {mname}")
        print(f"    every cell           {shrank}/{len(sub)} came in smaller "
              f"in wave 2, against {len(sub) / 2:.0f} under no attenuation "
              f"at all")
        print(f"    conditional on size  rho(wave 1 magnitude, change in "
              f"magnitude) {rho:+.3f} (permutation p {p_rho:.4f})")
        print(f"    top quartile         {t_shrank}/{len(top)} shrank, "
              f"mean change {snap(t_mean):+.3f}")
        print(f"    the other three      {r_shrank}/{len(rest)} shrank, "
              f"mean change {snap(r_mean):+.3f}")
        slope, (s_lo, s_hi), icept = shrinkage_slope(
            [a["w1_effect"] for a in sub], [a["w2_effect"] for a in sub])
        print(f"    shrinkage slope      wave 2 on wave 1 {slope:+.3f} "
              f"[{s_lo:+.3f}, {s_hi:+.3f}], intercept {icept:+.3f}")
        print(f"                         an identity slope of 1 is "
              f"{'outside' if s_hi < 1 else 'inside'} that interval, so the "
              f"fraction of a wave 1 effect that is signal is "
              f"{slope:.3f}" + (f" and the rest was the draw"
                                if s_hi < 1 else " but not resolved from 1"))
        out[mname] = dict(n_cells=len(sub), n_smaller=shrank, rho=rho,
                          rho_p=p_rho, top_quartile_n=len(top),
                          top_quartile_shrank=t_shrank,
                          top_quartile_mean_change=snap(t_mean),
                          rest_n=len(rest), rest_shrank=r_shrank,
                          rest_mean_change=snap(r_mean),
                          slope=slope, slope_ci=[s_lo, s_hi],
                          intercept=icept)
    return out


def compression(per_wave, shared):
    """Does the effort compression of the family spread hold on new items.

    The paper's second finding is that the spread of the nine family effects
    within a model narrows as effort rises, measured as the standard
    deviation of the nine absolute family effects. The spread at low effort
    is the largest single number in the study, so it is exactly the quantity
    the regression above says should come back smaller, and the replication
    has to be read with that in hand rather than against it.
    """
    print()
    print("=" * 78)
    print("The compression of the family spread, by wave")
    print("=" * 78)
    print("Standard deviation of the nine absolute family effects, per "
          "model and effort.")
    models = sorted({k[1] for k in shared})
    out = []
    for mname in MEASURES:
        print()
        print(f"  {mname}")
        for mdl in models:
            for w in sorted(per_wave):
                sds = []
                for e in config.EFFORTS:
                    fam = [abs(mean(per_wave[w][k])) for k in per_wave[w]
                           if k[0] == mname and k[1] == mdl and k[2] == e]
                    sds.append(statistics.pstdev(fam) if len(fam) > 1
                               else float("nan"))
                if any(math.isnan(v) for v in sds):
                    continue
                fall = sds[-1] - sds[0]
                print(f"    wave {w}  {mdl.replace('claude-', ''):<10} "
                      + "  ".join(f"{e} {v:7.3f}"
                                  for e, v in zip(config.EFFORTS, sds))
                      + f"   low to high {fall:+7.3f}"
                      f"   {'falls' if fall < 0 else 'RISES'}")
                out.append(dict(measure=mname, model=mdl, wave=w,
                                spreads=[snap(v) for v in sds],
                                low_to_high=snap(fall), falls=fall < 0))
    last = max(per_wave)
    n = [o for o in out if o["wave"] == last]
    print()
    print(f"  out of sample the spread still falls in "
          f"{sum(1 for o in n if o['falls'])} of {len(n)} model by measure "
          f"combinations wave 2 covers")
    return out


def print_reading(rows, label, note):
    print("=" * 78)
    print(f"{label}: {note}")
    print("=" * 78)
    for mname in MEASURES:
        sub = [r for r in rows if r["measure"] == mname]
        if not sub:
            continue
        sig = sum(1 for r in sub if r["significant"])
        holm_sig = sum(1 for r in sub if r["significant_holm"])
        reach = sum(1 for r in sub if r["p_floor"] <= 0.05)
        print(f"  {mname:<14} {len(sub):>3} cells, {sig:>3} with an interval "
              f"clear of zero, {holm_sig:>2} surviving Holm, "
              f"{reach:>2} where a p below 0.05 is attainable at all")


def main():
    have = {w: os.path.exists(config.WAVES[w]["responses"])
            for w in sorted(config.WAVES)}
    missing = [w for w, ok in have.items() if not ok]
    if missing:
        raise SystemExit(
            f"wave {', '.join(str(w) for w in missing)} not collected yet: "
            f"{', '.join(config.WAVES[w]['responses'] for w in missing)}")

    # The pooled reading depends on custom_ids never colliding across waves,
    # because load_rows deduplicates by custom_id: a collision would silently
    # drop one wave's response in favour of the other's. id_offset is what
    # keeps them apart, and this is the check that it did.
    ids = collections.defaultdict(set)
    for w in sorted(config.WAVES):
        for line in open(config.WAVES[w]["responses"]):
            cid = json.loads(line).get("custom_id")
            if cid is not None:
                ids[cid].add(w)
    collisions = sorted(c for c, ws in ids.items() if len(ws) > 1)
    if collisions:
        raise SystemExit(
            f"{len(collisions)} custom_ids appear in more than one wave, "
            f"first {collisions[0]}: pooling would drop responses")
    print(f"{len(ids):,} distinct custom_ids, none shared between waves")

    per_wave, readings = {}, {}
    print()
    for w in sorted(config.WAVES):
        rows = load_rows([w])
        ok = [r for r in rows if r.get("status") == "ok"]
        bad = len(rows) - len(ok)
        print(f"wave {w}: {len(rows):,} responses, {len(ok):,} usable"
              + (f", {bad:,} errored" if bad else ""))
        want = config.WAVES[w]["pairs"]
        full, dropped = complete_cells(diffs_by_cell(ok), want)
        report_dropped(dropped, want, f"wave {w}")
        per_wave[w] = full
        readings[w] = cell_rows(full, f"wave{w}")

    # Every reading below compares waves cell for cell, so the waves have to
    # cover the same cells. A wave still collecting covers fewer, and the
    # comparison would then be between different sets of models rather than
    # between different items, which is not the question. Loud, because a
    # partial wave produces numbers that look finished.
    cover = {w: {(k[1], k[2]) for k in per_wave[w]}
             for w in sorted(per_wave)}
    full = set.union(*cover.values())
    short = {w: sorted(full - c) for w, c in cover.items() if full - c}
    if short:
        print()
        for w, miss in short.items():
            print(f"  wave {w} covers {len(full) - len(miss)} of {len(full)} "
                  f"model by effort cells. Not covered: "
                  f"{', '.join(m.replace('claude-', '') + '/' + e for m, e in miss)}")
        print("  every comparison below is restricted to the cells both "
              "waves cover, so it is a comparison between item sets rather "
              "than between models. The models a wave does not cover are "
              "absent from it, not estimated from part of it.")

    pooled_rows = load_rows(tuple(sorted(config.WAVES)))
    pooled_ok = [r for r in pooled_rows if r.get("status") == "ok"]
    print(f"pooled: {len(pooled_rows):,} responses, {len(pooled_ok):,} usable")
    # Amendment 6 applies to the pooled reading through the same rule. A cell
    # whose wave 2 half was incomplete pools to wave 1's twelve pairs rather
    # than to twelve plus a ragged remainder, so the model whose wave 2 did
    # not finish keeps wave 1's precision and no more. Which cells those are
    # is printed, because the power claim below is only true of the rest.
    pooled_all = diffs_by_cell(pooled_ok)
    partial = {k for k in pooled_all
               if k not in per_wave[2] and k in per_wave[1]}
    pooled = {k: (per_wave[1][k] if k in partial else v)
              for k, v in pooled_all.items()}
    if partial:
        cells = sorted({(m, e) for _, m, e, _ in partial})
        print(f"  pooled: {len(partial)} cells pool to wave 1 alone, "
              f"their wave 2 half being incomplete: "
              + ", ".join(m.replace("claude-", "") + "/" + e
                          for m, e in cells))
    readings["pooled"] = cell_rows(pooled, "pooled")

    print()
    print_reading(readings[1], "Wave 1 alone",
                  "the registered result, twelve pairs per cell")
    print()
    print_reading(readings[2], "Wave 2 alone",
                  "out of sample, on items chosen after wave 1 was read")
    print()
    print_reading(readings["pooled"], "Pooled",
                  "twenty four pairs per cell where both waves are complete, "
                  "twelve where only wave 1 is")

    # Agreement between the waves, cell by cell.
    key = lambda r: (r["measure"], r["model"], r["effort"], r["bias"])
    w1 = {key(r): r for r in readings[1]}
    w2 = {key(r): r for r in readings[2]}
    pl = {key(r): r for r in readings["pooled"]}
    shared = sorted(set(w1) & set(w2))

    agree = []
    for k in shared:
        a, b = w1[k], w2[k]
        d_lo, d_hi = diff_ci(per_wave[1][k], per_wave[2][k])
        same_sign = (a["effect"] > ZERO_TOL and b["effect"] > ZERO_TOL) or \
                    (a["effect"] < -ZERO_TOL and b["effect"] < -ZERO_TOL)
        agree.append(dict(
            measure=k[0], model=k[1], effort=k[2], bias=k[3],
            w1_effect=a["effect"], w1_ci=[a["ci_low"], a["ci_high"]],
            w1_significant=a["significant"],
            w1_significant_holm=a["significant_holm"],
            w2_effect=b["effect"], w2_ci=[b["ci_low"], b["ci_high"]],
            w2_significant=b["significant"],
            w2_significant_holm=b["significant_holm"],
            pooled_effect=pl[k]["effect"],
            pooled_ci=[pl[k]["ci_low"], pl[k]["ci_high"]],
            pooled_significant=pl[k]["significant"],
            pooled_significant_holm=pl[k]["significant_holm"],
            same_sign=same_sign,
            w2_ci_covers_w1=b["ci_low"] <= a["effect"] <= b["ci_high"],
            diff_ci=[d_lo, d_hi],
            diff_excludes_zero=not (d_lo <= 0 <= d_hi),
        ))

    print()
    print("=" * 78)
    print("Agreement between the waves")
    print("=" * 78)
    covered = sorted({(k[1], k[2]) for k in shared})
    print(f"  over the {len(shared)} cells both waves carry: "
          + ", ".join(m.replace("claude-", "") + "/" + e
                      for m, e in covered))
    summary = {}
    for mname in MEASURES:
        sub = [a for a in agree if a["measure"] == mname]
        # Sign agreement is only meaningful where there is a sign to agree
        # with. A cell whose wave 1 effect is exactly zero, and there are
        # several on the four point categorical scale, is counted apart
        # rather than scored as a disagreement.
        signed = [a for a in sub
                  if abs(a["w1_effect"]) > ZERO_TOL
                  and abs(a["w2_effect"]) > ZERO_TOL]
        same = sum(1 for a in signed if a["same_sign"])
        covers = sum(1 for a in sub if a["w2_ci_covers_w1"])
        het = sum(1 for a in sub if a["diff_excludes_zero"])
        w1_sig = [a for a in sub if a["w1_significant"]]
        strict = sum(1 for a in w1_sig
                     if a["w2_significant"] and a["same_sign"])
        directional = sum(1 for a in w1_sig if a["same_sign"])
        rho, p_rho = perm_corr([a["w1_effect"] for a in sub],
                               [a["w2_effect"] for a in sub])
        print(f"\n  {mname}")
        print(f"    sign agreement        {same}/{len(signed)} cells with a "
              f"nonzero effect in both waves point the same way")
        print(f"    wave 2 covers wave 1  {covers}/{len(sub)} cells, wave 2's "
              f"interval contains wave 1's point estimate")
        print(f"    rank correlation      {rho:+.3f} across {len(sub)} cells "
              f"(permutation p {p_rho:.4f})")
        print(f"    heterogeneity         {het}/{len(sub)} cells differ "
              f"between waves by more than the pairs explain "
              f"({100 * het / max(len(sub), 1):.1f}%, near 5% under a true "
              f"replication)")
        print(f"    wave 1 significant    {len(w1_sig)} cells, of which "
              f"{directional} keep the sign in wave 2 and {strict} are "
              f"significant again")
        print(f"      the second figure is bounded by wave 2's own power, "
              f"which is wave 1's: twelve pairs, the same floor. The sign "
              f"is what a wave this size can replicate.")
        summary[mname] = dict(
            n_cells=len(sub), n_signed=len(signed), same_sign=same,
            w2_covers_w1=covers, heterogeneous=het,
            rho=rho, rho_p=p_rho,
            w1_significant=len(w1_sig),
            w1_significant_same_sign=directional,
            w1_significant_replicated=strict)

    spent = inference_cost(config.WAVES)
    rtm = regression_to_mean(agree)
    spreads = compression(per_wave, shared)

    # The abstract leads with the disposition effect pooled over model and
    # effort, so that is the one number in the paper most exposed to a
    # failed replication. It is reported per wave for the same reason the
    # cells are: a reversal that holds only on the items that found it is
    # not a property of these models.
    print()
    print("=" * 78)
    print("The abstract's claim, by wave: disposition pooled over model "
          "and effort")
    print("=" * 78)
    print("Not a registered quantity. It pools across two factors the "
          "design varies.")
    head = {}
    for mname in MEASURES:
        print(f"\n  {mname}")
        # Wave 1 appears twice on purpose. Its first row is the paper's
        # own figure, over every cell. Its second is the only row wave 2 can
        # be set against, because wave 2 does not cover every model: without
        # it a difference in the model mix would read as a difference
        # between the waves.
        def pull(src, keys=None):
            return [d for k, ds in src.items()
                    if k[0] == mname and k[3] == "disposition"
                    and (keys is None or (k[1], k[2]) in keys)
                    for d in ds]

        both = {(k[1], k[2]) for k in set(per_wave[1]) & set(per_wave[2])}
        row = [("wave 1", pull(per_wave[1]))]
        if {(k[1], k[2]) for k in per_wave[1]} != both:
            row.append(("w1 same cells", pull(per_wave[1], both)))
        row.append(("wave 2", pull(per_wave[2])))
        row.append(("pooled", pull(pooled)))
        head[mname] = []
        for label, ds in row:
            if not ds:
                continue
            lo, hi = bootstrap_ci(ds)
            pos = sum(1 for d in ds if d > ZERO_TOL)
            neg = sum(1 for d in ds if d < -ZERO_TOL)
            print(f"    {label:<8} {snap(mean(ds)):+8.3f} "
                  f"[{lo:+8.3f}, {hi:+8.3f}]   {len(ds):>3} pairs, "
                  f"{pos:>3} positive, {neg:>3} negative")
            head[mname].append(dict(reading=label, effect=snap(mean(ds)),
                                    ci_low=lo, ci_high=hi, n_pairs=len(ds),
                                    n_positive=pos, n_negative=neg))
        # The two rows a reader should compare are the only two drawn from
        # the same cells, so the difference between them is computed rather
        # than left to be eyeballed off two overlapping intervals.
        by_label = {r["reading"]: r for r in head[mname]}
        a_lab = "w1 same cells" if "w1 same cells" in by_label else "wave 1"
        a = pull(per_wave[1], both if a_lab != "wave 1" else None)
        b = pull(per_wave[2])
        d_lo, d_hi = diff_ci(a, b)
        gap = snap(mean(b) - mean(a))
        print(f"    {'wave 2 minus ' + a_lab:<13} {gap:+8.3f} "
              f"[{d_lo:+8.3f}, {d_hi:+8.3f}]"
              f"{'   excludes zero' if not (d_lo <= 0 <= d_hi) else ''}")
        head[mname].append(dict(reading=f"wave 2 minus {a_lab}", effect=gap,
                                ci_low=d_lo, ci_high=d_hi,
                                excludes_zero=not (d_lo <= 0 <= d_hi)))

    # The four cells that survive Holm anywhere in wave 1 are the paper's
    # strongest claims, so they are printed individually rather than counted.
    print()
    print("=" * 78)
    print("Every cell that survives Holm in wave 1, as the other two "
          "readings see it")
    print("=" * 78)
    hits = [a for a in agree if a["w1_significant_holm"]]
    if not hits:
        print("  none")
    for a in hits:
        print(f"  {a['measure']:<14} {a['model'].replace('claude-',''):<14} "
              f"{a['effort']:<7} {a['bias']:<20}")
        for tag, eff, ci, sig, hol in (
                ("wave 1", a["w1_effect"], a["w1_ci"],
                 a["w1_significant"], a["w1_significant_holm"]),
                ("wave 2", a["w2_effect"], a["w2_ci"],
                 a["w2_significant"], a["w2_significant_holm"]),
                ("pooled", a["pooled_effect"], a["pooled_ci"],
                 a["pooled_significant"], a["pooled_significant_holm"])):
            print(f"      {tag}  {eff:+9.3f} [{ci[0]:+9.3f}, {ci[1]:+9.3f}]"
                  f"  {'ci' if sig else '  '} {'holm' if hol else ''}")
        print(f"      between waves {a['diff_ci'][0]:+.3f} to "
              f"{a['diff_ci'][1]:+.3f}"
              f"{', excludes zero' if a['diff_excludes_zero'] else ''}")

    # What the extra pairs bought. The floor is a property of how many pairs
    # moved, so it is the honest way to state the power gain: not how many
    # cells turned significant, but how many could.
    print()
    print("=" * 78)
    print("What the pairs bought: cells where a p below 0.05 is attainable")
    print("=" * 78)
    gain = {}
    for mname in MEASURES:
        line = []
        for label in (1, 2, "pooled"):
            sub = [r for r in readings[label] if r["measure"] == mname]
            reach = sum(1 for r in sub if r["p_floor"] <= 0.05)
            holm_sig = sum(1 for r in sub if r["significant_holm"])
            line.append((str(label), reach, len(sub), holm_sig))
        gain[mname] = [dict(reading=a, reachable=b, cells=c, holm=d)
                       for a, b, c, d in line]
        print(f"  {mname:<14} " + "   ".join(
            f"{a}: {b}/{c} reachable, {d} Holm" for a, b, c, d in line))

    out = dict(registered=False,
               waves=sorted(config.WAVES),
               readings={str(k): v for k, v in readings.items()},
               agreement=agree, summary=summary, power=gain,
               disposition_aggregate=head,
               regression_to_mean=rtm, compression=spreads,
               consumed=spent)
    with open(OUT_JSON, "w") as f:
        json.dump(out, f, indent=2)
    print(f"\nwrote {OUT_JSON}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
