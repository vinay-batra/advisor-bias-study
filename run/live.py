"""Fill missing responses with live (non batch) requests, in parallel.

The fallback for a batch that will not clear its queue in time. Live requests
cost double, since the 50% batch discount does not apply, so this is only
worth running when waiting has become more expensive than the money.

Idempotent by design. A request is issued only for a `custom_id` that has no
successful row on disk, so this can be run after a partial batch collection,
re-run after an interruption, and run alongside a cancelled batch without
duplicating work. Rows are written in the same shape as run/collect.py, using
the same extract() function, so the two paths are indistinguishable
downstream.

Usage:
    python run/live.py --model claude-opus-5-5              # every effort
    python run/live.py --model claude-opus-5-5 --effort low
    python run/live.py --model claude-opus-5-5 --limit 4 --out /tmp/probe.jsonl
    python run/live.py --model claude-opus-5-5 --dry-run
"""

import argparse
import json
import os
import random
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from run.collect import extract
from run.common import client, custom_id, load_items, read_index

MAX_ATTEMPTS = 5


def existing_ok(path):
    """custom_ids that already have a usable row, so need no request."""
    ok = set()
    if not os.path.exists(path):
        return ok
    with open(path) as f:
        for line in f:
            r = json.loads(line)
            if r.get("status") == "ok":
                ok.add(r["custom_id"])
    return ok


def one(cli, model, effort, prompt):
    """A single request, retrying only what is worth retrying."""
    import anthropic
    for attempt in range(MAX_ATTEMPTS):
        try:
            return cli.messages.create(
                model=model,
                max_tokens=config.MAX_TOKENS,
                system=config.SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
                output_config={"effort": effort,
                               "format": config.RESPONSE_SCHEMA},
            )
        except (anthropic.RateLimitError, anthropic.APIStatusError) as e:
            # 429 and 529 are worth waiting out. A 400 is a bad request and
            # will fail identically however many times it is sent.
            status = getattr(e, "status_code", None)
            if status not in (429, 500, 502, 503, 529) \
                    or attempt == MAX_ATTEMPTS - 1:
                raise
            time.sleep(min(60, 2 ** attempt) * (1 + random.random()))
    raise RuntimeError("unreachable")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", action="append", default=None)
    ap.add_argument("--effort", action="append", default=None)
    ap.add_argument("--trials", type=int, default=config.N_TRIALS)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--limit", type=int, default=None,
                    help="stop after this many requests, for a cheap test")
    ap.add_argument("--out", default=config.RESPONSES_PATH)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    models = args.model or config.MODELS
    efforts = args.effort or config.EFFORTS
    index = read_index()
    item_ids, all_models = index["items"], index["models"]
    items = {it["item_id"]: it for it in load_items()}

    have = existing_ok(args.out)
    print(f"{len(have):,} usable rows already on disk at {args.out}")

    # The index fixes the model order, and custom_id encodes the model by its
    # position in it, so the position must come from the index rather than
    # from the order the arguments happened to arrive in.
    todo = []
    for model in models:
        midx = all_models.index(model)
        for effort in efforts:
            for item_idx, iid in enumerate(item_ids):
                for trial in range(args.trials):
                    cid = custom_id(item_idx, midx, effort, trial)
                    if cid in have:
                        continue
                    todo.append((cid, model, effort, item_idx, iid, trial))

    if args.limit:
        todo = todo[:args.limit]
    print(f"{len(todo):,} requests to issue "
          f"across {len(models)} model(s) x {len(efforts)} effort level(s)")
    if args.dry_run or not todo:
        for t in todo[:5]:
            print("  would send", t[0], t[1], t[2])
        return

    cli = client()
    lock = threading.Lock()
    out = open(args.out, "a")
    counts = {"ok": 0, "failed": 0}
    t0 = time.time()

    def work(job):
        cid, model, effort, item_idx, iid, trial = job
        item = items[iid]
        row = dict(custom_id=cid, item_id=iid, bias=item["bias"],
                   pair_id=item["pair_id"], condition=item["condition"],
                   status_class=item["status"], model=model, effort=effort,
                   trial=trial)
        try:
            msg = one(cli, model, effort, item["prompt"])
            row.update(extract(msg))
            row["input_tokens"] = msg.usage.input_tokens
            row["output_tokens"] = msg.usage.output_tokens
        except Exception as e:
            row["status"] = "live_error"
            row["reason"] = f"{type(e).__name__}: {e}"[:500]
        return row

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(work, j) for j in todo]
        for i, fut in enumerate(as_completed(futures), 1):
            row = fut.result()
            with lock:
                out.write(json.dumps(row) + "\n")
                out.flush()
                counts["ok" if row.get("status") == "ok" else "failed"] += 1
            if i % 100 == 0 or i == len(futures):
                rate = i / max(time.time() - t0, 1e-9)
                left = (len(futures) - i) / max(rate, 1e-9) / 60
                print(f"  {i:,}/{len(futures):,}  "
                      f"{rate:.1f}/s  ~{left:.1f} min left  "
                      f"ok={counts['ok']:,} failed={counts['failed']:,}",
                      flush=True)
    out.close()
    print(f"\ndone in {(time.time()-t0)/60:.1f} min: "
          f"{counts['ok']:,} ok, {counts['failed']:,} failed -> {args.out}")


if __name__ == "__main__":
    main()
