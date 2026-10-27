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
    for w in sorted(config.WAVES):
        rows = load_rows([w])
        ok = [r for r in rows if r.get("status") == "ok"]
        print(f"wave {w}: {len(rows):,} responses, {len(ok):,} usable")
        per_wave[w] = diffs_by_cell(ok)
        readings[w] = cell_rows(per_wave[w], f"wave{w}")

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
            print(f"  WARNING wave {w} is missing {len(miss)} of "
                  f"{len(full)} model by effort cells: "
                  f"{', '.join(m.replace('claude-', '') + '/' + e for m, e in miss)}")
        print("  the readings below compare different sets of models, not "
              "different items. Finish collection before quoting them.")

    pooled_rows = load_rows(tuple(sorted(config.WAVES)))
    pooled_ok = [r for r in pooled_rows if r.get("status") == "ok"]
    print(f"pooled: {len(pooled_rows):,} responses, {len(pooled_ok):,} usable")
    pooled = diffs_by_cell(pooled_ok)
    readings["pooled"] = cell_rows(pooled, "pooled")

    print()
    print_reading(readings[1], "Wave 1 alone",
                  "the registered result, twelve pairs per cell")
    print()
    print_reading(readings[2], "Wave 2 alone",
                  "out of sample, on items chosen after wave 1 was read")
    print()
    print_reading(readings["pooled"], "Pooled",
                  "twenty four pairs per cell, the powered reading")

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
        row = []
        for label, src in ((f"wave {w}", per_wave[w])
                           for w in sorted(config.WAVES)):
            row.append((label, [d for (m, _, _, b), ds in src.items()
                                if m == mname and b == "disposition"
                                for d in ds]))
        row.append(("pooled", [d for (m, _, _, b), ds in pooled.items()
                               if m == mname and b == "disposition"
                               for d in ds]))
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
               disposition_aggregate=head)
    with open(OUT_JSON, "w") as f:
        json.dump(out, f, indent=2)
    print(f"\nwrote {OUT_JSON}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
