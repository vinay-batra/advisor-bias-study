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
            "confidence": {"type": "integer", "minimum": 0, "maximum": 100},
            "one_sentence_reason": {"type": "string"},
        },
        "required": ["action", "confidence", "one_sentence_reason"],
        "additionalProperties": False,
    },
}

ITEMS_PATH = "data/items.jsonl"
RESPONSES_PATH = "data/responses.jsonl"
BATCH_STATE_PATH = "data/batches.json"
