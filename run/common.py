"""Shared plumbing for submitting and collecting runs."""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config

EFFORT_LETTER = {"low": "l", "medium": "m", "high": "h", "xhigh": "x", "max": "X"}
LETTER_EFFORT = {v: k for k, v in EFFORT_LETTER.items()}


def load_items():
    with open(config.ITEMS_PATH) as f:
        return [json.loads(line) for line in f]


def custom_id(item_idx, model_idx, effort, trial):
    """Short, unique, and decodable. Batch custom_ids have a length limit, so
    the full item_id is not embedded; index.json holds the mapping."""
    return f"i{item_idx:04d}_m{model_idx}_e{EFFORT_LETTER[effort]}_t{trial}"


def parse_custom_id(cid):
    item_part, model_part, effort_part, trial_part = cid.split("_")
    return (
        int(item_part[1:]),
        int(model_part[1:]),
        LETTER_EFFORT[effort_part[1:]],
        int(trial_part[1:]),
    )


def write_index(items):
    """Persist the index -> item_id mapping so results can be rejoined."""
    idx = {
        "models": config.MODELS,
        "items": [it["item_id"] for it in items],
    }
    with open("data/index.json", "w") as f:
        json.dump(idx, f, indent=2)
    return idx


def read_index():
    with open("data/index.json") as f:
        return json.load(f)


def client():
    import anthropic
    from dotenv import load_dotenv
    load_dotenv()
    return anthropic.Anthropic()
