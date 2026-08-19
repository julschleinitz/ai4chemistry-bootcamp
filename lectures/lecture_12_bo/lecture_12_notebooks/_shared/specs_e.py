"""Figure 21 - which knob actually matters.

All numbers transcribed verbatim from Table 3 of:
  B. Rankovic, R.-R. Griffiths, H. B. Moss, P. Schwaller,
  "Bayesian optimisation for additive screening and yield improvements -
  beyond one-hot encoding", Digital Discovery 2024, 3, 654-666.
  DOI 10.1039/D3DD00096F   (open access)

Their grid search: 720 additives, 4 reaction plates, 100 BO iterations from
10 initial points, 20 seeds per configuration. Table 3 aggregates over the
grid, one row per level of each knob.
"""

FIG21 = ("fig_21_which_knob_matters.ipynb",
         "Figure 21 - the acquisition function is the smallest knob you turn",
         "Rankovic et al. ran a full grid search over four Bayesian-optimisation "
         "design choices - kernel, initialisation, acquisition function and "
         "reaction representation - on the same 720-additive screen, 20 seeds "
         "each. Table 3 of that paper reports the marginal effect of three of "
         "them. Plotted side by side, the acquisition function moves the result "
         "least.\n\n"
         "The representation is the fourth knob and is NOT in Table 3 - it is "
         "their Figs 3 and 4, where one-hot encoding finishes *below random "
         "search* while drfp reaches the optimum. That is a far bigger swing "
         "than anything here.",
         [("## Table 3, transcribed",
           r'''
# (level, top-1 %, top-1 sd, top-5 %, top-5 sd)
TAB3 = {
 "kernel":        [("Matérn", 0.20, 0.40, 0.19, 0.31),
                   ("Tanimoto",     0.08, 0.28, 0.13, 0.24),
                   ("Linear",       0.02, 0.14, 0.09, 0.15)],
 "initialisation":[("clusters",     0.14, 0.34, 0.18, 0.28),
                   ("random",       0.10, 0.30, 0.13, 0.23),
                   ("maxmin",       0.07, 0.26, 0.11, 0.21)],
 "acquisition":   [("UCB",          0.11, 0.31, 0.15, 0.25),
                   ("EI",           0.09, 0.29, 0.12, 0.23)],
}
for k, rows in TAB3.items():
    v1 = [r[1] for r in rows]; v5 = [r[3] for r in rows]
    print(f"{k:16s} top-1 spread {max(v1)-min(v1):.2f}   "
          f"top-5 spread {max(v5)-min(v5):.2f}   "
          f"best/worst ratio {max(v1)/max(min(v1),1e-9):.0f}x")
'''),
          (None, r'''
fig, axes = plt.subplots(1, 3, figsize=(style.FIG_W_FULL, 3.5),
                         gridspec_kw=dict(wspace=0.30,
                                          width_ratios=[1, 1, 0.72]))
cols = {"kernel": style.RED, "initialisation": style.GOLD,
        "acquisition": style.TEAL}
for ax, (knob, rows) in zip(axes, TAB3.items()):
    lab = [r[0] for r in rows]
    v5  = [r[3] for r in rows]
    sd5 = [r[4] for r in rows]
    y = range(len(rows))[::-1]
    ax.barh(list(y), v5, color=cols[knob], height=0.55, zorder=3)
    ax.errorbar(v5, list(y), xerr=sd5, fmt="none", ecolor=style.INK,
                elinewidth=1.0, capsize=3, alpha=0.5, zorder=4)
    for yy, v in zip(y, v5):
        style.text(ax, v + 0.012, yy, f"{v:.2f}", va="center", fontsize=9.5,
                   color=style.INK)
    ax.set_yticks(list(y)); ax.set_yticklabels(lab, fontsize=10.5)
    ax.set_xlim(0, 0.50)
    ax.set_xticks([0, 0.1, 0.2, 0.3])
    spread = max(v5) - min(v5)
    style.title(ax, f"{knob}   —   spread {spread:.2f}", loc="left",
                fontsize=11.0)
axes[0].set_xlabel("fraction of the top-5 additives found in 100 experiments",
                   fontsize=9.5)
style.text(axes[2], 0.5, -0.34,
           "the knob everyone argues about moves the answer least",
           transform=axes[2].transAxes, ha="center", fontsize=10.5,
           color=style.TEAL, fontweight="bold")
style.save(fig, "fig_21_which_knob_matters", OUT)
''')])

ALL = [FIG21]
