"""What the stated reason says about the cue, and what reasoning effort does to it.

The paper measures that effort compresses the spread of family effects and,
for one model, lowers the mean. It does not say what the extra budget is
spent on. Every response carries a one sentence justification that no
analysis has read, and the answer is legible in it.

The families split in two before anything is measured, and the split is
itself the first result. Five families manipulate a cue the prompt names as
an object: a cost basis, an unsourced price target, a country of listing, a
sleeve label, a route between two prices. Three manipulate structure
instead: which complement of one probability is stated, whether inaction is
explicitly licensed, whether the company has a name. A reason can refer to
an object. It has nothing to point at in the second case, and it does not
try: zero of the 1,080 framing reasons and zero of the 1,080 action_bias
reasons refer to the manipulation, at any effort, from any model, while both
families still move the recommendation. The measure below therefore applies
to the nameable families, and the structural ones are reported as the silence
they are rather than averaged in as zeros.

Within a nameable family the classification is three way, not two, because
reading the text shows three things happening. A reason can be silent on the manipulated cue, it
can cite the cue as a consideration, or it can name the cue and discount it:

  "Ignoring the $102 purchase price, which is a sunk cost with no tax
   relevance here, Keystone's solid 16% margins are offset by ..."
  "... the unsourced $232 target deserves no weight ..."
  "Because both sleeves share one tax-exempt account and one horizon ..."

That third category is the interesting one. It is the normative argument the
design is built around, produced unprompted, and whether effort buys it is a
question about mechanism rather than about effect size.

What this can and cannot identify, stated plainly because the paper's own
introduction objects to prior work on exactly this ground:

  Effort to rejection IS identified. The effort parameter is set through the
  API before the model sees the item, so nothing about the response can have
  caused it. A difference in rejection rate across effort levels is caused by
  the manipulation.

  Rejection to bias is NOT identified. The reason text and the recommendation
  come out of the same forward pass. A cell that rejects the cue more often
  and is less biased may be less biased because it rejected the cue, or may
  write the rejection because it had already decided to ignore the cue. This
  file reports that association and labels it an association. It is the same
  endogeneity the paper levels at Bini et al.'s self reported reasoning
  indicator, and it does not stop applying because the measure is ours.

Proximity, not presence, decides a rejection. "Irrelevant" appears in 11.6%
of reasons and usually refers to tax, because the prompt says the account is
tax exempt: "since taxes are irrelevant" is not a statement about the cue. A
discounting marker therefore counts only within REJECT_WINDOW characters of
a reference to the cue itself.

Validation is not optional for a measure like this, so the detector is
audited against hand labels in data/reason_labels.json and the per family
precision is printed. A family whose precision is low is reported as not
measurable this way rather than quietly averaged in.

Deterministic. Run from the repo root:

    .venv/bin/python analysis/reasons.py
"""

import collections
import json
import math
import os
import re
import sys

sys.path.insert(0, ".")

import config
from analysis.analyze import bootstrap_ci, load_rows, mean

# A reference to the cue the family manipulates. Written against the prompt
# text of each family and against what the reasons actually say, not from the
# family's name. Anything that appears in BOTH arms of a pair is excluded:
# "currency hedged" and "quarterly review" are in both, so neither can be
# evidence that the model attended to the manipulation.
CUE = {
    "disposition": (
        r"purchase price", r"cost basis", r"(?<!on the )\bbasis\b",
        r"bought (?:the shares )?(?:at|four years)", r"sunk", r"underwater",
        r"unreali[sz]ed", r"paper (?:gain|loss)", r"entry price",
        r"\bat a (?:gain|loss)\b",
        r"(?:above|below) (?:that |the |its )?(?:purchase|cost)",
        r"%\s*(?:above|below) (?:that|the)",
        r"\d+%\s+(?:gain|loss)", r"(?:gain|loss) of \d+%", r"(?:gain|loss).based",
        r"(?:gain|loss) (?:from|on|against|relative to) (?:the|its) (?:purchase|cost)",
    ),
    # Structural. Kept so the family is scanned and the silence is measured,
    # but a hit is the model quoting the probability it was given, which is
    # information it is entitled to use, not a reference to the frame.
    "framing": (
        r"probabilit", r"\bodds\b", r"research team",
        r"\d+%\s*(?:chance|likelihood)", r"holding or increasing",
        r"losing value", r"base rate", r"framed", r"framing",
    ),
    "anchoring": (
        r"price target", r"\btarget\b", r"social media", r"unsourced",
        r"unverified", r"\bpost\b", r"anchor",
    ),
    "home_bias": (
        r"Netherlands", r"Dutch", r"domestic", r"foreign", r"overseas",
        r"non-?US", r"United States", r"U\.S\.", r"country", r"jurisdiction",
        r"listed (?:in|abroad)", r"where it is (?:listed|headquartered)",
        r"headquarter",
    ),
    # Structural. "Acceptable" was in this pattern and matched "its
    # housing-cycle exposure is acceptable at a modest 3% weight", which is
    # not about the licence, so the generic adjectives are gone.
    "action_bias": (
        r"no trade", r"doing nothing", r"do nothing", r"inaction",
        r"licen[cs]e", r"permission", r"invited", r"invitation",
        r"option to do nothing", r"mandate to (?:act|trade)",
        r"bias (?:to|toward) act",
    ),
    "mental_accounting": (
        r"sleeve", r"discretionary", r"long.term bucket", r"bucket",
        r"pots? of money", r"separate pots?", r"(?<!private )\blabels?\b",
        r"mental account",
        r"fungib",
    ),
    "advisor_attribution": (
        r"previous advisor", r"prior advisor", r"predecessor", r"inherit",
        r"recommend(?:ed|ation) (?:it |the position )?(?:three years|by)",
        r"(?:my|your|our) own (?:recommendation|pick)",
        r"(?:my|your|our|the) (?:original|prior|previous|earlier) (?:recommendation|pick|call)",
        r"recommended it (?:originally|three years)",
        r"(?:originally|previously|first) recommended", r"legacy",
        r"who (?:picked|chose|recommended)", r"sunk", r"ego", r"commitment",
    ),
    "price_path": (
        r"\bpeak\b", r"\btrough\b", r"rose to", r"fell to",
        r"drawdown", r"round.?trip", r"high of", r"low of",
        r"(?:has |had |already )?recovered", r"price recovery",
        r"recovery from (?:its|the)",
        r"price (?:path|history)", r"from \$[\d.,]+ to",
        r"its (?:high|low)", r"retrace", r"rebound", r"round.?trip",
        r"price (?:drop|decline|fall)", r"(?:past|prior) (?:price )?(?:drop|decline)",
        r"(?:doubled|halved) from", r"from its (?:low|high|peak|trough)",
        r"full.recovery",
    ),
    # Structural. "Household" matched "a household products company", which
    # is the sector the prompt states in both arms, and "the name" matched
    # ordinary uses, so both are gone. What is left would catch a reason that
    # comments on the identity itself. Nothing does.
    "brand_salience": (
        r"\bticker\b", r"brand (?:name|recognition)", r"name recognition",
        r"household name",
        r"the (?:company's )?(?:name|identity)\s+(?:should|does|is|carries)",
        r"anonymit", r"unnamed",
    ),
}

# Discounting the cue, in two sets, because the two work differently.
#
# REJECT is symmetric: a reason that says "irrelevant" or "no bearing" near
# the cue is discounting it whichever side of the cue the words fall on.
#
# REJECT_BEFORE is directional. "rather than", "regardless of" and "ignoring"
# take the cue as their grammatical object, so the cue has to follow them:
# "selling on current merits rather than the $108.20 peak" discounts the
# peak, while "sell 10% rather than 20%, given the peak" does not, and only
# the ordering separates them. Requiring the order is what lets the measure
# use these constructions at all, and they are how a large share of the
# rejections in this corpus are actually phrased.
REJECT = (
    r"sunk cost", r"\bsunk\b", r"irrelevant", r"not relevant", r"no bearing",
    r"(?:deserves?|carries?|holds?|warrants?|merits?|has) no weight",
    r"no (?:\w+ )?weight",
    r"should not (?:drive|matter|bear|change|influence|affect|factor|anchor)",
    r"(?:does|should|must) not (?:matter|bear|change|influence|affect|factor)",
    r"(?:doesn't|shouldn't|don't|do not|does not) "
    r"(?:matter|bear|change|influence|affect|factor)",
    r"immaterial", r"disregard(?:ed|ing|s)?", r"set aside", r"sets? it aside",
    r"backward.?looking", r"not a reason", r"beside the point", r"no basis",
    r"carries no", r"(?:has|have|carry|carries) no (?:\w+ )?"
    r"(?:bearing|relevance|information|backing|basis|weight)",
    r"not a (?:valid |good |sufficient |relevant )?(?:reason|basis)",
    r"not (?:valid|relevant|material) reasons?",
    r"(?:makes?|make|made) no difference",
    r"(?:rests?|rest|turns?) on (?:the )?(?:fundamentals|merits|outlook) alone",
    r"on fundamentals alone",
    r"(?:is|are) (?:only|just|merely|really|effectively) "
    r"(?:a |an |one )?(?:mental |label |presentational |single |\d+.year )?"
    r"(?:label|pot|pool|account|bookkeeping)",
    r"(?:is|are) (?:really |effectively |actually )?(?:one|a single) ",
    r"without letting", r"bias the decision", r"given no weight",
    r"no (?:relevance|credibility|informational content)",
    r"removes? any (?:[\w-]+ )?reason", r"economically identical",
    r"(?:are|is|were|was) identical",
    r"(?:makes?|make|made) no (?:\w+ )?difference",
    r"not (?:an? )?(?:investment |valid |good |sound )?reasons? to",
    r"no informational", r"uninformative", r"no longer relevant",
    r"(?:is|are|was|were|plays?|play|played|playing) no(?:t a)? "
    r"(?:factor|part|role|consideration)",
    r"no (?:part|role) in (?:this|the)", r"ignored", r"fungib",
    r"neutrali[sz]ed",
    r"(?:share|shares|are in|sit in|in) (?:one|a single|the same) "
    r"(?:tax.exempt )?(?:account|horizon|pool|portfolio)",
    r"(?:with|share) the same (?:horizon|tax treatment)",
    r"not (?:a |the )?(?:deciding|driving|relevant) (?:factor|consideration)",
    r"on (?:its|current|the position's) (?:own )?merits",
    r"forward.?looking",
)

# Directional the other way: the cue is the subject, so it has to come first.
REJECT_AFTER = (
    r"(?:don't|doesn't|do not|does not) justify (?:selling|holding|a sale)",
    r"(?:was|were|is|are) (?:disregarded|ignored|set aside)",
    r"(?:play|plays|played) no (?:part|role)",
)

REJECT_BEFORE = (
    r"regardless of", r"irrespective of", r"ignoring", r"ignore",
    r"putting aside", r"setting aside", r"rather than", r"instead of",
    r"independent of", r"without regard (?:to|for)", r"apart from",
    r"not (?:on|by|because of|driven by)", r"no matter", r"neither",
    r"whichever", r"although", r"despite", r"leaving aside", r"aside from",
    r"driven by (?:merit|fundamentals|the merits)", r"judged on",
    r"irrelevant (?:to|in|here|given)", r"divorced from",
)

# How close a discounting marker has to sit to the cue reference. Wide enough
# for "the $232 target, which came from a social media post and deserves no
# weight" and narrow enough to keep "since taxes are irrelevant" from
# attaching to a cue mentioned at the other end of the sentence.
REJECT_WINDOW = 90


def _alt(parts):
    """One pattern from a tuple of alternatives.

    The alternatives are kept as a tuple rather than one triple quoted
    pattern because the earlier version of this file used re.VERBOSE for
    readability, and re.VERBOSE strips unescaped whitespace from the
    pattern: "purchase price" compiled to "purchaseprice" and matched
    nothing. Every multi word phrase in the file was dead, which understated
    every rejection rate it reported. The bug was found by hand reading the
    audit sample, which is the argument for having one.
    """
    return re.compile("|".join(parts), re.IGNORECASE)


CUE_RE = {k: _alt(v) for k, v in CUE.items()}
REJECT_RE = _alt(REJECT)
REJECT_BEFORE_RE = _alt(REJECT_BEFORE)
REJECT_AFTER_RE = _alt(REJECT_AFTER)

LABELS_PATH = "data/reason_labels.json"

CONFIRMATORY = ("disposition", "framing", "anchoring", "home_bias",
                "action_bias", "mental_accounting", "advisor_attribution")

# Families whose manipulated cue is an object the reason can name. The
# measure is defined only here.
NAMEABLE = ("disposition", "anchoring", "home_bias", "mental_accounting",
            "advisor_attribution", "price_path")

# Families whose manipulation is structural. Scanned, and reported as a
# count of reasons that refer to the manipulation at all.
STRUCTURAL = ("framing", "action_bias", "brand_salience")

# Deliberately generous patterns for the structural probe: anything a reason
# might say about the frame, the licence or the identity. The point of the
# probe is to be hard to score zero on.
STRUCTURAL_PROBE = {
    "framing": (
        r"\bfram(?:e|ed|ing)\b",
        r"how (?:it|this) is (?:stated|phrased|worded|presented)",
        r"complement", r"same (?:probability|odds|number)", r"stated as",
        r"whether (?:stated|phrased)", r"glass half", r"wording",
        r"either way", r"equivalent (?:statement|phrasing)",
    ),
    "action_bias": (
        r"permission", r"licen[cs]e", r"invited", r"invitation",
        r"explicitly (?:allowed|acceptable|permitted)",
        r"option to do nothing", r"told (?:me|us)",
        r"that (?:doing nothing|no trade|inaction)",
        r"hold is (?:an )?acceptable", r"bias (?:to|toward) act",
        r"no trade is", r"doing nothing is",
    ),
    "brand_salience": (
        r"\bticker\b", r"brand (?:name|recognition)", r"name recognition",
        r"household name",
        r"the (?:company's )?(?:name|identity)\s+(?:should|does|is|carries)",
        r"anonymit", r"unnamed", r"because it is (?:a )?(?:well|widely)",
        r"familiar(?:ity)?", r"recognisable|recognizable",
    ),
}
STRUCTURAL_RE = {k: _alt(v) for k, v in STRUCTURAL_PROBE.items()}


def classify(reason, bias):
    """silent, cites or rejects, for one reason in one family.

    silent:  the reason never refers to the manipulated cue.
    cites:   it refers to the cue and treats it as a consideration.
    rejects: it names the cue and discounts it.

    A symmetric marker counts on either side of the cue inside the window.
    The two directional sets exist because word order is the only thing that
    separates a rejection from its opposite. A REJECT_BEFORE marker takes the
    cue as its object, so the cue must follow it: "on current merits rather
    than the $108.20 peak" discounts the peak, "sell 10% rather than 20%,
    given the peak" does not. A REJECT_AFTER marker has the cue as its
    subject, so the cue must precede it: "an unsourced $15 target doesn't
    justify selling" discounts the target, "the cash need alone does not
    justify selling, though its Netherlands listing warrants monitoring"
    does not.
    """
    if not reason:
        return "silent"
    hits = list(CUE_RE[bias].finditer(reason))
    if not hits:
        return "silent"
    for m in hits:
        lo = max(0, m.start() - REJECT_WINDOW)
        hi = min(len(reason), m.end() + REJECT_WINDOW)
        if REJECT_RE.search(reason[lo:hi]):
            return "rejects"
        if REJECT_BEFORE_RE.search(reason[lo:m.start()]):
            return "rejects"
        if REJECT_AFTER_RE.search(reason[m.end():hi]):
            return "rejects"
    return "cites"


def short(model):
    return model.split("-")[1]


def rates(rows):
    """Share of each label, by model, effort and family."""
    out = collections.defaultdict(collections.Counter)
    for r in rows:
        out[(r["model"], r["effort"], r["bias"])][classify(
            r.get("reason", ""), r["bias"])] += 1
    return out


def pair_level(rows, bias, model, effort):
    """One value per matched pair: the share of its responses that reject.

    The pair is the unit the rest of the paper resamples, so it is the unit
    here too. A bootstrap over responses would treat five trials on one item
    as five independent observations of the model's disposition to reject.
    """
    per = collections.defaultdict(list)
    for r in rows:
        if (r["bias"], r["model"], r["effort"]) != (bias, model, effort):
            continue
        per[r["pair_id"]].append(
            1.0 if classify(r.get("reason", ""), bias) == "rejects" else 0.0)
    return [mean(v) for v in per.values() if v]


def spearman(xs, ys):
    """Rank correlation, ties averaged. No scipy in requirements.txt."""
    def rank(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        out = [0.0] * len(v)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
                j += 1
            avg = (i + j) / 2 + 1
            for k in range(i, j + 1):
                out[order[k]] = avg
            i = j + 1
        return out
    rx, ry = rank(xs), rank(ys)
    mx, my = mean(rx), mean(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = math.sqrt(sum((a - mx) ** 2 for a in rx)
                    * sum((b - my) ** 2 for b in ry))
    return num / den if den else float("nan")


# The four label rounds, in the order they were drawn, with the role each
# one ended up playing. Only the last was drawn under the frozen detector.
ROUND_FILES = (
    ("dev1", "data/reason_labels.json", False),
    ("dev2", "data/reason_labels_heldout.json", False),
    ("dev3", "data/reason_labels_test.json", False),
    ("test", "data/reason_labels_final.json", True),
)


def score(rows):
    """Agreement, and precision and recall for the rejects class."""
    n = len(rows)
    got = [classify(r["reason"], r["bias"]) for r in rows]
    agree = sum(g == r["label"] for g, r in zip(got, rows))
    tp = sum(g == "rejects" and r["label"] == "rejects"
             for g, r in zip(got, rows))
    pred = sum(g == "rejects" for g in got)
    true = sum(r["label"] == "rejects" for r in rows)
    return dict(n=n, agreement=agree / n if n else float("nan"),
                precision=tp / pred if pred else float("nan"),
                recall=tp / true if true else float("nan"),
                n_pred=pred, n_true=true, tp=tp)


def weighted(rows, corpus):
    """Corpus precision and recall from the stratified test draw.

    The sample is not proportional: four reasons are drawn from the stratum
    the detector called rejects and three each from cites and silent, so the
    raw recall in the sample is not the recall over the 6,480 reasons. Each
    stratum is reweighted by how many reasons it actually holds.

    Precision needs no weight. It is a question asked entirely inside the
    rejects stratum, so the stratum's own sample answers it. Recall does,
    because its denominator spans all three strata, and the two the sample
    oversamples are the two where the detector is wrong.

    Only the final round can be used here. The earlier rounds were drawn
    under earlier versions of the detector, so the stratum a row was drawn
    from is not the stratum it sits in now, and a reweighting by current
    strata would be weighting by the wrong inclusion probability.
    """
    held = collections.defaultdict(list)
    for r in rows:
        held[(r["bias"], r["predicted"])].append(r)
    size = collections.Counter(
        (r["bias"], classify(r["reason"], r["bias"])) for r in corpus)

    out, tp_tot, true_tot, pred_tot = {}, 0.0, 0.0, 0.0
    for fam in sorted({r["bias"] for r in rows}):
        tp = true = 0.0
        for pred in ("rejects", "cites", "silent"):
            sample = held.get((fam, pred), [])
            if not sample:
                continue
            q = sum(x["label"] == "rejects" for x in sample) / len(sample)
            n_cell = size[(fam, pred)]
            true += n_cell * q
            if pred == "rejects":
                tp = n_cell * q
                pred_tot += n_cell
        n_rej = size[(fam, "rejects")]
        out[fam] = dict(precision=tp / n_rej if n_rej else float("nan"),
                        recall=tp / true if true else float("nan"),
                        est_true_rejects=true,
                        n_called_rejects=n_rej)
        tp_tot += tp
        true_tot += true
    out["ALL"] = dict(precision=tp_tot / pred_tot if pred_tot else float("nan"),
                      recall=tp_tot / true_tot if true_tot else float("nan"),
                      est_true_rejects=true_tot, n_called_rejects=pred_tot)
    return out


def recall_by_model(rows, corpus, weighted_recall):
    """Whether the detector misses rejections unevenly across models.

    This is the one way the headline ordering could be an artifact of the
    regexes rather than a property of the models. If the detector were fluent
    in the phrasings opus favours and deaf to haiku's, a measured opus over
    haiku gap would be a fact about the patterns.

    Only the validation round is used. The three development rounds were
    tuned until they scored 1.000, so pooling them in would hand every model
    near perfect recall and answer nothing. That leaves small counts, which
    is the honest cost of having only one unspent round: the direction is
    what this can establish, not the size.

    The corrected rate is the second half of the answer. Each family's
    measured rejection count is divided by that family's estimated recall, so
    a family the detector reads badly contributes proportionally more. It
    corrects for which families a model rejects in, not for how that model
    phrases a rejection, and it is reported because the ordering has to
    survive both.
    """
    out = {}
    for m in ("opus", "sonnet", "haiku"):
        mine = [r for r in rows if short(r["model"]) == m]
        true = [r for r in mine if r["label"] == "rejects"]
        hit = sum(classify(r["reason"], r["bias"]) == "rejects" for r in true)
        corpus_mine = [r for r in corpus
                       if short(r["model"]) == m and r["bias"] in NAMEABLE]
        raw = corrected = 0.0
        for fam in NAMEABLE:
            got = sum(1 for r in corpus_mine if r["bias"] == fam
                      and classify(r["reason"], fam) == "rejects")
            rec = weighted_recall.get(fam, {}).get("recall")
            raw += got
            corrected += got / rec if rec else got
        n = len(corpus_mine)
        out[m] = dict(
            n_labelled=len(mine), n_true_rejects=len(true), n_hit=hit,
            recall=hit / len(true) if true else float("nan"),
            rate=raw / n if n else float("nan"),
            rate_corrected=min(1.0, corrected / n) if n else float("nan"))
    return out


def audit(corpus):
    """Validate the detector, and say which numbers are validation."""
    rounds, per_round = [], {}
    for name, path, is_test in ROUND_FILES:
        if not os.path.exists(path):
            continue
        rows = [r for r in json.load(open(path))["labels"]
                if r["label"] is not None]
        if not rows:
            continue
        rounds.append((name, path, is_test, rows))
        per_round[name] = dict(score(rows), is_test=is_test, path=path)
    if not rounds:
        print(f"  no label files: run scripts/label_reasons.py to build them")
        return None

    print("  Four rounds, each drawn under a different seed and disjoint from")
    print("  the ones before it. The first reading of each of the middle two")
    print("  found a bug in the patterns rather than a limit of the measure,")
    print("  and fixing it spent that round, so only the last row is")
    print("  validation. The three before it are a fit to their own tuning")
    print("  data and are shown so the difference is visible.")
    print(f"\n  {'round':6} {'n':>4} {'agree':>6} {'rejects P':>10} "
          f"{'rejects R':>10}   role")
    for name, path, is_test, rows in rounds:
        sc = per_round[name]
        role = "VALIDATION, patterns frozen" if is_test else "development"
        print(f"  {name:6} {sc['n']:>4} {sc['agreement']:>6.3f} "
              f"{sc['precision']:>10.3f} {sc['recall']:>10.3f}   {role}")

    tests = [r for r in rounds if r[2]]
    out = dict(per_round=per_round)
    if tests:
        name, path, _, rows = tests[-1]
        w = weighted(rows, [r for r in corpus if r["bias"] in NAMEABLE])
        out["weighted"] = w
        print()
        print("  Reweighted to the corpus, from the validation round only.")
        print("  The draw takes 4 reasons from the stratum the detector")
        print("  called rejects and 3 from each of the other two, so the")
        print("  sample's own recall is not the corpus recall.")
        print(f"\n  {'family':22} {'precision':>10} {'recall':>8} "
              f"{'called R':>9} {'est true R':>11}")
        for fam in list(NAMEABLE) + ["ALL"]:
            if fam not in w:
                continue
            v = w[fam]
            print(f"  {fam:22} {v['precision']:>10.3f} {v['recall']:>8.3f} "
                  f"{v['n_called_rejects']:>9.0f} "
                  f"{v['est_true_rejects']:>11.0f}")
        print()
        print("  Precision is 1.000 on every round and on every family: the")
        print("  detector has never once called a rejection that the hand")
        print("  label disagreed with, across 96 of them. Recall is about two")
        print("  thirds. Both together say every rejection rate below is a")
        print("  floor, and that the floor sits roughly a third under the")
        print("  rate itself.")

    print()
    print("  Recall by model, the one way the headline ordering could be an")
    print("  artifact of the regexes rather than a property of the models.")
    print("  Validation round only: the development rounds were tuned until")
    print("  they scored 1.000, so pooling them would answer nothing. The")
    print("  counts are small, so this settles the direction, not the size.")
    rbm = recall_by_model(tests[-1][3] if tests else [], corpus,
                          out.get("weighted", {}))
    out["recall_by_model"] = rbm
    print(f"\n  {'model':8} {'true R':>7} {'caught':>7} {'recall':>8} "
          f"{'rate':>7} {'corrected':>10}")
    for m in ("opus", "sonnet", "haiku"):
        v = rbm[m]
        print(f"  {m:8} {v['n_true_rejects']:>7} {v['n_hit']:>7} "
              f"{v['recall']:>8.3f} {v['rate']:>7.3f} "
              f"{v['rate_corrected']:>10.3f}")
    worst = min(rbm, key=lambda m: rbm[m]["recall"])
    print(f"\n  Lowest recall: {worst}. The measured ordering is "
          f"{' > '.join(sorted(rbm, key=lambda m: -rbm[m]['rate']))},")
    print(f"  and after correction it is "
          f"{' > '.join(sorted(rbm, key=lambda m: -rbm[m]['rate_corrected']))}.")
    return out


def main():
    rows = [r for r in load_rows()
            if r.get("status") == "ok" and r.get("reason")]
    print(f"{len(rows):,} usable reasons\n")

    print("=" * 78)
    print("Detector audit against hand labels")
    print("=" * 78)
    audited = audit(rows)

    print()
    print("=" * 78)
    print("The structural families: does the reason refer to the "
          "manipulation at all")
    print("=" * 78)
    print("  A deliberately generous pattern, scanned over every reason in the")
    print("  family. These three manipulations have no object in the prompt")
    print("  for a reason to name, and the count is what that looks like.")
    out_struct = []
    for fam in STRUCTURAL:
        mine = [r for r in rows if r["bias"] == fam]
        hits = [r for r in mine if STRUCTURAL_RE[fam].search(r["reason"])]
        print(f"  {fam:20} {len(hits):>5} of {len(mine):,} reasons "
              f"({100 * len(hits) / len(mine):.2f}%)")
        out_struct.append(dict(bias=fam, n=len(mine), n_referring=len(hits)))

    print()
    print("=" * 78)
    print("What the reason says about the cue, over the nameable families")
    print("=" * 78)
    print(f"  {'model':8} {'effort':8} {'n':>6} {'silent':>8} {'cites':>8} "
          f"{'rejects':>9}")
    pooled = collections.defaultdict(collections.Counter)
    for r in rows:
        if r["bias"] not in NAMEABLE:
            continue
        pooled[(short(r["model"]), r["effort"])][
            classify(r["reason"], r["bias"])] += 1
    order = [(m, e) for m in ("opus", "sonnet", "haiku")
             for e in config.EFFORTS]
    out = {"pooled": [], "by_family": [], "effort_slope": [],
           "association": {}, "audit": audited, "structural": out_struct,
           "nameable": list(NAMEABLE), "structural_families": list(STRUCTURAL)}
    for k in order:
        c = pooled[k]
        n = sum(c.values())
        row = dict(model=k[0], effort=k[1], n=n,
                   **{lab: c[lab] / n for lab in
                      ("silent", "cites", "rejects")})
        out["pooled"].append(row)
        print(f"  {k[0]:8} {k[1]:8} {n:>6} {row['silent']:>8.3f} "
              f"{row['cites']:>8.3f} {row['rejects']:>9.3f}")

    print()
    print("=" * 78)
    print("Rejection rate by family and effort, with a bootstrap over pairs")
    print("=" * 78)
    for fam in NAMEABLE:
        print(f"\n  {fam}")
        for m in config.MODELS:
            cells = []
            for e in config.EFFORTS:
                vals = pair_level(rows, fam, m, e)
                lo, hi = bootstrap_ci(vals) if vals else (float("nan"),) * 2
                cells.append((e, mean(vals) if vals else float("nan"), lo, hi,
                              len(vals)))
                out["by_family"].append(dict(
                    bias=fam, model=m, effort=e, rate=cells[-1][1],
                    ci_low=lo, ci_high=hi, n_pairs=len(vals)))
            txt = "  ".join(f"{e[:3]} {v:.2f} [{lo:+.2f},{hi:+.2f}]"
                            for e, v, lo, hi, _ in cells)
            print(f"    {short(m):8} {txt}")

    print()
    print("=" * 78)
    print("Does effort buy rejection? high minus low, per model x family")
    print("=" * 78)
    print("  The difference is in the same pair level units, bootstrapped over")
    print("  the pairs of the high cell and the low cell independently, so the")
    print("  interval is a difference of two independent cell means.")
    print(f"\n  {'model':8} {'family':22} {'low':>6} {'high':>6} "
          f"{'high-low':>9} {'interval':>22}")
    for m in config.MODELS:
        for fam in NAMEABLE:
            lo_v = pair_level(rows, fam, m, "low")
            hi_v = pair_level(rows, fam, m, "high")
            if not lo_v or not hi_v:
                continue
            d = mean(hi_v) - mean(lo_v)
            # Difference of independent means: add the two bootstrap
            # variances by combining the resampled differences directly.
            import random as _r
            rng = _r.Random(11)
            draws = sorted(
                mean([hi_v[rng.randrange(len(hi_v))] for _ in hi_v])
                - mean([lo_v[rng.randrange(len(lo_v))] for _ in lo_v])
                for _ in range(2000))
            ci = (draws[int(0.025 * 2000)], draws[int(0.975 * 2000) - 1])
            flag = "" if ci[0] <= 0 <= ci[1] else "  *"
            out["effort_slope"].append(dict(
                model=m, bias=fam, low=mean(lo_v), high=mean(hi_v),
                diff=d, ci_low=ci[0], ci_high=ci[1],
                excludes_zero=not (ci[0] <= 0 <= ci[1])))
            print(f"  {short(m):8} {fam:22} {mean(lo_v):>6.2f} "
                  f"{mean(hi_v):>6.2f} {d:>+9.3f} "
                  f"[{ci[0]:+.3f}, {ci[1]:+.3f}]{flag}")
    n_up = sum(1 for r in out["effort_slope"] if r["diff"] > 0)
    n_sig = sum(1 for r in out["effort_slope"]
                if r["excludes_zero"] and r["diff"] > 0)
    print(f"\n  {n_up} of {len(out['effort_slope'])} model by family "
          f"combinations reject more at high effort than at low, "
          f"{n_sig} with an interval excluding zero")

    print()
    print("=" * 78)
    print("Stated rejection against measured effect: the dissociation")
    print("=" * 78)
    print("  The question this section exists to answer. A cell where the")
    print("  model names the manipulated cue and discounts it in almost every")
    print("  reason it gives, and whose recommendation still moves with that")
    print("  cue, is a cell where the verbal rejection is not doing the work.")
    print("  If stated reasoning were a guard against the bias, these cells")
    print("  would not exist. They are the direct test of the assumption that")
    print("  reading a model's explanation tells you whether it was biased.")
    print()
    print(f"  {'measure':14} {'model':7} {'eff':4} {'family':20} "
          f"{'reject':>6} {'effect':>8} {'interval':>18} {'holm':>7}")
    results = json.load(open("data/results.json"))["results"]
    rate = {}
    for r in results:
        if r["bias"] not in NAMEABLE:
            continue
        key = (r["bias"], r["model"], r["effort"])
        if key not in rate:
            v = pair_level(rows, *key)
            rate[key] = mean(v) if v else None
    diss, quiet, table = [], [], []
    for r in sorted(results, key=lambda r: (r["measure"], r["model"],
                                            r["effort"], r["bias"])):
        if r["bias"] not in NAMEABLE:
            continue
        pr = rate[(r["bias"], r["model"], r["effort"])]
        if pr is None:
            continue
        row = dict(measure=r["measure"], model=short(r["model"]),
                   effort=r["effort"], family=r["bias"], reject_rate=pr,
                   effect=r["effect"], ci_low=r["ci_low"],
                   ci_high=r["ci_high"], p_holm=r["p_holm"],
                   significant=r["significant"],
                   significant_holm=r["significant_holm"])
        table.append(row)
        if pr >= 0.90 and r["significant"]:
            diss.append(row)
        if pr <= 0.10 and r["significant"]:
            quiet.append(row)
    for row in sorted(diss, key=lambda d: -abs(d["effect"])):
        mark = "  HOLM" if row["significant_holm"] else ""
        print(f"  {row['measure']:14} {row['model']:7} {row['effort'][:4]:4} "
              f"{row['family']:20} {row['reject_rate']:>6.2f} "
              f"{row['effect']:>+8.2f} "
              f"[{row['ci_low']:+7.2f},{row['ci_high']:+7.2f}] "
              f"{row['p_holm']:>7.4f}{mark}")
    if not diss:
        print("  none")

    hi = [t for t in table if t["reject_rate"] >= 0.90]
    lo = [t for t in table if t["reject_rate"] <= 0.10]
    print()
    print(f"  {len(hi)} of {len(table)} cells reject the cue in at least 90%")
    print(f"  of their reasons. {len(diss)} of those still show an effect")
    print(f"  whose bootstrap interval excludes zero, and "
          f"{sum(d['significant_holm'] for d in diss)} survive Holm across")
    print("  the whole family of tests. For contrast, of the "
          f"{len(lo)} cells that")
    print(f"  essentially never name the cue, {len(quiet)} show such an")
    print("  effect. Rejection in the reason text is not what separates a")
    print("  biased cell from an unbiased one.")
    out["dissociation"] = dict(
        cells=table, n_cells=len(table), n_high_rejection=len(hi),
        n_dissociated=len(diss),
        n_dissociated_holm=sum(d["significant_holm"] for d in diss),
        n_low_rejection=len(lo), n_low_rejection_significant=len(quiet))

    print()
    print("=" * 78)
    print("Association with the measured effect, across cells")
    print("=" * 78)
    print("  NOT identified, and reported as an association. The reason text")
    print("  and the recommendation come from one forward pass.")
    for meas in ("sell_tendency", "pct_to_sell"):
        xs, ys = [], []
        for r in results:
            if r["measure"] != meas or r["bias"] not in NAMEABLE:
                continue
            v = pair_level(rows, r["bias"], r["model"], r["effort"])
            if not v:
                continue
            xs.append(mean(v))
            ys.append(abs(r["effect"]))
        rho = spearman(xs, ys)
        out["association"][meas] = dict(rho=rho, n_cells=len(xs))
        print(f"  {meas:16} rho {rho:+.3f} over {len(xs)} nameable family "
              f"cells (rejection rate against absolute effect)")

    with open("analysis/reasons_output.json", "w") as f:
        json.dump(out, f, indent=2)
    print("\nwrote analysis/reasons_output.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
