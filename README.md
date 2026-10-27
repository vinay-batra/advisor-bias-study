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
analysis/exploratory.py   seven questions the prereg does not cover
analysis/robustness.py    is the compression regression to the mean?
analysis/h10_placebo.py   is H10's ten of ten evidence, or the selection rule?
analysis/figures.py       the five paper figures
scripts/selftest.py       proves the analysis recovers a planted effect
scripts/pilot.py          a few live pairs, printed side by side
scripts/estimate.py       prices the full study using real token counts
paper/main.tex            the paper
paper/render_items.py     generates the example pair and the appendix
paper/Makefile            builds the paper, and `make check` gates it
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
python analysis/exploratory.py     # not pre-registered, labelled as such
python analysis/robustness.py      # does the mechanism survive?
python analysis/h10_placebo.py     # does the headline survive? a few minutes
make -C paper check                # builds the PDF, fails on a loose end
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
| Collect, analyse, figures | done, 9,720 of 9,720 usable, nothing excluded |
| Pre-registered analysis | done, `analysis/analyze.py` |
| Exploratory analysis, labelled as not registered | done |
| Robustness: compression against regression to the mean | done |
| Robustness: H10 against its own selection rule | done |
| Paper written, compiles clean | done, `make -C paper check` |
| Four follow-up reads listed at the end of `LITERATURE.md` | not started |
| Repository URL for the reproducibility section | **needs a remote** |
| Replace the preamble with the venue style files | not started |

### What the confirmatory run found, and where the pilot was wrong

All 9,720 requests returned usable responses. Nothing was excluded.

**The disposition effect is reversed and that is the registered sign
failing.** Pooled, $+0.239$ [$+0.148$, $+0.331$] on the four point scale and
$+13.4$ [$+8.8$, $+18.1$] percentage points. The models are more willing to
sell at a loss than at a gain, where H1 predicted the human direction.
`analysis/directions.py` was deliberately not edited.

**H10 holds in all ten qualifying cases.** Five families qualify on each
measure and in all ten the absolute effect at `high` is smaller than at
`low`. How much that is worth is the subject of `analysis/h10_placebo.py`,
because the hypothesis selects families on a noisy baseline and then asks
whether a second measurement is smaller, which shrinks on its own.

**Effort compresses rather than removes.** The spread of the nine family
effects falls with effort in all six model by measure combinations while the
mean does not. `analysis/robustness.py` tests that against regression to the
mean: it is large and survives every correction in Haiku, survives on the
continuous measure in Sonnet, and in Opus the nine families are not
separable from one another once item to item variation is charged against the
estimate, so there it is a conjecture.

**Two pilot readings were wrong, and the write-up says so.**

- *"Deliberation substitutes for capability"* is refuted. On the full data
  Opus has the **steepest** pooled effort slope and the only one whose
  interval excludes zero. The pilot's Opus row read as flat because 24 items
  at 2 trials could not resolve it.
- *"Longer answers carry less bias"* is refuted within a fixed effort cell,
  where the correlation is **positive**: $+0.190$ categorical and $+0.154$
  continuous over 972 pairs. The budget an experimenter sets and the
  deliberation a model displays are not the same variable, which is the
  paper's sharpest result against mediator designs.

Pilot numbers are in `data/pilot/` and are never pooled with the
confirmatory run.

## Building the paper

```bash
brew install tectonic
make -C paper check
```

`tectonic` is a single binary that fetches the packages it needs on first
run, so it does not want an administrator password and it is not the 5 GB
MacTeX download. `make check` builds the PDF and then **fails** if there is
an unresolved citation, a dangling cross reference or a line past the
margin; a clean build prints one line saying so. Run it before sending the
paper anywhere.

`paper/example_pair.tex` and `paper/items_appendix.tex` are generated from
`data/items.jsonl` by `paper/render_items.py`, and `make` regenerates them.
Editing either by hand is pointless because the next build overwrites it.

Replace the preamble with the venue's own style files before submitting; the
comment at the top of `main.tex` says which ones. The body is about 8,200
words in the article class, which is well over a workshop limit, so expect
to cut once the two-column style is in place.

## Reproducing a published result

Everything needed is in this repository: the generator seed, the exact model
IDs with no date suffixes, the effort levels, the trial count, the prompts,
the raw responses and the analysis. Model behaviour changes over time, so
record the run date alongside the model ID. Appendix A of the paper is
generated from `data/items.jsonl`: it prints one matched pair in full from
each family and the manipulated cue in all 108, so a reader can check that
no pair differs in anything but its cue.

The repository has no git remote, so the paper's reproducibility section
prints a visible placeholder rather than a URL that does not resolve. It is
a single macro, `\repourl`, set once at the top of `main.tex`.
