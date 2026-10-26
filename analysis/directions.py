"""Pre-registered condition ordering and predicted directions.

Fixed before any data was collected. The sign of every effect in the paper is
read against this table, so it must not be edited after a run.

effect = mean sell tendency in `treatment` minus mean sell tendency in
`baseline`, where sell tendency runs 0 (buy more) to 3 (sell all).
"""

DIRECTIONS = {
    # bias:            (baseline,          treatment,            predicted sign)
    "disposition":        ("gain",            "loss",               "-"),
    "framing":            ("gain_frame",      "loss_frame",         "?"),
    "anchoring":          ("low_anchor",      "high_anchor",        "-"),
    "home_bias":          ("domestic",        "foreign",            "+"),
    "action_bias":        ("no_license",      "license",            "-"),
    "mental_accounting":  ("serious_sleeve",  "fun_sleeve",         "+"),
    "advisor_attribution":("inherited",       "self_recommended",   "-"),
    "price_path":         ("fell_then_rose",  "rose_then_fell",     "+"),
    "brand_salience":     ("anonymous",       "named",              "?"),
}

# Why each sign. Goes in the paper's hypothesis table.
RATIONALE = {
    "disposition": "Investors are reluctant to realise losses, so a position "
                   "held below cost should draw fewer sell recommendations.",
    "framing": "Prospect theory predicts the frame moves the choice, but the "
               "direction in an advisory setting is not pinned down, so this "
               "is pre-registered two sided.",
    "anchoring": "A higher salient number, even an uninformative one, should "
                 "make the current price look cheap and reduce selling.",
    "home_bias": "Investors overweight domestic assets, so an identical "
                 "foreign listing should draw more selling.",
    "action_bias": "Explicit permission to do nothing should reduce the pull "
                   "toward recommending a trade.",
    "mental_accounting": "Money in a sleeve labelled discretionary is treated "
                         "as more expendable.",
    "advisor_attribution": "Commitment to a prior recommendation should make "
                           "an advisor less willing to unwind it.",
    "price_path": "A position that has fallen from a peak invites regret and "
                  "should draw more selling than the same price reached from "
                  "below.",
    "brand_salience": "A familiar name may draw either loyalty or scepticism, "
                      "so this is two sided and exploratory.",
}
