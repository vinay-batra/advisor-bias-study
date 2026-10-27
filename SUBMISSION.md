# Where this paper can actually go

Checked 2026-10-26. Verify every date before acting on it; conference pages
move and I am quoting them, not reading your calendar.

## The short version

Every venue I recommended earlier is closed. The next real deadline is the
ACL Rolling Review cycle that opens in January 2027, about ten weeks out.
That is not a setback. It is the first time this paper has had slack in its
schedule, and there is one thing worth spending the slack on.

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

**ACL Rolling Review, January 2027 cycle.** The ARR dates page lists "ACL
2027, January 2027" with no exact day yet. On the 2026 pattern of five
10-week cycles, expect a submission deadline in the first half of January.
Reviews arrive about five weeks later, and an accepted paper commits to ACL
2027 or any later venue that takes ARR reviews. This is the right target:
the paper is written to ACL format, it fits the limit, and ARR reviews are
reusable even if the first commitment fails.

Two things to set up before then, both free and both now required:

- An **OpenReview account**. From the October 2026 cycle onward every author
  must have one, with an **ORCID** attached. Register the ORCID first at
  orcid.org, then add it to OpenReview.
- An **anonymised archive** for `\repourl`. anonymous.4open.science mirrors a
  Git repository behind a random URL. The submission build will not accept a
  personal code host: `anonaudit.py` fails the build on one.

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
pairs reach 0.00003. It would turn the multiplicity paragraph from a
limitation into a result, and it is the single change that most improves the
paper's chance of acceptance. It costs API money, it reuses the existing
generator and analysis unchanged, and ten weeks is more than enough time.

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
