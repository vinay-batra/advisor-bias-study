"""Print the live status of every submitted batch.

Read only. Safe to run at any time, including while run/collect.py is
polling, because it only retrieves batch metadata and writes nothing.

Usage:
    python run/status.py
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from run.common import client


def main():
    with open(config.BATCH_STATE_PATH) as f:
        batches = json.load(f)

    c = client()
    done = processing = errored = total = 0
    print(f"{'cell':34s} {'status':12s} {'ok':>6s} {'proc':>6s} {'err':>5s}")
    for key, b in batches.items():
        st = c.messages.batches.retrieve(b["batch_id"])
        rc = st.request_counts
        done += rc.succeeded
        processing += rc.processing
        errored += rc.errored + rc.canceled + rc.expired
        total += b["n_requests"]
        print(f"{key:34s} {st.processing_status:12s} {rc.succeeded:6d} "
              f"{rc.processing:6d} {rc.errored:5d}")

    pct = 100 * done / max(total, 1)
    print(f"\n{done:,} of {total:,} succeeded ({pct:.1f}%), "
          f"{processing:,} still processing, {errored:,} failed")

    # Rows already written to disk by the collector, which lags the batches.
    if os.path.exists(config.RESPONSES_PATH):
        with open(config.RESPONSES_PATH) as f:
            n = sum(1 for _ in f)
        print(f"{n:,} rows collected to {config.RESPONSES_PATH}")


if __name__ == "__main__":
    main()
