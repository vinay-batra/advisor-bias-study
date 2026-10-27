"""Hold the paper's integer counts to the same standard as its decimals.

numaudit.py scans decimals only, because a decimal is distinctive enough that
finding it in a script's output means something. An integer count is not:
"three of six" is prose, the script prints "6/6" or a table, and searching
for 3 and 6 near each other in an output file finds coincidences as readily
as sources. So the counts in this paper were verified by hand, and exactly
one of twenty-seven was wrong. That is a good hit rate for an afternoon and a
useless one for a paper that will be edited again.

This file makes the hand verification durable. It extracts every "N of M"
claim from the prose, normalising spelled-out numbers, and holds the set
against intclaims.txt, which records how each one was checked. A claim the
manifest does not cover fails the build, because it is either new or edited
and in both cases a human has to look at it again. A manifest line nothing
claims any more fails too, so the file cannot rot into a list of counts the
paper stopped making.

Where a pair is mechanically findable in a script's output the check says so,
which shortens the next audit without being trusted as the audit.

    python3 paper/intaudit.py        # from the repo root or from paper/
"""

import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
MANIFEST = HERE / "intclaims.txt"

WORDS = {w: i for i, w in enumerate(
    "zero one two three four five six seven eight nine ten eleven twelve "
    "thirteen fourteen fifteen sixteen seventeen eighteen nineteen "
    "twenty".split())}
WORDS.update({"thirty": 30, "forty": 40, "fifty": 50, "sixty": 60,
              "seventy": 70, "eighty": 80, "ninety": 90})

# A LaTeX thousands separator is 9{,}720, so the comma group has to be part
# of the number or "86 of 9{,}720" parses as "86 of 9".
NUM = r"(?:\d+(?:\{,\}\d{3}|,\d{3})*|" + "|".join(WORDS) + r")"
# "five of the remaining six" and "one of the 86" both state a total, so the
# determiner and any adjective in front of it are skipped. Only words, never
# another number, so "one of the nine families" cannot pair across a comma
# into the next clause.
DET = r"(?:(?:the|its|their|those|these|other|remaining|possible|first|last)\s+)*"
# "one cell of nine" says the same thing as "one of nine cells" and has to key
# to the same pair, so the unit is allowed to sit between the two numbers.
UNIT = (r"(?:cells?|families|family|models?|rows?|combinations?|measures?"
        r"|pairs?|cases?|responses?|trials?|items?|levels?)")
CLAIM = re.compile(
    rf"\b({NUM})\s+(?:{UNIT}\s+)?of\s+{DET}({NUM})\b", re.I)
# "Every one of the 86 is Opus" asserts 86 of 86, not 1 of 86, and the same
# goes for "each one of". The quantifier before the number decides.
ALL_OF = re.compile(r"\b(?:every|each)\s+$", re.I)
# A total the sentence refers to rather than states. Resolving "them" means
# reading the clause before it, which is the job the manifest note does, so
# these are listed and not keyed.
ANAPHORIC = re.compile(rf"\b({NUM})\s+of\s+(?:them|those|these)\b", re.I)


def value(tok):
    tok = tok.lower().replace("{,}", "").replace(",", "")
    return int(tok) if tok.isdigit() else WORDS[tok]


def claims():
    """Every (n, m) the prose asserts, with where it says it.

    Also the anaphoric ones, separately, which are reported rather than
    keyed.
    """
    srcs = [HERE / "body.tex"] + sorted(HERE.glob("sec_*.tex"))
    out, loose = {}, []
    for s in srcs:
        for i, line in enumerate(s.read_text().splitlines(), 1):
            line = re.sub(r"%.*", " ", line)
            for m in ANAPHORIC.finditer(line):
                loose.append(f"{s.name}:{i}  {m.group(0)}")
            for m in CLAIM.finditer(line):
                if ALL_OF.search(line[:m.start()]):
                    continue
                n, d = value(m.group(1)), value(m.group(2))
                # A pair that is not a count out of a total, such as a figure
                # written in words that the "of" happens to join.
                if d == 0 or n > d:
                    continue
                out.setdefault((n, d), []).append(f"{s.name}:{i}")
    return out, loose


def sourced():
    """Pairs a script printed in a form a reader would recognise as the pair."""
    pat = re.compile(r"(\d+)\s*(?:/|\s+of\s+|\s+out\s+of\s+)\s*(\d+)")
    found = set()
    files = sorted(ROOT.glob("analysis/*_output.txt")) + \
        sorted(ROOT.glob("analysis/*_output.json")) + \
        sorted(ROOT.glob("data/pilot/*_out.txt"))
    for f in files:
        for m in pat.finditer(f.read_text()):
            found.add((int(m.group(1)), int(m.group(2))))
    return found


def manifest():
    """(n, m) -> note, from intclaims.txt. Blank lines and # are comments."""
    if not MANIFEST.exists():
        raise SystemExit(f"intaudit: {MANIFEST.name} is missing. Every "
                         f"integer count in the paper needs a line in it.")
    out = {}
    for i, line in enumerate(MANIFEST.read_text().splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = re.match(r"(\d+)/(\d+)\s+(\S.*)$", line)
        if not m:
            raise SystemExit(f"{MANIFEST.name}:{i}: expected "
                             f"'n/m  how it was checked', got {line!r}")
        out[(int(m.group(1)), int(m.group(2)))] = m.group(3)
    return out


def main():
    (paper, loose), placed, auto = claims(), manifest(), sourced()

    missing = sorted(set(paper) - set(placed))
    stale = sorted(set(placed) - set(paper))

    print(f"{len(paper)} distinct integer counts in the paper, "
          f"{len(placed)} placed in {MANIFEST.name}, "
          f"{len(set(paper) & auto)} of them also found verbatim in a "
          f"script's output")

    if missing:
        print(f"\n{len(missing)} not placed. Check each against the data, then "
              f"add a line to {MANIFEST.name}:")
        for n, d in missing:
            where = ", ".join(sorted(set(paper[(n, d)]))[:4])
            hint = "  (found verbatim in an output)" if (n, d) in auto else ""
            print(f"  {n}/{d}  {where}{hint}")
    if stale:
        print(f"\n{len(stale)} placed but no longer claimed. Remove from "
              f"{MANIFEST.name}:")
        for n, d in stale:
            print(f"  {n}/{d}  {placed[(n, d)]}")
    if loose:
        print(f"\n{len(loose)} counts out of a total the sentence refers to "
              f"rather than states, which this check cannot key:")
        for l in loose:
            print(f"  {l}")
    return 1 if (missing or stale) else 0


if __name__ == "__main__":
    sys.exit(main())
