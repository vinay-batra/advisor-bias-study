"""Price the study without spending anything.

Runs with no API key. Input tokens are approximated from character counts,
which is accurate to roughly plus or minus 15 percent for English prose with
embedded numbers. Output tokens are an assumption, not a measurement, because
thinking tokens are billed as output and scale with reasoning effort.

Replace this with scripts/estimate.py once a key is in .env. That version
calls messages.count_tokens for the exact input count and samples four live
items per cell to measure real output length. The numbers below are for
deciding whether the study is affordable, not for the paper.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

# Per million tokens, input / output, at standard pricing.
PRICES = {
    "claude-opus-5-5": (4.00, 20.00),
    "claude-sonnet-5-5": (2.00, 10.00),
    "claude-haiku-5-5": (0.10, 0.50),
}

# ASSUMPTION, not measurement. Thinking tokens are billed as output and are
# the dominant term at high effort. The structured answer itself is short:
# an enum, an integer and one sentence, so call it 60 tokens.
ANSWER_TOKENS = 60
THINKING_TOKENS = {"low": 250, "medium": 800, "high": 2000}

CHARS_PER_TOKEN = 3.7
BATCH_DISCOUNT = 0.5


def main():
    items = [json.loads(l) for l in open("data/items.jsonl")]
    sys_chars = len(config.SYSTEM_PROMPT)
    prompt_chars = sum(len(it["prompt"]) for it in items) / len(items)
    in_tok = (sys_chars + prompt_chars) / CHARS_PER_TOKEN

    print(f"{len(items)} items, {len(config.MODELS)} models, "
          f"{len(config.EFFORTS)} efforts, {config.N_TRIALS} trials")
    print(f"approx input tokens per request: {in_tok:.0f} "
          f"(system {sys_chars/CHARS_PER_TOKEN:.0f} + prompt "
          f"{prompt_chars/CHARS_PER_TOKEN:.0f})")
    print()
    print(f"{'model':<20} {'effort':<8} {'requests':>9} {'in Mtok':>9} "
          f"{'out Mtok':>9} {'batch $':>9}")
    print("-" * 70)

    total = 0.0
    n_req_total = 0
    for model in config.MODELS:
        p_in, p_out = PRICES[model]
        for effort in config.EFFORTS:
            n = len(items) * config.N_TRIALS
            out_tok = ANSWER_TOKENS + THINKING_TOKENS[effort]
            m_in = n * in_tok / 1e6
            m_out = n * out_tok / 1e6
            cost = (m_in * p_in + m_out * p_out) * BATCH_DISCOUNT
            total += cost
            n_req_total += n
            print(f"{model:<20} {effort:<8} {n:>9} {m_in:>9.3f} "
                  f"{m_out:>9.3f} {cost:>9.2f}")

    print("-" * 70)
    print(f"{'TOTAL':<29} {n_req_total:>9} {'':>9} {'':>9} {total:>9.2f}")
    print()
    print(f"at standard (non-batch) pricing: ${total / BATCH_DISCOUNT:.2f}")
    print(f"one pilot cell, 3 pairs x 1 trial, sonnet medium, non-batch: "
          f"${(6 * (in_tok * 2.0 + (ANSWER_TOKENS + 800) * 10.0) / 1e6):.4f}")
    print()
    print("Output tokens are an assumption. If high effort spends 4000")
    print("thinking tokens instead of 2000, the opus high cell doubles.")
    print("Run scripts/estimate.py with a key for measured numbers.")


if __name__ == "__main__":
    main()
