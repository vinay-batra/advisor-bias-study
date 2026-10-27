"""Measure the submission body against the venue page limit.

ACL counts the body only: references, appendices and Limitations are
excluded, which is why body.tex ends with a \\label{xbodyend} and a
\\message that reports the position of that point. The body length is

    (page - 1) + (column - 1) * 0.5 + pagetotal / pagegoal * 0.5

in a two column document. The column indicator is not optional: without it
a reading is ambiguous by half a page.
"""
import re
import sys

LIMIT = 8.0


def body_pages(log_path):
    log = open(log_path, errors="ignore").read()
    m = re.search(r"BODYFILL page=(\d+) col=(\d) used=([\d.]+)pt of=([\d.]+)pt",
                  log)
    if not m:
        raise SystemExit(f"{log_path}: no BODYFILL marker, did the build run?")
    page, col, used, goal = (int(m.group(1)), int(m.group(2)),
                             float(m.group(3)), float(m.group(4)))
    return (page - 1) + (col - 1) * 0.5 + (used / goal) * 0.5 if goal else 0.0


if __name__ == "__main__":
    log = sys.argv[1] if len(sys.argv) > 1 else "main_acl.log"
    limit = float(sys.argv[2]) if len(sys.argv) > 2 else LIMIT
    n = body_pages(log)
    over = n > limit
    print(f"body: {n:.2f} pages (limit {limit:.0f}, "
          f"{'OVER by %.2f' % (n - limit) if over else 'room for %.2f' % (limit - n)})")
    sys.exit(1 if over else 0)
