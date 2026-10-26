"""Poll the submitted batches and write one row per response.

Results come back in arbitrary order, so every row is keyed by custom_id and
rejoined through data/index.json. Never by position.

Usage:
    python run/collect.py            # poll until every batch has ended
    python run/collect.py --once     # one pass, then exit
"""

import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from run.common import load_items, parse_custom_id, read_index, client


def extract(msg):
    """Pull the structured recommendation out of a completed message."""
    if getattr(msg, "stop_reason", None) == "refusal":
        cat = getattr(getattr(msg, "stop_details", None), "category", None)
        return dict(status="refusal", refusal_category=cat)
    if getattr(msg, "stop_reason", None) == "max_tokens":
        return dict(status="truncated")
    text = "".join(b.text for b in msg.content if b.type == "text")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return dict(status="unparseable", raw=text[:400])
    if payload.get("action") not in config.ACTION_SCORE:
        return dict(status="bad_action", raw=text[:400])
    return dict(
        status="ok",
        action=payload["action"],
        confidence=payload.get("confidence"),
        reason=payload.get("one_sentence_reason", "")[:500],
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--interval", type=int, default=60)
    args = ap.parse_args()

    with open(config.BATCH_STATE_PATH) as f:
        state = json.load(f)
    index = read_index()
    items = {it["item_id"]: it for it in load_items()}
    item_ids = index["items"]
    models = index["models"]
    cli = client()

    done = set()
    if os.path.exists(config.RESPONSES_PATH):
        with open(config.RESPONSES_PATH) as f:
            for line in f:
                done.add(json.loads(line)["custom_id"])
        print(f"{len(done):,} responses already on disk")

    while True:
        pending = []
        for cell, info in state.items():
            if info.get("collected"):
                continue
            batch = cli.messages.batches.retrieve(info["batch_id"])
            if batch.processing_status != "ended":
                c = batch.request_counts
                pending.append(f"{cell}: {batch.processing_status} "
                               f"({c.succeeded} ok, {c.processing} left)")
                continue

            n = 0
            with open(config.RESPONSES_PATH, "a") as out:
                for res in cli.messages.batches.results(info["batch_id"]):
                    if res.custom_id in done:
                        continue
                    item_idx, model_idx, effort, trial = parse_custom_id(res.custom_id)
                    item = items[item_ids[item_idx]]
                    row = dict(
                        custom_id=res.custom_id,
                        item_id=item["item_id"],
                        bias=item["bias"],
                        pair_id=item["pair_id"],
                        condition=item["condition"],
                        status_class=item["status"],
                        model=models[model_idx],
                        effort=effort,
                        trial=trial,
                    )
                    if res.result.type == "succeeded":
                        row.update(extract(res.result.message))
                        u = res.result.message.usage
                        row["input_tokens"] = u.input_tokens
                        row["output_tokens"] = u.output_tokens
                    else:
                        row["status"] = res.result.type
                    out.write(json.dumps(row) + "\n")
                    done.add(res.custom_id)
                    n += 1
            info["collected"] = True
            with open(config.BATCH_STATE_PATH, "w") as f:
                json.dump(state, f, indent=2)
            print(f"collected {cell}: {n:,} rows")

        if not pending:
            print(f"\nall batches collected -> {config.RESPONSES_PATH}")
            return
        print(" | ".join(pending))
        if args.once:
            return
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
