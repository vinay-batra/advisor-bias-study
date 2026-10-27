# Where this paper can actually go

Checked 2026-10-26. Verify every date before acting on it; conference pages
move and I am quoting them, not reading your calendar.

## The short version

Every venue I recommended earlier is closed. The next real deadline is the
ACL Rolling Review cycle whose submission deadline is 4 January 2027, ten
weeks out.
That is not a setback. It is the first time this paper has had slack in its
schedule, and there is one thing worth spending the slack on.

**Updated 2026-10-27.** Part of that one thing has been done. A replication
wave of 9,720 responses ran on 27 October and is reported in the paper's
appendix. Haiku and Sonnet came back complete; the three Opus batches failed
on an exhausted API credit balance and are excluded whole under amendment 6.
The study's credit is spent, so any further collection needs funding before
it can start. What the wave bought, and what it did not, is in "What to
spend the ten weeks on" below, and it changes the case for a third wave.

## What is closed, and when it closed

| Venue | Deadline | Status |
|---|---|---|
| FinNLP 2026 (11th, at EMNLP) | 11 Aug 2026 | Closed. The workshop runs 28 Oct 2026 in Budapest, which is tomorrow. |
| ARR October 2026 cycle | 12 Oct 2026 | Closed. Feeds NAACL 2027 and COLING 2027; reviews out 17 Dec. |
| ARR August 2026 cycle | 3 Aug 2026 | Closed. Fed EACL 2027. |
| ICAIF 2026 (7th, ACM) | 9 Aug 2026 | Closed. Conference 14 to 17 Nov 2026 in Milan. |

I told you to aim at FinNLP and I was wrong about the timing. The 8-page fit
was the right work regardless, because every ACL-family venue uses the same
limit, but the slot I pointed at had been gone for ten weeks.

## What is open

**ACL Rolling Review, January 2027 cycle.** Confirmed 2026-10-27 from the
ACL 2027 first call for papers: **ARR submission deadline 4 January 2027**,
11:59 PM UTC-12:00 (anywhere on Earth), handled through ARR. The ACL
commitment deadline is still listed as TBD. Reviews arrive about five weeks
after submission, and an accepted paper commits to ACL 2027 or any later
venue that takes ARR reviews. This is the right target:
the paper is written to ACL format, it fits the limit, and ARR reviews are
reusable even if the first commitment fails.

Two things to set up before then, both free and both now required:

- An **OpenReview account**. From the October 2026 cycle onward every author
  must have one, with an **ORCID** attached. Register the ORCID first at
  orcid.org, then add it to OpenReview.
- An **anonymised archive** for `\repourl`. anonymous.4open.science mirrors a
  Git repository behind a random URL. The submission build will not accept a
  personal code host: `anonaudit.py` fails the build on one.

### The two policies disagree about preprints, and the date decides it

Checked 2026-10-27. ARR's own anonymity page says there is no anonymity
period and that "authors are free to post and discuss non-anonymous
preprints at any time", in force since the February 2024 cycle. The ACL 2027
first call says the opposite: "no deanonymized preprint may be posted in the
month prior to submission". Nothing on either page explains the conflict.

Resolve it by not standing in the disputed window. With submission on 4
January 2027, the stricter reading blacks out roughly 4 December 2026 to 4
January 2027. A preprint posted before December is clear under either policy
and the conflict never applies to you. A preprint posted in December might
not be. If you want to post in that window, write to
editors@aclrollingreview.org first.

**SSRN, as an immediate preprint.** SSRN takes submissions from anyone with a
free account and no endorsement, which matters because arXiv does not. This
paper already cites two SSRN working papers, so the venue is one its own
bibliography treats as citable. Posting there gives you a date-stamped,
citable version tomorrow if you want one.

**arXiv needs an endorsement you do not have.** A first submission to any
category requires an endorsement from an established author in that
category, and automatic endorsement generally goes to authors at recognised
institutions. A gmail address and no affiliation means asking a q-fin or
cs.CL author to endorse you through the link arXiv generates. Worth starting
early if you want arXiv specifically, because it depends on a stranger
replying. Not worth blocking on.

**Journal of Emerging Investigators is no longer a fit.** As of 10 March 2026
JEI narrowed to hypothesis-driven life sciences and experimental physical
sciences and stopped accepting work that is purely computer science. It also
requires a teacher or mentor to submit on your behalf, and a Word manuscript.
Drop it from the plan.

## What to spend the ten weeks on

One thing, and the paper names the problem itself.

Every cell rests on 12 matched pairs. A sign-flipping permutation test draws
its resolution from the pairs that moved, so with $n_z$ moving pairs the
smallest attainable two-sided $p$ is about $2/2^{n_z}$. At twelve pairs a
cell where five pairs moved has a floor of 0.0625, above 0.05, and no effect
size can push it under. The paper says this plainly, reports every $p$ beside
its floor, and rests its calls on the intervals instead. That is the honest
move and it is still a weakness a reviewer will press, because the answer to
"your test cannot express significance in most cells" is more items, not a
better paragraph.

Raising items per family above 12 lowers the floor geometrically: 16 moving
pairs reach 0.00003.

**That reasoning has now been tested, and it was half right.** A second wave
of 9,720 responses doubled the pairs to 24 per cell on Haiku and Sonnet. The
floor fell exactly as predicted: cells where a $p$ below 0.05 is attainable
at all rose from 33 to 42 of 81 on the categorical measure and from 64 to 72
on the continuous one. But Holm survival barely moved, from one cell to two
on the first measure and from three to three on the second, because
reachability was never the binding constraint. Holm over 81 cells needs the
smallest $p$ under about 0.0006, and most of these effects are not large
enough to get there at any number of pairs this study can afford.

So if you fund a third wave, fund it knowing what it buys. More items per
family will keep widening the set of cells where significance is expressible,
which is worth having and is what the limitations section now reports. It
will not convert the multiplicity paragraph into a result. The honest reading
is that the per-cell design is interval-reported by necessity, not by choice,
and the paper is stronger for saying so than it would be for a third wave
that says it again with a larger $n$.

The one place a third wave would change a finding rather than a $p$ is Opus.
Its disposition interval spans zero because its sign flips with effort, and
the replication wave could not speak to it because the credit ran out before
its batches finished. Twelve more Opus pairs per family is a far smaller buy
than a full third wave and it addresses the paper's largest remaining defect.

That is your call and it is the one decision in this file I cannot make for
you. The battery, the grading and the analysis all run unchanged on more
items, so the work is a collection run and a rebuild, not a rewrite.

## Placeholders still in the paper

Both are deliberate and both are visible in the PDF, so neither can ship by
accident.

- `\repourl` in `paper/shared.tex`, two values. The submission build prints
  `[anonymised archive URL to be added]` and the reading build `[repository
  URL to be added]`. There is no git remote yet; creating one is a publishing
  decision and I have not made it for you.
- Nothing else. `make check` passes six gates: body under 8 pages,
  cross-reference wording correct in both builds, every decimal traceable to
  a script, every integer count out of a total placed in
  `paper/intclaims.txt` with how it was verified, no overfull lines or
  dangling references, and the submission PDF free of your name, your email
  and any code host.

### If you do make the repo public, it is already safe to

Checked 2026-10-27, because git history cannot be unpublished:

- `.env` has never been tracked. Only `.env.example` is, and it holds
  `sk-ant-...` as a placeholder.
- No key-shaped string appears in any commit, on any branch, anywhere in
  history. Searched every reachable commit for `sk-ant-` followed by twenty
  or more key characters: nothing.
- 109 tracked files, 11 MB. The bulk is `data/responses.jsonl` at 7.6 MB,
  which is the release, not an accident.

That makes `git remote add` plus a push the whole job, with nothing to
rewrite first. It is still your call whether to do it.

## Sources

- FinNLP 2026: https://sigfintech.github.io/finnlp2026/
- ARR dates: https://aclrollingreview.org/dates
- ARR sustainable reviewing policy (author caps, ORCID): https://aclrollingreview.org/sustainable-reviewing-2026
- arXiv endorsement: https://info.arxiv.org/help/endorsement.html
- JEI guidelines: https://emerginginvestigators.org/submissions/guidelines
