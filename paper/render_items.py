"""Render the prompt battery in data/items.jsonl into LaTeX.

Writes two files that paper/main.tex inputs:

  paper/example_pair.tex     one pair in full, for the Method section
  paper/items_appendix.tex   one pair in full per family, plus a table of
                             the manipulated cue in all 108 pairs

The appendix does not print all 216 prompts. At roughly 250 words each that
is sixty pages of near-duplicate text, and the differing clause is the only
part a reader needs in order to judge whether the pair is matched. The full
file is in the repository. What the appendix must show, and does, is every
pair's manipulated cue, so a reader can check that no pair differs in
anything else.

Run from the repository root:  python3 paper/render_items.py
"""

import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ITEMS = os.path.join(ROOT, "data", "items.jsonl")
OUT_EXAMPLE = os.path.join(ROOT, "paper", "example_pair.tex")
OUT_APPENDIX = os.path.join(ROOT, "paper", "items_appendix.tex")

# The pair shown in full for each family. One per family, lowest pair index,
# so the choice is not a selection on anything the model did.
FAMILY_ORDER = [
    # Cue descriptions below were checked against the actual differing
    # sentences in data/items.jsonl, not written from the family name. Four
    # of them were wrong on the first pass: action bias is a licence to do
    # nothing rather than a status quo label, brand salience is a real
    # ticker against an anonymous placeholder rather than consumer against
    # industrial, mental accounting relabels one sleeve as another rather
    # than moving money out of the main account, and anchoring uses an
    # unsourced number the client saw online rather than a prior traded
    # price. They match Table 1 of the paper.
    ("disposition", "Disposition effect",
     "The purchase price, stated so the position is 50% above it in one "
     "arm and 50% below it in the other. Current price, share count and "
     "fundamentals are identical."),
    ("framing", "Framing",
     "One probability stated as its own complement: a 65% chance of "
     "holding or increasing value against a 35% chance of losing value."),
    ("anchoring", "Anchoring",
     "A price target the client saw in a social media post, high in one arm "
     "and low in the other, explicitly not the firm's research."),
    ("home_bias", "Home bias",
     "The country of domicile and listing, with the currency exposure "
     "neutralised in both arms, unhedged and absent in one and hedged in "
     "the other, and tax treatment held identical."),
    ("action_bias", "Action bias",
     "Whether the prompt states that leaving the position alone is an "
     "acceptable recommendation. The other arm carries a filler sentence "
     "about review scheduling in its place, so prompt length is matched."),
    ("mental_accounting", "Mental accounting",
     "Which labelled sleeve the position is said to sit in, discretionary "
     "or long term, with horizon and tax treatment identical."),
    ("advisor_attribution", "Advisor attribution",
     "Who recommended the position three years ago, the client's previous "
     "advisor or the reader."),
    ("price_path", "Price path",
     "The route to the same current price: a fall then a recovery, or a "
     "rise then a fall back."),
    ("brand_salience", "Brand salience",
     "Whether the issuer is named as a real listed company with its ticker "
     "or as an anonymous placeholder, with the same price and fundamentals."),
]


def tex_escape(s):
    out = []
    for ch in s:
        if ch in "&%$#_{}":
            out.append("\\" + ch)
        elif ch == "~":
            out.append("\\textasciitilde{}")
        elif ch == "^":
            out.append("\\textasciicircum{}")
        elif ch == "\\":
            out.append("\\textbackslash{}")
        else:
            out.append(ch)
    return "".join(out)


def sentences(block):
    """Split a paragraph into sentence-ish units for diffing.

    A plain split on '. ' breaks on '$51,000.' and on '4%.' only by luck;
    the regex below keeps a split point only where the period is followed
    by a space and a capital or a digit, which is what the generator's own
    sentence boundaries look like.
    """
    parts = re.split(r"(?<=\.)\s+(?=[A-Z0-9])", block.strip())
    return [p for p in parts if p]


def diff_paragraphs(a, b):
    """Return per-paragraph (text, differs) lists for the two prompts.

    Paragraph counts are equal by construction in every pair; if a future
    generator breaks that, fall back to marking the whole prompt.
    """
    pa, pb = a.split("\n\n"), b.split("\n\n")
    if len(pa) != len(pb):
        return [(a, True)], [(b, True)]
    ra, rb = [], []
    for x, y in zip(pa, pb):
        if x == y:
            ra.append((x, False))
            rb.append((y, False))
            continue
        sa, sb = sentences(x), sentences(y)
        if len(sa) == len(sb):
            ra.append(([(s, s != t) for s, t in zip(sa, sb)], None))
            rb.append(([(t, s != t) for s, t in zip(sa, sb)], None))
        else:
            ra.append((x, True))
            rb.append((y, True))
    return ra, rb


def render_prompt(marked):
    lines = []
    for body, differs in marked:
        if differs is None:
            chunk = []
            for sent, d in body:
                t = tex_escape(sent)
                chunk.append("\\textbf{" + t + "}" if d else t)
            lines.append(" ".join(chunk))
        elif differs:
            lines.append("\\textbf{" + tex_escape(body) + "}")
        else:
            lines.append(tex_escape(body))
    return "\n\n".join(lines)


def load():
    rows = [json.loads(l) for l in open(ITEMS, encoding="utf-8")]
    pairs = {}
    for r in rows:
        pairs.setdefault(r["pair_id"], {})[r["condition"]] = r
    return rows, pairs


def pair_block(pid, pair, label_a, label_b):
    a, b = pair[label_a], pair[label_b]
    ma, mb = diff_paragraphs(a["prompt"], b["prompt"])
    s = []
    s.append("\\begin{quote}\\small")
    s.append("\\textit{%s, arm \\texttt{%s}.} The sentence that differs "
             "between the arms is set in bold; everything else is "
             "character for character identical.\n" %
             (tex_escape(pid), tex_escape(label_a)))
    s.append(render_prompt(ma))
    s.append("\\end{quote}")
    s.append("\\begin{quote}\\small")
    s.append("\\textit{%s, arm \\texttt{%s}.}\n" %
             (tex_escape(pid), tex_escape(label_b)))
    s.append(render_prompt(mb))
    s.append("\\end{quote}")
    return "\n".join(s)


def main():
    rows, pairs = load()
    by_family = {}
    for r in rows:
        by_family.setdefault(r["bias"], set()).add(r["pair_id"])

    # The example pair in the Method section.
    pid = "disposition_000"
    conds = sorted(pairs[pid].keys())
    with open(OUT_EXAMPLE, "w", encoding="utf-8") as f:
        f.write("% Generated by paper/render_items.py. Do not edit by hand.\n")
        f.write(pair_block(pid, pairs[pid], conds[0], conds[1]))
        f.write("\n")

    # The appendix.
    out = ["% Generated by paper/render_items.py. Do not edit by hand.",
           ""]
    out.append("The battery is 108 matched pairs, 216 prompts, 12 pairs in "
               "each of nine families. Every prompt is in "
               "\\texttt{data/items.jsonl} in the repository, with the "
               "generator that produced it and its seed. This appendix "
               "prints one pair in full from each family, and then the "
               "manipulated cue in all 108 pairs, which is what determines "
               "whether a pair is matched.")
    out.append("")
    for fam, title, cue in FAMILY_ORDER:
        ids = sorted(by_family.get(fam, []))
        if not ids:
            continue
        pid = ids[0]
        conds = sorted(pairs[pid].keys())
        out.append("\\subsection{%s}" % tex_escape(title))
        out.append("\\textit{Manipulated cue.} %s \\textit{Normative "
                   "principle.} %s. %d pairs." %
                   (tex_escape(cue),
                    tex_escape(pairs[pid][conds[0]]["normative"]),
                    len(ids)))
        out.append("")
        out.append(pair_block(pid, pairs[pid], conds[0], conds[1]))
        out.append("")

    out.append("\\subsection{The manipulated cue in every pair}")
    out.append("Each row is one pair. The two arms of a pair are the same "
               "throughout a family and are named in that family's "
               "subsection above, so they are not repeated here. The cue "
               "column gives the value the generator varied. A blank cell "
               "means the manipulation is a word or a label rather than a "
               "number, so there is no numeric value to print; those are "
               "visible in the full prompts in the repository.")
    out.append("")
    out.append("\\begin{longtable}{@{}p{3.3cm}l p{8.4cm}@{}}")
    head = ("\\toprule\nFamily & Pair & Cue value \\\\\n\\midrule")
    out.append(head)
    out.append("\\endfirsthead")
    out.append(head)
    out.append("\\endhead")
    for fam, title, _cue in FAMILY_ORDER:
        ids = sorted(by_family.get(fam, []))
        for i, pid in enumerate(ids):
            conds = sorted(pairs[pid].keys())
            meta = pairs[pid][conds[0]].get("meta") or {}
            vals = []
            for k in sorted(meta):
                v = meta[k]
                if isinstance(v, bool):
                    continue
                if isinstance(v, (int, float)):
                    vals.append("%s %s" % (k.replace("_", " "), v))
                elif isinstance(v, str) and len(v) < 40:
                    vals.append("%s %s" % (k.replace("_", " "), v))
            cell = tex_escape("; ".join(vals)) if vals else ""
            # Name the family once per block. Repeating it on twelve rows
            # is the kind of table a reader stops reading.
            famcell = tex_escape(title) if i == 0 else ""
            out.append("%s & \\texttt{%s} & %s \\\\" % (
                famcell,
                tex_escape(pid.rsplit("_", 1)[1]),
                cell))
        out.append("\\midrule")
    out.append("\\bottomrule")
    out.append("\\end{longtable}")
    with open(OUT_APPENDIX, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")

    print("wrote %s and %s" % (OUT_EXAMPLE, OUT_APPENDIX))
    print("%d pairs across %d families" % (len(pairs), len(by_family)))


if __name__ == "__main__":
    main()
