# Pre-registration

**Locked 2026-10-26, before any model was queried.**
Committed to git before the first API call. Nothing in this file is edited
after data collection begins. If something has to change, it is added below
under "Deviations" with a date and a reason.

**Amendment 1, 2026-10-26, before any model was queried.** The literature
search was run after the first version of this file was committed and before
any data was collected. It found prior work on three of the nine bias
families and changed what this study can honestly claim to be first at. The
"Why this is not a replication" section below was rewritten to match the
evidence, a competing hypothesis was added to H10, and nothing about the
design, the items, the dependent variable or the analysis plan changed. The
superseded version is in the git history at commit 170e6f6. The record of
the search is in `LITERATURE.md`.

## Research question

Do large language models acting as portfolio advisors exhibit the behavioural
biases documented in human investors, and does increasing the model's
reasoning effort reduce them?

## Why this is not a replication

The literature search in `LITERATURE.md` found that several of these biases
have been measured in language models before. That is stated plainly here so
that the contribution claim rests on what is actually new.

Already established by prior work, and replicated rather than discovered here:

- Anchoring, framing, loss aversion and mental accounting appear in language
  models across many model families (`hagendorff2023intuitive`,
  `malberg2025comprehensive`, `bini2026behavioral`).
- The disposition effect has been tested twice and found absent. Malberg et
  al. report it as one of only two of thirty biases with a strong negative
  average, meaning a preference for change, and Yee and Koh report a
  near-zero disposition effect at baseline. H1 therefore predicts a negative
  effect in a setting where prior work found near zero or reversed, which is
  a genuine test and not a safe bet.
- Reasoning models are less prone to anchoring than non-reasoning models
  (`takenami2025anchoring`).

What is new:

1. **Reasoning effort as an exogenous, graded treatment.** Bini, Cong, Huang
   and Jin report that an indicator for self-reported analytical reasoning
   raises rational responses by about 40 percent, and use it as a mediator.
   That indicator is the model's own description of its reasoning, produced
   by the same forward pass as the answer, so it cannot separate deliberation
   causing a better answer from a model labelling its own better answers as
   analytical. Here the reasoning budget is set by an API parameter before
   the model sees the item, at three levels, with the prompt held constant.
   No paper found manipulates it that way against a behavioural finance bias.
2. **Advisory framing with portfolio state.** Prior items are abstract
   gambles, or a choice between two assets. These state a cost basis, a share
   count, a position weight and a fundamentals block, and ask whether to hold
   or sell.
3. **A sampling protocol for models that have no sampling parameters.**
   `temperature`, `top_p` and `top_k` return HTTP 400 on every current Claude
   model as of 2026-10-21. Bini et al. set temperature to 0.5, top-k to 50
   and top-p to 0.9; Malberg et al. run at temperature 0.0 with one sample
   per item. Neither protocol can now be executed. This study samples each
   cell repeatedly, reports percentile bootstrap intervals over matched
   pairs, and reports within-item entropy as a result rather than as noise.
4. **Two bias families that appear nowhere in the searched literature.**
   Advisor attribution, where the only thing that varies is whether the
   advisor recommended the position or inherited it, and price path, where
   the current price and cost basis are identical and only the route there
   differs.

The headline question is therefore not whether these models are biased. It is
whether the bias is a dial that deliberation turns down.

## Design

Nine bias families. Twelve matched pairs each. Two conditions per pair, so
216 distinct prompts. Three models crossed with three reasoning effort
levels, five trials per cell: 9,720 requests.

- Models: `claude-opus-5-5`, `claude-sonnet-5-5`, `claude-haiku-5-5`
- Effort: `low`, `medium`, `high`
- Trials: 5
- Generator seed: 20261026

Each matched pair holds current price, position size, portfolio weight and
the full fundamentals block constant, and varies exactly one cue that
standard finance theory says must not change the recommendation.

## Dependent variable

The model returns a structured recommendation constrained to
`BUY_MORE`, `HOLD`, `SELL_PARTIAL`, `SELL_ALL`, scored 0 to 3 as a sell
tendency. Grading is mechanical. No human reads an output to assign a label,
so there is no grader bias to control for.

Amendment 3 adds a continuous co-primary measure, the percentage of the
position the model would sell, because the categorical scale proved to be at
ceiling. Both are reported for every hypothesis. Where they disagree the
categorical measure is the pre-registered primary and the continuous measure
is reported alongside it.

## Hypotheses and predicted directions

Effect = mean sell tendency under the treatment condition minus the mean
under the baseline condition. Signs are fixed in `analysis/directions.py`.

| # | Bias | Baseline | Treatment | Predicted | Status |
|---|---|---|---|---|---|
| H1 | Disposition effect | gain | loss | negative | confirmatory |
| H2 | Framing | gain frame | loss frame | two sided | confirmatory |
| H3 | Anchoring | low anchor | high anchor | negative | confirmatory |
| H4 | Home bias | domestic | foreign | positive | confirmatory |
| H5 | Action bias | no licence | licence to do nothing | negative | confirmatory |
| H6 | Mental accounting | long term sleeve | discretionary sleeve | positive | confirmatory |
| H7 | Advisor attribution | inherited | self recommended | negative | confirmatory |
| H8 | Price path | fell then rose | rose then fell | positive | exploratory |
| H9 | Brand salience | anonymous | real ticker | two sided | exploratory |

**H10, the effort hypothesis.** For any bias family where a non-zero effect
is found at `low`, the absolute effect at `high` will be smaller.

**H10-null, the pre-registered competing hypothesis.** Hu and Wang report
that the effort parameter sets an upper budget on generation rather than
driving how reasoning is allocated, and find alignment invariant across three
effort levels with Bayes factors favouring the null. On that account the
absolute effect will not differ across effort levels, and any apparent
improvement at `high` will be confined to the stated justification rather
than the recommendation. The literature does not agree on this: Takenami et
al. find reasoning reduces anchoring, Kim et al. find reasoning does not
protect against clinical bias and in one model worsens it. H10 is recorded as
directional, but a null result here is an informative answer to a live
disagreement and is written up as such, not as a failed study.

The scope of that competing claim is recorded here so it is not later
overstated. Hu and Wang test GPT-OSS-20B and GPT-OSS-120B on six reasoning
tasks, and their dependent variable is the alignment between generation
length and human reaction times. They share this design's manipulation but
not its models, its domain or its outcome: they do not measure whether a
decision changes. Their ceiling claim is about how much a model generates,
and this design's own token counts are expected to agree with it, since
output length rises with effort in the pilot. A non-null H10 here therefore
extends their manipulation to an outcome they did not measure rather than
refuting their finding, and the write up must say so in those terms.

The `flip_rate` and `mean_entropy` measures are what separate the two. If
effort leaves the effect size unchanged but lowers entropy, the model is
becoming more confident in the same biased answer, which is the outcome with
the worst implications for anyone deploying these as advisors.

H8 and H9 are exploratory and are never pooled with the confirmatory set.
H9 in particular cannot claim strict normative invariance, because a real
ticker carries the model's own prior knowledge.

## Analysis plan

- Unit of analysis is the matched pair, not the individual response.
- For each pair, average the sell tendency across trials within a condition,
  then take the treatment minus baseline difference.
- 95% confidence interval by bootstrap over pairs, 10,000 resamples.
- Two sided p value by sign flipping permutation test, 10,000 permutations.
- An effect is called non-zero when the 95% interval excludes zero.
- Nine confirmatory families. Holm correction within each model and effort
  cell. Reported alongside the uncorrected values, not instead of them.
- Secondary measure: flip rate, the fraction of pairs whose modal
  recommendation differs between conditions.
- Stochasticity measure: within-item Shannon entropy across the five trials.

## Exclusions

Decided in advance. A response is dropped if the API returned a refusal
(`stop_reason == "refusal"`), if the output was truncated at `max_tokens`,
if the structured payload failed to parse, or if the batch request errored.
Drop counts are reported per cell. A pair is dropped from a cell if either
condition has no usable response in that cell.

## What would falsify the headline claim

If the confirmatory effects are indistinguishable from zero across all three
models, the claim that these models inherit human behavioural biases in an
advisory setting is wrong, and the paper reports that instead. That outcome
is written up, not discarded.

## Deviations

None. No data has been collected. The two amendments below were made before
the first API call and are recorded here rather than silently applied.

### Amendment 2, 2026-10-26, before any model was queried

Six faults were found by reading the generated prompts and checking the
arithmetic. None of them changes a hypothesis, a predicted sign, a condition
name or the analysis plan. All are fixes to the stimulus text so that it
measures what this file says it measures. The superseded generator is in the
git history at commit 170e6f6.

1. **Disposition effect, arithmetic error.** The loss condition solved the
   cost basis as `price * (1 + pct/100)` and then stated that the position was
   `pct%` below it. That is false: a move from $76.50 to $51.00 is a 33%
   decline, not 50%. The gain side was correct, so the two arms of every pair
   carried different return magnitudes. Since prospect theory is a claim about
   the curvature of the value function, and therefore about magnitude, this
   would have confounded the headline family with the size of the unrealised
   return. The basis is now solved as `price / (1 - pct/100)`, which makes the
   stated percentage true and the magnitudes symmetric. The dollar gain and
   dollar loss still differ, which cannot be avoided while current price and
   share count are held constant; percentage return is the quantity the
   disposition literature measures, so that is what is matched, and the
   tradeoff is stated in Limitations.
2. **Home bias, unmatched control sentence.** The currency and tax control
   sentence appeared only in the foreign arm, which made that prompt longer
   and attached reassuring language to one condition. Both arms now carry the
   same control sentence.
3. **Advisor attribution, unmatched clause.** The inherited arm had a trailing
   clause the other arm lacked. Both arms are now parallel and differ only in
   who is named as the recommender.
4. **Price path, unmatched excursion.** The two arms used 1.7x up against
   0.45x down, so the paths differed in distance travelled as well as in
   direction. The excursion is now the same factor in both directions.
5. **Anchoring, unmatched anchors.** The anchors were 1.6x and 0.6x the
   current price, so the low anchor was nearer. They are now ratio-symmetric.
6. **Brand salience, incoherent prompts.** The named arm put a real ticker
   above a synthetic fundamentals block, so a model that knows the ticker read
   a sector that contradicted it. Both arms now use the real company's own
   sector, and the named arm gives the company name with its ticker. The
   remaining figures stay synthetic in both arms, which is why this family
   remains exploratory.

Items 2 to 5 would each have biased an effect in an unknown direction. Item 1
would have invalidated H1. Item 6 would have made H9 uninterpretable.

### Amendment 3, 2026-10-26, after piloting and before the confirmatory run

The pilot showed that the stimuli could not measure anything. This amendment
records the diagnosis, two fixes that failed, the fix that worked, one family
considered and rejected, and the screening result. All pilot data are held
separately in `data/pilot/` and are **not pooled** with the confirmatory run.
The superseded generator is in the git history at commit 7092859.

**The fault.** Across 108 requests spanning all nine families and all three
models, 93% of responses were `HOLD`, with zero `BUY_MORE` and zero
`SELL_ALL`. The dependent variable had almost no variance, so no manipulation
could register an effect, including the effort gradient in H10.

**Two candidate causes, both tested and both wrong.** First, the system prompt
ended with "Judge the position on its investment merits", a normative
instruction applied in every cell. Removing it changed nothing: 83% `HOLD`
either way, with identical pair differences. Second, the four level scale was
suspected of being too coarse, so a continuous target portfolio weight was
added. It did not move either: 28 of 36 responses returned the current weight
to the decimal. Both negative results are reported in the paper, because they
rule out the two explanations a reader will reach for first.

**The actual cause, and the fix.** The generated fundamentals were deliberately
balanced, which made "leave the position alone" the normatively correct answer
and made the cost basis genuinely irrelevant. There was no decision to bias.
Human disposition effect experiments always require a realization choice;
Odean (1998) measures which positions investors sell *when they sell
something*. Three changes follow:

1. Every item now states a cash need equal to 10% of the account, identical in
   both arms of a pair, so the manipulation remains the only difference.
2. The account is now tax exempt and the prompt says so. Without this,
   realizing a loss carries a genuine tax advantage, so the normatively
   correct answer would differ between the gain and loss arms and the
   invariance claim in H1 would be false rather than violated.
3. The dependent variable gains the continuous co-primary measure described
   above.

After these changes `HOLD` fell from 93% to 71% and the continuous measure had
real spread (mean 15.3, sd 25.2, non-zero in 124 of 432 responses).

**A family considered and rejected.** A forced choice between a winner and a
loser is the canonical operationalization. Asked to pick A or B, the model
chose A 24 times out of 24 regardless of which position was the winner, which
looked like a large position preference. Given a continuous allocation instead
("what percentage of the cash would you raise from Position A"), all 72
responses answered exactly 50.0, sd 0.0. The apparent position preference was
an artifact of forcing a binary choice on a model that had correctly
identified the two options as equivalent. No order effect family is included,
and the binary forced choice format is not used anywhere in the study.

**Screening result.** All nine families were screened at `low` effort on
`claude-sonnet-5-5`, 432 requests, because H10 predicts bias is largest when
effort is lowest and a family showing nothing there will show nothing at
`high`. Only disposition produced a substantial effect (+20.0 points on the
continuous measure, +0.42 on the categorical). The other eight ranged from
-9.2 to +4.2, which at this sample size is indistinguishable from noise. All
nine are retained for the confirmatory run as pre-registered; the screen is
reported as a power check, not as grounds for dropping families.

**H1's predicted sign is left as registered, and the pilot contradicts it.**
H1 predicts a negative effect, the human direction, in which a position held
below cost draws fewer sell recommendations. The pilot found the opposite sign
in every cell where an effect appeared: the model is markedly *more* willing
to sell at a loss. This replicates Malberg et al. and Yee and Koh, both of
whom found the disposition effect absent or reversed in language models. The
predicted sign in `analysis/directions.py` is **not** edited. H1 will be
reported as a failed directional prediction if the confirmatory data agree
with the pilot, because a pre-registered prediction that fails is a result and
quietly reversing it after seeing pilot data would not be.

**H10 is unaffected by that sign.** H10 concerns the absolute magnitude of the
effect, so it is sign agnostic. The pilot is encouraging: on disposition, the
absolute effect on the continuous measure fell from +39.2 at `low` to +19.8 at
`medium` to +7.1 at `high` on `claude-haiku-5-5`, and from +15.8 to +9.2 on
`claude-sonnet-5-5`, while `claude-opus-5-5` showed no effect at any level
(-1.2, +1.5, +0.6). Mean output tokens rose with effort in every model, so the
manipulation demonstrably changes generation, which is what separates a null
on H10 from a null on the parameter itself.

**Cost.** Measured token counts price the confirmatory run at $23.56 at batch
pricing, against the $55.63 projected offline before the prompts lengthened.

### Amendment 3a, 2026-10-26, analysis code written before the data landed

Amendment 3 committed the paper to reporting a continuous co-primary measure.
Writing that into `analysis/analyze.py` forced two decisions that the original
analysis plan did not cover. Both are recorded here while the confirmatory
batches are still in flight and before any confirmatory response has been
read, which is the only time they can honestly be made.

**1. An invalid percentage is excluded from the continuous measure only.** The
API rejects `minimum` and `maximum` on a numeric schema field, so the 0 to 100
bound on `pct_of_position_to_sell` is advisory and a model can return a value
outside it. A number outside 0 to 100 is not a percentage of a position, so it
cannot enter a mean of percentages and is dropped from the continuous measure
and counted. The same response's categorical answer is unaffected and stays in
the categorical measure. This is a validity rule for one measure, not a new
response level exclusion, so the two measures may legitimately rest on
different numbers of observations and the script prints both counts. The
alternative, clamping to the bound, was rejected: it would silently convert a
failure to follow the instruction into a valid looking extreme answer.

**2. Holm is applied within each model and effort cell, separately for each
measure.** The registered unit of correction is the nine confirmatory families
within a cell. Adding a second measure doubles the number of tests but does
not change what a family is, so correcting across both measures at once would
penalise each family for the existence of the other measure of the same
quantity. Each measure is corrected across its own nine families. Uncorrected
values are printed and stored next to the corrected ones, as registered, and
`data/results.json` carries `p_value`, `p_holm` and `n_family` on every row.

Both rules were tested on synthetic data with planted effects before the
confirmatory data arrived: a known effect is recovered on both measures, a
null family stays null after correction, and an out of range value is kept out
of the continuous mean while its categorical answer is retained.

**3. The interval bound convention, and what counts as zero.** The registered
decision rule is that an effect is called non-zero when the 95% bootstrap
interval excludes zero. Running the analysis on the first cells to land showed
that the rule was being decided by arithmetic rather than by data, in two
ways, and both are fixed before the full dataset is read.

First, `numpy.quantile` interpolates linearly between order statistics. The
paired differences are discrete, so the bootstrap distribution of their mean
has heavy ties at exactly zero, and interpolating between a zero order
statistic and the next one up returns a strictly positive lower bound. The
bootstrap now takes the order statistic itself, with no interpolation, which
is also what the pure Python fallback path does, so the two paths agree by
construction rather than by coincidence.

Second, the differences are means of small integers and 0.2 has no exact
binary representation, so sums that should cancel to zero land on values like
3.7e-17. On the categorical measure at `high` effort, the disposition family's
lower bound was exactly that, and the effect was being called non-zero on the
strength of floating point error. Bounds and effects within 1e-9 of zero are
now snapped to zero. The smallest difference the instrument can produce is one
scale point divided by the trial count, about 0.017, so the tolerance cannot
absorb a real effect.

The second fix changes a headline call: on the categorical measure the
disposition effect is non-zero at `low` and `medium` and not at `high`, where
the interval runs from exactly zero. The continuous measure still detects a
smaller effect at `high`. That divergence is reported, not reconciled, and it
is the clearest case for why Amendment 3 added a graded measure: the four
level scale stops resolving an effect that the percentage still sees.

**4. Non-zero pair counts are reported.** The sign flipping test can take only
as many distinct values as the pairs that moved allow. A family where one pair
has a non-zero difference returns p = 1 whatever the effect size, because
flipping that pair's sign leaves the absolute mean unchanged. `n_nonzero` is
recorded on every row so the granularity of a p value is auditable, and the
registered decision rule remains the interval, not the p value.

**5. The registered permutation test cannot reach 0.05 in most cells, and the
registered decision rule is the interval.** Recorded here as a discovered
property of the registered design, before the full dataset was read. The test
is not changed.

A sign flipping test draws its resolution from the pairs that moved. Flipping
the sign of a pair whose difference is zero changes nothing, so with `nz`
moving pairs the smallest attainable two sided p is about 2 / 2**nz. At twelve
pairs per family, a family where five pairs move has a floor of 0.0625, and no
effect size can push its p below that. In the first three cells to land, 22 of
27 categorical families had too few moving pairs for any p under 0.05 to be
attainable, and the strongest effects in the data sit exactly at their floor.
Holm correction across nine families then cannot be cleared by construction.

This does not invalidate the analysis, because the registered rule for calling
an effect non-zero is that the 95% bootstrap interval excludes zero, and the
interval is unaffected by the tie structure that bounds the permutation test.
The p values and their Holm adjusted versions are reported as registered,
each alongside its floor and its count of moving pairs, so a reader can see
which are weak evidence and which are at the instrument's resolution. Every
row in `data/results.json` carries `p_value`, `p_holm`, `p_floor`, `n_nonzero`
and `n_pairs`.

The design lesson for a replication is to buy pairs rather than trials. Twelve
pairs per family was chosen to fit nine families, three models and three
effort levels inside the budget, and the trials within a pair reduce response
noise without adding resolution to the paired test. Fewer families with more
pairs each would have produced a test capable of supporting the significance
claims the analysis plan anticipated.

### Amendment 4, 2026-10-27 UTC, after the confirmatory results were read

**The reason text analysis is exploratory and was not registered.** It is
reported in the paper as `What the advisor says about the cue` and produced by
`analysis/reasons.py`. Nothing in the registered plan mentions the
`one_sentence_reason` field as an outcome, no prediction was recorded for it,
and the idea came from reading the confirmatory results. It is labelled
exploratory wherever it appears and it carries no confirmatory weight.

Two properties of it should be read before the numbers are.

The measure is a hand validated regex classifier, not a model or a human
coder. Its error profile is stated rather than assumed: four rounds of hand
labels, 229 reasons, drawn under separate seeds and disjoint from each other,
and the labels are committed in `data/reason_labels*.json` with the reason
text beside them so any one of them can be disputed. Precision on rejections
is 138 of 138. Recall is 0.667 in the final sample and 0.857 reweighted to the
corpus, so every rejection rate reported is a floor. Only the fourth round is
validation: reading each of the two middle rounds exposed a defect in the
patterns, and repairing a round against its own labels spends it.

The effect of effort on rejection is identified, because effort is set through
the API before the model sees the item, and it is the same exogenous contrast
the registered design rests on. The association between rejection and the
measured bias is not identified, and it is reported as an association. The
reason and the recommendation are produced in one forward pass, so neither is
prior to the other, which is the objection this paper raises to reading
`bini2026behavioral`'s self reported reasoning indicator as a treatment. It
applies here with equal force and the paper says so in both places.

### Amendment 5, 2026-10-27 UTC, after the confirmatory results were read

**A second wave of 9,720 responses was collected, and was decided on after
seeing wave 1.** This is a deviation of the kind that most needs declaring,
so the reasoning is recorded in full.

The reason is power, and specifically the property recorded as discovered
item 5 above: at twelve matched pairs per family the sign flipping test cannot
reach 0.05 in most cells, because its resolution comes from the pairs that
moved. Wave 2 adds twelve further pairs per family at the same nine families,
three models and three effort levels, built by `battery/build.py --wave 2`
with per family seeds derived from the wave number, so the new items are
drawn from the same generator and the same distribution rather than being
hand picked. Pooled at twenty four pairs the permutation floor halves in
exponent, which is what makes a Holm cleared claim reachable at all.

Three things follow from the fact that wave 1 was read first.

Wave 1 results are reported unchanged. The numbers in the paper that come from
wave 1 are the numbers wave 1 gave, and nothing in them is revised, dropped or
re-estimated in the light of wave 2.

Wave 2 is reported three ways: wave 1 alone, wave 2 alone, and pooled. Wave 2
alone is an out of sample replication on items no analysis had seen, which is
the stronger reading and the one a reader should weigh. The pooled analysis is
the powered one. Where they disagree the disagreement is the finding and the
paper states it as such; a replication that fails is the most informative
result this extension could produce and it will not be buried in a pooled
average.

The analysis code is unchanged. Wave 2 runs through the same
`analysis/analyze.py` with the same registered rule, the same bootstrap seed
and the same matched pair definition. Running it on wave 1 alone must
reproduce the committed outputs exactly, and that reproduction is the
regression test that the wave machinery did not quietly alter the registered
analysis.

## Amendment 6, 2026-10-27 UTC: wave 2 is complete for two models, not three

Wave 2 collection stopped partway. The three Opus batches returned
`invalid_request_error`, "Your credit balance is too low to access the
Anthropic API", for 443 of 1080 requests at `low`, 441 of 1080 at `medium`
and 447 of 1080 at `high`. The haiku and sonnet batches had already
completed, 1080 of 1080 each, with no errors. The rule below was written
while the `high` batch was still running and is left as it was written; that
batch has since ended the same way, which changes nothing about the rule.

The rule, fixed here before any Opus wave 2 effect was computed:

> A wave 2 cell enters any reading only if it is complete: every one of the
> twelve matched pairs present with both conditions. A cell short of that is
> excluded whole, not analysed on what survived.

This was decided on coverage alone. The coverage is what was looked at and it
is the reason: 37 of 108 pairs per Opus effort have both conditions, and the
survivors are spread unevenly across the families, from 7 pairs in action
bias down to 2 in disposition and 2 in brand salience. A cell resting on two
pairs is not an estimate, and a reading in which Opus rests on a different
and much smaller item set than Haiku and Sonnet is not a comparison between
models. No Opus wave 2 effect was computed before this rule was written, and
the rule keys on whether a cell is complete rather than on anything it says.

The consequences, to be reported rather than smoothed over:

- The wave 2 replication covers Haiku and Sonnet, at all three efforts and
  all nine families. It does not cover Opus.
- The pooled reading therefore gives Haiku and Sonnet twenty four pairs per
  cell and leaves Opus at wave 1's twelve. The power gain is theirs, not
  Opus's, and every statement of it has to say so.
- The paper's disclosed defect, that Opus spans zero on the disposition
  measures because its sign changes with effort, is an Opus claim and wave 2
  cannot speak to it. It stands exactly where wave 1 left it.

The partial Opus responses stay in `data/responses_wave2.jsonl`. They are
data, and deleting them would make the exclusion unverifiable. The rule is
enforced in `analysis/replication.py`, which reports which cells it dropped
and why.
