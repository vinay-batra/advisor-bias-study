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

python battery/build.py            # 216 prompts, costs nothing
python scripts/selftest.py         # proves the analysis works, costs nothing
python scripts/estimate_offline.py # prices the study, needs no key
python scripts/pilot.py --bias disposition --pairs 3
python scripts/estimate.py         # measured cost, needs a key
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

1. Lock the pre-registration and commit it. Done, commit `170e6f6`.
2. Run the literature search before writing a word of the paper. Done, see
   `LITERATURE.md`. It changed what the paper claims, and it is the reason
   `PREREGISTRATION.md` carries Amendment 1.
3. Build the battery and read the prompts by hand. Done, and it found six
   faults including an arithmetic error that would have invalidated H1. See
   Amendment 2. Re-read them whenever the generator changes:
   `python battery/build.py` then compare the two arms of each pair.
4. Run the self test. Done, passes, and it recovers planted effects.
5. Run the pilot on one bias. Confirm the effect is visible or absent. Done,
   and it is the reason this study exists in its current form. The pilot found
   that 93% of responses were `HOLD`, so the dependent variable had no
   variance and nothing could be measured. Diagnosing that took four rounds of
   cheap probing and cost about $4. See Amendment 3.
6. Screen every family at `low` effort before committing to the full grid.
   Bias is largest where effort is lowest, so a family that shows nothing in
   the screen will show nothing at `high`. Done, $1.53, and it found one
   substantial effect out of nine.
7. Only then submit the full batch.

If the pilot comes back flat, do not conclude there is no bias. Check first
that the dependent variable can move at all. A measure that never changes
looks exactly like a model that is never biased.

## State

| Step | Status |
|---|---|
| Pre-registration committed before first API call | done |
| Literature search, 20 papers read, novelty repositioned | done |
| Every citation verified by DOI against Crossref | done, 2 were wrong |
| Prompt battery built and hand-checked | done, 6 faults fixed |
| Analysis validated against planted effects | done, passes |
| API key in `.env` | done, chmod 600, gitignored |
| Pilot | done, found the dependent variable was at ceiling |
| Stimulus redesign, decision pressure added | done, Amendment 3 |
| Screening run, all nine families at low effort | done, $1.53 |
| Cost re-estimated from measured tokens | done, $23.56 batch, not $56 |
| Confirmatory batch submitted, 9,720 requests | done, 9 batches |
| Collect, analyse, figures | running |
| Four follow-up reads listed at the end of `LITERATURE.md` | not started |
| Rotate the API key | **do this when the run is finished** |

### What the pilot and the screen found

The dependent variable had to be rebuilt before anything could be measured.
With decision pressure in place, one family of nine shows a substantial
effect, and it has the opposite sign to the human literature: the model is
markedly more willing to sell at a loss, not less. On that family the effect
shrinks as reasoning effort rises, steeply in the weakest model and not at
all in the strongest, which is the paper's headline.

| disposition, continuous measure | low | medium | high |
|---|---|---|---|
| `claude-opus-5-5` | -1.2 | +1.5 | +0.6 |
| `claude-sonnet-5-5` | +15.8 | +17.9 | +9.2 |
| `claude-haiku-5-5` | +39.2 | +19.8 | +7.1 |

These are pilot numbers on 24 items at 2 trials. They are held in
`data/pilot/` and are never pooled with the confirmatory run.

## Building the paper

No LaTeX is installed on this machine, and installing MacTeX is a 5 GB
download that needs an administrator password. Put `paper/` into Overleaf
instead, which is free and is what the target venues expect anyway. Replace
the preamble with the venue's own style files before submitting; the comment
at the top of `main.tex` says which ones.

## Reproducing a published result

Everything needed is in this repository: the generator seed, the exact model
IDs with no date suffixes, the effort levels, the trial count, the prompts,
the raw responses and the analysis. Model behaviour changes over time, so
record the run date alongside the model ID. Appendix A of the paper is
`data/items.jsonl`.
