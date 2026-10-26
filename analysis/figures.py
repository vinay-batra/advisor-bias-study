"""Build the paper's figures from data/results.json.

Figures, one pair per dependent variable:
  fig1_forest   effect size per bias with 95% CIs, one panel per model
  fig2_effort   absolute effect against reasoning effort
  fig3_entropy  response entropy per item, the stochasticity evidence
  fig4, fig5    the same forest and effort plots on the continuous
                co-primary measure added in Amendment 3

results.json carries two rows per cell, one per measure, so every
figure filters on `measure` first. A row without that key predates
Amendment 3 and is read as the categorical measure.

Usage:
    python analysis/figures.py
"""

import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analysis.directions import DIRECTIONS

EFFORT_ORDER = ["low", "medium", "high", "xhigh", "max"]
os.makedirs("figures", exist_ok=True)

AXIS = {
    "sell_tendency": "effect on sell tendency (scale points)",
    "pct_to_sell": "effect on percent of position sold",
}


def load():
    with open("data/results.json") as f:
        return json.load(f)["results"]


def only(results, measure):
    """Rows for one dependent variable."""
    return [r for r in results if r.get("measure", "sell_tendency") == measure]


def fig_forest(results, effort="high", measure="sell_tendency", stem="fig1_forest"):
    results = only(results, measure)
    if not results:
        return
    models = sorted({r["model"] for r in results})
    fig, axes = plt.subplots(1, len(models), figsize=(4.2 * len(models), 5),
                             sharey=True)
    if len(models) == 1:
        axes = [axes]
    biases = list(DIRECTIONS)
    for ax, model in zip(axes, models):
        rows = {r["bias"]: r for r in results
                if r["model"] == model and r["effort"] == effort}
        ys, xs, los, his = [], [], [], []
        for i, b in enumerate(biases):
            if b not in rows:
                continue
            ys.append(i)
            xs.append(rows[b]["effect"])
            los.append(rows[b]["effect"] - rows[b]["ci_low"])
            his.append(rows[b]["ci_high"] - rows[b]["effect"])
        ax.errorbar(xs, ys, xerr=[los, his], fmt="o", capsize=3, color="black")
        ax.axvline(0, color="grey", lw=1, ls="--")
        ax.set_yticks(range(len(biases)))
        ax.set_yticklabels([b.replace("_", " ") for b in biases])
        ax.set_title(model.replace("claude-", ""), fontsize=10)
        ax.set_xlabel(AXIS[measure])
        ax.invert_yaxis()
    fig.suptitle(f"Matched pair effects at effort = {effort}\n"
                 f"zero means the irrelevant cue changed nothing", fontsize=11)
    fig.tight_layout()
    fig.savefig(f"figures/{stem}.pdf")
    fig.savefig(f"figures/{stem}.png", dpi=200)
    plt.close(fig)
    print(f"figures/{stem}.pdf")


def fig_effort(results, measure="sell_tendency", stem="fig2_effort"):
    results = only(results, measure)
    if not results:
        return
    models = sorted({r["model"] for r in results})
    fig, axes = plt.subplots(1, len(models), figsize=(4.2 * len(models), 4),
                             sharey=True)
    if len(models) == 1:
        axes = [axes]
    for ax, model in zip(axes, models):
        for bias in DIRECTIONS:
            cells = [r for r in results
                     if r["model"] == model and r["bias"] == bias]
            cells.sort(key=lambda r: EFFORT_ORDER.index(r["effort"]))
            if len(cells) < 2:
                continue
            ax.plot([EFFORT_ORDER.index(c["effort"]) for c in cells],
                    [abs(c["effect"]) for c in cells],
                    marker="o", lw=1.2, label=bias.replace("_", " "))
        used = sorted({EFFORT_ORDER.index(r["effort"]) for r in results})
        ax.set_xticks(used)
        ax.set_xticklabels([EFFORT_ORDER[i] for i in used])
        ax.set_xlabel("reasoning effort")
        ax.set_title(model.replace("claude-", ""), fontsize=10)
    axes[0].set_ylabel("absolute " + AXIS[measure])
    axes[-1].legend(fontsize=6, loc="upper right")
    fig.suptitle("Does more reasoning reduce behavioural bias?", fontsize=11)
    fig.tight_layout()
    fig.savefig(f"figures/{stem}.pdf")
    fig.savefig(f"figures/{stem}.png", dpi=200)
    plt.close(fig)
    print(f"figures/{stem}.pdf")


def fig_entropy(results):
    # Entropy is a property of the categorical answer, so one figure only.
    results = only(results, "sell_tendency")
    fig, ax = plt.subplots(figsize=(6, 4))
    models = sorted({r["model"] for r in results})
    for model in models:
        cells = [r for r in results if r["model"] == model]
        cells.sort(key=lambda r: EFFORT_ORDER.index(r["effort"]))
        by_effort = {}
        for c in cells:
            by_effort.setdefault(c["effort"], []).append(c["mean_entropy"])
        xs = sorted(by_effort, key=EFFORT_ORDER.index)
        ax.plot([EFFORT_ORDER.index(x) for x in xs],
                [sum(by_effort[x]) / len(by_effort[x]) for x in xs],
                marker="s", label=model.replace("claude-", ""))
    used = sorted({EFFORT_ORDER.index(r["effort"]) for r in results})
    ax.set_xticks(used)
    ax.set_xticklabels([EFFORT_ORDER[i] for i in used])
    ax.set_xlabel("reasoning effort")
    ax.set_ylabel("mean within item entropy (bits)")
    ax.set_title("Response variability across repeated identical prompts")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig("figures/fig3_entropy.pdf")
    fig.savefig("figures/fig3_entropy.png", dpi=200)
    plt.close(fig)
    print("figures/fig3_entropy.pdf")


if __name__ == "__main__":
    r = load()
    fig_forest(r)
    fig_effort(r)
    fig_entropy(r)
    fig_forest(r, measure="pct_to_sell", stem="fig4_forest_pct")
    fig_effort(r, measure="pct_to_sell", stem="fig5_effort_pct")
