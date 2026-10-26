# Behavioural bias in LLM portfolio advisors

A measurement study. Nine behavioural finance biases, three models, three
reasoning effort levels, matched pair design, mechanical grading.

**Read `PREREGISTRATION.md` first.** It was locked before any model was
queried and it fixes the hypotheses, the predicted directions and the
analysis plan.

## The design in one paragraph

Every item is a matched pair: two prompts identical in current price,
position size, portfolio weight and fundamentals, differing only in a cue
that standard finance theory says is irrelevant to a hold-or-sell decision.
If the recommendation changes, the cue moved it, and that is the measured
bias. Grading is mechanical, because the model answers through a constrained
schema rather than in prose.

## Why the methodology is unusual

Sampling parameters were removed from the Messages API. `temperature`,
`top_p` and `top_k` now return HTTP 400 on every model, so the standard
"pin temperature to zero and send the prompt once" protocol from the prior
literature cannot be run any more. Every cell here is sampled five times and
reported as a distribution with a bootstrap confidence interval. Response
entropy across identical repeated prompts is reported as a result in its own
right.

Server-side refusal fallbacks are deliberately **not** enabled. A fallback
would answer on a substitute model, and model identity is an independent
variable in this study. Refusals are recorded as refusals and counted.

## Layout

```
config.py                 every number that goes in the methods section
battery/companies.py      synthetic company profiles
battery/items.py          the nine bias generators, one function each
battery/build.py          writes data/items.jsonl
run/submit.py             submits one Batch API job per model x effort cell
run/collect.py            polls, then joins results by custom_id
analysis/directions.py    pre-registered condition order and predicted signs
analysis/analyze.py       bootstrap CIs, permutation tests, effort trends
analysis/figures.py       the three paper figures
scripts/selftest.py       proves the analysis recovers a planted effect
scripts/pilot.py          a few live pairs, printed side by side
scripts/estimate.py       prices the full study using real token counts
paper/main.tex            the paper
```

## Running it

```bash
bash scripts/setup.sh
cp .env.example .env          # then put your API key in it
source .venv/bin/activate

python battery/build.py       # 216 prompts, costs nothing
python scripts/selftest.py    # proves the analysis works, costs nothing
python scripts/pilot.py --bias disposition --pairs 3
python scripts/estimate.py    # what the full run will cost
python run/submit.py          # the real run, batch pricing
python run/collect.py
python analysis/analyze.py
python analysis/figures.py
```

Do the first three steps before spending anything. `selftest.py` plants a
known bias in simulated data and checks the pipeline finds it: if it cannot
recover an effect that is definitely there, it cannot be trusted to report
one that is.

## Order of operations that matters

1. Lock the pre-registration and commit it.
2. Build the battery and read ten prompts by hand. Confirm that the two
   conditions of a pair differ in exactly one sentence.
3. Run the self test.
4. Run the pilot on one bias. Confirm the effect is visible or absent.
5. Only then submit the full batch.

## Reproducing a published result

Everything needed is in this repository: the generator seed, the exact model
IDs with no date suffixes, the effort levels, the trial count, the prompts,
the raw responses and the analysis. Model behaviour changes over time, so
record the run date alongside the model ID. Appendix A of the paper is
`data/items.jsonl`.
