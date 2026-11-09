"""Recollect wave 2's three Opus cells, which died on an exhausted balance.

Amendment 6 excluded those cells under a completeness rule: a wave 2 cell
enters a reading only if every one of its matched pairs is present with both
conditions. The rule keys on completeness and on nothing else, so it does not
need rewriting for the cells to come back. It needs the cells to be complete.

Three things stand in the way of simply resubmitting, and this file handles
all three rather than leaving them to be discovered mid-run.

First, collect.py skips any custom_id already on disk, which is how it stays
safe to re-poll a batch. Every one of the 3,240 Opus wave 2 custom_ids is
already there, 1,909 as ok and 1,331 as errored, so a resubmission collected
against the file as it stands would record nothing at all and the money would
buy a no-op. The old rows therefore have to leave responses_wave2.jsonl
before the new ones can land.

Second, Amendment 6 promised those rows would not be deleted, because an
exclusion nobody can inspect is not an exclusion. They are moved, not
removed: every row goes to responses_wave2_opus_superseded.jsonl intact, and
Amendment 7 records the move. The file is not read by any analysis, which is
the point, but it is in the repository and a reader can diff it against what
replaces it.

Third, the three dead batch ids are provenance. They are what shows the
failure was an exhausted balance rather than a choice, so they move to a
superseded list inside batches_wave2.json instead of being overwritten by the
new submission.

What this does not do is decide anything. The completeness rule was fixed
before any Opus wave 2 effect was computed and is unchanged here; recollected
cells enter a reading if they are complete and stay out if they are not, on
the same terms as every other cell.

    python scripts/resubmit_opus_wave2.py           # plan and price, no spend
    python scripts/resubmit_opus_wave2.py --go      # submit the three batches
"""

import argparse
import json
import os
import shutil
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from run.common import load_items, write_index, client, wave as wave_paths
from run.submit import build_requests

MODEL = "claude-opus-5-5"
WAVE = 2
SUPERSEDED = "data/responses_wave2_opus_superseded.jsonl"
# Opus 5.5 standard pricing, per million. Batch is half.
PRICE_IN, PRICE_OUT = 4.00, 20.00
AMENDMENT = "Amendment 7"


def require_amendment():
    """Refuse to spend until the move is on the record.

    The repository's standing rule is that a claim with no artifact behind it
    does not ship. Moving analysed data out of the analysed file is exactly
    such a claim, so the preregistration has to carry it first.
    """
    text = open("PREREGISTRATION.md").read()
    if AMENDMENT not in text:
        raise SystemExit(
            f"{AMENDMENT} is not in PREREGISTRATION.md.\n"
            "It has to record the move of the superseded Opus rows before "
            "this script will submit anything. Write it, then re-run.")


def split_rows():
    """Partition wave 2's responses into Opus and everything else."""
    w = wave_paths(WAVE)
    keep, move = [], []
    with open(w["responses"]) as f:
        for line in f:
            (move if json.loads(line).get("model") == MODEL else keep).append(line)
    return w, keep, move


def price(move):
    """Price the resubmission off the tokens the survivors actually used."""
    ok = [json.loads(l) for l in move]
    ok = [r for r in ok if r.get("status") == "ok" and r.get("input_tokens")]
    if not ok:
        return None
    mi = statistics.mean(r["input_tokens"] for r in ok)
    mo = statistics.mean(r["output_tokens"] for r in ok)
    n = len(config.EFFORTS) * len(load_items(wave_paths(WAVE)["items"])) \
        * config.N_TRIALS
    return n, mi, mo, (n * mi / 1e6 * PRICE_IN / 2 + n * mo / 1e6 * PRICE_OUT / 2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--go", action="store_true",
                    help="actually move the rows and submit the batches")
    args = ap.parse_args()

    w, keep, move = split_rows()
    quoted = price(move)

    print(f"wave {WAVE} responses on disk: {len(keep) + len(move):,}")
    print(f"  {MODEL}: {len(move):,} rows, to be superseded")
    print(f"  other models: {len(keep):,} rows, untouched")
    if quoted:
        n, mi, mo, cost = quoted
        print(f"\nresubmit {len(config.EFFORTS)} cells, {n:,} requests, "
              f"batch pricing")
        print(f"  measured {mi:.0f} input and {mo:.0f} output tokens per "
              f"request, from the {len([1 for l in move if json.loads(l).get('status') == 'ok']):,} that returned")
        print(f"  estimated ${cost:.2f}")

    if not args.go:
        print("\nnothing spent and nothing moved. --go to do it.")
        return 0

    require_amendment()

    # The move, with the original kept until the rewrite is on disk. A crash
    # between the truncate and the rewrite would otherwise lose wave 2.
    shutil.copy(w["responses"], w["responses"] + ".before_opus_resubmit")
    with open(SUPERSEDED, "a") as f:
        f.writelines(move)
    with open(w["responses"], "w") as f:
        f.writelines(keep)
    print(f"\nmoved {len(move):,} rows to {SUPERSEDED}")
    print(f"backup at {w['responses']}.before_opus_resubmit")

    with open(w["batches"]) as f:
        state = json.load(f)
    dead = {k: v for k, v in state.items() if v.get("model") == MODEL}
    state.setdefault("_superseded", []).append(
        {"reason": "credit balance exhausted mid-batch, see Amendment 6 and 7",
         "cells": dead})
    for k in dead:
        state.pop(k)
    with open(w["batches"], "w") as f:
        json.dump(state, f, indent=2)
    print(f"archived {len(dead)} dead batch ids under _superseded")

    items = load_items(w["items"])
    write_index(items, w["index"], w["id_offset"])
    cli = client()
    model_idx = config.MODELS.index(MODEL)
    for effort in config.EFFORTS:
        reqs = build_requests(items, model_idx, MODEL, effort,
                              config.N_TRIALS, w["id_offset"])
        batch = cli.messages.batches.create(requests=reqs)
        state[f"{MODEL}|{effort}"] = {
            "batch_id": batch.id, "model": MODEL, "effort": effort,
            "trials": config.N_TRIALS, "n_requests": len(reqs), "wave": WAVE,
            "resubmission": True,
        }
        with open(w["batches"], "w") as f:
            json.dump(state, f, indent=2)
        print(f"submitted {MODEL}|{effort}: {batch.id} ({len(reqs):,} requests)")

    print(f"\nnow run: .venv/bin/python run/collect.py --wave {WAVE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
