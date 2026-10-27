"""Report which build branch each cross reference sits in.

A ref to a moved section reads correctly only if the word matches the build
that prints it, so a ref in shared prose has to be build aware while one
inside an \ifsubmission branch can say Appendix outright.
"""
import re, sys, pathlib

# Moved sections: inline in the reading build, appendix in the submission one.
MOVED = set()
for p in pathlib.Path(".").glob("sec_*.tex"):
    for m in re.finditer(r"\\label\{((?:sec|app):[a-z0-9]+)\}", p.read_text()):
        MOVED.add(m.group(1))

def branches(path):
    """Yield (lineno, text, branch) with branch in shared/submission/reading."""
    stack = []
    for i, line in enumerate(path.read_text().splitlines(), 1):
        # Track the switch before reporting, so a one line \ifsubmission..\fi
        # is reported as shared, which is what it is for this purpose.
        opens = line.count(r"\ifsubmission")
        state = "shared" if not stack else ("submission" if stack[-1] else "reading")
        yield i, line, state
        for tok in re.findall(r"\\ifsubmission|\\else|\\fi", line):
            if tok == r"\ifsubmission":
                stack.append(True)
            elif tok == r"\else" and stack:
                stack[-1] = False
            elif tok == r"\fi" and stack:
                stack.pop()

bad = 0
for path in sorted(pathlib.Path(".").glob("*.tex")):
    for i, line, state in branches(path):
        for word, lab in re.findall(r"(Appendix|Section)~\\ref\{([a-z]+:[a-z0-9]+)\}", line):
            if lab not in MOVED:
                continue
            ok = (state == "submission" and word == "Appendix") or \
                 (state == "reading" and word == "Section")
            if not ok:
                bad += 1
                print(f"{path}:{i}: {word}~\\ref{{{lab}}} in {state} prose")
print(f"{bad} hardcoded word(s) that can print with the wrong label type")
sys.exit(1 if bad else 0)
