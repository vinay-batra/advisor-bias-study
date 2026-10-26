"""Synchronous pilot. Small, immediate, and cheap.

Run this before spending anything on the full batch. It sends a handful of
matched pairs to one model and prints both conditions side by side, so a
broken prompt, a refusal, or a schema problem shows up in a minute instead of
after a 9,000 request batch.

Usage:
    python scripts/pilot.py --bias disposition --pairs 3
    python scripts/pilot.py --model claude-haiku-5-5 --effort low
"""

import argparse
import collections
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from run.common import load_items, client
from run.collect import extract


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="claude-opus-5-5")
    ap.add_argument("--effort", default="medium")
    ap.add_argument("--bias", default="disposition")
    ap.add_argument("--pairs", type=int, default=3)
    ap.add_argument("--trials", type=int, default=3)
    args = ap.parse_args()

    items = [it for it in load_items() if it["bias"] == args.bias]
    pair_ids = sorted({it["pair_id"] for it in items})[: args.pairs]
    items = [it for it in items if it["pair_id"] in pair_ids]
    cli = client()

    scores = collections.defaultdict(list)
    for it in items:
        for trial in range(args.trials):
            msg = cli.messages.create(
                model=args.model,
                max_tokens=config.MAX_TOKENS,
                system=config.SYSTEM_PROMPT,
                messages=[{"role": "user", "content": it["prompt"]}],
                output_config={"effort": args.effort, "format": config.RESPONSE_SCHEMA},
            )
            r = extract(msg)
            if r["status"] != "ok":
                print(f"  {it['item_id']} t{trial}: {r['status']}")
                continue
            scores[it["condition"]].append(config.ACTION_SCORE[r["action"]])
            print(f"  {it['item_id']:46s} t{trial}  {r['action']:13s} "
                  f"conf {r['confidence']:3d}  {r['reason'][:70]}")

    print(f"\n{args.bias} on {args.model} at effort={args.effort}")
    print("mean sell tendency (0 = buy more, 3 = sell all):")
    for cond, vals in sorted(scores.items()):
        if vals:
            print(f"  {cond:18s} {sum(vals) / len(vals):.2f}   n={len(vals)}")
    if len(scores) == 2:
        a, b = sorted(scores)
        if scores[a] and scores[b]:
            d = sum(scores[b]) / len(scores[b]) - sum(scores[a]) / len(scores[a])
            print(f"\n  difference ({b} minus {a}): {d:+.2f}")
            print("  a difference near zero means no bias detected on this slice")


if __name__ == "__main__":
    main()
