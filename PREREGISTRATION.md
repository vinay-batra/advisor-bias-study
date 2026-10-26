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
