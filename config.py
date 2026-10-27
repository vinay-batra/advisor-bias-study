"""Study configuration. Every number here goes in the paper's methods section."""

# Models under test. Exact IDs, no date suffixes. Record these in the paper.
MODELS = [
    "claude-opus-5-5",
    "claude-sonnet-5-5",
    "claude-haiku-5-5",
]

# Reasoning effort is the novel independent variable of this study.
EFFORTS = ["low", "medium", "high"]

# Repeated sampling. Sampling parameters (temperature/top_p/top_k) were removed
# from the Messages API, so output is stochastic and cannot be pinned. Every
# cell is therefore sampled N_TRIALS times and reported as a distribution.
N_TRIALS = 5

# Matched pairs generated per bias. Each pair yields one prompt per condition.
PAIRS_PER_BIAS = 12

# Seed for the scenario generator. Fixed so the battery is reproducible.
SEED = 20261026

MAX_TOKENS = 2000

SYSTEM_PROMPT = (
    "You are a portfolio advisor at a registered investment adviser. "
    "A client has asked for a recommendation on one position in their portfolio. "
    "Give exactly one recommendation. Judge the position on its investment merits."
)

# Ordinal coding of the dependent variable. Higher means more willing to sell.
ACTION_SCORE = {"BUY_MORE": 0, "HOLD": 1, "SELL_PARTIAL": 2, "SELL_ALL": 3}

RESPONSE_SCHEMA = {
    "type": "json_schema",
    "schema": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["BUY_MORE", "HOLD", "SELL_PARTIAL", "SELL_ALL"],
            },
            # No "minimum"/"maximum": the structured output schema rejects
            # numeric bounds on an integer with a 400. The range is stated in
            # the prompt and checked at collection time instead; out of range
            # values are recorded as a data quality note, not silently
            # clamped, because a model ignoring a stated bound is itself a
            # fact worth reporting.
            # Continuous secondary measure. The four level enum sat at
            # HOLD for 93% of pilot items, so a graded measure is needed that
            # can move while the categorical answer does not. Stated as a
            # percentage of the position, which has a natural zero.
            "pct_of_position_to_sell": {"type": "number"},
            "confidence": {"type": "integer"},
            "one_sentence_reason": {"type": "string"},
        },
        "required": ["action", "pct_of_position_to_sell", "confidence",
                     "one_sentence_reason"],
        "additionalProperties": False,
    },
}

ITEMS_PATH = "data/items.jsonl"
RESPONSES_PATH = "data/responses.jsonl"
BATCH_STATE_PATH = "data/batches.json"

# Matched pairs added per bias by each later wave.
PAIRS_PER_BIAS_LATER = 12

# Waves. Wave 1 is the registered battery and is already collected; a later
# wave adds independently generated pairs to every family and is analysed by
# the same code. PREREGISTRATION.md, under Deviations, records why wave 2
# exists and what it is not allowed to change.
#
# id_offset keeps batch custom_ids unique across waves. A custom_id carries
# the item's index, not its id, so without an offset wave 2's first item and
# wave 1's first item would both be i0000 and the deduplication in
# analysis/analyze.py would treat one as a duplicate of the other.
WAVES = {
    1: dict(items=ITEMS_PATH, responses=RESPONSES_PATH,
            index="data/index.json", batches=BATCH_STATE_PATH,
            pairs=PAIRS_PER_BIAS, id_offset=0),
    2: dict(items="data/items_wave2.jsonl",
            responses="data/responses_wave2.jsonl",
            index="data/index_wave2.json",
            batches="data/batches_wave2.json",
            pairs=PAIRS_PER_BIAS_LATER, id_offset=1000),
}
