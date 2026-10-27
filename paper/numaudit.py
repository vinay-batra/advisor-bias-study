"""Trace every number the paper states about its own data back to a script.

A figure in the prose that no released script produces is either a typo or a
claim nothing supports, and it is the defect a reviewer is most likely to
catch and least likely to forgive. This file does not check that a number is
right, only that something in analysis/ printed it, which is the property the
reproducibility appendix claims for every number in the paper.

Matching allows for rounding, because prose quotes +13.4 for a figure the
script prints as 13.376, and the appendix quotes 12.54 for 12.535. A paper
number counts as sourced if it equals an output value rounded to its own
number of decimals.

What it cannot know is provenance: a figure from the literature, a dimension
in a table preamble and a percentage inside a prompt are all numbers no
script produces. Citations, labels and lengths are stripped, and whatever
survives is listed for a human to place. The list is meant to be read, not
to reach zero.

    python3 paper/numaudit.py        # from the repo root or from paper/
"""

import collections
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
# Odean's PGR and PLR, which the paper quotes from his Table I. Published
# figures, not measurements of ours, and there is nothing to reproduce them
# from.
FROM_LITERATURE = {"0.148", "0.098", "0.050", "11.4", "0.5", "0.6", "0.9"}


def produced():
    """Every number any analysis script printed, as literal strings."""
    out = set()
    # The pilot is reported in the paper and its run logs ship beside the
    # pilot data, so they count as released output the same way.
    files = sorted(ROOT.glob("analysis/*_output.txt")) + \
        sorted(ROOT.glob("analysis/*_output.json")) + \
        sorted(ROOT.glob("data/pilot/*_out.txt"))
    if not files:
        raise SystemExit("no analysis/*_output.* files: run the analyses first")
    for f in files:
        text = f.read_text()
        for m in re.finditer(r"\d+(?:\.\d+)?", text):
            raw = m.group(0)
            out.add(raw)
            if "." in raw:
                # The paper rounds. 12.535 licenses 12.54 and 12.5, and a
                # value that rounds to an integer licenses that integer.
                for places in range(0, len(raw.split(".")[1])):
                    out.add(f"{round(float(raw), places):.{places}f}"
                            if places else str(int(round(float(raw)))))
    return out


def strip_latex(line):
    """Remove the numbers that are not claims about the data."""
    line = re.sub(r"%.*", " ", line)
    line = re.sub(r"\\cite[a-z]*\{[^}]*\}", " ", line)
    line = re.sub(r"\\(?:label|ref|eqref|input|includegraphics)\{[^}]*\}", " ",
                  line)
    # Column widths and other lengths: p{1.9cm}, \setlength{..}{4pt}, 6.3in.
    line = re.sub(r"[pmb]\{[\d.]+(?:cm|mm|in|pt|em|ex)\}", " ", line)
    line = re.sub(r"\\setlength\{[^}]*\}\{[^}]*\}", " ", line)
    line = re.sub(r"[\d.]+\s*(?:cm|mm|in|pt|em|ex)\b", " ", line)
    line = re.sub(r"\\[a-zA-Z]+", " ", line)
    return line


def main():
    srcs = [p for pat in ("body.tex", "sec_*.tex", "tab_*.tex", "fig_*.tex")
            for p in sorted(HERE.glob(pat))]
    if not srcs:
        raise SystemExit(f"no paper sources under {HERE}")
    known = produced()

    found = collections.defaultdict(list)
    for s in srcs:
        for i, line in enumerate(s.read_text().splitlines(), 1):
            for m in re.finditer(r"(?<![\d.])(\d+(?:,\d{3})*\.\d+)",
                                 strip_latex(line)):
                found[m.group(1).replace(",", "")].append(f"{s.name}:{i}")

    unsourced = {k: v for k, v in found.items()
                 if k not in known and k not in FROM_LITERATURE}
    print(f"{len(found)} distinct decimal figures in the paper, "
          f"{len(known):,} distinct values across the analysis outputs")
    if not unsourced:
        print("every one is produced by a script, quoted from the literature, "
              "or a rounding of a produced value")
        return 0
    print(f"\n{len(unsourced)} not accounted for, to place by hand:")
    for k in sorted(unsourced, key=float):
        print(f"  {k:>12}  {', '.join(sorted(set(unsourced[k]))[:4])}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
