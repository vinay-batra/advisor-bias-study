"""Price the study before running it, using real token counts.

Counts input tokens with the API's own counter (never a third party
tokenizer), measures output length on a small live sample, then extrapolates
to the full design at batch pricing.

Usage:
    python scripts/estimate.py
"""

import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from run.common import load_items, client

# Per million tokens, standard pricing. Batch is half of this.
PRICES = {
    "claude-opus-5-5":   (4.00, 20.00),
    "claude-opus-5":     (5.00, 25.00),
    "claude-sonnet-5-5": (2.00, 10.00),
    "claude-sonnet-5":   (2.00, 10.00),
    "claude-haiku-5-5":  (0.10, 0.50),
}

SAMPLE = 4


def main():
    items = load_items()
    cli = client()

    counted = cli.messages.count_tokens(
        model=config.MODELS[0],
        system=config.SYSTEM_PROMPT,
        messages=[{"role": "user", "content": items[0]["prompt"]}],
    )
    in_tok = counted.input_tokens
    print(f"input tokens per prompt: {in_tok}")

    total = 0.0
    print(f"\n{'cell':40s} {'out tok':>8s} {'requests':>10s} {'batch $':>9s}")
    for model in config.MODELS:
        pin, pout = PRICES[model]
        for effort in config.EFFORTS:
            outs = []
            for it in items[:SAMPLE]:
                msg = cli.messages.create(
                    model=model, max_tokens=config.MAX_TOKENS,
                    system=config.SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": it["prompt"]}],
                    output_config={"effort": effort, "format": config.RESPONSE_SCHEMA},
                )
                outs.append(msg.usage.output_tokens)
            out_tok = statistics.mean(outs)
            n = len(items) * config.N_TRIALS
            cost = n * (in_tok * pin + out_tok * pout) / 1_000_000 * 0.5
            total += cost
            print(f"{model + ' @ ' + effort:40s} {out_tok:8.0f} {n:10,} {cost:9.2f}")

    print(f"\nfull study at batch pricing: ${total:.2f}")
    print(f"(output token counts include billed thinking tokens, which is why "
          f"effort drives the cost)")


if __name__ == "__main__":
    main()
