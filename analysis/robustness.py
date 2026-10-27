"""Is the compression result real, or is it regression to the mean?

The paper's mechanism claim is that reasoning effort compresses the spread of
the nine family effects without moving their mean: the worst-behaved cue
improves most, the well-behaved ones barely move. Measured as the standard
deviation of the nine absolute family effects, the spread falls from low to
high effort in all six model by measure combinations.

That pattern has an innocent explanation that would sink the paper. Each
family effect is estimated from twelve pairs with five trials an arm, so each
carries sampling error. Sampling error inflates the spread of the estimates
above the spread of the truth, and it inflates an absolute value upward most
where the true effect is near zero. If the error is larger at low effort than
at high, the spread will fall from low to high even when nothing about the
model's bias has changed. Regression to the mean alone would produce the
headline.

exploratory.py names this threat in a docstring and does not test it. This
file tests it three ways.

  1. Noise corrected spread. The variance of the nine estimates is the
     variance of the truth plus the mean sampling variance of an estimate.
     Subtracting the second leaves an estimate of the first. If the fall in
     spread survives the subtraction at both effort levels, it is not a
     noise artifact.

  2. Permutation placebo. Shuffle the effort label among the responses to
     the same item, which destroys any real effect of effort while leaving
     every other feature of the data alone, and ask how often the spread
     then falls in all six combinations. This is the direct null for the
     6 of 6 claim.

  3. Leave one family out. Drop each family in turn and recount. A result
     carried by one family is a result about that family.

Not pre-registered. Run from the repository root:
    python3 analysis/robustness.py
"""

import collections
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from analysis.analyze import DIRECTIONS, load_rows, mean, snap

MODELS = list(config.MODELS)
EFFORTS = list(config.EFFORTS)
SHORT = {m: m.replace("claude-", "").replace("-5-5", "") for m in MODELS}
N_PERM = 2000
N_BOOT = 2000


def usable(rows):
    return [r for r in rows if r.get("status") == "ok"]


def pct_of(r):
    v = r.get("pct_of_position_to_sell")
    if r.get("pct_out_of_range") or not isinstance(v, (int, float)):
        return None
    return v if 0 <= v <= 100 else None


def cat_of(r):
    a = r.get("action")
    return config.ACTION_SCORE.get(a) if a in config.ACTION_SCORE else None


VALUE = {"cat": cat_of, "pct": pct_of}


def pair_diffs(rows, measure, effort_of=None):
    """Pair level differences, keyed (model, effort, family) -> [(diff, var)].

    var is the variance of that one pair's difference attributable to trial
    sampling alone, var(treat)/n + var(base)/n. It is the only part of the
    spread that is unambiguously error. The variance across pairs within a
    family is larger than this, and the excess is real: it is the family's
    effect differing from one item to the next, which is a property of the
    model and not a measurement fault.

    effort_of lets the caller override the effort label on a response, which
    is what the permutation placebo needs. Everything else about the row,
    including which item and condition it answered, is untouched.
    """
    get = VALUE[measure]
    cells = collections.defaultdict(lambda: collections.defaultdict(list))
    for r in rows:
        eff = effort_of(r) if effort_of else r["effort"]
        key = (r["model"], eff, r["bias"], r["pair_id"])
        v = get(r)
        if v is not None:
            cells[key][r["condition"]].append(v)
    def var_of_mean(vs):
        if len(vs) < 2:
            return 0.0
        m = mean(vs)
        return (sum((v - m) ** 2 for v in vs) / (len(vs) - 1)) / len(vs)

    out = collections.defaultdict(list)
    for key, byc in cells.items():
        base, treat, _ = DIRECTIONS[key[2]]
        if base not in byc or treat not in byc:
            continue
        out[(key[0], key[1], key[2])].append((
            snap(mean(byc[treat]) - mean(byc[base])),
            var_of_mean(byc[treat]) + var_of_mean(byc[base])))
    return out


def spread(diffs, model, effort, families):
    """sd of the absolute family effects, with two floors under it.

    Returns (sd, var_total, var_trial, n_families).

    var_total is the mean squared standard error of a family estimate taken
    across its twelve pairs. It is the floor that treats item to item
    variation within a family as error, and subtracting it is too harsh:
    an effect that genuinely differs across the items of a family is a fact
    about the model.

    var_trial uses only the trial resampling variance of each pair's own
    difference. It is the floor that is unambiguously measurement error.
    The truth lies between the two corrections, so they bracket it.
    """
    mags, se_total, se_trial = [], [], []
    for fam in families:
        ds = diffs.get((model, effort, fam))
        if not ds or len(ds) < 2:
            continue
        vals = [d for d, _ in ds]
        m = mean(vals)
        mags.append(abs(m))
        v = sum((d - m) ** 2 for d in vals) / (len(vals) - 1)
        se_total.append(v / len(vals))
        se_trial.append(mean([tv for _, tv in ds]) / len(ds))
    if len(mags) < 2:
        return float("nan"), float("nan"), float("nan"), len(mags)
    mu = mean(mags)
    sd = math.sqrt(sum((x - mu) ** 2 for x in mags) / len(mags))
    return sd, mean(se_total), mean(se_trial), len(mags)


def corrected_sd(sd, noise_var):
    """Spread with the sampling noise component removed.

    var(estimates) = var(truth) + mean sampling var, so the corrected
    variance is the difference. A negative difference means the observed
    spread is no larger than sampling error alone would produce; it is
    reported as zero, and flagged, rather than hidden as a nan.
    """
    v = sd * sd - noise_var
    return math.sqrt(v) if v > 0 else 0.0


def report_corrected(diffs_by_measure, families):
    print("\n" + "=" * 78)
    print("1. Noise corrected spread of the nine family effects.")
    print("   raw sd, the sampling noise floor under it, and the sd that")
    print("   remains once the floor is removed.")
    print("=" * 78)
    verdict = {}
    for measure, diffs in diffs_by_measure.items():
        print(f"\n  {measure}")
        for m in MODELS:
            cells = []
            for eff in EFFORTS:
                sd, nv, tv, n = spread(diffs, m, eff, families)
                cells.append((eff, sd, nv, corrected_sd(sd, nv), tv,
                              corrected_sd(sd, tv), n))
            for eff, sd, nv, cs, tv, ct, _ in cells:
                print(f"    {SHORT[m]:10s} {eff:7s} raw {sd:7.3f}  "
                      f"trial floor {math.sqrt(tv):7.3f} -> {ct:7.3f}  "
                      f"harsh floor {math.sqrt(nv):7.3f} -> {cs:7.3f}")
            raw_falls = cells[-1][1] < cells[0][1]
            trial_falls = cells[-1][5] < cells[0][5]
            harsh_falls = cells[-1][3] < cells[0][3]
            verdict[(measure, m)] = (raw_falls, trial_falls, harsh_falls)
            print(f"    {SHORT[m]:10s} low to high: raw "
                  f"{'falls' if raw_falls else 'does not fall'}, "
                  f"trial corrected "
                  f"{'falls' if trial_falls else 'does not fall'}, "
                  f"harsh corrected "
                  f"{'falls' if harsh_falls else 'does not fall'}")
            print()
    nraw = sum(1 for v in verdict.values() if v[0])
    ntri = sum(1 for v in verdict.values() if v[1])
    nhar = sum(1 for v in verdict.values() if v[2])
    print(f"  spread falls low to high in {nraw}/6 raw, {ntri}/6 after "
          f"removing trial noise only,\n  {nhar}/6 after also removing "
          f"item to item variation within a family.")
    return verdict


def report_permutation(rows, families):
    print("\n" + "=" * 78)
    print("2. Permutation placebo. The effort label is shuffled among the")
    print("   responses to the same item within a model, which destroys any")
    print("   real effect of effort and keeps everything else. How often")
    print("   does the spread then fall in all six combinations?")
    print("=" * 78)

    obs = 0
    real = {}
    for measure in ("cat", "pct"):
        d = pair_diffs(rows, measure)
        for m in MODELS:
            lo, _, _, _ = spread(d, m, "low", families)
            hi, _, _, _ = spread(d, m, "high", families)
            real[(measure, m)] = hi - lo
            if hi < lo:
                obs += 1
    print(f"\n  observed: spread falls in {obs}/6")
    for k in sorted(real):
        print(f"    {k[0]:4s} {SHORT[k[1]]:10s} change {real[k]:+8.4f}")

    # Pool the responses that answered the same item in the same model, then
    # redeal the effort labels among them. Each cell keeps its size, so the
    # permuted data has the same shape as the real data.
    groups = collections.defaultdict(list)
    for i, r in enumerate(rows):
        groups[(r["model"], r["item_id"])].append(i)

    rng = random.Random(1789)
    hits_all6, counts = 0, collections.Counter()
    bigger = collections.Counter()
    for _ in range(N_PERM):
        label = {}
        for g in groups.values():
            effs = [rows[i]["effort"] for i in g]
            rng.shuffle(effs)
            for i, e in zip(g, effs):
                label[i] = e
        idx = {id(rows[i]): label[i] for i in label}
        eff_of = (lambda r, idx=idx: idx.get(id(r), r["effort"]))
        n_fall = 0
        for measure in ("cat", "pct"):
            d = pair_diffs(rows, measure, effort_of=eff_of)
            for m in MODELS:
                lo, _, _, _ = spread(d, m, "low", families)
                hi, _, _, _ = spread(d, m, "high", families)
                ch = hi - lo
                if ch < 0:
                    n_fall += 1
                if ch <= real[(measure, m)]:
                    bigger[(measure, m)] += 1
        counts[n_fall] += 1
        if n_fall == 6:
            hits_all6 += 1

    print(f"\n  under the placebo, {N_PERM:,} shuffles:")
    for k in sorted(counts):
        print(f"    spread fell in {k}/6: {counts[k]:5d} "
              f"({counts[k] / N_PERM:6.2%})")
    print(f"\n  p(all six fall by chance) = {hits_all6 / N_PERM:.4f} "
          f"({hits_all6}/{N_PERM})")
    # Iterate the cells, not the counter. A cell no shuffle matched has no
    # key in the counter, and printing only the counter's keys drops exactly
    # the strongest results, which reads as a missing row rather than a
    # p value of zero.
    print("\n  per cell, p(placebo change this negative or more):")
    for k in sorted(real):
        hits = bigger[k]
        shown = (f"< {1 / N_PERM:.4f}" if hits == 0
                 else f"= {hits / N_PERM:.4f}")
        print(f"    {k[0]:4s} {SHORT[k[1]]:10s} p {shown}  "
              f"({hits}/{N_PERM} shuffles at least this negative)")
    return hits_all6 / N_PERM


def report_loo(diffs_by_measure, families):
    print("\n" + "=" * 78)
    print("3. Leave one family out. Drop each family and recount how many")
    print("   of the six combinations still show a falling spread.")
    print("=" * 78)
    for drop in [None] + list(families):
        keep = [f for f in families if f != drop]
        n = 0
        for measure, diffs in diffs_by_measure.items():
            for m in MODELS:
                lo, _, _, _ = spread(diffs, m, "low", keep)
                hi, _, _, _ = spread(diffs, m, "high", keep)
                if hi < lo:
                    n += 1
        name = "all nine" if drop is None else f"without {drop}"
        print(f"    {name:28s} {n}/6")


def main():
    rows = usable(load_rows())
    print(f"{len(rows):,} usable responses")
    families = [f for f in DIRECTIONS]
    diffs_by_measure = {m: pair_diffs(rows, m) for m in ("cat", "pct")}
    report_corrected(diffs_by_measure, families)
    p = report_permutation(rows, families)
    report_loo(diffs_by_measure, families)
    print("\n" + "=" * 78)
    print("Read this as follows. The compression claim survives only if the")
    print("corrected spread still falls, the placebo p is small, and the")
    print("count does not collapse when one family is dropped. If the")
    print("corrected spread does not fall, the honest conclusion is that")
    print("the design cannot separate compression from regression to the")
    print("mean, and the claim has to be stated as a conjecture.")
    print("=" * 78)
    return p


if __name__ == "__main__":
    main()
