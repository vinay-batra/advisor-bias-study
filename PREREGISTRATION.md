# Pre-registration

**Locked 2026-10-26, before any model was queried.**
Committed to git before the first API call. Nothing in this file is edited
after data collection begins. If something has to change, it is added below
under "Deviations" with a date and a reason.

## Research question

Do large language models acting as portfolio advisors exhibit the behavioural
biases documented in human investors, and does increasing the model's
reasoning effort reduce them?

## Why this is not a replication

Existing work on cognitive bias in language models tests abstract gambles
drawn from the Kahneman and Tversky tradition, on models that are now several
generations old, and reports single samples at a fixed temperature. Three
things are new here.

1. **Advisory framing with portfolio state.** Items are posed as a client
   portfolio review with holdings, cost basis, position weight and
   fundamentals, not as an abstract lottery.
2. **Reasoning effort as an independent variable.** Current models expose a
   reasoning effort control. Whether deliberation reduces behavioural bias or
   simply produces better rationalisations of the same biased answer is, as
   far as we know, unmeasured.
3. **A distributional protocol, by necessity.** Sampling parameters
   (`temperature`, `top_p`, `top_k`) were removed from the Messages API and
   now return HTTP 400 on every model. The fix-temperature-to-zero protocol
   used by nearly all prior work can no longer be executed. Every cell here
   is sampled repeatedly and reported as a distribution with a confidence
   interval.

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

H10, the effort hypothesis: for any bias family where a non-zero effect is
found at `low`, the absolute effect at `high` will be smaller. The
alternative, that deliberation leaves the answer unchanged and only improves
the stated justification, is the outcome we consider most likely to surprise
reviewers if it holds.

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

None yet.
