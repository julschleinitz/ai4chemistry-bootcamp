#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Builds lecture_04-intro-deep-learning.pptx.

Every figure is a NATIVE PowerPoint object — real charts, shapes and tables — so
each one can be clicked and edited. Numbers come from figure_data.json, which is
written by generate_figures.ipynb.

    python build_deck.py
"""
import json, sys
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR

from deck_lib import *          # slide furniture, palette, text/bullets helpers
import deck_lib as L
from nativefigs import *        # the figures themselves

try:
    D = json.load(open("figure_data.json"))
except FileNotFoundError:
    sys.exit("figure_data.json not found — run generate_figures.ipynb first.")

PN = D["parity_net"]
XOR = D["xor_2d"]
PC = D["param_count"]
SEEDS = D["parity_seeds"]
OC = D["overfit_curves"]
seed_lo, seed_hi = min(SEEDS["acc"]), max(SEEDS["acc"])

# =====================================================================
# TITLE
# =====================================================================
s = new_slide("Introduction to Deep Learning for Chemistry")
centered(s, "From linear models to neural networks — and where the physics goes",
         1.32, size=19, color=GRAY, italic=True)
fig_timeline(s, D, x=0.55, y=1.80, w=12.25, h=4.0)
text(s, "J. Schleinitz  ·  Monday, August 10, 2026  ·  RSC 275, Caltech",
     0.54, 6.57, 10.0, 0.4, size=12, color=INK)

# =====================================================================
# PLAN
# =====================================================================
s = new_slide("Plan")
bullets(s, [
    "**Why deep learning?** where it changed chemistry, and how it got here",
    "**A reminder:** linear models, and where they break",
    "**Neural networks:** the perceptron, a worked molecular example, and how training works",
    "**Model capacity:** counting parameters, overfitting, regularization",
    "**Architectures:** convolution, pooling, message passing",
    "**Physics-infused networks:** putting chemistry into the model",
    "**When to use deep learning — and when not to**",
], 1.85, 1.42, 10.2, size=17.5, gap=0.20, lh=0.29)

# =====================================================================
# 1 — WHY DEEP LEARNING
# =====================================================================
section_slide(1, "Why deep learning?", [
    "Where it has already changed chemistry",
    "How it got here — and why now",
])

s = new_slide("Deep learning is a subset of machine learning")
bullets(s, [
    "**Machine learning:** fit a model's parameters to data instead of programming rules by hand.",
    "**Deep learning:** use many-layer neural networks that learn their own internal "
    "representation of the data — no hand-crafted features required.",
    "The “deep” simply means several layers stacked, each transforming the output of the one before it.",
], 0.75, 1.5, 6.5, size=15.5, gap=0.24)
fig_ai_ml_dl(s, cx=10.15, cy=3.95)
key_box(s, "**A neural network is a stack of linear algebra operations, "
           "glued together by nonlinear functions.**")

s = new_slide("Deep learning has already changed chemistry")
table(s, ["Breakthrough", "What it did", "Why it mattered"],
      [["AlphaFold2\n(2021)", "predicted protein structures to ~1 Å\nbackbone accuracy",
        "~200M structures released — a\n50-year-old problem largely solved"],
       ["MPNNs for quantum\nchemistry (2017)", "learned DFT-level molecular properties\nfrom the molecular graph",
        "molecular property prediction at a\nfraction of the DFT cost"],
       ["GNoME\n(2023)", "screened candidate crystals, DFT-verified\nonly the promising ones",
        "380,000+ new stable materials;\n736 experimentally realised"],
       ["Retrosynthesis &\nreaction prediction", "learned reaction rules from millions of\nliterature reactions",
        "route planning that competes with\nexpert chemists"]],
      x=0.6, y=1.45, col_w=[2.7, 4.6, 4.8], size=12.5, row_h=4.5)
text(s, "Jumper et al. Nature 596, 583 (2021)  ·  Gilmer et al. ICML (2017)  ·  "
        "Merchant et al. Nature 624, 80 (2023)  ·  Segler et al. Nature 555, 604 (2018)",
     0.6, 6.15, 12.1, 0.4, size=10.5, color=GRAY, italic=True)

s = new_slide("2024: two Nobel Prizes for neural networks")
card(s, 0.8, 1.5, 5.5, 3.3, fill=CARD)
text(s, "Physics 2024", 1.1, 1.72, 4.9, 0.4, size=20, color=TEAL, bold=True)
text(s, "John Hopfield  ·  Geoffrey Hinton", 1.1, 2.20, 4.9, 0.4, size=14, color=INK)
text(s, "“for foundational discoveries and inventions that enable machine learning "
        "with artificial neural networks”", 1.1, 2.62, 4.9, 1.1, size=13, color=GRAY,
     italic=True)
text(s, "The methods came from statistical physics — Hopfield networks and the "
        "Boltzmann machine.", 1.1, 3.75, 4.9, 0.9, size=13, color=INK)
card(s, 7.0, 1.5, 5.5, 3.3, fill=PEACH)
text(s, "Chemistry 2024", 7.3, 1.72, 4.9, 0.4, size=20, color=ORANGE_D, bold=True)
text(s, "David Baker  ·  Demis Hassabis  ·  John Jumper", 7.3, 2.20, 4.9, 0.4,
     size=14, color=INK)
text(s, "“for computational protein design” and “for protein structure prediction”",
     7.3, 2.62, 4.9, 0.8, size=13, color=GRAY, italic=True)
text(s, "AlphaFold2 predicted structures for essentially every protein known to science.",
     7.3, 3.60, 4.9, 1.0, size=13, color=INK)
key_box(s, "**The tools of this lecture are now mainstream chemistry — "
           "and they were recognised in both physics and chemistry in the same year.**",
        y=5.15)

s = new_slide("How did we get here?")
bullets(s, [
    "**1958 — the perceptron.** Rosenblatt builds a trainable single neuron. The idea we start from today.",
    "**1986 — backpropagation.** An efficient way to compute how every weight affects the loss. "
    "Networks with hidden layers become trainable.",
    "**Then two “AI winters”.** The mathematics was largely in place; the data and the compute were not.",
    "**2012 — AlexNet.** 15.3% vs 26.2% top-5 error on ImageNet. Three enabling ingredients: "
    "**GPUs**, a **large labelled dataset**, and practical tricks (**ReLU**, **dropout**).",
    "**2017 onwards — chemistry adopts it.** Molecules are graphs, not images, so the field "
    "builds its own architectures.",
], 0.8, 1.45, 11.8, size=15.5, gap=0.20, lh=0.27)
key_box(s, "**What changed was not the idea of a neural network — it was data, hardware, "
           "and software.**")

# =====================================================================
# 2 — LINEAR MODELS
# =====================================================================
section_slide(2, "A reminder: linear models", [
    "What “training the weights” actually means",
    "Where a linear model breaks down",
])

s = new_slide("The linear model, and how its weights are trained")
fig_linear_fit(s, D, y=1.52, h=3.05)
e = bullets(s, [
    "**The model:** ŷ = w·x + b — one weight per feature, plus a bias.",
    "**The loss:** mean squared error over the dataset. It measures how wrong we currently are.",
    "**Training:** pick w and b to make the loss as small as possible. For a linear model the "
    "loss is a **single smooth bowl** — one minimum, and we can even solve for it exactly.",
], 0.8, 5.10, 11.9, size=14, gap=0.08, lh=0.24)

s = new_slide("Where the linear model breaks")
fig_xor(s, D, y=1.48, h=3.05)
e = bullets(s, [
    f"Two classes in opposite corners — the classic **XOR** pattern. The best possible "
    f"straight line gets **{XOR['acc_linear']:.0f}%**: no better than a coin flip.",
    f"Add **one hidden layer** and the same data is separated perfectly "
    f"(**{XOR['acc_mlp']:.0f}%**). The boundary is now curved.",
], 0.8, 5.22, 11.9, size=14, gap=0.08, lh=0.24)
key_box(s, "**The problem is the model class, not the optimizer.**")

# =====================================================================
# 3 — NEURAL NETWORKS
# =====================================================================
section_slide(3, "Neural networks", [
    "(a) the perceptron, component by component",
    "(b) a worked molecular example",
    "(c) how learning actually happens",
])


def perceptron_slide(stage, title):
    s = new_slide(title)
    x_in, x_sum, x_act, x_out = 2.35, 6.05, 8.35, 10.9
    ys = [2.15, 2.95, 3.75]
    y_bias, y_mid = 4.75, 2.95
    labels = ["x₁", "x₂", "x₃"]
    wlabels = ["w₁", "w₂", "w₃"]
    sub = ["bond length", "partial charge", "Δ electronegativity"]
    for i, (lab, sb) in enumerate(zip(labels, sub)):
        node(s, x_in, ys[i], 0.62, fill=WHITE, edge=TEAL, label=lab, size=15)
        text(s, sb, x_in - 2.45, ys[i] - 0.16, 2.05, 0.35, size=12, color=GRAY,
             align=PP_ALIGN.RIGHT)
    text(s, "inputs", x_in - 0.6, 1.45, 1.2, 0.3, size=12.5, color=GRAY,
         align=PP_ALIGN.CENTER, bold=True)
    if stage >= 2:
        for i in range(3):
            line(s, x_in + 0.31, ys[i], x_sum - 0.42, y_mid, color=TEAL, w=2.0, arrow=True)
            mx = x_in + (x_sum - x_in) * 0.44
            my = ys[i] + (y_mid - ys[i]) * 0.44
            text(s, wlabels[i], mx - 0.28, my - 0.34, 0.62, 0.3, size=14,
                 color=ORANGE_D, bold=True, align=PP_ALIGN.CENTER)
    if stage >= 3:
        node(s, x_in, y_bias, 0.62, fill=PEACH, edge=ORANGE, label="1", size=14)
        text(s, "bias input", x_in - 2.45, y_bias - 0.16, 2.05, 0.35, size=12,
             color=GRAY, align=PP_ALIGN.RIGHT)
        line(s, x_in + 0.31, y_bias, x_sum - 0.42, y_mid, color=ORANGE, w=2.0, arrow=True)
        text(s, "b", x_in + 1.65, y_bias - 0.52, 0.5, 0.3, size=14, color=ORANGE_D,
             bold=True, align=PP_ALIGN.CENTER)
        node(s, x_sum, y_mid, 0.85, fill=TEAL, edge=TEAL, label="Σ", size=24,
             label_color=WHITE)
        text(s, "weighted sum", x_sum - 1.0, 1.45, 2.0, 0.3, size=12.5, color=GRAY,
             align=PP_ALIGN.CENTER, bold=True)
        text(s, "z = w₁x₁ + w₂x₂ + w₃x₃ + b", x_sum - 1.9, 5.05, 3.8, 0.4, size=15,
             color=TEAL, bold=True, align=PP_ALIGN.CENTER)
    if stage >= 4:
        line(s, x_sum + 0.43, y_mid, x_act - 0.06, y_mid, color=GRAY, w=1.6, arrow=True)
        rbox(s, x_act, y_mid - 0.62, 1.55, 1.24, fill=WHITE, edge=ORANGE, label="")
        line(s, x_act + 0.22, y_mid + 0.22, x_act + 1.33, y_mid + 0.22, color=LGRAY, w=1.0)
        line(s, x_act + 0.22, y_mid + 0.22, x_act + 0.22, y_mid - 0.48, color=LGRAY, w=1.0)
        line(s, x_act + 0.25, y_mid + 0.18, x_act + 0.74, y_mid + 0.18, color=ORANGE, w=2.6)
        line(s, x_act + 0.74, y_mid + 0.18, x_act + 1.28, y_mid - 0.44, color=ORANGE, w=2.6)
        text(s, "σ(z)", x_act, y_mid + 0.28, 1.55, 0.28, size=12, color=ORANGE_D,
             bold=True, align=PP_ALIGN.CENTER)
        text(s, "activation", x_act - 0.2, 1.45, 2.0, 0.3, size=12.5, color=GRAY,
             align=PP_ALIGN.CENTER, bold=True)
        line(s, x_act + 1.6, y_mid, x_out - 0.36, y_mid, color=GRAY, w=1.6, arrow=True)
        node(s, x_out, y_mid, 0.70, fill=ORANGE, edge=ORANGE_D, label="a", size=17,
             label_color=WHITE)
        text(s, "output", x_out - 0.6, 1.45, 1.2, 0.3, size=12.5, color=GRAY,
             align=PP_ALIGN.CENTER, bold=True)
        text(s, "a = σ(z)", x_out - 0.85, 3.55, 1.7, 0.35, size=14, color=ORANGE_D,
             bold=True, align=PP_ALIGN.CENTER)
    key_box(s, {
        1: "Three numbers describing a molecule — this is all the neuron ever sees.",
        2: "**Each input gets its own weight.** These are the numbers that get learned.",
        3: "**The bias b shifts the threshold** — it lets the neuron fire even when every "
           "input is zero.",
        4: "**Without a nonlinear σ, stacking layers collapses back to a single linear model.**",
    }[stage], y=6.15)
    return s


perceptron_slide(1, "The perceptron: start with the inputs")
perceptron_slide(2, "The perceptron: add the weights")
perceptron_slide(3, "The perceptron: add the bias and the sum")
perceptron_slide(4, "The perceptron: add the activation function")

s = new_slide("Choosing the activation function")
fig_activations(s, D, y=1.72, h=2.70)
bullets(s, [
    "**ReLU** is the default: cheap, and it lets a unit switch fully off.",
    "**tanh** and **sigmoid** saturate at both ends — useful for outputs, but they slow "
    "deep networks down.",
    "The only hard requirement is that σ be **nonlinear** — otherwise the whole network "
    "reduces to ŷ = w·x + b.",
], 0.8, 4.95, 11.9, size=14.5, gap=0.10, lh=0.25)

# --- (b) the molecular task
s = new_slide("A concrete task: is the electron count odd or even?")
b = fig_parity_table(s, D, x=2.15, y=1.32, w=9.0)
e = bullets(s, [
    "Inputs: the counts **nH, nC, nN, nO** — four numbers per molecule.",
    "Target: is the total electron count **odd** or **even**?  "
    "(odd ⇒ an unpaired electron ⇒ a radical)",
    "Because 6 and 8 are even, the answer depends only on **(nH + nN) mod 2** — "
    "the same XOR structure that just defeated our linear model.",
], 0.8, b + 0.06, 11.9, size=14, gap=0.08, lh=0.24)
key_box(s, f"**A linear model scores {PN['acc_linear']:.0f}% here. Chance is 50%.**")

s = new_slide("The network: 4 inputs → 5 hidden units → 1 output")
fig_net_init(s, D, x=0.50, y=1.75, w=7.0, h=3.15)
card(s, 8.10, 1.55, 4.6, 3.45, fill=CARD)
text(s, "Reading the picture", 8.40, 1.72, 4.1, 0.3, size=14, color=TEAL, bold=True)
bullets(s, ["**teal** line = positive weight",
            "**orange** line = negative weight",
            "**thickness** = magnitude of the weight"],
        8.40, 2.16, 4.1, size=13, gap=0.10, lh=0.24)
text(s, "Weights start as small random numbers, so the network's very first predictions "
        "are no better than guessing.",
     8.40, 3.76, 4.1, 1.1, size=13, color=INK, line_spacing=1.2)
bullets(s, [
    "Every hidden unit computes its own weighted sum of the four inputs, then applies tanh.",
    "The output unit combines the five hidden values into a single probability of “odd”.",
    f"Accuracy before any training: **{PN['acc_init']:.1f}%** — exactly chance, as expected.",
], 0.8, 5.22, 11.9, size=14.5, gap=0.10, lh=0.25)

s = new_slide("What training does to the weights")
fig_net_before_after(s, D, y=1.92, h=2.95)
bullets(s, [
    f"Trained on **{PN['n_train']:,}** molecules (up to {PN['maxc']} of each element), "
    f"tested on **{PN['n_test']}** unseen ones.",
    f"Test accuracy climbs from **{PN['acc_init']:.1f}% → {PN['acc_test']:.1f}%**, "
    f"while the linear model stays at **{PN['acc_linear']:.1f}%**.",
    "Notice the loss curve: a long **plateau**, then a sudden drop. The network sits stuck "
    "before it finds the parity rule.",
], 0.8, 5.15, 11.9, size=14, gap=0.08, lh=0.24)

# --- (c) learning
s = new_slide("How learning works: follow the gradient downhill")
fig_loss_contour(s, D, x=0.75, y=1.45, w=6.3, h=3.35)
card(s, 7.70, 1.70, 5.0, 2.05, fill=PEACH)
text(s, "w  ←  w  −  η · ∂L/∂w", 7.80, 2.06, 4.8, 0.5, size=24, color=TEAL,
     bold=True, align=PP_ALIGN.CENTER)
text(s, "read it aloud: nudge each weight a little way\ndownhill, then do it again",
     7.90, 2.86, 4.6, 0.7, size=12.5, color=INK, italic=True, align=PP_ALIGN.CENTER)
bullets(s, [
    "**∂L/∂w** — the gradient — is just “how much does the loss change if I nudge this "
    "weight?”. Backpropagation computes it for every weight at once.",
    "Take a small step in the **opposite** direction, and repeat. That is the whole algorithm.",
], 7.75, 4.05, 4.95, size=13, gap=0.10, lh=0.24)
key_box(s, "**Only two weights can be drawn. The real network has 31 axes — "
           "and a modern model has billions.**")

s = new_slide("Gradient descent is not guaranteed to work")
b = fig_seeds(s, D, x=0.80, y=1.68, w=7.1, h=3.35)
card(s, 8.45, 1.50, 4.3, 4.55, fill=PEACH)
text(s, "Difficulties", 8.72, 1.66, 3.8, 0.35, size=16, color=ORANGE_D, bold=True)
bullets(s, [
    "**Local minima & plateaus** — the run can stall somewhere mediocre.",
    f"**Initialization matters** — identical architecture, identical data, different "
    f"random start: {seed_lo:.0f}% to {seed_hi:.0f}%.",
    "**Vanishing gradients** — with saturating activations the signal fades in deep stacks.",
    "**No convexity** — unlike the linear model, there is no single guaranteed answer.",
], 8.72, 2.14, 3.85, size=12.5, gap=0.16, lh=0.24)
text(s, "In practice: try several random seeds, and never trust a single training run.",
     0.80, b + 0.50, 7.2, 0.6, size=14, color=INK, italic=True, align=PP_ALIGN.CENTER)

s = new_slide("The learning rate η sets the step size")
fig_learning_rate(s, D, y=1.80, h=2.80)
bullets(s, [
    "**Too small:** the loss creeps down and you waste your compute budget.",
    "**Too large:** each step overshoots the valley and the loss diverges.",
    "In practice η is **scheduled** — warm up, then decay — and adaptive optimizers like "
    "**Adam** tune an effective step size per weight.",
], 0.8, 5.15, 11.9, size=14.5, gap=0.10, lh=0.25)

# =====================================================================
# 4 — CAPACITY
# =====================================================================
section_slide(4, "Capacity and its consequences", [
    "(a) counting your parameters",
    "(b) overfitting",
    "(c) regularization: early stopping, weight decay, dropout",
])

s = new_slide("How many parameters does my model have?")
b = fig_param_count(s, D, y=1.42, h=2.85)
e = bullets(s, [
    "A dense layer from **D** inputs to **F** outputs carries **D × F** weights plus **F** biases.",
    f"Our little network: (4×5 + 5) + (5×1 + 1) = **{PC['total']} parameters** — trained on "
    f"~{PN['n_train']:,} molecules, a comfortable ratio.",
    "For scale: **AlexNet** had ~60 million parameters; today's largest have billions.",
], 0.8, max(b, 4.55) + 0.08, 11.9, size=13.5, gap=0.06, lh=0.23)
key_box(s, "**Rule of thumb: if parameters ≫ data points, expect trouble.**")

s = new_slide("Overfitting: fitting the noise instead of the chemistry")
fig_overfit_capacity(s, D, y=1.78, h=2.85)
bullets(s, [
    "**Underfitting** (left): the model is too rigid to capture the trend.",
    "**Overfitting** (right): the model passes through every training point and predicts "
    "nonsense in between.",
    "The training error keeps falling in both cases — so training error alone cannot tell "
    "you which situation you are in.",
], 0.8, 5.15, 11.9, size=14.5, gap=0.10, lh=0.25)

s = new_slide("How to spot overfitting: watch a held-out set")
b = fig_overfit_curves(s, D, x=1.30, y=1.55, w=6.5, h=3.05)
e = bullets(s, [
    "Split the data: **train** to fit, **validation** to make decisions, **test** touched "
    "once at the very end.",
    f"Training loss falls forever. **Validation loss turns around** at epoch "
    f"**{OC['best_epoch']}** — that is where the model stops learning chemistry and starts "
    f"memorizing.",
    "The gap between the two curves is the overfitting.",
], 0.8, b + 0.22, 11.9, size=14, gap=0.08, lh=0.24)
key_box(s, "**Never tune on your test set — the moment you do, it stops being a test set.**")

s = new_slide("Three ways to fight overfitting")
fig_regularization(s, D, y=1.92, h=2.50)
bullets(s, [
    "**Early stopping** — keep the weights from the validation minimum. Free, and always "
    "worth doing.",
    "**Weight decay (L2)** — add λ·Σwᵢ² to the loss so large weights must justify themselves.",
    "**Dropout** — randomly silence a fraction of units at each step, so the network cannot "
    "depend on any single pathway. One of the tricks that made AlexNet work.",
], 0.7, 5.15, 12.0, size=13.5, gap=0.07, lh=0.23)
text(s, "More data — and data augmentation — are also regularizers, usually the most "
        "effective ones.", 0.7, BODY_BOT - 0.34, 12.0, 0.35, size=12.5, color=GRAY,
     italic=True)

# =====================================================================
# 5 — ARCHITECTURES
# =====================================================================
section_slide(5, "Architectures: matching the model to the data", [
    "Convolution and pooling",
    "Message passing",
    "The breakthroughs each one enabled",
])

s = new_slide("An architecture is a set of built-in assumptions")
e = bullets(s, [
    "A **dense** layer assumes nothing: every input touches every output. Flexible, but it "
    "must learn every regularity from scratch.",
    "If you already know something about your data's structure, **build it in** — the network "
    "then spends its capacity on chemistry rather than on rediscovering geometry.",
], 0.8, 1.42, 11.8, size=15, gap=0.14, lh=0.26)
table(s, ["Structure in the data", "Architecture", "Chemistry example"],
      [["values on a regular grid", "convolution + pooling", "spectra (IR, NMR, XRD), microscopy images"],
       ["an ordered sequence", "RNN / Transformer", "SMILES strings, reaction procedures"],
       ["atoms and bonds", "message passing (GNN)", "molecules, crystals, catalyst surfaces"],
       ["nothing in particular", "dense layers", "a handful of computed descriptors"]],
      x=0.8, y=2.85, col_w=[3.7, 3.5, 4.5], size=13, row_h=2.5)
key_box(s, "**Next lecture is devoted to the third row — graph neural networks.**", y=5.75)

s = new_slide("Convolution and pooling")
fig_conv_pool(s, D, y=1.42, h=3.0)
fig_pooling(s, D, x=7.75, y=1.80, cell=0.50)
bullets(s, [
    "**Convolution:** one small filter is slid across the whole input, reusing the same "
    "weights everywhere. That weight-sharing is what makes it translation-invariant.",
    "**Pooling:** summarise each neighbourhood by its strongest response — shrinking the map "
    "and buying tolerance to small shifts.",
    "**Breakthrough:** AlexNet (Krizhevsky, Sutskever & Hinton, 2012) — 15.3% vs 26.2% error "
    "on ImageNet, and the start of the modern era.",
], 0.7, 4.98, 12.0, size=13.5, gap=0.07, lh=0.23)

s = new_slide("Message passing: convolution for graphs")
fig_message_passing(s, D, y=1.45, h=3.05)
bullets(s, [
    "Each round, every atom collects a **message** from each of its neighbours and updates "
    "its own representation. After k rounds an atom knows about its k-bond neighbourhood.",
    "This respects what a molecule actually is: variable in size, with no natural atom "
    "ordering — relabel the atoms and the prediction is unchanged.",
    "**Breakthrough:** Gilmer et al. (2017) unified these models as MPNNs and reached "
    "DFT-level accuracy on QM9 molecular properties.",
], 0.7, 4.90, 12.0, size=13.5, gap=0.07, lh=0.23)

# =====================================================================
# 6 — PHYSICS-INFUSED
# =====================================================================
section_slide(6, "Physics-infused neural networks", [
    "Symmetry: invariance and equivariance",
    "Physics in the loss: PINNs",
    "Why this is the highest-leverage choice in chemistry",
])

s = new_slide("Chemistry comes with symmetries — use them")
b = fig_equivariance(s, D, y=1.45, h=2.75)
e = bullets(s, [
    "**Invariant** — rotate or translate a molecule and its **energy** does not change.",
    "**Equivariant** — rotate a molecule and its **force vectors rotate with it**.",
    "A plain network fed raw coordinates has to learn this from data, wasting capacity — or "
    "worse, it never quite learns it and predicts different energies for the same molecule.",
], 0.8, b + 0.10, 11.9, size=14, gap=0.08, lh=0.24)
key_box(s, "**Build the symmetry in and it holds exactly — for free — on every molecule.**")

s = new_slide("Ways to put physics into a neural network")
bullets(s, [
    "**Symmetry in the architecture** — invariant or equivariant layers. This is what modern "
    "interatomic potentials do, and it buys enormous data efficiency: equivariant models have "
    "matched earlier architectures with up to ~1000× less training data.",
    "**Physics in the loss (PINNs)** — add the residual of a governing equation to the loss, "
    "so the network is penalised for violating known physics. Widely used for PDE-constrained "
    "problems in transport, kinetics and spectroscopy.",
    "**Conservation by construction** — predict the energy, then obtain forces as **−∂E/∂r**. "
    "Energy conservation then holds by construction rather than by hope.",
    "**Physically meaningful inputs** — charges, spin state, oxidation state; and "
    "**multi-fidelity** training that mixes cheap and expensive theory.",
], 0.8, 1.42, 11.9, size=15, gap=0.20, lh=0.26)
text(s, "Batzner et al. Nat. Commun. 13, 2453 (2022)  ·  Raissi, Perdikaris & Karniadakis, "
        "J. Comput. Phys. 378, 686 (2019)",
     0.8, 6.30, 11.9, 0.35, size=11, color=GRAY, italic=True)

s = new_slide("Where this is heading")
bullets(s, [
    "**Graph neural networks** treat the molecule as atoms and bonds — the natural "
    "representation. Adding rotational equivariance on top is what makes today's "
    "machine-learned interatomic potentials work.",
    "**Foundation potentials** trained on millions of DFT calculations can now be fine-tuned "
    "to your own system with a few hundred extra data points.",
    "**The trade-off is real:** more built-in physics means better data efficiency and "
    "generalization, but more engineering effort — and it hurts if the assumed symmetry is "
    "only approximate for your system.",
], 0.8, 1.45, 11.9, size=16, gap=0.24, lh=0.28)
key_box(s, "**Next lecture: graph neural networks and machine-learned interatomic "
           "potentials, in full.**", y=5.30)

# =====================================================================
# 7 — WHEN TO USE
# =====================================================================
section_slide(7, "When to use deep learning — and when not to", [
    "An honest decision framework",
])

s = new_slide("Rule of thumb: start from your dataset size")
table(s, ["Dataset size", "Reach for", "Why"],
      [["< ~1,000 points", "classical ML\n(random forest, GP, kernel ridge)",
        "small networks memorize noise here;\ngood descriptors win"],
       ["~1,000 – 10,000", "small networks, or architectures\nwith physics built in",
        "the competitive zone — the right\ninductive bias decides it"],
       ["> ~10,000, or a pretrained\nmodel you can fine-tune", "deep learning",
        "clear advantage on complex,\nheterogeneous chemistries"]],
      x=0.75, y=1.55, col_w=[3.6, 4.4, 4.2], size=13, row_h=3.6)
key_box(s, "**Deep learning is not a default. It is the right answer in a specific regime — "
           "and you should know which regime you are in.**", y=5.55)

s = new_slide("Four questions before you train a network")
bullets(s, [
    "**Is the relationship actually nonlinear?** Fit a linear or kernel baseline first. "
    "If it does the job, you are finished — and you have something interpretable.",
    "**Do you need gradients?** If you need forces or want to run dynamics, a differentiable "
    "network gives them for free via backpropagation.",
    "**Will you run it many times?** Screening thousands of candidates amortizes the training "
    "cost. A one-off analysis does not.",
    "**Can you check it?** Hold out a genuinely independent test set. For a surrogate of DFT, "
    "spot-check against DFT on new chemistry before you trust it.",
], 0.8, 1.45, 11.9, size=15.5, marker="num", gap=0.22, lh=0.27)
key_box(s, "**And always report the baseline you beat.**", y=5.90)

s = new_slide("Take-home messages")
msgs = [
    "A neural network is layers of weighted sums glued together by nonlinear activations — "
    "nothing more mysterious than that.",
    "Training means following the gradient of the loss downhill. It works well, but it is not "
    "guaranteed: initialization, learning rate and plateaus all matter.",
    "Capacity cuts both ways. Count your parameters, watch a validation set, and regularize "
    "with early stopping, weight decay and dropout.",
    "Choose the architecture that matches the structure of your data — and in chemistry, "
    "build the symmetry in.",
]
y = 1.55
for i, m in enumerate(msgs, 1):
    card(s, 0.85, y, 11.6, 1.08, fill=CARD if i % 2 else PEACH)
    node(s, 1.45, y + 0.54, 0.56, fill=ORANGE, edge=ORANGE, label=str(i), size=17,
         label_color=WHITE)
    text(s, m, 2.0, y + 0.14, 10.2, 0.85, size=14.5, color=INK,
         anchor=MSO_ANCHOR.MIDDLE, line_spacing=1.15)
    y += 1.20

s = new_slide("Further reading")
bullets(s, [
    "**dmol.pub** — *Deep Learning for Molecules & Materials*, A. D. White. Chemistry-first, "
    "with runnable notebooks.",
    "**introtodeeplearning.com** — MIT 6.S191. Excellent lectures on the perceptron, training "
    "and regularization.",
    "Krizhevsky, Sutskever & Hinton, **AlexNet**, NeurIPS (2012).",
    "Gilmer et al., **Neural Message Passing for Quantum Chemistry**, ICML (2017); arXiv:1704.01212.",
    "Jumper et al., **AlphaFold2**, Nature 596, 583 (2021).",
    "Merchant et al., **GNoME**, Nature 624, 80 (2023).",
    "Batzner et al., **NequIP** (equivariant potentials), Nat. Commun. 13, 2453 (2022).",
    "Raissi, Perdikaris & Karniadakis, **Physics-informed neural networks**, "
    "J. Comput. Phys. 378, 686 (2019).",
], 0.8, 1.45, 11.9, size=14.5, gap=0.15, lh=0.25)

s = new_slide("Questions")
centered(s, "Three to think about for your own work:", 2.35, size=17, color=GRAY, italic=True)
bullets(s, [
    "Where in your research is the bottleneck a calculation or a measurement you have to "
    "repeat thousands of times?",
    "Do you already have a thousand labelled data points sitting in a folder somewhere?",
    "In your system, which symmetries are exact — and which are only approximate?",
], 1.6, 3.05, 10.2, size=16.5, gap=0.30, lh=0.28)

save("lecture_04-intro-deep-learning.pptx")
