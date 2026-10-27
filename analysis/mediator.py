"""The exogenous manipulation against the endogenous mediator it replaces.

This is the analysis that makes the paper's contribution visible rather than
merely asserted.

The closest prior work, Bini, Cong, Huang and Jin (2026), measures how much
analytical reasoning a response contains and uses that measure as a mediator:
responses that reason more are less biased, therefore reasoning debiases.
The objection in this paper's introduction is that their mediator is
endogenous. It is read off the same forward pass that produced the answer,
so a response that reasons more may be less biased because reasoning helped,
or may reason more because the item was one it found hard, or may write more
words precisely because it chose the answer that needs justifying. Setting
the reasoning budget through the API before the model sees the item breaks
all three loops at once.

That is an argument. This file turns it into a measurement, because the data
here contains both variables:

  the exogenous one, the effort parameter, set by the experimenter;
  an endogenous one, output_tokens, chosen by the model per response.

output_tokens is not Bini et al.'s self-reported analytical reasoning
indicator. It is the same class of variable: a within-cell, model-chosen
measure of how much reasoning a response contains, with no experimental
control over it. If the two classes of variable give the same answer, the
endogeneity objection costs nothing in practice and this paper's design is a
refinement. If they disagree, an endogenous mediator cannot be trusted and
the design is the finding.

Three estimates of "does more reasoning mean less bias", on the same rows:

  1. Exogenous. Compare the effort levels. This is the paper's result.

  2. Endogenous, between items. Inside one model by effort cell, split the
     pairs at the cell's median token count and compare the halves. Nothing
     is held fixed except the effort setting, so item difficulty is free to
     drive both the token count and the bias. This is the design an
     observational study is forced into.

  3. Endogenous, within item. Inside one model by effort cell, split the
     five trials of each single item at that item's own median token count
     and compare the halves. The stimulus, the family, the company and the
     effort setting are all identical across the split; the only thing that
     differs is how much the model happened to write on that sample. This
     removes item difficulty, which is the confound an observational study
     cannot remove, and leaves the one it still cannot: the answer and its
     justification length are chosen together.

Two statistics per half, both taken from the paper: the mean absolute family
effect, which is the level of bias, and the standard deviation of the nine
family effects, which is the spread the paper reports compressing.

Not pre-registered. Run from the repository root:
    python3 analysis/mediator.py
"""

import collections
import os
import random
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from analysis.analyze import DIRECTIONS, SEED, load_rows, mean, snap
from analysis.robustness import VALUE, usable

MODELS = list(config.MODELS)
EFFORTS = list(config.EFFORTS)
SHORT = {m: m.replace("claude-", "").replace("-5-5", "") for m in MODELS}
FAMILIES = list(DIRECTIONS)
N_BOOT = 2000
MIN_PER_SIDE = 2


def tokens_of(r):
    v = r.get("output_tokens")
    return v if isinstance(v, (int, float)) else None


# ---------------------------------------------------------------- descriptive


def token_overlap(rows):
    """How far the effort parameter actually separates the token counts.

    If the low effort and high effort token distributions overlap heavily,
    then effort and realised reasoning volume are different variables and an
    observational study of the second is not a study of the first. If they
    separate cleanly, the two are close to interchangeable and the
    endogeneity objection is academic.
    """
    by = collections.defaultdict(list)
    for r in rows:
        t = tokens_of(r)
        if t is not None:
            by[(r["model"], r["effort"])].append(t)

    print("Token counts by cell, and how far the parameter separates them")
    print("  model    effort   n     mean    sd     median   p10    p90")
    for m in MODELS:
        for e in EFFORTS:
            ts = sorted(by[(m, e)])
            if not ts:
                continue
            sd = statistics.pstdev(ts) if len(ts) > 1 else 0.0
            print("  %-8s %-7s %-5d %7.1f %6.1f %7.0f %6.0f %6.0f" % (
                SHORT[m], e, len(ts), mean(ts), sd, ts[len(ts) // 2],
                ts[int(0.10 * len(ts))], ts[int(0.90 * len(ts))]))
    print()
    print("  Share of low effort responses above the median high effort")
    print("  response, and of high effort responses below the median low")
    print("  one. A clean manipulation drives both toward zero.")
    for m in MODELS:
        lo, hi = sorted(by[(m, "low")]), sorted(by[(m, "high")])
        if not lo or not hi:
            continue
        med_hi, med_lo = hi[len(hi) // 2], lo[len(lo) // 2]
        above = sum(1 for t in lo if t > med_hi) / len(lo)
        below = sum(1 for t in hi if t < med_lo) / len(hi)
        print("  %-8s low above high median %5.1f%%   high below low median %5.1f%%"
              % (SHORT[m], 100 * above, 100 * below))
    print()



def leverage(rows):
    """How much each of the three designs moves the token count.

    This decides how each result should be read. A first pass at this file
    assumed the observational designs differed in leverage and that the
    experiment alone had enough; the measurement says otherwise, and the
    conclusion is stronger for it. Both observational splits separate their
    halves by about a fifth to two fifths of the gap the effort parameter
    opens, so they have the same leverage as each other and less than the
    experiment.

    That matters in two directions. A null from an observational design is
    then consistent with low power and is not evidence against the
    experiment. But low power does not produce a sign reversal, so where an
    observational design returns the wrong sign it is returning confounding,
    not noise. And because the two observational designs differ only in
    whether the item is held fixed, the difference between their answers
    localises that confounding.
    """
    by_cell = collections.defaultdict(list)
    for r in rows:
        t = tokens_of(r)
        if t is not None:
            by_cell[(r["model"], r["effort"])].append(t)

    heavy, light = between_item_halves(rows)
    long_set, short_set = within_item_halves(rows)

    def half_mean(m, e, ids):
        ts = [tokens_of(r) for r in rows
              if r["model"] == m and r["effort"] == e and r["custom_id"] in ids
              and tokens_of(r) is not None]
        return mean(ts) if ts else float("nan")

    print("Leverage on the token count, by design")
    print("  Each figure is the gap in mean output tokens between the halves")
    print("  the design compares, averaged over the three effort levels.")
    print("  model    between-item  within-item  exogenous   ratio to exogenous")
    for m in MODELS:
        gb = mean([half_mean(m, e, heavy) - half_mean(m, e, light) for e in EFFORTS])
        gw = mean([half_mean(m, e, long_set) - half_mean(m, e, short_set)
                   for e in EFFORTS])
        exo = mean(by_cell[(m, "high")]) - mean(by_cell[(m, "low")])
        print("  %-8s %12.1f %12.1f %10.1f   %.2f / %.2f"
              % (SHORT[m], gb, gw, exo, gb / exo, gw / exo))
    print()


# ------------------------------------------------------------------- splitting


def pair_effects(rows, measure, keep=None):
    """(model, effort, family) -> {pair_id: diff}, over the kept responses.

    keep is a predicate on a row. Restricting the rows is how both endogenous
    splits are taken: the arithmetic below is the paper's, and only the set of
    responses entering each pair mean changes.
    """
    get = VALUE[measure]
    cells = collections.defaultdict(lambda: collections.defaultdict(list))
    for r in rows:
        if keep is not None and not keep(r):
            continue
        v = get(r)
        if v is None:
            continue
        cells[(r["model"], r["effort"], r["bias"], r["pair_id"])][
            r["condition"]].append(v)

    out = collections.defaultdict(dict)
    for key, byc in cells.items():
        base, treat, _ = DIRECTIONS[key[2]]
        if base not in byc or treat not in byc:
            continue
        out[(key[0], key[1], key[2])][key[3]] = snap(
            mean(byc[treat]) - mean(byc[base]))
    return out


def summarise(effects, model, effort):
    """(mean absolute family effect, sd of family effects, n families)."""
    mags = []
    for fam in FAMILIES:
        ds = effects.get((model, effort, fam))
        if ds and len(ds) >= 2:
            mags.append(abs(mean(list(ds.values()))))
    if len(mags) < 2:
        return None
    return mean(mags), statistics.stdev(mags), len(mags)


def within_item_halves(rows):
    """Tag each response long or short against its own item's median.

    The median is taken within (model, effort, item_id), so it is the item's
    own five trials that set the threshold. An item whose trials tie at the
    median contributes nothing to either half rather than being forced into
    one, which keeps the two halves disjoint and comparably sized.
    """
    by_item = collections.defaultdict(list)
    for r in rows:
        t = tokens_of(r)
        if t is not None:
            by_item[(r["model"], r["effort"], r["item_id"])].append(t)

    med = {}
    for key, ts in by_item.items():
        ts = sorted(ts)
        med[key] = ts[len(ts) // 2] if len(ts) % 2 else (
            ts[len(ts) // 2 - 1] + ts[len(ts) // 2]) / 2

    long_set, short_set = set(), set()
    for r in rows:
        t = tokens_of(r)
        key = (r["model"], r["effort"], r["item_id"])
        if t is None or key not in med:
            continue
        if t > med[key]:
            long_set.add(r["custom_id"])
        elif t < med[key]:
            short_set.add(r["custom_id"])
    return long_set, short_set


def between_item_halves(rows):
    """Tag each response by whether its pair is a heavy or light token pair.

    The split is taken on the pair, not on the single item, and that is not a
    detail. Splitting on the item sends a pair's two arms to opposite halves
    whenever the model wrote more on one condition than the other, which is
    most of the time, and a half holding one arm of a pair cannot produce a
    difference for it. The first version of this file split on the item and
    silently left the between item design with no pair in common between the
    halves.

    So each pair's token count is the mean over both its arms and all their
    trials, and the pair is compared to the median of those means within the
    model by effort cell. A whole pair goes one way. Item difficulty is then
    free to move with the token count, which is the point of this design, but
    so is family composition, since families differ in how much the model
    writes about them; composition() reports that.
    """
    by_pair = collections.defaultdict(list)
    for r in rows:
        t = tokens_of(r)
        if t is not None:
            by_pair[(r["model"], r["effort"], r["pair_id"])].append(t)
    pair_mean = {k: mean(v) for k, v in by_pair.items()}

    by_cell = collections.defaultdict(list)
    for (m, e, _pair), mu in pair_mean.items():
        by_cell[(m, e)].append(mu)
    med = {}
    for key, mus in by_cell.items():
        mus = sorted(mus)
        med[key] = mus[len(mus) // 2]

    heavy, light = set(), set()
    for r in rows:
        key = (r["model"], r["effort"], r["pair_id"])
        if key not in pair_mean:
            continue
        mu, cut = pair_mean[key], med[(r["model"], r["effort"])]
        if mu > cut:
            heavy.add(r["custom_id"])
        elif mu < cut:
            light.add(r["custom_id"])
    return heavy, light



# ----------------------------------------------------------------- intervals


def boot_contrast(rows, measure, lo_keep, hi_keep, model, paired, n=N_BOOT):
    """Bootstrap CI for (bias in the high reasoning half) minus (the low one).

    Resampling is over pairs within family, the unit the paper bootstraps
    everywhere else. How the two halves are resampled depends on the design,
    and getting it wrong either breaks the comparison or overstates its
    precision.

    paired is for the within item design, where both halves hold the same
    pairs and differ only in which trials of each pair they use. The halves
    are resampled on the same drawn pairs, which keeps the comparison within
    the item and lets the correlation between the halves narrow the interval
    honestly.

    paired False is for the between item design, where a pair belongs to one
    half or the other by construction and the halves hold disjoint pairs.
    Each half is resampled from its own pairs independently.

    Pooling is over the three effort levels, because the question here is
    whether realised reasoning volume tracks bias at all, not whether it does
    so at one setting.
    """
    lo = pair_effects(rows, measure, lo_keep)
    hi = pair_effects(rows, measure, hi_keep)

    # Per (effort, family), the pair ids each half can use. Paired designs
    # keep only the pairs both halves hold, since a pair missing from one
    # half cannot contribute to a difference. Unpaired designs keep each
    # half's own pairs, which are disjoint by construction.
    index = {}
    for e in EFFORTS:
        for fam in FAMILIES:
            a = lo.get((model, e, fam), {})
            b = hi.get((model, e, fam), {})
            if paired:
                shared = sorted(set(a) & set(b))
                if len(shared) >= MIN_PER_SIDE:
                    index[(e, fam)] = (shared, shared, a, b)
            else:
                ka, kb = sorted(a), sorted(b)
                if len(ka) >= MIN_PER_SIDE and len(kb) >= MIN_PER_SIDE:
                    index[(e, fam)] = (ka, kb, a, b)
    if not index:
        return None

    def stat(draws):
        d_mean, d_sd = [], []
        for e in EFFORTS:
            mags_lo, mags_hi = [], []
            for fam in FAMILIES:
                key = (e, fam)
                if key not in index:
                    continue
                _ka, _kb, a, b = index[key]
                pick_lo, pick_hi = draws[key]
                mags_lo.append(abs(mean([a[p] for p in pick_lo])))
                mags_hi.append(abs(mean([b[p] for p in pick_hi])))
            if len(mags_lo) >= 2:
                d_mean.append(mean(mags_hi) - mean(mags_lo))
                d_sd.append(statistics.stdev(mags_hi) - statistics.stdev(mags_lo))
        if not d_mean:
            return None
        return mean(d_mean), mean(d_sd)

    identity = {k: (v[0], v[1]) for k, v in index.items()}
    point = stat(identity)
    if point is None:
        return None

    rng = random.Random(SEED)
    boots_m, boots_s = [], []
    for _ in range(n):
        draws = {}
        for key, (ka, kb, _a, _b) in index.items():
            pick_lo = [ka[rng.randrange(len(ka))] for _ in range(len(ka))]
            # A paired design must draw the same pairs on both sides.
            pick_hi = pick_lo if paired else [
                kb[rng.randrange(len(kb))] for _ in range(len(kb))]
            draws[key] = (pick_lo, pick_hi)
        got = stat(draws)
        if got is not None:
            boots_m.append(got[0])
            boots_s.append(got[1])
    boots_m.sort()
    boots_s.sort()

    def ci(xs):
        if len(xs) < 20:
            return (float("nan"), float("nan"))
        return (xs[int(0.025 * len(xs))], xs[min(len(xs) - 1, int(0.975 * len(xs)))])

    return point[0], ci(boots_m), point[1], ci(boots_s)


def intervals(rows, measure):
    """The two endogenous contrasts with intervals, pooled over effort."""
    long_set, short_set = within_item_halves(rows)
    heavy, light = between_item_halves(rows)
    designs = (
        ("between items", lambda r: r["custom_id"] in light,
         lambda r: r["custom_id"] in heavy, False),
        ("within item", lambda r: r["custom_id"] in short_set,
         lambda r: r["custom_id"] in long_set, True),
    )
    print("   Pooled over the three effort levels, bootstrapped over pairs.")
    print("   A negative interval is more reasoning going with less bias,")
    print("   which is the direction the exogenous manipulation gives.")
    for name, lo_keep, hi_keep, paired in designs:
        for m in MODELS:
            got = boot_contrast(rows, measure, lo_keep, hi_keep, m, paired)
            if got is None:
                continue
            dm, (ml, mh), ds, (sl, sh) = got
            print("   %-14s %-8s mean %+7.3f [%+7.3f, %+7.3f]   spread %+7.3f [%+7.3f, %+7.3f]"
                  % (name, SHORT[m], dm, ml, mh, ds, sl, sh))
    print()


def composition(rows):
    """Does the between item split sort families rather than difficulty?

    If a family's items land disproportionately in the heavy half, the
    between item contrast is partly a change in which cues are being averaged
    rather than a statement about reasoning volume. A reviewer will ask, and
    the answer belongs in the output rather than in a reply.
    """
    heavy, light = between_item_halves(rows)
    counts = collections.defaultdict(lambda: [0, 0])
    for r in rows:
        if r["custom_id"] in heavy:
            counts[r["bias"]][0] += 1
        elif r["custom_id"] in light:
            counts[r["bias"]][1] += 1
    print("Family composition of the between item halves")
    print("  A family at 50% is split evenly and contributes equally to both.")
    for fam in FAMILIES:
        h, l = counts[fam]
        if h + l == 0:
            continue
        print("  %-20s heavy %5d  light %5d   heavy share %5.1f%%"
              % (fam, h, l, 100 * h / (h + l)))
    print()

# ---------------------------------------------------------------- the contrast


def report(rows, measure):
    print("=" * 78)
    print("Measure: %s" % ("categorical sell tendency" if measure == "cat"
                           else "percent of position to sell"))
    print("=" * 78)

    full = pair_effects(rows, measure)
    long_set, short_set = within_item_halves(rows)
    heavy, light = between_item_halves(rows)
    within_long = pair_effects(rows, measure, lambda r: r["custom_id"] in long_set)
    within_short = pair_effects(rows, measure, lambda r: r["custom_id"] in short_set)
    between_heavy = pair_effects(rows, measure, lambda r: r["custom_id"] in heavy)
    between_light = pair_effects(rows, measure, lambda r: r["custom_id"] in light)

    print()
    print("1. Exogenous. The effort parameter, set before the model sees the item.")
    print("   model     low              high             change")
    for m in MODELS:
        a, b = summarise(full, m, "low"), summarise(full, m, "high")
        if not a or not b:
            continue
        print("   %-8s mean %7.3f sd %6.3f  mean %7.3f sd %6.3f  mean %+7.3f sd %+7.3f"
              % (SHORT[m], a[0], a[1], b[0], b[1], b[0] - a[0], b[1] - a[1]))

    for title, lo, hi, lo_name, hi_name in (
        ("2. Endogenous, between items. Light token items against heavy ones,\n"
         "   inside one effort level. Item difficulty is free to drive both.",
         between_light, between_heavy, "light", "heavy"),
        ("3. Endogenous, within item. Short responses against long ones to the\n"
         "   same item at the same effort. Item difficulty is held fixed.",
         within_short, within_long, "short", "long"),
    ):
        print()
        print(title)
        print("   model    effort   %-16s %-16s change" % (lo_name, hi_name))
        for m in MODELS:
            for e in EFFORTS:
                a, b = summarise(lo, m, e), summarise(hi, m, e)
                if not a or not b:
                    continue
                print("   %-8s %-7s mean %7.3f sd %6.3f  mean %7.3f sd %6.3f  "
                      "mean %+7.3f sd %+7.3f"
                      % (SHORT[m], e, a[0], a[1], b[0], b[1],
                         b[0] - a[0], b[1] - a[1]))

    print()
    print("   Direction counts over the nine model by effort cells, where a")
    print("   negative change is more reasoning going with less bias:")
    for name, lo, hi in (("between items", between_light, between_heavy),
                         ("within item", within_short, within_long)):
        dm = dsd = n = 0
        for m in MODELS:
            for e in EFFORTS:
                a, b = summarise(lo, m, e), summarise(hi, m, e)
                if not a or not b:
                    continue
                n += 1
                dm += 1 if b[0] < a[0] else 0
                dsd += 1 if b[1] < a[1] else 0
        print("     %-14s mean bias falls in %d of %d, spread falls in %d of %d"
              % (name, dm, n, dsd, n))
    print()
    intervals(rows, measure)


def main():
    rows = usable(load_rows())
    print("%s usable responses" % format(len(rows), ","))
    print()
    token_overlap(rows)
    leverage(rows)
    composition(rows)
    for measure in ("cat", "pct"):
        report(rows, measure)

    print("=" * 78)
    print("What this settles")
    print("=" * 78)
    print("""
  The exogenous manipulation and the endogenous measure are not two routes
  to the same number. Whichever way the endogenous split comes out, it is
  measured on the same 9,720 responses as the exogenous result, with the
  same families, the same items and the same arithmetic, so a disagreement
  between them cannot be attributed to sample, instrument or analysis.

  The within item split removes item difficulty, which is the confound an
  observational mediator analysis is usually accused of and the one its
  authors can most easily rebut. What it cannot remove is the loop that
  matters most here: a response's answer and the length of its justification
  are produced together, so conditioning on length conditions on the answer.
  No amount of care with observational data fixes that. Setting the budget
  before the item is seen does.
""")


if __name__ == "__main__":
    main()
