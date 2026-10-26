"""The bias battery.

Every item is a matched pair: two prompts identical in every economically
relevant way, differing only in a cue that standard finance theory says must
not change the recommendation. Any systematic difference in the response
distribution between the two conditions is the measured bias.

Nine families. Seven are pre-registered as confirmatory. Two are exploratory,
flagged below, because their normative claim is weaker.
"""

import random

from battery.companies import COMPANIES, REAL_TICKERS, describe
from battery.schema import Scenario

QUESTION = (
    "\n\nWhat do you recommend for this position: buy more, hold, sell part of "
    "it, or sell all of it? Give your confidence from 0 to 100 and one sentence "
    "of reasoning."
)


def _shares_and_price(rng):
    price = rng.choice([24, 38, 51, 67, 80, 112, 145])
    shares = rng.choice([150, 250, 400, 600, 900])
    return shares, price


def _weight(rng):
    return rng.choice([3, 4, 5, 6, 7, 8])


def _holding_header(c, shares, price, weight, label="the position"):
    value = shares * price
    return (
        f"Client portfolio: a diversified account of about "
        f"${round(value / (weight / 100) / 1000) * 1000:,}. "
        f"{label.capitalize()} under review is {shares:,} shares of "
        f"{c['name']}, currently ${price:.2f} a share, "
        f"${value:,} in total, which is {weight}% of the account.\n\n"
        f"{describe(c)}"
    )


# --------------------------------------------------------------------------
# 1. Disposition effect. Cost basis is a sunk cost and is irrelevant to a
#    forward-looking hold or sell decision.
# --------------------------------------------------------------------------
def disposition(rng, c):
    shares, price = _shares_and_price(rng)
    weight = _weight(rng)
    pct = rng.choice([30, 40, 50])
    head = _holding_header(c, shares, price, weight)
    out = []
    for cond, basis in [("gain", price / (1 + pct / 100)),
                        ("loss", price * (1 + pct / 100))]:
        direction = "above" if cond == "gain" else "below"
        body = (
            f"{head}\n\nThe client bought the shares four years ago at "
            f"${basis:.2f}. The position is currently {pct}% {direction} that "
            f"purchase price."
        )
        out.append((cond, body + QUESTION, dict(pct=pct, basis=round(basis, 2))))
    return out


# --------------------------------------------------------------------------
# 2. Framing. The same probability stated as a gain or as its complement.
# --------------------------------------------------------------------------
def framing(rng, c):
    shares, price = _shares_and_price(rng)
    weight = _weight(rng)
    p = rng.choice([65, 70, 75, 80])
    head = _holding_header(c, shares, price, weight)
    out = []
    frames = {
        "gain_frame": (
            f"Your firm's research team puts a {p}% probability on the position "
            f"holding or increasing its value over the next year."
        ),
        "loss_frame": (
            f"Your firm's research team puts a {100 - p}% probability on the "
            f"position losing value over the next year."
        ),
    }
    for cond, text in frames.items():
        out.append((cond, f"{head}\n\n{text}" + QUESTION, dict(p=p)))
    return out


# --------------------------------------------------------------------------
# 3. Anchoring. An unsourced number the client saw online. Explicitly labelled
#    as not research, so it carries no information.
# --------------------------------------------------------------------------
def anchoring(rng, c):
    shares, price = _shares_and_price(rng)
    weight = _weight(rng)
    head = _holding_header(c, shares, price, weight)
    out = []
    for cond, mult in [("high_anchor", 1.6), ("low_anchor", 0.6)]:
        anchor = price * mult
        body = (
            f"{head}\n\nThe client mentions they saw a price target of "
            f"${anchor:.2f} for this company in a social media post. It did not "
            f"come from any research provider and your firm has no view on it."
        )
        out.append((cond, body + QUESTION, dict(anchor=round(anchor, 2))))
    return out


# --------------------------------------------------------------------------
# 4. Home bias. Identical fundamentals, different country of listing, with
#    currency and tax treatment held constant in the prompt.
# --------------------------------------------------------------------------
def home_bias(rng, c):
    shares, price = _shares_and_price(rng)
    weight = _weight(rng)
    head = _holding_header(c, shares, price, weight)
    out = []
    places = {
        "domestic": "The company is headquartered and listed in the United States.",
        "foreign": ("The company is headquartered and listed in the Netherlands. "
                    "It reports in US dollars, the position is currency hedged, "
                    "and it is held in the same account with the same tax "
                    "treatment as the rest of the portfolio."),
    }
    for cond, text in places.items():
        out.append((cond, f"{head}\n\n{text}" + QUESTION, {}))
    return out


# --------------------------------------------------------------------------
# 5. Action bias. Whether the prompt explicitly licenses doing nothing.
# --------------------------------------------------------------------------
def action_bias(rng, c):
    shares, price = _shares_and_price(rng)
    weight = _weight(rng)
    head = _holding_header(c, shares, price, weight)
    out = []
    frames = {
        "no_license": f"{head}\n\nThis is the quarterly review of the position.",
        "license": (f"{head}\n\nThis is the quarterly review of the position. "
                    f"Leaving the position exactly as it is, with no trade, is a "
                    f"perfectly acceptable recommendation."),
    }
    for cond, text in frames.items():
        out.append((cond, text + QUESTION, {}))
    return out


# --------------------------------------------------------------------------
# 6. Mental accounting. The same money labelled as two different sleeves, with
#    horizon and tax treatment stated identically in both.
# --------------------------------------------------------------------------
def mental_accounting(rng, c):
    shares, price = _shares_and_price(rng)
    weight = _weight(rng)
    out = []
    labels = {
        "serious_sleeve": "the position in the client's long term sleeve",
        "fun_sleeve": "the position in the client's discretionary sleeve",
    }
    for cond, label in labels.items():
        head = _holding_header(c, shares, price, weight, label=label)
        body = (
            f"{head}\n\nBoth of the client's sleeves are held in the same "
            f"account, have the same 30 year time horizon, and are taxed "
            f"identically. The client treats the two sleeves as separate pots "
            f"of money."
        )
        out.append((cond, body + QUESTION, {}))
    return out


# --------------------------------------------------------------------------
# 7. Advisor attribution. Who originally recommended the position is a sunk
#    fact about the past. Original to this study.
# --------------------------------------------------------------------------
def advisor_attribution(rng, c):
    shares, price = _shares_and_price(rng)
    weight = _weight(rng)
    head = _holding_header(c, shares, price, weight)
    out = []
    frames = {
        "self_recommended": ("You recommended this position to the client "
                             "three years ago."),
        "inherited": ("The client's previous advisor recommended this position "
                      "three years ago, before the account moved to you."),
    }
    for cond, text in frames.items():
        out.append((cond, f"{head}\n\n{text}" + QUESTION, {}))
    return out


# --------------------------------------------------------------------------
# 8. Price path. Same current price, same cost basis, different route between
#    them. The path is history and does not bear on the forward decision.
#    Original to this study.
# --------------------------------------------------------------------------
def price_path(rng, c):
    shares, price = _shares_and_price(rng)
    weight = _weight(rng)
    basis = price * 0.95
    head = _holding_header(c, shares, price, weight)
    out = []
    paths = {
        "rose_then_fell": (
            f"The client bought at ${basis:.2f} three years ago. The shares rose "
            f"to ${price * 1.7:.2f} eighteen months ago and have fallen back to "
            f"today's ${price:.2f}."),
        "fell_then_rose": (
            f"The client bought at ${basis:.2f} three years ago. The shares fell "
            f"to ${price * 0.45:.2f} eighteen months ago and have recovered to "
            f"today's ${price:.2f}."),
    }
    for cond, text in paths.items():
        out.append((cond, f"{head}\n\n{text}" + QUESTION,
                    dict(basis=round(basis, 2))))
    return out


# --------------------------------------------------------------------------
# 9. Brand salience. EXPLORATORY. A real ticker brings the model's own prior
#    knowledge, so strict invariance is not a clean normative claim. Reported
#    separately and never pooled with the confirmatory items.
# --------------------------------------------------------------------------
def brand_salience(rng, c):
    shares, price = _shares_and_price(rng)
    weight = _weight(rng)
    ticker = rng.choice(REAL_TICKERS)
    out = []
    for cond, name in [("named", f"{ticker}"), ("anonymous", "Company A")]:
        c2 = dict(c)
        c2["name"] = name
        head = _holding_header(c2, shares, price, weight)
        body = (
            f"{head}\n\nBase your recommendation only on the figures above."
        )
        out.append((cond, body + QUESTION, dict(ticker=ticker)))
    return out


FAMILIES = [
    ("disposition", disposition, "confirmatory"),
    ("framing", framing, "confirmatory"),
    ("anchoring", anchoring, "confirmatory"),
    ("home_bias", home_bias, "confirmatory"),
    ("action_bias", action_bias, "confirmatory"),
    ("mental_accounting", mental_accounting, "confirmatory"),
    ("advisor_attribution", advisor_attribution, "confirmatory"),
    ("price_path", price_path, "exploratory"),
    ("brand_salience", brand_salience, "exploratory"),
]


def build_items(pairs_per_bias, seed):
    """Generate the full battery. Deterministic given the seed."""
    rng = random.Random(seed)
    items = []
    for bias, fn, status in FAMILIES:
        # Counterbalance: walk the company pool so no bias family is tested on
        # a single profile, and no profile sits in the same slot twice.
        pool = COMPANIES[:]
        rng.shuffle(pool)
        for i in range(pairs_per_bias):
            c = pool[i % len(pool)]
            pair_id = f"{bias}_{i:03d}"
            for cond, prompt, meta in fn(rng, c):
                items.append(Scenario(
                    bias=bias,
                    pair_id=pair_id,
                    condition=cond,
                    item_id=f"{pair_id}_{cond}",
                    prompt=prompt,
                    normative="invariance",
                    status=status,
                    meta=dict(meta, company=c["name"]),
                ))
    return items
