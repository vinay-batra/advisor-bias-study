"""Submit the battery to the Batch API, one batch per model x effort cell.

Batch runs at 50% of standard price and is asynchronous. One batch per cell so
cells can be added or re-run independently, and so a failure never costs the
whole study.

Deliberate choice: server-side refusal fallbacks are NOT enabled. A fallback
would silently answer on a different model, and model identity is an
independent variable here. Refusals are recorded as refusals instead.

Usage:
    python run/submit.py                      # every cell in config
    python run/submit.py --wave 2             # the extension's cells
    python run/submit.py --model claude-haiku-5-5 --effort low
    python run/submit.py --dry-run
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from run.common import (load_items, custom_id, write_index, client,
                        wave as wave_paths)


def build_requests(items, model_idx, model, effort, n_trials, id_offset=0):
    from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
    from anthropic.types.messages.batch_create_params import Request

    reqs = []
    for item_idx, it in enumerate(items):
        for trial in range(n_trials):
            reqs.append(Request(
                custom_id=custom_id(item_idx + id_offset, model_idx,
                                        effort, trial),
                params=MessageCreateParamsNonStreaming(
                    model=model,
                    max_tokens=config.MAX_TOKENS,
                    system=config.SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": it["prompt"]}],
                    output_config={
                        "effort": effort,
                        "format": config.RESPONSE_SCHEMA,
                    },
                ),
            ))
    return reqs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", action="append", default=None)
    ap.add_argument("--effort", action="append", default=None)
    ap.add_argument("--trials", type=int, default=config.N_TRIALS)
    ap.add_argument("--wave", type=int, default=1)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    models = args.model or config.MODELS
    efforts = args.effort or config.EFFORTS

    w = wave_paths(args.wave)
    items = load_items(w["items"])
    write_index(items, w["index"], w["id_offset"])

    state = {}
    if os.path.exists(w["batches"]):
        with open(w["batches"]) as f:
            state = json.load(f)

    cli = None if args.dry_run else client()

    for model in models:
        model_idx = config.MODELS.index(model)
        for effort in efforts:
            cell = f"{model}|{effort}"
            if cell in state:
                print(f"skip {cell} (already submitted as {state[cell]['batch_id']})")
                continue
            reqs = build_requests(items, model_idx, model, effort,
                                  args.trials, w["id_offset"])
            if args.dry_run:
                print(f"would submit {len(reqs):,} requests for {cell}")
                continue
            batch = cli.messages.batches.create(requests=reqs)
            state[cell] = {
                "batch_id": batch.id,
                "model": model,
                "effort": effort,
                "trials": args.trials,
                "n_requests": len(reqs),
                "wave": args.wave,
            }
            with open(w["batches"], "w") as f:
                json.dump(state, f, indent=2)
            print(f"submitted {cell}: {batch.id} ({len(reqs):,} requests)")

    if not args.dry_run:
        print(f"\nstate saved to {w['batches']}. "
              f"run: python run/collect.py --wave {args.wave}")


if __name__ == "__main__":
    main()
