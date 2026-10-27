"""Build the paper's figures from data/results.json.

Figures, one pair per dependent variable:
  fig1_forest   effect size per bias with 95% CIs, one panel per model
  fig2_effort   absolute effect against reasoning effort
  fig3_entropy  response entropy per item, the stochasticity evidence
  fig4, fig5    the same forest and effort plots on the continuous
                co-primary measure added in Amendment 3
  fig6          whether dismissing a cue predicts not acting on it
  fig7          wave 2 against wave 1, the regression to the mean

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
from matplotlib.legend_handler import HandlerTuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analysis.directions import DIRECTIONS
from analysis.exploratory import spearman

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


# The reason-text measure lives in its own output file, because it is read
# from the response text rather than from the matched pair means, and it is
# not a registered quantity.
REASONS_JSON = "analysis/reasons_output.json"
REPLICATION_JSON = "analysis/replication_output.json"

# Shape by model rather than colour, so the panel survives a greyscale
# print the way the rest of the paper's figures do.
MODEL_MARKER = {"haiku": "o", "sonnet": "s", "opus": "^"}


def fig_dissociation(stem="fig6_dissociation", compact=False):
    """Does dismissing the cue predict not acting on it? One panel per measure.

    The x axis is the share of a cell's one-sentence reasons that name the
    manipulated cue and dismiss it. The y axis is the size of that cell's
    effect, unsigned, because the claim is about magnitude. If saying the
    right thing meant doing the right thing, the cloud would run downhill.

    Only the six families the advisor ever refers to appear. Three of the nine
    manipulate how the decision is framed rather than what is in it, and a
    rejection rate of essentially zero for them is a fact about the probe, not
    about the model, so plotting it would put thirty points on the left wall
    for the wrong reason.

    A filled marker is a cell whose interval clears zero; a ringed one also
    survives Holm. The ringed points are the paper's strongest claims, and
    where they sit is the figure's argument: two of the four are at the far
    right, in cells that dismiss the cue in over nine tenths of their reasons.
    """
    if not os.path.exists(REASONS_JSON):
        print(f"{REASONS_JSON} missing, skipping {stem}")
        return
    with open(REASONS_JSON) as f:
        cells = json.load(f)["dissociation"]["cells"]
    measures = [m for m in ("sell_tendency", "pct_to_sell")
                if any(c["measure"] == m for c in cells)]
    if not measures:
        return

    size = (6.3, 2.5) if compact else (11, 4.6)
    with compact_rc(compact):
        fig, axes = plt.subplots(1, len(measures), figsize=size)
    if len(measures) == 1:
        axes = [axes]
    for ax, measure in zip(axes, measures):
        sub = [c for c in cells if c["measure"] == measure]
        for model, marker in MODEL_MARKER.items():
            mine = [c for c in sub if c["model"] == model]
            if not mine:
                continue
            for c in mine:
                y = abs(c["effect"])
                face = "black" if c["significant"] else "none"
                ax.plot(c["reject_rate"], y, marker=marker, color="black",
                        markerfacecolor=face,
                        markersize=(4 if compact else 7),
                        linestyle="none")
                if c["significant_holm"]:
                    ax.plot(c["reject_rate"], y, marker="o", color="black",
                            markerfacecolor="none",
                            markersize=(9 if compact else 15),
                            markeredgewidth=1.2, linestyle="none")
        rho = spearman([c["reject_rate"] for c in sub],
                       [abs(c["effect"]) for c in sub])
        ax.set_title(f"{measure.replace('_', ' ')}"
                     f"   rank correlation {rho:+.3f}, "
                     f"{len(sub)} cells",
                     fontsize=7 if compact else 11)
        ax.set_xlabel("share of reasons that dismiss the cue")
        ax.set_ylabel(SHORT_AXIS[measure])
        ax.set_xlim(-0.05, 1.05)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
    # Shape carries the model, fill carries significance, and the ring
    # carries Holm. The fill and ring keys use a diamond, which is not one of
    # the model shapes, so a legend entry cannot be read as a fourth model.
    ms = 4 if compact else 7
    handles = [plt.Line2D([], [], marker=m, color="black", linestyle="none",
                          markerfacecolor="black", markersize=ms, label=k)
               for k, m in MODEL_MARKER.items()]
    handles += [
        plt.Line2D([], [], marker="D", color="black", linestyle="none",
                   markerfacecolor="none", markersize=ms),
    ]
    # The ring key is drawn rather than described: two markers at one point,
    # which is what the plot itself does for a Holm survivor.
    ringed = (plt.Line2D([], [], marker="D", color="black", linestyle="none",
                         markerfacecolor="black", markersize=ms),
              plt.Line2D([], [], marker="o", color="black", linestyle="none",
                         markerfacecolor="none", markersize=ms * 1.9,
                         markeredgewidth=1.2))
    handles.append(ringed)
    labels = list(MODEL_MARKER) + ["hollow: interval spans zero",
                                   "ringed: survives Holm"]
    axes[0].legend(handles, labels, fontsize=5.5 if compact else 8,
                   loc="upper left", frameon=False,
                   handletextpad=0.9, labelspacing=0.5, handlelength=1.8,
                   handler_map={tuple: HandlerTuple(ndivide=None)})
    if not compact:
        fig.suptitle("Saying the cue is irrelevant and not acting on it are "
                     "different things", fontsize=12)
    fig.tight_layout(pad=0.45 if compact else 1.08)
    fig.savefig(f"figures/{stem}.pdf")
    fig.savefig(f"figures/{stem}.png", dpi=200)
    plt.close(fig)
    print(f"figures/{stem}.pdf")


def fig_replication(stem="fig7_replication", compact=False):
    """Wave 2 against wave 1, one point per cell. Galton's plot.

    The whole regression-to-the-mean argument is one picture. Each point is a
    cell the two waves share, its wave 1 effect on the x axis and its wave 2
    effect on the y. If a wave 1 estimate were the truth, the cloud would sit
    on the dashed identity line. If the finding were noise, the cloud would be
    round. It is neither: it tilts, which is the replication, and it tilts at
    about half the identity slope, which is the shrinkage.

    Both axes are forced to the same symmetric range, because an identity
    line that is not drawn at forty five degrees is a lie about how far the
    points fall from it. That is also why the fitted line is drawn over the
    observed x range only and not extrapolated to the frame.

    The slope and its interval come from replication.py rather than being
    refitted here, so the number in the panel is the number in the appendix.
    """
    if not os.path.exists(REPLICATION_JSON):
        print(f"{REPLICATION_JSON} missing, skipping {stem}")
        return
    with open(REPLICATION_JSON) as f:
        blob = json.load(f)
    cells, rtm = blob["agreement"], blob["regression_to_mean"]
    measures = [m for m in ("sell_tendency", "pct_to_sell")
                if any(c["measure"] == m for c in cells) and m in rtm]
    if not measures:
        return

    size = (6.3, 3.0) if compact else (11, 5.0)
    with compact_rc(compact):
        fig, axes = plt.subplots(1, len(measures), figsize=size)
    if len(measures) == 1:
        axes = [axes]
    for ax, measure in zip(axes, measures):
        sub = [c for c in cells if c["measure"] == measure]
        xs = [c["w1_effect"] for c in sub]
        ys = [c["w2_effect"] for c in sub]
        # One range for both axes, so the identity line is drawn at forty
        # five degrees, but not forced symmetric about zero: the effects are
        # mostly positive and a symmetric frame would spend half the panel on
        # an empty quadrant.
        pad = (max(xs + ys) - min(xs + ys)) * 0.06
        lo, hi = min(xs + ys) - pad, max(xs + ys) + pad
        ax.plot([lo, hi], [lo, hi], linestyle="--", color="0.55",
                linewidth=0.9, zorder=1)
        ax.axhline(0, color="0.8", linewidth=0.7, zorder=0)
        ax.axvline(0, color="0.8", linewidth=0.7, zorder=0)

        stat = rtm[measure]
        b, a = stat["slope"], stat["intercept"]
        x0, x1 = min(xs), max(xs)
        ax.plot([x0, x1], [a + b * x0, a + b * x1], color="black",
                linewidth=1.3, zorder=2)

        # The top quartile by wave 1 magnitude is where the paper says all of
        # the shrinkage sits, so it is marked rather than described: the band
        # outside the dotted verticals is that quartile.
        cut = sorted((abs(v) for v in xs), reverse=True)[stat["top_quartile_n"]
                                                         - 1]
        for v in (-cut, cut):
            ax.axvline(v, color="0.75", linestyle=":", linewidth=0.8,
                       zorder=0)

        for model, marker in MODEL_MARKER.items():
            mine = [c for c in sub if model in c["model"]]
            for c in mine:
                ax.plot(c["w1_effect"], c["w2_effect"], marker=marker,
                        color="black",
                        markerfacecolor=("black" if c["w2_significant"]
                                         else "none"),
                        markersize=(3.6 if compact else 6.5),
                        markeredgewidth=0.9, linestyle="none", zorder=3)

        ax.set_title(f"{measure.replace('_', ' ')}"
                     f"   slope {b:+.3f} "
                     f"[{stat['slope_ci'][0]:+.3f}, "
                     f"{stat['slope_ci'][1]:+.3f}], "
                     f"{stat['n_cells']} cells",
                     fontsize=7 if compact else 11)
        ax.set_xlabel("wave 1 effect")
        ax.set_ylabel("wave 2 effect")
        ax.set_xlim(lo, hi)
        ax.set_ylim(lo, hi)
        ax.set_aspect("equal", adjustable="box")
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)

    ms = 3.6 if compact else 6.5
    handles = [plt.Line2D([], [], marker=m, color="black", linestyle="none",
                          markerfacecolor="black", markersize=ms, label=k)
               for k, m in MODEL_MARKER.items()
               if any(k in c["model"] for c in cells)]
    handles += [
        plt.Line2D([], [], marker="D", color="black", linestyle="none",
                   markerfacecolor="none", markersize=ms),
        plt.Line2D([], [], linestyle="--", color="0.55", linewidth=0.9),
        plt.Line2D([], [], linestyle="-", color="black", linewidth=1.3),
    ]
    labels = [k for k in MODEL_MARKER
              if any(k in c["model"] for c in cells)] + [
        "hollow: wave 2 interval spans zero",
        "dashed: perfect replication",
        "solid: fitted",
    ]
    axes[0].legend(handles, labels, fontsize=5.5 if compact else 8,
                   loc="upper left", frameon=False,
                   handletextpad=0.9, labelspacing=0.5, handlelength=1.8)
    if not compact:
        fig.suptitle("Half of a wave 1 effect was the item draw", fontsize=12)
    fig.tight_layout(pad=0.45 if compact else 1.08)
    fig.savefig(f"figures/{stem}.pdf")
    fig.savefig(f"figures/{stem}.png", dpi=200)
    plt.close(fig)
    print(f"figures/{stem}.pdf")


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
    fig_dissociation()
    fig_dissociation(stem="fig6_dissociation_acl", compact=True)
    fig_replication()
    fig_replication(stem="fig7_replication_acl", compact=True)
