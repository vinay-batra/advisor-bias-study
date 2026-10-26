"""Write the battery to data/items.jsonl."""

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from battery.items import build_items


def main():
    items = build_items(config.PAIRS_PER_BIAS, config.SEED)
    os.makedirs("data", exist_ok=True)
    with open(config.ITEMS_PATH, "w") as f:
        for it in items:
            f.write(json.dumps(it.to_dict()) + "\n")
    by_bias = {}
    for it in items:
        by_bias[it.bias] = by_bias.get(it.bias, 0) + 1
    print(f"wrote {len(items)} prompts to {config.ITEMS_PATH}")
    for k, v in by_bias.items():
        print(f"  {k:24s} {v:4d} prompts ({v // 2} pairs)")
    cells = len(config.MODELS) * len(config.EFFORTS)
    print(f"\n{cells} model x effort cells x {config.N_TRIALS} trials "
          f"= {len(items) * cells * config.N_TRIALS:,} API requests")


if __name__ == "__main__":
    main()
