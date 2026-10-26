"""End to end test of the analysis pipeline on simulated responses.

Spends nothing. Generates fake answers with a known injected bias, runs the
real analysis, and checks it recovers the planted effect. Run this before
spending money: if the pipeline cannot find a bias that is definitely there,
it cannot be trusted to report one that is.

Usage:
    python scripts/selftest.py
"""

import json
import os
import random
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from analysis.directions import DIRECTIONS

PLANTED = {"disposition": -0.8, "anchoring": -0.4, "home_bias": 0.3}
ACTIONS = ["BUY_MORE", "HOLD", "SELL_PARTIAL", "SELL_ALL"]


def main():
    rng = random.Random(1)
    items = [json.loads(l) for l in open(config.ITEMS_PATH)]
    out = "data/responses.selftest.jsonl"
    n = 0
    with open(out, "w") as f:
        for model in config.MODELS:
            for effort in config.EFFORTS:
                for it in items:
                    base_c, treat_c, _ = DIRECTIONS[it["bias"]]
                    shift = PLANTED.get(it["bias"], 0.0)
                    # Effort shrinks the planted bias, the hypothesis the real
                    # study tests. Simulated here only to exercise the code.
                    shift *= {"low": 1.0, "medium": 0.6, "high": 0.3}[effort]
                    centre = 1.5 + (shift if it["condition"] == treat_c else 0)
                    for trial in range(config.N_TRIALS):
                        score = round(rng.gauss(centre, 0.7))
                        score = max(0, min(3, score))
                        f.write(json.dumps(dict(
                            custom_id=f"fake{n}", item_id=it["item_id"],
                            bias=it["bias"], pair_id=it["pair_id"],
                            condition=it["condition"], status_class=it["status"],
                            model=model, effort=effort, trial=trial,
                            status="ok", action=ACTIONS[score],
                            confidence=rng.randint(50, 90), reason="simulated",
                        )) + "\n")
                        n += 1
    print(f"simulated {n:,} responses -> {out}")

    real = config.RESPONSES_PATH
    backup = real + ".bak"
    if os.path.exists(real):
        os.rename(real, backup)
    os.rename(out, real)
    try:
        subprocess.run([sys.executable, "analysis/analyze.py"], check=True)
        fig = subprocess.run([sys.executable, "analysis/figures.py"])
        if fig.returncode:
            print("figures skipped (matplotlib not installed)")
    finally:
        os.rename(real, out)
        if os.path.exists(backup):
            os.rename(backup, real)

    res = json.load(open("data/results.json"))["results"]
    print("\nrecovery check (planted vs recovered, effort=low):")
    bad = 0
    for bias, planted in PLANTED.items():
        got = [r["effect"] for r in res
               if r["bias"] == bias and r["effort"] == "low"]
        avg = sum(got) / len(got)
        flag = "ok" if abs(avg - planted) < 0.25 else "MISMATCH"
        if flag != "ok":
            bad += 1
        print(f"  {bias:20s} planted {planted:+.2f}  recovered {avg:+.2f}  {flag}")
    null = [r for r in res if r["bias"] not in PLANTED and r["significant"]]
    print(f"  false positives on the {len(DIRECTIONS) - len(PLANTED)} null "
          f"biases: {len(null)} of {len([r for r in res if r['bias'] not in PLANTED])} cells")
    print("\nPASS" if bad == 0 else "\nFAIL")


if __name__ == "__main__":
    main()
