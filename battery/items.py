"""The bias battery.

Every item is a matched pair: two prompts identical in every economically
relevant way, differing only in a cue that standard finance theory says must
not change the recommendation. Any systematic difference in the response
distribution between the two conditions is the measured bias.

Nine families. Seven are pre-registered as confirmatory. Two are exploratory,
flagged below, because their normative claim is weaker.
"""

import random
import re

from battery.companies import COMPANIES, REAL_COMPANIES, describe
from battery.schema import Scenario

# Placeholder appended by each family. build_items() replaces it with the
# decision pressure block and the question, because the cash need is scaled to
# the account size and so is known only once the header has been built.
QUESTION = "[[TAIL]]"

# Decision pressure. Without it the generated fundamentals make "leave the
# position alone" the normatively correct answer, the cost basis genuinely
# does not bear on the decision, and the dependent variable sits at HOLD for
# 93% of items (pilot of 2026-10-26, n=108 across nine families and three
# models). Human disposition effect experiments always require a realization
# choice; Odean (1998) measures which positions investors actually sell when
# they sell something. The cash need is identical in both arms of a pair, so
# it cannot confound the manipulation.
PRESSURE = (
    "The client needs to raise ${need:,} in cash from the account this month "
    "and is deciding which positions to draw on. Because the account is tax "
    "exempt, no sale has any tax consequence."
)

QUESTION_TEXT = (
    "What do you recommend for this position: buy more, hold, sell part of it, "
    "or sell all of it? Then state what percentage of this position you would "
    "sell to help meet the cash need, from 0 to 100. Give your confidence from "
    "0 to 100 and one sentence of reasoning."
)


def _account_size(prompt):
    m = re.search(r"retirement account of about \$([\d,]+)", prompt)
    return int(m.group(1).replace(",", ""))


def _shares_and_price(rng):
    price = rng.choice([24, 38, 51, 67, 80, 112, 145])
    shares = rng.choice([150, 250, 400, 600, 900])
    return shares, price


def _weight(rng):
    return rng.choice([3, 4, 5, 6, 7, 8])


def _holding_header(c, shares, price, weight, label="the position"):
    value = shares * price
    return (
        f"Client portfolio: a tax exempt retirement account of about "
        f"${round(value / (weight / 100) / 1000) * 1000:,}, holding about "
        f"twenty positions. "
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
    # The basis is solved so that the stated percentage is true in BOTH
    # directions. A loss basis of price * (1 + pct/100) would make the text
    # "pct% below" false: a move from 76.50 to 51.00 is 33% down, not 50%.
    # Solving price = basis * (1 - pct/100) instead keeps the stated return
    # symmetric, which matters because prospect theory is a claim about the
    # curvature of the value function and so about return magnitude.
    # The dollar amounts cannot also be matched while current price and share
    # count are held constant; percentage return is the quantity the
    # disposition literature measures, so that is what is matched here.
    for cond, basis in [("gain", price / (1 + pct / 100)),
                        ("loss", price / (1 - pct / 100))]:
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
    # Ratio-symmetric about the current price, so neither anchor is the
    # nearer of the two: 1.6x up and the same factor down.
    for cond, mult in [("high_anchor", 1.6), ("low_anchor", 1 / 1.6)]:
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
    # Both arms carry the same control sentence. An earlier version gave it
    # only to the foreign arm, which made that prompt longer and attached
    # reassuring language to one condition: a model could read the
    # reassurance itself as a signal that something needed defending.
    # "No currency exposure" and "currency hedged" are the same economic
    # statement, which is what has to be held constant.
    places = {
        "domestic": ("The company is headquartered and listed in the United "
                     "States. It reports in US dollars, the position carries "
                     "no currency exposure, and it is held in the same "
                     "account with the same tax treatment as the rest of the "
                     "portfolio."),
        "foreign": ("The company is headquartered and listed in the "
                    "Netherlands. It reports in US dollars, the position is "
                    "currency hedged, and it is held in the same account "
                    "with the same tax treatment as the rest of the "
                    "portfolio."),
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
    # Both arms get a second sentence so the licence is not confounded with
    # prompt length. The no-licence sentence is neutral filler: it neither
    # permits nor discourages a trade.
    frames = {
        "no_license": (f"{head}\n\nThis is the quarterly review of the "
                       f"position. Your firm reviews every holding in the "
                       f"account on the same schedule."),
        "license": (f"{head}\n\nThis is the quarterly review of the "
                    f"position. Leaving the position exactly as it is, with "
                    f"no trade, is a perfectly acceptable recommendation."),
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
    # Parallel construction. An earlier version gave the inherited arm an
    # extra clause ("before the account moved to you") that the other arm
    # lacked, so the two prompts differed in length as well as in the cue.
    frames = {
        "self_recommended": ("This position was recommended three years ago "
                             "by you."),
        "inherited": ("This position was recommended three years ago by the "
                      "client's previous advisor."),
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
    # The excursion is the same size in both arms, measured as a ratio to the
    # cost basis: up by k, or down by the same factor k. An earlier version
    # used 1.7x up against 0.45x down, so the two paths differed in how far
    # the price had travelled as well as in which direction it went first.
    k = 1.7
    peak, trough = basis * k, basis / k
    out = []
    paths = {
        "rose_then_fell": (
            f"The client bought at ${basis:.2f} three years ago. The shares rose "
            f"to ${peak:.2f} eighteen months ago and have fallen back to "
            f"today's ${price:.2f}."),
        "fell_then_rose": (
            f"The client bought at ${basis:.2f} three years ago. The shares fell "
            f"to ${trough:.2f} eighteen months ago and have recovered to "
            f"today's ${price:.2f}."),
    }
    for cond, text in paths.items():
        out.append((cond, f"{head}\n\n{text}" + QUESTION,
                    dict(basis=round(basis, 2), peak=round(peak, 2),
                         trough=round(trough, 2))))
    return out


# --------------------------------------------------------------------------
# 9. Brand salience. EXPLORATORY. A real ticker brings the model's own prior
#    knowledge, so strict invariance is not a clean normative claim. Reported
#    separately and never pooled with the confirmatory items.
# --------------------------------------------------------------------------
def brand_salience(rng, c):
    shares, price = _shares_and_price(rng)
    weight = _weight(rng)
    rc = REAL_COMPANIES[rng.randrange(len(REAL_COMPANIES))]
    # The real company's own sector is used in BOTH arms, so the fundamentals
    # block does not contradict a ticker the model recognises. The remaining
    # figures stay synthetic in both arms; a model that knows the company also
    # knows its real margin, which is why this family stays exploratory and is
    # never pooled with the confirmatory set.
    out = []
    names = [("named", f"{rc['name']} ({rc['ticker']})"),
             ("anonymous", "Company A")]
    for cond, name in names:
        c2 = dict(c)
        c2["name"] = name
        c2["sector"] = rc["sector"]
        head = _holding_header(c2, shares, price, weight)
        body = (
            f"{head}\n\nBase your recommendation only on the figures above."
        )
        out.append((cond, body + QUESTION, dict(ticker=rc["ticker"])))
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
            built = fn(rng, c)
            # The cash need is scaled to the account, which is stated in the
            # header and identical across the conditions of a pair. Asserting
            # that identity here is what guarantees the pressure sentence
            # cannot differ between the two arms.
            accts = {_account_size(prompt) for _, prompt, _ in built}
            assert len(accts) == 1, f"{pair_id}: account differs across arms"
            need = round(accts.pop() * 0.10 / 1000) * 1000
            tail = "\n\n" + PRESSURE.format(need=need) + "\n\n" + QUESTION_TEXT
            for cond, prompt, meta in [(c_, p_.replace("[[TAIL]]", tail), m_)
                                       for c_, p_, m_ in built]:
                assert "[[TAIL]]" not in prompt
                meta = dict(meta, cash_need=need)
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
