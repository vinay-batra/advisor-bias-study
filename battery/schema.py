"""Scenario record. One row per prompt that will be sent to a model."""

from dataclasses import dataclass, asdict, field
from typing import Dict, Any


@dataclass
class Scenario:
    bias: str          # which bias family this item tests
    pair_id: str       # shared by the conditions of one matched pair
    condition: str     # the manipulated level, e.g. "gain" / "loss"
    item_id: str       # pair_id + condition, unique
    prompt: str        # the user message sent to the model
    normative: str     # "invariance" or a specific required action
    status: str        # "confirmatory" or "exploratory" (pre-registered)
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self):
        return asdict(self)
