"""Write a wave of the battery to its items file.

    python battery/build.py            # wave 1, the registered battery
    python battery/build.py --wave 2   # the power extension
"""

import argparse
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from battery.items import build_items, build_wave
from run.common import wave as wave_paths


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--wave", type=int, default=1)
    ap.add_argument("--pairs", type=int, default=None)
    args = ap.parse_args()
    w = wave_paths(args.wave)
    pairs = args.pairs or w["pairs"]
    if args.wave == 1:
        items = build_items(pairs, config.SEED)
    else:
        # Every wave before this one, so no item in a later wave repeats an
        # item that has already been paid for.
        avoid = set()
        for earlier in sorted(k for k in config.WAVES if k < args.wave):
            path = config.WAVES[earlier]["items"]
            if os.path.exists(path):
                with open(path) as f:
                    avoid.update(json.loads(line)["prompt"] for line in f)
        print(f"avoiding {len(avoid)} prompts from earlier waves")
        items = build_wave(args.wave, pairs, config.SEED, avoid)
    os.makedirs("data", exist_ok=True)
    with open(w["items"], "w") as f:
        for it in items:
            f.write(json.dumps(it.to_dict()) + "\n")
    by_bias = {}
    for it in items:
        by_bias[it.bias] = by_bias.get(it.bias, 0) + 1
    print(f"wrote {len(items)} prompts to {w['items']}")
    for k, v in by_bias.items():
        print(f"  {k:24s} {v:4d} prompts ({v // 2} pairs)")
    cells = len(config.MODELS) * len(config.EFFORTS)
    print(f"\n{cells} model x effort cells x {config.N_TRIALS} trials "
          f"= {len(items) * cells * config.N_TRIALS:,} API requests")


if __name__ == "__main__":
    main()
