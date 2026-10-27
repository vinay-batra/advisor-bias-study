"""Fail the build if the submission PDF identifies its author.

The ACL template's [review] option suppresses the author block, which is
necessary and not sufficient. Three things can carry a name past it: the PDF
Info dictionary, which tectonic fills from the document and no \\author
switch touches; an acknowledgement or funding line written before the author
remembered the submission is blind; and the repository URL, which is the
likely one here, because the obvious value for it is a personal account on a
code host and the obvious moment to fill it in is the hour before the
deadline.

The identifying strings are read out of shared.tex's \\author block rather
than written here, so this file holds no personal data and stays correct if
the author block changes.

Checks the submission build only. main.pdf is a reading copy and is supposed
to carry a name.

    python3 paper/anonaudit.py        # from the repo root or from paper/
"""

import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
PDF = HERE / "main_acl.pdf"
SHARED = HERE / "shared.tex"

# A repository on a personal account de-anonymises as surely as a name, and
# the paper cites no code host, so any of these in the submission is a defect.
HOSTS = ("github.com", "gitlab.com", "bitbucket.org", "huggingface.co",
         "drive.google.com", "dropbox.com")


def identifying_tokens():
    """Name words and email parts from the \\author block, lowercased."""
    text = SHARED.read_text()
    m = re.search(r"\\author\{(.*?)\n(?:\\date|\\title|$)", text, re.S)
    if not m:
        raise SystemExit("anonaudit: no \\author block in shared.tex")
    block = m.group(1)
    toks = set()
    for email in re.findall(r"[\w.+-]+@[\w.-]+", block):
        local, _, domain = email.partition("@")
        toks.add(email.lower())
        # The local part is the identifying half. A bare "gmail.com" would
        # match nothing useful and a bare "com" would match everything.
        if len(local) >= 4:
            toks.add(local.lower())
    stripped = re.sub(r"[\w.+-]+@[\w.-]+", " ", block)
    stripped = re.sub(r"\\[a-zA-Z]+|[{}\\]", " ", stripped)
    for word in re.findall(r"[A-Za-z][A-Za-z'-]{3,}", stripped):
        toks.add(word.lower())
    if not toks:
        raise SystemExit("anonaudit: parsed no identifying tokens; check the "
                         "\\author block in shared.tex")
    return toks


def pdf_text_and_info():
    try:
        from pypdf import PdfReader
    except ImportError:
        raise SystemExit("anonaudit: pypdf not available; run with the repo "
                         "venv, .venv/bin/python paper/anonaudit.py")
    reader = PdfReader(str(PDF))
    pages = []
    for page in reader.pages:
        # ACL line numbers attach to the end of an extracted line with no
        # separating space, so a number run there is layout, not content.
        lines = [re.sub(r"(?<=\S)0*\d{1,4}\s*$", "", ln)
                 for ln in page.extract_text().splitlines()]
        pages.append("\n".join(lines))
    info = {str(k): str(v) for k, v in (reader.metadata or {}).items()}
    return pages, info


def main():
    if not PDF.exists():
        raise SystemExit(f"anonaudit: {PDF.name} not built")
    toks = identifying_tokens()
    pages, info = pdf_text_and_info()

    bad = []
    for i, text in enumerate(pages, 1):
        low = text.lower()
        for t in sorted(toks):
            if t in low:
                bad.append(f"page {i}: author token {t!r} in the text layer")
        for h in HOSTS:
            if h in low:
                bad.append(f"page {i}: code host {h!r} in the text layer; an "
                           f"anonymous submission cannot carry a personal "
                           f"repository URL")
    for key, val in info.items():
        low = val.lower()
        for t in sorted(toks):
            if t in low:
                bad.append(f"metadata {key} = {val!r} carries {t!r}")

    if bad:
        print(f"anonaudit: {len(bad)} anonymity problem(s) in {PDF.name}")
        for b in bad:
            print(f"  {b}")
        return 1
    print(f"{PDF.name}: anonymous, {len(pages)} pages checked against "
          f"{len(toks)} author tokens and {len(HOSTS)} code hosts")
    return 0


if __name__ == "__main__":
    sys.exit(main())
