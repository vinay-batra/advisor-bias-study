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
from contextlib import nullcontext

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analysis.directions import DIRECTIONS

EFFORT_ORDER = ["low", "medium", "high", "xhigh", "max"]

# Panels run weakest to strongest, which is the order every claim in the paper
# is stated in. Alphabetical would put opus in the middle.
MODEL_ORDER = ["claude-haiku-5-5", "claude-sonnet-5-5", "claude-opus-5-5"]


def by_capability(models):
    return sorted(models, key=lambda m: (MODEL_ORDER.index(m)
                                         if m in MODEL_ORDER else len(MODEL_ORDER), m))

os.makedirs("figures", exist_ok=True)

AXIS = {
    "sell_tendency": "effect on sell tendency (scale points)",
    "pct_to_sell": "effect on percent of position sold",
}

# A rotated y label has only the axes height to live in, which in a compact
# panel is about an inch. The units move to the caption.
SHORT_AXIS = {
    "sell_tendency": "absolute effect",
    "pct_to_sell": "absolute effect",
}

# Two sizes come out of the same code. The single-column reading build prints
# wide panels; the ACL build prints across both columns, 6.3in, and a figure
# drawn at 12.6in and scaled down to that has 5pt type. The compact variants
# are drawn at the width they are printed instead of scaled to it, and drop
# the suptitle because in ACL style the caption carries it.
COMPACT_RC = {
    "font.size": 6.5,
    "axes.titlesize": 7,
    "axes.labelsize": 6.5,
    "xtick.labelsize": 6,
    "ytick.labelsize": 6,
    "lines.markersize": 3,
}


def compact_rc(compact):
    return plt.rc_context(COMPACT_RC) if compact else nullcontext()


def load():
    with open("data/results.json") as f:
        return json.load(f)["results"]


def only(results, measure):
    """Rows for one dependent variable."""
    return [r for r in results if r.get("measure", "sell_tendency") == measure]


def fig_forest(results, effort="high", measure="sell_tendency", stem="fig1_forest",
               compact=False):
    results = only(results, measure)
    if not results:
        return
    models = by_capability({r["model"] for r in results})
    # 6.3in is ACL \textwidth. The height is set by the nine family rows,
    # not by the aspect ratio: a figure* costs its height out of a page.
    size = (6.3, 2.15) if compact else (4.2 * len(models), 5)
    with compact_rc(compact):
        fig, axes = plt.subplots(1, len(models), figsize=size, sharey=True,
                                 sharex=True)
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
        ax.errorbar(xs, ys, xerr=[los, his], fmt="o",
                    capsize=2 if compact else 3, color="black")
        ax.axvline(0, color="grey", lw=1, ls="--")
        ax.set_yticks(range(len(biases)))
        ax.set_yticklabels([b.replace("_", " ") for b in biases])
        ax.set_title(model.replace("claude-", ""),
                     fontsize=7 if compact else 10)
        ax.invert_yaxis()
        if not compact:
            continue
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
    if not compact:
        fig.suptitle(f"Matched pair effects at effort = {effort}\n"
                     f"zero means the irrelevant cue changed nothing",
                     fontsize=11)
    fig.supxlabel(AXIS[measure], fontsize=6.5 if compact else 10)
    fig.tight_layout(pad=0.45 if compact else 1.08)
    fig.savefig(f"figures/{stem}.pdf")
    fig.savefig(f"figures/{stem}.png", dpi=200)
    plt.close(fig)
    print(f"figures/{stem}.pdf")


def fig_effort(results, measure="sell_tendency", stem="fig2_effort",
               compact=False):
    results = only(results, measure)
    if not results:
        return
    models = by_capability({r["model"] for r in results})
    size = (6.3, 2.2) if compact else (4.2 * len(models), 4)
    with compact_rc(compact):
        fig, axes = plt.subplots(1, len(models), figsize=size, sharey=True)
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
                    [abs(c["effect"]) for c in cells], marker="o",
                    lw=1.0 if compact else 1.2, ms=2.5 if compact else 5,
                    label=bias.replace("_", " "))
        used = sorted({EFFORT_ORDER.index(r["effort"]) for r in results})
        ax.set_xticks(used)
        ax.set_xticklabels([EFFORT_ORDER[i] for i in used])
        if not compact:
            ax.set_xlabel("reasoning effort")
        ax.set_title(model.replace("claude-", ""),
                     fontsize=7 if compact else 10)
        if compact:
            for s in ("top", "right"):
                ax.spines[s].set_visible(False)
    axes[0].set_ylabel(SHORT_AXIS[measure] if compact
                       else "absolute " + AXIS[measure])
    if compact:
        # One shared legend under the panels: nine series in a 2in panel is
        # unreadable, and all three panels carry the same nine.
        handles, labels = axes[0].get_legend_handles_labels()
        fig.supxlabel("reasoning effort", fontsize=6.5, y=0.155)
        fig.legend(handles, labels, fontsize=5.5, ncol=5, frameon=False,
                   loc="lower center", bbox_to_anchor=(0.5, 0.0))
        fig.tight_layout(pad=0.45, rect=(0, 0.22, 1, 1))
        fig.savefig(f"figures/{stem}.pdf")
        fig.savefig(f"figures/{stem}.png", dpi=200)
        plt.close(fig)
        print(f"figures/{stem}.pdf")
        return
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
    models = by_capability({r["model"] for r in results})
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
    # Sized for the ACL two-column build.
    fig_forest(r, stem="fig1_forest_acl", compact=True)
    fig_effort(r, stem="fig2_effort_acl", compact=True)
    fig_forest(r, measure="pct_to_sell", stem="fig4_forest_pct_acl",
               compact=True)
    fig_effort(r, measure="pct_to_sell", stem="fig5_effort_pct_acl",
               compact=True)
