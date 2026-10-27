"""Poll the submitted batches and write one row per response.

Results come back in arbitrary order, so every row is keyed by custom_id and
rejoined through data/index.json. Never by position.

Usage:
    python run/collect.py            # poll until every batch has ended
    python run/collect.py --wave 2   # the extension's batches
    python run/collect.py --once     # one pass, then exit
"""

import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from run.common import (load_items, parse_custom_id, read_index, client,
                        wave as wave_paths)


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
    # The schema cannot express the 0 to 100 bound (the API rejects numeric
    # bounds on an integer), so it is checked here. An out of range value is
    # kept and flagged rather than clamped: the action is the dependent
    # variable and is still usable, and a model ignoring a stated bound is a
    # reportable fact about instruction following, not noise to be tidied.
    conf = payload.get("confidence")
    conf_ok = isinstance(conf, int) and 0 <= conf <= 100
    pct = payload.get("pct_of_position_to_sell")
    pct_ok = isinstance(pct, (int, float)) and 0 <= pct <= 100
    # The two measures can disagree: HOLD with a non-zero percentage, or a
    # sell action with zero. Flagged, never reconciled, because which measure
    # the model honours when they conflict is itself a result.
    action = payload["action"]
    inconsistent = pct_ok and (
        (action in ("BUY_MORE", "HOLD") and pct > 0)
        or (action in ("SELL_PARTIAL", "SELL_ALL") and pct == 0)
    )
    return dict(
        status="ok",
        action=action,
        pct_of_position_to_sell=pct,
        pct_out_of_range=(not pct_ok),
        action_pct_inconsistent=inconsistent,
        confidence=conf,
        confidence_out_of_range=(not conf_ok),
        reason=payload.get("one_sentence_reason", "")[:500],
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--interval", type=int, default=60)
    ap.add_argument("--wave", type=int, default=1)
    args = ap.parse_args()

    w = wave_paths(args.wave)
    with open(w["batches"]) as f:
        state = json.load(f)
    index = read_index(w["index"])
    items = {it["item_id"]: it for it in load_items(w["items"])}
    item_ids = index["items"]
    offset = index.get("id_offset", 0)
    models = index["models"]
    cli = client()

    done = set()
    if os.path.exists(w["responses"]):
        with open(w["responses"]) as f:
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
            with open(w["responses"], "a") as out:
                for res in cli.messages.batches.results(info["batch_id"]):
                    if res.custom_id in done:
                        continue
                    item_idx, model_idx, effort, trial = parse_custom_id(res.custom_id)
                    item = items[item_ids[item_idx - offset]]
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
                        wave=args.wave,
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
            with open(w["batches"], "w") as f:
                json.dump(state, f, indent=2)
            print(f"collected {cell}: {n:,} rows")

        if not pending:
            print(f"\nall batches collected -> {w['responses']}")
            return
        print(" | ".join(pending))
        if args.once:
            return
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
