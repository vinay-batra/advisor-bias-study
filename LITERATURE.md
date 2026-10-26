# Literature search

Searched 2026-10-26 on Google Scholar, arXiv, ACL Anthology, Crossref and
publisher pages. This file is the record of what exists, so that Related Work
is written from papers that were actually opened and so that the novelty claim
in `PREREGISTRATION.md` can be checked by someone else.

Every bibliographic entry in `paper/refs.bib` was verified by DOI lookup
against Crossref, or against the publisher's own page where the venue is not
indexed. Two recalled citations were wrong and are corrected there.

## Verdict

The study is not a replication, but the original framing of it was too
confident. Three of the nine bias families have been tested on language models
before, and the headline question needed to move.

What already exists:

- Anchoring, framing, loss aversion and mental accounting in LLMs: tested
  repeatedly, across many models.
- The disposition effect in LLMs: tested twice, by `malberg2025comprehensive`
  as one of thirty biases and by `yee2026calibrating` as one of eight
  behavioural parameters. Both find LLMs do **not** show the human pattern.
- Reasoning models being less biased than non-reasoning models: found by
  `takenami2025anchoring` for anchoring.

What does not exist, and is what this paper does:

1. **Reasoning effort as an exogenous, graded treatment.** No paper found
   manipulates the reasoning budget at three levels inside a fixed model and
   measures the change in a behavioural finance bias.
2. **Advisory framing with portfolio state.** Prior work asks the model to
   choose between abstract gambles, or between two assets. None states a cost
   basis, a position weight and a fundamentals block and asks whether to hold
   or sell.
3. **A sampling protocol for models with no sampling parameters.** The
   protocol every prior paper uses is no longer executable (see below).
4. **Two bias families that appear nowhere**: advisor attribution and price
   path.

## The paper this one is positioned against

`bini2026behavioral`, Bini, Cong, Huang and Jin, "Behavioral Economics of AI:
LLM Biases and Corrections". 69 pages, Boston University Questrom plus Cornell
SC Johnson plus NBER, first draft January 2025, this draft January 2026,
presented at the 2026 AFA Annual Meeting. It describes itself as the most
comprehensive set of such experiments to date and it is the serious prior work
in this exact area.

What it does: sixteen experimental questions from cognitive psychology and
experimental economics, put to twelve LLMs across families and generations
(benchmark models GPT-4, Claude 3 Opus, Gemini 1.5 Pro, Llama 3 70B), 100 API
calls per question per model, temperature 0.5, top-k 50, top-p 0.9. Responses
are graded rational, human-like, or other. Debiasing is attempted by role
priming and by a four-step expected-utility procedure in the prompt.

What it finds that matters here: an indicator they call "system 2 thinking",
set to one when the model reports its reasoning was analytical rather than
intuitive, **increases rational responses by about 40 percent**. They use it as
a mediator for the effect of role priming.

### Why that leaves this paper a question to answer

Their reasoning measure is the model's own self-report, collected in the same
response as the answer. It is not exogenous. The same forward pass that
produced the answer also produced the label describing it, so a model that
answers correctly and then calls its own reasoning analytical generates that
correlation without any causal path from deliberation to accuracy. Their
mediation analysis assumes the direction of causation that the design cannot
establish.

This study replaces the self-report with an API parameter set before the model
sees the item, at three levels, with the prompt held constant. That converts a
correlation into an experiment, and it is a gap in a paper going to the AFA,
which is a defensible place for a contribution to sit.

## The methodological contribution, with a named instance

`bini2026behavioral` sets temperature to 0.5, top-k to 50 and top-p to 0.9,
and discusses at length how temperature reshapes the token distribution. As of
2026-10-21, `temperature`, `top_p` and `top_k` return HTTP 400 on every current
Claude model. `malberg2025comprehensive` runs at temperature 0.0 with one
sample per item, which is also no longer possible.

So the protocol of the leading paper in this area cannot be run on the models
people now deploy, and the single-sample-at-temperature-zero protocol cannot
either. This paper proposes the replacement: repeated sampling per item,
percentile bootstrap intervals over matched pairs, and within-item response
entropy reported as a result rather than suppressed as noise. That is a
contribution available to this paper only because of when it is being written.

## The disagreement this paper can resolve

Does more deliberation reduce bias? The literature does not agree, and nobody
has tested it with the reasoning budget as the treatment.

| Paper | Design | Finding |
|---|---|---|
| `takenami2025anchoring` | reasoning models vs others, price negotiation | reasoning models less prone to anchoring |
| `bini2026behavioral` | self-reported reasoning type as mediator | analytical self-report, +40% rational |
| `kim2025biasmedqa` | reasoning models on clinical vignettes | reasoning does not protect, sometimes worse |
| `hu2026effort` | three effort levels, GPT-OSS 20B and 120B | effort is a ceiling on generation, not a dial; Bayes factors favour the null |
| arXiv 2505.15392 | anchoring mitigations | conventional mitigation fails, reasoning helps somewhat |

The first two compare different models, or compare a model to its own account
of itself. Only `hu2026effort` manipulates effort directly, and it finds
nothing, on reasoning-time alignment rather than on bias. H10 is therefore a
real test with a real chance of a null, and `hu2026effort` is pre-registered as
the competing hypothesis.

## Everything else found, and why it does not overlap

- `malberg2025comprehensive`, Malberg et al., NLP4DH 2025. Thirty biases, twenty
  models, temperature 0.0, one sample per test case, 30,000 cases. Disposition
  effect is bias 30. Reports disposition effect and status-quo bias as the only
  two with a strong negative average, meaning these models preferred change.
  No cost basis, no advisory frame, no reasoning control, no repeated sampling.
  Appendix B.30 read in full 2026-10-26, and it matters more than the summary
  above suggests. Their instrument presents two owned assets, one up and one
  down by a percentage drawn uniformly from [10, 50], asks which the model
  would rather sell while keeping the other, and **swaps which asset has
  gained between the control and treatment arms**, scoring a disposition
  effect only when the preference for selling the winner survives the swap.
  The response is a 7-point Likert scale, not a binary pick.
  Two consequences for this paper. First, that swap is exactly the control
  this paper's rejected two-asset format lacked: a model that names the same
  position in both arms scores near zero under their design rather than
  presenting as biased, so the pilot's 24-of-24 artifact is not a fault in
  their result and must not be written up as one. Second, their strong
  negative average is therefore not an option-preference artifact either,
  which makes it real independent support for the sign reversal.
  What their format cannot do is attach a cost basis to a single position and
  ask whether to act on it. A relative preference between two assets is not a
  realisation decision, and the realisation decision is what Shefrin and
  Statman and Odean measure in humans. That is the gap this design fills, and
  it is now stated in the paper's rejected-format subsection.
  Verbatim, p. 8: "Only two of the 30 tested biases, Status-Quo Bias and
  Disposition Effect, were measured with strong negative direction, on
  average. On both biases, negative scores express a model's preference for
  change."
- `yee2026calibrating`, Yee and Koh, arXiv 2602.01022, revised May 2026. Four
  models, 24,000 agent-scenario pairs, eight behavioural parameters. Finds
  near-zero disposition effect at baseline and shifts it with profile-based
  prompting. Calibration paper, not a bias audit, and no effort manipulation.
- `takenami2025anchoring`, Findings of EMNLP 2025, pages 4481 to 4498. Seller
  agents told to anchor in price negotiations. Compares reasoning models to
  others; does not vary effort within a model.
- `kim2025biasmedqa`, medRxiv 2025. Clinical vignettes, BiasMedQA. Finds
  reasoning does not consistently prevent bias and in one model increased
  vulnerability to frequency and recency bias. Different domain, useful
  counterweight.
- `hu2026effort`, arXiv 2605.16938. Three effort levels on GPT-OSS 20B and
  120B over six reasoning tasks. Concludes the effort parameter sets an upper
  budget on generation rather than driving real-time allocation. Measures
  cost alignment with human reaction times, not bias.
- `lee2025yourai`, Lee et al., ICAIF 2025, arXiv 2507.20957. Balanced and
  imbalanced argument scenarios. Finds preferences for technology, large-cap
  and contrarian positions, escalating into confirmation bias. Measures
  preference over assets, not normative invariance, and has no owned position.
- CogBias, Huang et al., arXiv 2604.01366. Four bias families, steering and
  mitigation, three models. No finance domain, no effort manipulation.
- Weerasekara et al., arXiv 2608.05166. Nine biases by eight frontier models
  over a 9x9 interaction matrix, 24,300 prompts. Studies how biased user turns
  modulate in-context reasoning. Multi-turn, no finance, no effort control.
- arXiv 2602.14233, evaluating LLMs in finance. Argues finance-specific biases
  contaminate benchmarks. Useful for the limitations section, not a competitor.
- arXiv 2609.15727, He, Hong, Chen, Ni and Liu, "Are LLMs Good Financial User
  Simulators? Multi-view Investor Logic Alignment", 14 Sep 2026. **Corrected
  2026-10-26.** An earlier version of this file recorded that this paper
  reports models overpredicting hold and underpredicting sell. It does not.
  It predicts individual users' next-day trades in an 80-participant paper
  trading study, 1,239 aligned user-days, and has no hold category at all.
  Its finding is that no evaluated model beat a recent-activity persistence
  baseline. Not a competitor and not a source for the hold baseline. The
  mistake is kept visible here because the claim had already been used in
  conversation before it was checked.
- arXiv 2507.20957, Lee, Seo, Park, Lee, Ahn, Choi, Lopez-Lira and Lee, "Your
  AI, Not Your View: The Bias of LLMs in Investment Analysis", 28 Jul 2025.
  The closest neighbour found so far. Six models, 427 S&P 500 stocks, 3,416
  evidence items, 10 repetitions per stock at temperature 0.6. Measures sector
  preference, market-cap preference, momentum versus contrarian preference,
  and confirmation bias as a flip rate under counter-evidence. Three reasons
  it does not overlap:
  1. It does not manipulate reasoning effort, thinking budget or deliberation
     anywhere, and its own limitations section says the design is weak for
     reasoning models. That is the gap this paper fills, stated by a recent
     paper in the same area, which is worth quoting in the introduction.
  2. It tests neither the disposition effect nor cost basis.
  3. Its action set is buy or sell with no hold, so it cannot observe the
     ceiling documented in Amendment 3.
  Two further uses. It is a third named instance of the now-unexecutable
  fixed-temperature protocol, alongside Bini et al. at 0.5 and Malberg et al.
  at 0.0, which strengthens the methodological contribution. And it reports
  response entropy for two models, so it is the right citation for the
  within-item entropy measure.
- arXiv 2503.08750, product bias in LLM investment recommendation. Reports
  persistent preferences for specific tickers such as AAPL and MSFT. This is
  the published justification for using synthetic companies in the
  confirmatory families.

## Still to read before Related Work is final

- ~~`bini2026behavioral` Table 1, the full list of sixteen questions, to
  confirm no overlap item by item.~~ Closed 2026-10-26, read in full. Their
  sixteen, verbatim from Table 1. Panel A, preferences: prospect theory
  diminishing sensitivity, prospect theory loss aversion, prospect theory
  probability weighting, narrow framing, ambiguity aversion, hyperbolic
  discounting. Panel B, beliefs: sample size neglect (three items), base rate
  neglect, conjunction fallacy, gambler's fallacy, confirmation bias,
  anchoring, overconfidence as overprecision, overconfidence as
  overestimation.
  Overlap with this paper's nine families is two at the level of the name and
  neither at the level of the item. Their narrow framing is a modified
  Problem 10 from Tversky and Kahneman (1981), a risk-preference question,
  not a valence frame on one recommendation. Their anchoring is Question 14,
  the general-knowledge anchor from Tversky and Kahneman (1974) page 1128,
  not an anchor inside a portfolio decision. The word "disposition" does not
  appear anywhere in the 69 pages, and neither do mental accounting, advisor
  attribution, price path or brand salience. Seven of nine families have no
  counterpart, and none of their sixteen items states a cost basis, a
  position weight or a fundamentals block.
  Two corrections to how this repository had been describing the paper.
  First, their effective correction is role priming to act as a rational
  investor under expected utility, which they call economically modest, while
  the detailed version of the same idea, a four-step expected utility
  procedure, is ineffective, and supplying the Kahneman and Tversky (1979)
  findings reduces rational responses by about 29 percent. The paper's own
  summary is that debiasing remains a challenging task, which is a better
  motivation for this study than the +40 percent mediator figure alone.
  Second, their mediator is confidence and reasoning *type*, self-reported in
  the same forward pass, which is exactly the identification problem this
  design removes by setting the budget before the model sees the item. The
  numbers, now verified rather than remembered, make the point harder than
  the +40 percent figure alone did. Their Table 8 reports that "system 2
  thinking", an indicator equal to one when the LLM selects reasoning type B,
  increases rational responses by 40 percent in Panel A and 38 percent in
  Panel B. Their actual exogenous lever, rational-investor role priming,
  moves that same indicator by only 11.4 percentage points, and high
  confidence by 6.6. So the big number belongs to the correlational mediator,
  not to anything the experimenter set.
  And the self-report is unambiguous, because their Internet Appendix prints
  the prompt: the model is asked to return its choice, its confidence level,
  a brief explanation and its reasoning type, type A for intuitive and type B
  for "analytical thinking and calculations", all in one response. One
  forward pass produces both the answer and the account of how it was
  reached. That is the sentence to cite when a reviewer asks why an exogenous
  effort manipulation is worth running at all.
- ~~`malberg2025comprehensive` Appendix B.30, the exact disposition effect
  prompt.~~ Closed 2026-10-26, read in full. See the expanded entry above.
- ~~arXiv 2609.15727 in full, for the hold-over-sell baseline.~~ Closed
  2026-10-26: the paper does not contain that result. See the corrected entry
  above.
- Finance Research Letters, "Multifaceted variability in LLM-driven stock
  recommendations", doi prefix S1544612325021762 on ScienceDirect. Paywalled,
  HTTP 403. Relevant to the repeated-sampling argument. Get it through a
  library or find the preprint.
- A targeted SSRN sweep for working papers from the last four months. Scholar
  and arXiv do not index SSRN reliably and finance work appears there first.

## The hold ceiling appears to be unreported

A targeted search for prior work documenting a hold default, an inaction bias,
or a degenerate recommendation distribution in language model investment advice
returned nothing that measures it. The nearest results are a large-cap tilt, a
product preference for specific tickers (arXiv 2503.08750), recommendation
variability across identical prompts, and confirmation bias. None of them
reports the distribution of buy, hold and sell recommendations, and the two
closest papers (arXiv 2507.20957 and the forced-choice portion of this study's
own pilot) restrict the action set to buy or sell, which makes the ceiling
unobservable by construction.

So the finding in Amendment 3, that 93% of advisory recommendations are hold
when the scenario carries no decision pressure, and that this floors any
matched-pair bias measurement, is original rather than a replication. It
belongs in the paper as a methodological result, not as a footnote. The search
is recorded here so the claim of novelty is auditable.
