# SSRN posting package

Everything the SSRN submission form asks for, written out to paste. Posting
itself needs your own account, so this file stops at the point where only
you can act.

## What SSRN is, in one paragraph

Not a journal. It is a preprint repository: it hosts the paper, gives it a
permanent URL and a DOI, counts downloads, and performs no peer review.
Nothing about posting here competes with submitting the same paper to a
reviewed venue, and economics and finance use it as the default place a
working paper lives while it is under review somewhere else.

## Why posting now is safe, and why December is not

Two policies govern this and they contradict each other.

- **ARR's anonymity policy** says there is no anonymity period and that
  authors are free to post and discuss non-anonymous preprints at any time.
  In force since the February 2024 cycle.
- **The ACL 2027 call** says no deanonymised preprint may be posted in the
  month prior to submission.

Neither acknowledges the other. With ARR submission on 4 January 2027, the
stricter reading blacks out roughly **4 December 2026 to 4 January 2027**.
Anything posted before December is clear under either reading, so the window
is now and it closes at the end of November.

## Title

Does Deliberation Debias? Exogenous Reasoning Effort and Behavioural Finance Bias in Large Language Model Portfolio Advisors

## Abstract

Plain text, math markup stripped. SSRN does not publish an abstract character
limit anywhere I could find on 2026-10-27, and I am not inventing one. The
nearest real evidence is the submission form for SSRN's Financial Economics
Network at NYU Stern, which asks for 500 words or less; the long version is
about 330 words, so it clears that. Paste the long one. The short one exists
only so that a refusal at the live form does not turn into trimming by hand.

### Long version, 2,147 characters. Use this one.

Language models are increasingly asked for advice about financial positions people already hold, and they carry measurable behavioural bias. Whether deliberation removes it is unsettled, because the available evidence either compares different models, so that capability and deliberation move together, or infers deliberation from the model's own account of its reasoning, produced by the same forward pass as the answer.

We instead set the reasoning budget exogenously through the API, at three levels, before the model sees the item, and measure nine families of normatively irrelevant cue against matched pairs that differ only in that cue.

Across 9,720 responses from three models the disposition effect runs opposite to the human direction: pooled, these models are more willing to sell at a loss than at a gain, +0.239 [+0.148, +0.331] on a four-point sell-tendency measure and +13.4 [+8.8, +18.0] percentage points of the position, where the pre-registered prediction was negative. The reversal is carried by the two smaller models and appears in the strongest only as effort rises.

A second wave of 9,720 responses on two of those models reproduces the pattern at half that magnitude, which we measure to be regression to the mean rather than a failure to replicate: the slope of wave 2 on wave 1 across cells is +0.46 and +0.48, so a little under half of a first-wave effect was the item draw rather than the model.

Reasoning effort reduces the absolute effect in all nine qualifying confirmatory cases, against a shuffled-label null of 0.0125 rather than the 1-in-512 a count would suggest. It does so by compressing the spread of bias magnitudes across families rather than by lowering their mean.

The exogenous manipulation is what makes this visible. Measured the observational way on the same responses, with output tokens standing in for displayed deliberation, more reasoning goes with more bias between items and with nothing at all within an item. We also report that temperature is unavailable on these models, which makes this literature's fixed-temperature protocol unexecutable, and give a repeated-sampling replacement.

### Short version, 1,469 characters. Fallback only.

Language models are increasingly asked for advice about financial positions people already hold, and they carry measurable behavioural bias. Whether deliberation removes it is unsettled: the available evidence either compares different models, so capability and deliberation move together, or infers deliberation from the model's own account of its reasoning, produced by the same forward pass as the answer.

We set the reasoning budget exogenously through the API, at three levels, before the model sees the item, and measure nine families of normatively irrelevant cue against matched pairs differing only in that cue. Across 9,720 responses from three models the disposition effect runs opposite to the human direction: these models are more willing to sell at a loss than at a gain, +0.239 [+0.148, +0.331] on a four-point sell-tendency measure, where the pre-registered prediction was negative. A second wave of 9,720 responses reproduces the pattern at half that magnitude, which we measure to be regression to the mean rather than a failure to replicate: the slope of wave 2 on wave 1 is +0.46, so a little under half of a first-wave effect was the item draw. Reasoning effort reduces the absolute effect in all nine qualifying confirmatory cases, and it does so by compressing the spread of bias magnitudes across families rather than by lowering their mean. Measured observationally instead, with output tokens standing in for deliberation, the sign reverses.

## Keywords

behavioural finance, disposition effect, large language models, reasoning
effort, cognitive bias, matched-pair experiment, pre-registration, regression
to the mean, replication, robo-advice

## JEL codes

Optional on SSRN's current form and they do not affect distribution, but they
are displayed publicly under the keywords and they are how a finance reader
finds this.

- **G41** Behavioral Finance: Role of Psychology, Emotions, Culture, Social Norms
- **G11** Portfolio Choice; Investment Decisions
- **D91** Micro-Based Behavioral Economics
- **C90** Design of Experiments: General
- **C45** Neural Networks and Related Topics

## Which PDF to upload

`paper/main.pdf`, the single-column reading build. It carries your name and the
filled repository URL, which is what SSRN wants.

**Not `paper/main_acl.pdf`.** That one is anonymised for review, so it has no
author on it and its repository URL is still a placeholder.

## What only you can do

1. Create the SSRN account, if there is not one already.
2. Upload, paste the fields above, submit. SSRN moderates before the paper
   goes public, usually within a few business days.
3. Decide whether to post at all. The only argument against is that it fixes
   a public version of a paper that a third wave would change, and the credit
   to fund that wave is spent.
