#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Builds lecture_07-learned-representations.pptx.

Figure-first deck: every slide is one native, editable PowerPoint figure with a
short take-away. What to say is in the speaker notes of each slide.

    python build_deck.py
"""
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.dml.color import RGBColor

from deck_lib import *              # slide furniture, palette, text/bullets
import deck_lib as L
from figs7 import *                 # parts 1-2 figures + shared helpers
from figs7b import *                # parts 3-6 figures

TITLE_SZ = 26

# One-line take-away printed in a peach strip under each figure. Keyed by slide
# title so the call sites stay uncluttered.
TAKE = {
 "The bottleneck is labels, not molecules":
    "Molecules are free. **Labels are the scarce resource** — everything today "
    "spends the first to make up for the second.",
 "Three ways to learn — only one of them needs you":
    "**Self-supervised learning turns unlabelled molecules into a training signal.** "
    "That is the bridge from 10⁹ molecules to a trainable model.",
 "Unsupervised learning does three jobs":
    "Decide which job you want **before** you open the notebook — a UMAP is not a "
    "clustering, and a clustering is not a generative model.",
 "PCA: a rotation, and an honest one":
    "PCA is transparent and invertible, but **two components never show you "
    "fingerprint data** — the variance you cannot see is chemistry, not noise.",
 "t-SNE and UMAP: keep the neighbours, lose the distances":
    "The trade is deliberate: **neighbourhoods are preserved, distances are not.** "
    "That is the right trade for fingerprints — and a trap if you forget it.",
 "A chemical space map is a chain of choices":
    "A chemical space map is **a picture of your fingerprint**, not a picture of "
    "chemistry. Change the fingerprint and the story changes.",
 "At a million molecules, the algorithm matters":
    "**TMAP: ~117× faster than UMAP at 10⁶ molecules, and reproducible.** "
    "Branches are analogue series — a chemically meaningful unit.",
 "Three things your map is not telling you":
    "**Never read clusters off a map.** Cluster explicitly in the original space, "
    "then use the map only to display the result.",
 "Butina clustering: the cheminformatics default":
    "**No k to choose, deterministic, and the centres are real molecules.** "
    "Run it at two or three cut-offs and check your conclusion survives.",
 "Scaffolds: chemistry is far more clustered than it looks":
    "**32 frameworks cover half of all known drugs.** This is why you must split "
    "by scaffold — and why your effective sample size is smaller than you think.",
 "Case study: the periodic table, from text alone":
    "Nobody taught it any chemistry. **Unsupervised learning on 3.3 M abstracts "
    "recovers the periodic table** — and predicts new thermoelectrics.",
 "Case study: reaction classes, unsupervised":
    "**Masked-language pre-training alone recovers most of the reaction taxonomy** "
    "— 81.9% vs 41.0% for a hand-crafted fingerprint, with zero labels.",
 "The autoencoder: learn by rebuilding the input":
    "The molecule is its own label. **If 196 numbers can rebuild the molecule, "
    "those 196 numbers are a representation the model invented.**",
 "The bottleneck is the whole trick": None,     # figure supplies its own strip
 "The problem: a plain autoencoder learns islands":
    "Nothing in the loss describes the space **between** the molecules — so the "
    "model never learns it, and sampling there produces garbage.",
 "The VAE in one idea: encode a cloud, not a point": None,
 "Two forces, and a dial between them":
    "**β is the whole design decision.** Too small and you are back to islands; "
    "too large and the decoder ignores z entirely.",
 "The payoff: a space you can walk through":
    "A VAE turns a **discrete** object into a **continuous** one — which is what "
    "every optimiser, gradient and Bayesian loop wants.",
 "ChemVAE, 2018 — the paper that started it":
    "Joint property training is the idea that survived: **give the encoder a whiff "
    "of the task and the latent space organises itself around it.**",
 "The validity arms race":
    "**The last two bars are won by construction, not by learning.** The model did "
    "not get better at chemistry; the output format got stricter.",
 "Two ways to make invalidity impossible":
    "Both guarantee **syntactic** validity only. A 100%-valid molecule can still be "
    "one no chemist would draw.",
 "The turn: validity was the easy metric":
    "**Validity was easy, so it got measured; quality is hard, so it did not.** "
    "A 30-second genetic algorithm beats 8 hours of VAE + Bayesian optimisation.",
 "Keep the encoder, throw away the decoder":
    "**The decoder disappointed. The encoder became the foundation of everything "
    "after it** — pretext task in, reusable encoder out.",
 "Two ways to make the data label itself":
    "Masked prediction teaches **local chemistry**; contrastive teaches **what to "
    "ignore**. Both need only unlabelled molecules.",
 "Choosing augmentations is choosing your chemistry": None,
 "Scale helps — until it doesn't":
    "**Corpus composition beats corpus size.** A 15× bigger corpus made ClinTox "
    "substantially worse; a smaller, more diverse one beat a bigger, narrower one.",
 "Pre-training GNNs: local and global, or negative transfer":
    "“We pre-trained it” guarantees nothing. **Pre-training a weaker architecture "
    "cost 6.5 points of ROC-AUC.**",
 "The recipe: pre-train once, fine-tune many times":
    "The expensive half is **amortised across the whole community**. You are "
    "buying a billion molecules' worth of chemistry for a coffee break.",
 "Three knobs — pick by your dataset size":
    "**Always run the frozen probe first.** Two minutes, no risk, and it tells you "
    "whether the representation contains anything useful for your task.",
 "Where pre-training genuinely pays":
    "**Pre-training is a prior:** worth 3× when you have ~100 labels, worth nothing "
    "by ~1,000, and occasionally worth less than nothing.",
 "The same shape, in three different fields":
    "Different fields, different architectures, **the same shape** — the value of "
    "pre-training is concentrated where labels are most expensive.",
 "Foundation models for atoms — the same play, at scale":
    "**You will never train one of these — you will fine-tune one.** Same recipe, "
    "applied to potentials instead of properties.",
 "The uncomfortable benchmark":
    "**Always run ECFP + random forest first.** If your model cannot beat it, you "
    "have learned something valuable for the price of two minutes.",
 "Activity cliffs: where smoothness is a lie":
    "Smoothness is an assumption, and cliffs violate it. **Report cliff performance "
    "separately** — overall RMSE hides exactly the compounds that matter.",
 "So when is a learned representation worth it?":
    "The shapes are robust; **the crossover is yours to measure**, and it moves "
    "with label noise, split type and how narrow your chemistry is.",
 "What to do on Monday": None,
}


def S(title, note=None, title_size=TITLE_SZ):
    s = new_slide(title, title_size=title_size)
    if note:
        notes(s, note)
    msg = TAKE.get(title)
    if msg:
        key_box(s, msg, y=5.78, size=13.5)
    return s


# =====================================================================
# TITLE
# =====================================================================
s = new_slide("Learned Representations")
centered(s, "Letting the model choose the features", 1.24, size=18, color=GRAY,
         italic=True)
fig_two_pipelines(s, y=2.00)
text(s, "J. Schleinitz  ·  Wednesday, August 12, 2026  ·  RSC 275, Caltech",
     0.54, 6.52, 10.0, 0.4, size=12, color=INK)
notes(s, """
Welcome back. Yesterday morning you did supervised learning, yesterday afternoon
neural networks. Monday you did molecular representations — SMILES, fingerprints,
descriptors, graphs.

This lecture sits exactly at the join between those two. Every representation you
met on Monday was something a human designed: someone decided that a radius-2
circular environment was the right unit of chemistry, or that these 200 RDKit
descriptors were the right summary. Today the question is what happens when you
stop deciding, and let the model work out its own description of a molecule
from data.

Point at the figure: top row is Monday. Bottom row is today. The only thing that
changes is which box is fitted to data — but that one change is what makes
pre-training, foundation models and chemical language models possible.

Three promises for the next 90 minutes:
 1. You will know what "unsupervised" and "self-supervised" actually mean, and
    why chemists should care.
 2. You will be able to read a VAE figure in a paper and know what is and is not
    being claimed.
 3. You will have a defensible rule for when to reach for a pre-trained model —
    and, just as importantly, when not to.
""")

# =====================================================================
# PLAN
# =====================================================================
s = new_slide("Plan")
bullets(s, [
    "**Why learn a representation?**  the label bottleneck (10 min)",
    "**Unsupervised learning:**  clustering, chemical space maps, what they do and "
    "do not tell you (20 min)",
    "**Autoencoders and VAEs:**  compression, latent spaces, and an honest look at "
    "molecular generation (20 min)",
    "*— break —*",
    "**Self-supervised pre-training:**  masked prediction and contrastive learning "
    "(15 min)",
    "**Transfer learning:**  frozen, partial, full — and where it genuinely pays "
    "(15 min)",
    "**When it fails:**  negative transfer, activity cliffs, and the baseline you "
    "must always run (10 min)",
], 1.55, 1.48, 10.6, size=16.5, gap=0.22, lh=0.29)
key_box(s, "**Tutorial at 15:15** — you will build the map and measure the "
           "crossover yourself, on real data.")
notes(s, """
Rough timings are on the slide. Two structural things to flag.

First, there is a deliberate turn in the middle of Part 3. I am going to spend
fifteen minutes explaining why VAEs are elegant, and then five minutes showing you
that as molecule generators they lose to a genetic algorithm from 2019. That is not
me wasting your time — the encoder half of that architecture is what the whole
modern pre-training field is built on, and you need to understand it. But I do not
want anybody leaving here thinking a VAE is the state of the art in generation.
Thursday's diffusion lecture picks that thread up.

Second, Part 6 is the part I would keep if I only had ten minutes. The literature
on learned representations has a serious replication problem, and knowing that is
more useful to you as practising chemists than any architecture diagram.

Ask: who here has fewer than 1,000 data points in the project they came here with?
(Usually most hands.) Good — Part 5 and Part 6 are written for you.
""")

# =====================================================================
# PART 1
# =====================================================================
section_slide(1, "Why learn a representation?", [
    "Hand-crafted vs learned features",
    "The label bottleneck",
    "Three kinds of supervision",
])

s = S("The bottleneck is labels, not molecules", """
This is the single slide that motivates everything else today. Note the axis is
log10 — every bar is a factor of ten.

Top: GDB-17, the exhaustive enumeration of everything you can draw with up to 17
heavy atoms from C, N, O, S and halogens under simple stability and synthesizability
rules. 166 billion molecules. Enamine REAL, which is molecules you can actually
order and get in two weeks: 9.6 billion. PubChem, catalogued: about 120 million.
ChEMBL, molecules with a measured bioactivity: a few million.

Now the bottom two bars. A typical MoleculeNet task is one to eight thousand
molecules. Your own HTE campaign is a few hundred wells.

So: molecules are essentially free, and labels are the scarcest thing in the room.
Eight orders of magnitude between what we can enumerate and what we have measured.

Every idea in this lecture is an attempt to exploit the top of this chart to make
up for the bottom of it. That is the whole game. If you remember nothing else,
remember that learned representations are a response to label scarcity.

Caveat worth saying out loud: GDB-17 is enumerated, not made. Only a tiny
fraction has ever been synthesised. But even ChEMBL versus your assay is four
orders of magnitude.
""")
fig_label_gap(s)
ref(s, "GDB-17: Ruddigkeit et al., J. Chem. Inf. Model. 2012, 52, 2864 · "
       "Enamine REAL (2026) · PubChem · ChEMBL")

s = S("Three ways to learn — only one of them needs you", """
Set up the vocabulary carefully here; students confuse the last two constantly.

SUPERVISED — what you did yesterday. Pairs of (molecule, measured property). The
label is the expensive part: someone ran the assay, someone did the DFT.

UNSUPERVISED — you hand the algorithm molecules and nothing else. It can only tell
you about the shape of the data: which molecules group together, what the main axes
of variation are, what a typical molecule looks like. No property is being predicted.

SELF-SUPERVISED — the clever middle. You take unlabelled data and manufacture a
supervised problem out of it by hiding part of the input and asking the model to
recover it. Nobody annotated anything, but you now have a loss function with a
correct answer, so you can use all the supervised machinery — backprop, big models,
the lot.

The point to land: self-supervised learning is how you convert the enormous
top-of-chart data from the previous slide into something a neural network can
actually be trained on. It is the bridge.

A useful analogy if they are struggling: a chemist who reads ten thousand papers
without ever running a reaction still develops good intuition about what will work.
Nobody graded them. They were predicting the next step and checking against what
the paper said. That is self-supervision.
""")
fig_supervision(s)

# =====================================================================
# PART 2
# =====================================================================
section_slide(2, "Unsupervised learning", [
    "Clustering, dimensionality reduction, density",
    "Chemical space maps — and how to read them honestly",
    "Case study: the periodic table from text alone",
])

s = S("Unsupervised learning does three jobs", """
Three jobs, and it is worth naming which one you want before you open a notebook,
because people reach for UMAP when they actually wanted clustering.

CLUSTERING gives you group memberships and no coordinates. Use it when the question
is "how many distinct chemotypes are in my screening deck", or when you need to pick
a diverse subset to buy.

DIMENSIONALITY REDUCTION gives you coordinates and no groups. Use it when you want
to look at your data. Crucially: the fact that you can see clusters in a UMAP does
not mean the clustering algorithm would find them.

DENSITY AND GENERATION gives you a model of what a plausible molecule looks like,
which you can sample from. This is where VAEs live, and it is where we go in Part 3.

The thing all three share: no labels anywhere. Which means you can run them on
every molecule you have, not just the ones you measured. For most groups in this
room that is the difference between 400 compounds and 40,000.

Practical aside: this is also the cheapest possible first thing to do with a new
dataset. Before you fit anything, cluster it and look at it. You will find the
duplicate series, the one bad plate, and the fact that all your actives came from
one scaffold.
""")
fig_three_jobs(s)

s = S("PCA: a rotation, and an honest one", """
Start with PCA because it is the one method here that is completely transparent,
and because it sets up why we need the nonlinear ones.

PCA finds the directions of greatest variance and rotates your coordinate system
onto them. That is all it does. It is linear, deterministic, has a closed-form
solution, and — the property people forget — it is invertible. You can go back.
Every point in PCA space corresponds to a real position in the original space.

Now the scree plot, which is the honest part. On molecular fingerprints, the first
two components typically capture something like half to sixty percent of the
variance. People show you the PC1-PC2 plot and imply you are looking at the data.
You are looking at a shadow of the data, and the forty percent you cannot see is
not noise — it is chemistry that happens to vary along directions three through
two thousand.

So: PCA is a good sanity check and a good preprocessing step. It is a bad way to
claim two clusters are distinct.

If asked why fingerprints need so many components: ECFP bits are sparse and
near-orthogonal by construction. There genuinely is no low-dimensional linear
structure. That is the motivation for the next slide.
""")
fig_pca(s)

s = S("t-SNE and UMAP: keep the neighbours, lose the distances", """
The move from PCA to t-SNE or UMAP is a trade. You give up the global geometry to
buy local faithfulness.

Both methods do roughly the same thing: build a graph of who is near whom in the
high-dimensional space, then find a 2-D arrangement whose neighbourhood graph looks
as similar as possible. UMAP does it with a fuzzy simplicial set and is faster and
somewhat more global; t-SNE does it with a Student-t kernel and is more aggressive
about separating clusters. For our purposes they behave similarly.

Why this matters in fingerprint space specifically: in 2048 dimensions with sparse
binary vectors, almost every pair of molecules has Tanimoto similarity around 0.1.
Distances are nearly all the same and therefore nearly meaningless. But the *ranking*
of nearest neighbours is still informative. Neighbour embeddings throw away the
distances and keep the ranking. That is exactly the right trade for this data.

The cost is on the right in red, and it is the subject of the next slide, so do not
dwell — just plant it: the gaps between the islands, and the sizes of the islands,
are artefacts.
""")
fig_neighbour_embedding(s)

s = S("A chemical space map is a chain of choices", """
Walk the chain left to right, and make the point at the bottom hard.

Which molecules you put in decides what the map is of. Which fingerprint you choose
decides what "similar" means — ECFP4 says two molecules are similar if they share
circular substructures; a pharmacophore fingerprint says something completely
different; a learned embedding says something different again. The layout algorithm
and its hyperparameters then decide what you actually see.

So when a paper shows you a beautiful chemical space map with the actives clustered
in one corner, the correct first question is not "what does this tell us about
chemistry" — it is "what would this look like with a different fingerprint".

This is not a counsel of despair. Maps are genuinely useful: for spotting that your
train and test sets occupy different regions, for choosing a diverse subset, for
noticing that your whole "diverse" library is three scaffolds. Just do not treat the
picture as a fact about chemistry. It is a fact about your fingerprint.

In the tutorial you will make the same map with two different representations and
see how much it moves.
""")
fig_map_pipeline(s)

s = S("At a million molecules, the algorithm matters", """
A concrete example of the engineering, because chemical space has got big enough
that the method has to change.

TMAP, from the Reymond group, swaps the scatter plot for a tree. It builds an
approximate k-nearest-neighbour graph using locality-sensitive hashing, takes the
minimum spanning tree of that graph, and lays the tree out. You get branches instead
of blobs — and a branch is usually a series of analogues, which is a chemically
meaningful object in a way that a blob is not.

The numbers on the right are from their benchmark on ChEMBL subsets. At one million
molecules TMAP takes about six minutes; UMAP takes eleven and a half hours. Roughly
117-fold, and about six times less memory. TMAP is also deterministic — run it twice,
get the same map — which UMAP is not.

The 2026 follow-up nests these maps and handles Enamine REAL at 9.6 billion
molecules. That is the scale at which "let me just have a look at my library" now
operates.

Do not oversell: TMAP is a visualisation tool, not a representation learner. I am
showing it because it is the workhorse people actually use, and because the
tree-versus-scatter distinction is a nice illustration that the layout is a choice.
""")
fig_tmap(s)
ref(s, "Probst & Reymond, J. Cheminform. 2020, 12, 12 · Flores Sepúlveda & Reymond, "
       "J. Chem. Inf. Model. 2026, 66, 5595")

s = S("Three things your map is not telling you", """
This is the slide I most want you to photograph. These are not pedantic caveats;
they are the three ways published chemical space figures mislead people.

ONE — gap width means nothing. t-SNE and UMAP have no notion of how far apart two
clusters should be. Change the perplexity or the n_neighbors parameter and the gaps
change. Two islands sitting far apart on your plot are not necessarily more different
than two islands sitting close.

TWO — cluster size means nothing. Both algorithms tend to expand sparse regions and
compress dense ones. A blob containing seven molecules and a blob containing two
hundred and forty can be drawn almost the same size. So never say "this cluster is
bigger, therefore this chemotype is over-represented" from a UMAP.

THREE — and this is the one that gets people into real trouble — these methods will
produce clean, convincing clusters from pure random noise. There is a well-known
demonstration where uniform random data in high dimensions comes out of t-SNE
looking like five beautiful, well-separated groups. Seeing clusters is not evidence
that clusters exist.

The remedy in one line: if the clustering matters to your argument, cluster
explicitly in the original space — Butina, k-medoids, whatever — and use the map
only to display the result. Never read the clusters off the map.
""")
fig_tsne_warnings(s)

s = S("Butina clustering: the cheminformatics default", """
Quick and practical, because this is the one people actually run.

Butina is sphere exclusion. Pick a Tanimoto cut-off — 0.4 to 0.65 depending on the
fingerprint and how tight you want your clusters. For every molecule, count how many
molecules fall within that cut-off. Take the molecule with the most neighbours, call
it a cluster centre, and remove it and all its neighbours from the pool. Repeat on
what is left.

Why chemists like it: no k to choose, it is deterministic, it runs on a laptop, and
the cluster centres are real molecules you can order rather than abstract centroids.
It is the standard way to pick a diverse subset for a screen.

Two honest weaknesses. It is greedy — the first sphere claims everything nearby,
so a molecule that would have been a great centre can end up as a singleton simply
because it got absorbed. And it is very sensitive to the cut-off; changing 0.6 to
0.65 can change the number of clusters substantially. Run it at two or three
thresholds and see whether your conclusion survives.

Contrast with k-means: k-means needs a k, needs a Euclidean space, and produces
centroids that are not molecules. For fingerprints, Butina is usually the better
tool.
""")
fig_butina(s)
ref(s, "Butina, J. Chem. Inf. Comput. Sci. 1999, 39, 747")

s = S("Scaffolds: chemistry is far more clustered than it looks", """
Bemis and Murcko, 1996 — the single most quoted piece of cheminformatics, and it
is a purely unsupervised analysis.

Take a drug, strip every side chain, keep the ring systems and the linkers between
them. If you also throw away atom types and bond orders you get the graph framework.
Do this to the 5,120 drugs known at the time and you get 1,179 distinct frameworks.

The number that should surprise you is on the chart: thirty-two frameworks account
for half of all known drugs. Medicinal chemistry, for all its apparent diversity,
lives on a very small number of ring systems.

Two consequences, both of which bite you in machine learning.

First, if you split a dataset at random, near-identical analogues end up in both
train and test, your model looks brilliant, and it has learned nothing that
generalises. That is why every serious paper today uses a SCAFFOLD SPLIT — hold out
whole frameworks. Expect your numbers to get worse. They were never real.

Second, this is why molecular datasets are so much smaller than they appear.
Four thousand compounds from a med-chem programme might be forty scaffolds. Your
effective sample size is forty.

You will do a random split and a scaffold split on the same data in the tutorial
and watch the score fall. That gap is the most honest number in your whole project.
""")
fig_scaffolds(s)
ref(s, "Bemis & Murcko, J. Med. Chem. 1996, 39, 2887 — 1,179 frameworks among 5,120 drugs")

s = S("Case study: the periodic table, from text alone", """
My favourite result in this whole area, and the cleanest possible demonstration that
unsupervised learning finds real structure.

Tshitoyan and co-workers took 3.3 million materials science abstracts, filtered to
1.5 million, and trained word2vec on them. Word2vec is self-supervised in the sense
we defined earlier: predict a word from its neighbours. It knows nothing about
chemistry. It has never seen a periodic table, an atomic number, or an electron
configuration. It has only seen which words appear near which other words.

Then they took the hundred element symbols, pulled out their 200-dimensional
vectors, and ran t-SNE. What comes out is the periodic table. The alkali metals sit
together. The halogens sit together. The noble gases are off on their own. The
transition metals form a band.

Why: because chemists write about lithium in sentences that look like sentences
about sodium. The structure of the language mirrors the structure of the chemistry,
and the model recovers the chemistry from the language.

Then they went further and used it prospectively: element embeddings as features
predicted elpasolite formation energies to 0.056 eV per atom, better than
hand-crafted descriptors. And their thermoelectric predictions were about eight
times more likely than chance to be reported as thermoelectrics in the following
five years. CuGaTe2 would have been a top-five pick four years before it was
published.

One correction, since it circulates in talks: the "8x" is an enrichment over random,
not "8 of the top 10 worked".
""")
fig_periodic_embedding(s)
ref(s, "Tshitoyan et al., Nature 2019, 571, 95")

s = S("Case study: reaction classes, unsupervised", """
The same phenomenon in reaction space, and closer to what most of you do.

Schwaller and colleagues trained a BERT model on 2.6 million reaction SMILES from
Pistachio with a masked-token objective. No reaction class labels. Then they took
the embeddings and asked a simple 5-nearest-neighbour classifier to recover the 792
reaction classes.

A traditional reaction fingerprint gets 41%. The self-supervised embedding, with no
labels at any point, gets 81.9%. Fine-tune the same model with labels and you get
98.9%.

So: masked-language-model pre-training on reaction strings discovers most of the
reaction taxonomy on its own. That is a strong statement — the model worked out what
a Suzuki coupling is from nothing but co-occurrence statistics in reaction strings.

Be precise about one thing, because the paper is often overstated: the fully clean,
beautifully separated reaction atlas that people show is from the FINE-TUNED
fingerprint. The purely self-supervised one shows substantial but partial class
structure. 81.9% is the honest number and it is impressive enough.

The counterpoint I like to pair with this: DRFP, a hand-crafted, training-free
reaction fingerprint, matches the learned one on both classification and yield
prediction. Which is a preview of Part 6.
""")
fig_rxnfp(s)
ref(s, "Schwaller et al., Nat. Mach. Intell. 2021, 3, 144 · counterpoint: Probst et al., "
       "Digital Discovery 2022, 1, 91 (DRFP)")

# =====================================================================
# PART 3
# =====================================================================
section_slide(3, "Autoencoders and VAEs", [
    "Compression as representation learning",
    "Why a plain autoencoder is not enough",
    "What VAEs are — and are not — good for",
])

s = S("The autoencoder: learn by rebuilding the input", """
Here is the architecture that starts the modern story.

An encoder squeezes the molecule down to a small vector z. A decoder tries to rebuild
the original molecule from z alone. The loss is simply: did you get the input back.

Note what is NOT here. No property. No assay. No label of any kind. The molecule is
its own target. This is self-supervision in its purest form, and it means you can
train on every molecule in ZINC.

Now the important bit conceptually. If the decoder can rebuild the molecule from
196 numbers, then those 196 numbers must contain essentially everything about the
molecule that matters. z is a learned representation — a compressed description that
the model invented, rather than one you specified.

The word "bottleneck" is doing real work here, and the next slide unpacks it.

Historical aside if you have time: this idea is old, it goes back to the 1980s. What
changed is that we got enough unlabelled molecules and enough GPU to make it work.
""")
fig_autoencoder(s)

s = S("The bottleneck is the whole trick", """
Why does compression produce something useful? Because it forces a choice.

If z is as wide as the input, the network learns the identity function. It copies
the input across and reconstructs perfectly, and z tells you nothing. This is a real
failure mode, not a hypothetical.

If z is far too narrow — say two numbers — nothing reconstructs, and everything
decodes to something like benzene.

In between, the model is forced to triage. It has, say, 196 numbers to describe an
arbitrary drug-like molecule. It cannot store the SMILES string. So it has to work
out what is worth keeping: ring systems, molecular size, the presence of a carbonyl,
halogen substitution, roughly where things are attached. And it discovers those
features itself, because they are the ones that buy the most reconstruction accuracy
per bit.

That is the sentence to take away: what survives the bottleneck is what the data says
matters. Compare that with ECFP, where what survives is what Rogers and Hahn decided
mattered in 2010.

Which is better? Genuinely open — Part 6. But they are different in kind.
""")
fig_bottleneck_why(s)

s = S("The problem: a plain autoencoder learns islands", """
Now the failure that motivates the VAE, and it is worth being concrete because this
is where students' intuition usually breaks.

The autoencoder was only ever asked to do one thing: reconstruct the molecules in the
training set. Nothing in the loss says anything about the space between them. So the
optimiser does the easiest thing — it scatters the training molecules into isolated
islands, as far from each other as possible, because that makes them maximally easy
to tell apart and reconstruct.

The result is on the left: a latent space that is mostly empty. And if you pick a
point in one of those empty regions and decode it — the red star — you get the mess
on the right. Unparseable strings, pentavalent carbons, absurd structures.

Why does this matter? Because a representation you cannot move around in is much less
useful. If you want to optimise a molecule, or interpolate between two molecules, or
sample a new one, you need the space between the data to mean something.

The VAE is precisely the fix for this, and it is one idea.
""")
fig_ae_holes(s)

s = S("The VAE in one idea: encode a cloud, not a point", """
Here is the entire conceptual content of a variational autoencoder. Everything else
is machinery.

Instead of mapping each molecule to a single point in latent space, map it to a small
region — a mean and a spread. Then, during training, do not decode the mean. Decode a
random sample drawn from that region.

Think about what that does. The model is now being told: every point in this little
cloud has to decode back to aspirin. Not just the centre — the whole neighbourhood.

Do that for every molecule in the training set, and the clouds start to overlap and
tile the space. The holes fill in. The space becomes continuous, in the sense that
moving a small distance changes the molecule a small amount, rather than falling off
a cliff into garbage.

That is it. That is the idea. The mathematics — variational inference, the ELBO, the
reparameterisation trick — is machinery for making that trainable, and I am
deliberately not showing it. If you want it, Kingma and Welling 2013, and the
reparameterisation trick is the one piece genuinely worth reading about.

Check for understanding: ask why we sample instead of just adding noise to the
output. Answer: because the model also gets to CHOOSE the spread, and that choice is
what gets regularised.
""")
fig_vae_point_vs_blob(s)

s = S("Two forces, and a dial between them", """
The VAE loss has two terms pulling in opposite directions, and understanding the
tension is enough to read any VAE paper.

RECONSTRUCTION wants every molecule to be perfectly recoverable. The way to achieve
that is to make the clouds tiny and far apart, so no two molecules can be confused.
That is the autoencoder failure mode coming back in.

REGULARISATION wants all the clouds to look like one standard blob centred at the
origin. Taken alone, that collapses everything on top of everything else and you can
reconstruct nothing.

Beta is the dial between them. Turn it down and you have an autoencoder with holes.
Turn it up and you get mush — in the worst case the model ignores z entirely and the
decoder just produces generic molecules. That failure has a name, posterior collapse,
and it is common enough that a lot of practical VAE work is about scheduling beta.

The original chemical VAE annealed beta on a sigmoid schedule after 29 epochs, for
exactly this reason.

What to take away: when someone shows you a beautiful smooth latent space, ask what
beta was, and ask what the reconstruction accuracy was. There is always a trade, and
the pretty picture usually costs fidelity.
""")
fig_vae_forces(s)

s = S("The payoff: a space you can walk through", """
This is the picture that made the field excited in 2016, and it is worth
understanding why.

Take two molecules. Encode both to get two points in latent space. Draw the straight
line between them. Decode at intervals along the line. You get a series of molecules
that morph gradually from one to the other.

Notice what that means. Chemical structure is discrete — you cannot have half a
nitrogen. But the latent space is continuous. The VAE has given you a continuous
handle on a discrete object, and continuous is what every optimisation algorithm in
existence wants: gradients, Bayesian optimisation, gradient descent on a property.

That is the promise: turn molecular design into continuous optimisation. Encode your
library, train a property predictor on the latent vectors, follow the gradient
uphill, decode.

Hold onto that promise for two slides, because we are going to test it.

Note for honesty: real interpolations are choppier than this cartoon. Papers show you
the good ones.
""")
fig_interpolation(s)

s = S("ChemVAE, 2018 — the paper that started it", """
Gómez-Bombarelli and Aspuru-Guzik, ACS Central Science 2018 — the reference everyone
cites.

Architecture: SMILES in, convolutional encoder, 196-dimensional latent space for the
ZINC model, GRU decoder, SMILES out. Trained on 250,000 drug-like ZINC molecules.

The clever addition is the purple box. Alongside the decoder they attached a small
property predictor that reads z and predicts logP, QED, synthetic accessibility.
Trained jointly. And that changes the geometry of the latent space: instead of
organising molecules by whatever is easiest to reconstruct, it organises them
partly by property. Their own ablation says that without the property head there is
no discernible pattern in the latent space.

That is a genuinely important idea and it survives: if you want a representation
that is useful for a task, giving it a whiff of the task during training helps a lot.
You will see the same idea in Part 4 as multi-task regression pre-training.

Now the number in red, and I want to be careful because the literature is messy here.
Take random points from the latent space and decode them: roughly 4% give a valid
molecule, according to the published main text. Near real molecules it is much better,
70-80%. The arXiv version reports these differently and the definitions vary. But the
qualitative fact is not in dispute: most of that beautiful continuous space decodes
to nothing.
""")
fig_chemvae(s)
ref(s, "Gómez-Bombarelli et al., ACS Cent. Sci. 2018, 4, 268 — validity figures are "
       "version- and definition-dependent; see notes")

s = S("The validity arms race", """
The 4% number set off five years of work, and this chart is that story.

Character-level VAE — the JT-VAE authors reproduced it at 0.7% prior validity.
Grammar VAE, which forces the output to follow a SMILES grammar: 7.2%. Syntax-directed
VAE, which adds semantics on top: 43.5%. Junction-tree VAE: 100%. SELFIES: 100%.

Now the honest reading, which is the line above the last two bars. Those hundreds are
not achieved by learning. They are achieved by construction — by making it
structurally impossible to emit an invalid molecule. The model did not get better at
chemistry. The output format got stricter.

The JT-VAE authors say this themselves, and I like them for it: a degenerate model
could hit 100% validity by only ever generating long alkane chains.

So the right question is not "is it valid". Validity is table stakes and it is solved.
The right question is "is it any good", and that turns out to be much harder to
measure — and much less flattering. Two slides from now.
""")
fig_validity_race(s)
ref(s, "Jin, Barzilay & Jaakkola, ICML 2018, Table 1 · Krenn et al., "
       "Mach. Learn.: Sci. Technol. 2020, 1, 045024")

s = S("Two ways to make invalidity impossible", """
Both worth knowing because you will meet both.

JT-VAE, on the left. Do not generate atom by atom — generate at the level of
chemically valid pieces. Decompose each molecule into a junction tree whose nodes are
rings, bonds and single atoms, with a vocabulary of 780 substructures learned from
ZINC. Generate the tree first, then assemble the pieces into a graph, masking out any
join that would be chemically illegal. You cannot produce an invalid molecule because
you are only ever gluing together valid parts in legal ways.

SELFIES, on the right, is more elegant. It is a formal grammar with a state machine.
Each symbol is not a fixed token — it is an index into a rule table, and which rule
fires depends on how much valence is left. Follow the example: we are in state X1
with one bond available, the string asks for a double bond to carbon, so the grammar
CLAMPS it to a single bond. It never rejects; it absorbs. Combined with encoding
branch lengths and ring sizes as counts rather than paired brackets, there is
literally no string of SELFIES symbols that fails to decode.

The limitation, and say it clearly: SELFIES enforces local valence only. Not
aromaticity, not ring strain, not stability, not synthesizability. A 100%-valid
SELFIES molecule can still be something no chemist would ever draw.
""")
fig_jtvae_selfies(s)

s = S("The turn: validity was the easy metric", """
This is the slide where I ask you to update. Three results, all from people inside
the field.

LEFT — memorisation. On the MOSES benchmark the VAE's novelty score is 0.695. Nearly
a third of what it "designs" is literally already in the training set. The benchmark
authors' own words: autoencoder-based models overfit to the training set. A
character-RNN — a much simpler model — is more novel.

MIDDLE — validity does not buy quality. FCD measures how close your generated
distribution is to real chemistry. Look at CGVAE: 100% valid, and by a wide margin the
worst distribution match in the table. Molecule Chef, at 99% valid, is sixteen times
better on FCD. The relationship between validity and quality is not just weak, in this
table it is inverted.

RIGHT — and this is the one that should sting. Jan Jensen took a graph-based genetic
algorithm, a technique from the 1970s, and ran it for thirty seconds on a laptop. It
scored 7.4 on penalised logP. ChemVAE with Bayesian optimisation, eight hours: 0.0.

Add to that: on the PMO benchmark, randomly screening ZINC beats both JT-VAE and
SMILES-VAE. And Gao and Coley found that only about 30% of top-scoring generated
molecules have a findable synthetic route.

Pause here. Let it sit. Then ask: so why did I spend fifteen minutes on this?
""")
fig_honest_turn(s)
ref(s, "MOSES: Polykovskiy et al., Front. Pharmacol. 2020 · Molecule Chef: Bradshaw "
       "et al., NeurIPS 2019 · Jensen, Chem. Sci. 2019, 10, 3567")

s = S("Keep the encoder, throw away the decoder", """
Here is the answer to the question I just asked, and it is the hinge of the lecture.

As a molecule GENERATOR, the VAE lost. It lost to genetic algorithms, to plain SMILES
language models, and on some benchmarks to random screening. The generative baton has
passed to diffusion models — which is Thursday afternoon with Chenru — and to
LLM-based approaches, which is next week.

But look at what the architecture actually gave us. A way to map any molecule to a
fixed-length vector. Trained on hundreds of thousands of molecules with zero labels.
Where the geometry means something. And where the encoder can be pulled off and
reused for anything.

The decoder was the part that disappointed. The ENCODER is the part that became the
foundation of everything in the second half of this lecture. Every chemical language
model, every pre-trained GNN, every foundation MLIP is running the same play: train an
encoder on a pretext task using unlabelled data, then throw away the pretext head and
keep the encoder.

The VAE's pretext task was reconstruction. Part 4 is about better pretext tasks.

Break here — ten minutes.
""")
fig_vae_verdict(s)

# ---- break ----
s = new_slide(None, footer=False)
text(s, "☕", 0, 2.35, SW, 1.0, size=52, align=PP_ALIGN.CENTER)
centered(s, "Break", 3.45, size=40, color=INK, bold=True)
centered(s, "10 minutes — back for pre-training and transfer learning", 4.35,
         size=16, color=GRAY, italic=True)
notes(s, """
Ten minutes. When we come back: the second half is the practical half — this is the
part you will actually use.

If anyone asks during the break why VAEs are still taught: because the encoder-latent-
decoder pattern is everywhere, and because you cannot read the 2018-2022 chemistry ML
literature without it.
""")

# =====================================================================
# PART 4
# =====================================================================
section_slide(4, "Self-supervised pre-training", [
    "Masked prediction and contrastive learning",
    "Chemical language models at scale",
    "Pre-training graph neural networks",
])

s = S("Two ways to make the data label itself", """
Two families. Nearly everything you will meet is one of these or a combination.

MASKED PREDICTION. Hide part of the input, predict it back. On SMILES you mask
tokens, exactly as BERT does for English. On graphs you mask atom or bond attributes.
The insight: to fill in that gap correctly the model has to have internalised valence
rules, ring closure, which functional groups co-occur, what makes a molecule
plausible. You never told it any of that. It had to learn chemistry to solve the
puzzle. ChemBERTa and MoLFormer are this family.

CONTRASTIVE. Make two corrupted views of the same molecule. Push their embeddings
together. Push embeddings of different molecules apart. The insight here is different:
you are teaching the model what to IGNORE. If deleting a bond or masking an atom
should not change the embedding much, the model learns representations that are
robust to small perturbations and that capture the overall identity of the molecule.
MolCLR is the reference here.

Trade-off worth stating: masked prediction gives you fine-grained local knowledge;
contrastive gives you a more global, invariance-flavoured representation. Contrastive
is very sensitive to which augmentations you pick — next slide.
""")
fig_two_families(s)

s = S("Choosing augmentations is choosing your chemistry", """
MolCLR's three augmentations, and the reason this slide exists is the red line at
the bottom.

Atom masking: replace an atom's identity with a dummy. Bond deletion: remove a bond
but keep the atoms. Subgraph removal: delete a whole connected region.

Here is the conceptual problem, and it is specific to chemistry. In computer vision,
contrastive learning works because the augmentations are obviously label-preserving —
a rotated cat is a cat, a cropped cat is a cat. In chemistry that is not true. Delete
a bond and you may have changed the molecule from an agonist to an antagonist. Every
augmentation is a claim that some perturbation does not matter, and in chemistry that
claim is often false.

Their own ablation shows it. Subgraph removal alone works best. Combining all three
makes things worse, because you destroy too much structure. And specifically on
BBBP — blood-brain barrier penetration — the fixed augmentation ratio hurts, because
small topological changes really do flip that property.

Their honest conclusion: the optimal augmentation is task-dependent. Which is
awkward, because the whole point of pre-training is to do it once, before you know
the task.
""")
fig_molclr_augs(s)
ref(s, "Wang, Wang, Cao & Barati Farimani, Nat. Mach. Intell. 2022, 4, 279")

s = S("Scale helps — until it doesn't", """
Two halves, and you need both.

LEFT: the scaling story. ChemBERTa, 10 million SMILES, BBBP 64.3. MoLFormer-XL, 1.1
billion SMILES from PubChem and ZINC, BBBP 93.7. That is a real and large jump. The
engineering matters too: linear attention plus length bucketing took this from
needing roughly a thousand GPUs to sixteen. That is the difference between a national
lab and a well-funded group.

RIGHT: the part that does not get put on slides. ChemBERTa-2's masked-language model,
same architecture, same everything, corpus grown from 5 million to 77 million.
ClinTox ROC-AUC goes 0.341, then 0.349, then 0.239. Fifteen times more pre-training
data made that task substantially worse.

And there is a diversity effect in MoLFormer's own ablation: 10% of ZINC plus 10% of
PubChem beats 100% of ZINC on five of six tasks. A smaller, more chemically diverse
corpus beats a bigger, narrower one.

So the rule is not "more data is better". It is "more data that resembles your
problem is better". If your chemistry is organometallic and the corpus is drug-like,
scale will not save you.

One more caveat on all these tables: MoLFormer's classification numbers are scaffold
split, its regression numbers are random split, and the baselines are copied from
other papers rather than re-run. Read benchmark tables with that in mind.
""")
fig_corpus_scaling(s)
ref(s, "Ross et al., Nat. Mach. Intell. 2022, 4, 1256 · Ahmad et al., arXiv:2209.01712")

s = S("Pre-training GNNs: local and global, or negative transfer", """
The most instructive pre-training paper in chemistry, because half its message is
about failure.

Hu and colleagues tried node-level self-supervision alone: average ROC-AUC across
eight datasets goes from 67.0 to about 71. They tried graph-level supervised
pre-training alone on ChEMBL: 70.0. Combine them — node-level context prediction plus
graph-level multi-task supervision — and you get 74.2. Plus 7.2 over no pre-training.

The interpretation: node-level pre-training teaches local chemistry, what a
substructure is. Graph-level teaches what makes a whole molecule active. Do only the
first and the readout layer is untrained garbage. Do only the second and you overfit
to ChEMBL's particular tasks. You need both.

Now the right panel, which is the bit to remember. Same recipe, different backbone.
GIN gains 7.2. GCN gains 3.4. GraphSAGE gains 2.0. GAT LOSES 6.5.

Pre-training a less expressive architecture actively hurt. And in their tables,
graph-level pre-training alone caused negative transfer on two of the eight molecular
datasets outright.

So "we pre-trained it" is not a guarantee of anything. It is a hypothesis you have to
test against the un-pre-trained model. That is a habit, not a technique, and it is
Part 6.
""")
fig_hu_pretraining(s)
ref(s, "Hu et al., ICLR 2020, arXiv:1905.12265 — chemistry average; the +9.4% in the "
       "abstract is the biology result")

# =====================================================================
# PART 5
# =====================================================================
section_slide(5, "Transfer learning", [
    "Pre-train once, fine-tune many times",
    "Frozen, partial, full",
    "Where it genuinely pays",
])

s = S("The recipe: pre-train once, fine-tune many times", """
The economics of this is the reason it took over, so lead with that.

Stage one is done once, by someone with a cluster, on millions to billions of
unlabelled molecules, using one of the pretext tasks from Part 4. It costs days of
GPU time. The output is a set of encoder weights.

Stage two is done by you. You download those weights, attach a small head for your
task, and train on the two hundred molecules you actually measured. It takes minutes
on a laptop, or a free Colab GPU.

The asymmetry is the point: the expensive part is amortised across the entire
community. You are buying the chemistry that a model learned from a billion molecules
for the cost of a coffee break.

The analogy chemists like: you do not re-derive quantum mechanics every time you run
a DFT calculation. You use a functional someone else parameterised. Same idea —
someone else paid for the general knowledge, you supply the specific.

Terminology, since papers are sloppy about it: "transfer learning" is the general
idea of reusing knowledge; "fine-tuning" is the specific act of continuing to train
pre-trained weights on new data; "pre-training" is stage one. Foundation model is
marketing for a stage-one model big enough to be worth reusing.
""")
fig_pretrain_finetune(s)

s = S("Three knobs — pick by your dataset size", """
The practical decision you will actually make, and it is essentially determined by
how many labels you have.

FROZEN, also called a linear probe. Do not touch the encoder at all. Push your
molecules through, get embeddings, fit a ridge regression or a random forest on top.
Fast, needs almost no data, and you cannot overfit the encoder because you are not
training it. This is the correct default below a few hundred labels, and it is also
the correct FIRST experiment at any size, because it tells you cheaply whether the
representation contains anything useful for your task.

PARTIAL. Unfreeze the last few layers. The early layers hold general chemistry, the
later ones are more task-specific, so this adapts the specific part while protecting
the general part. Reach for it in the low thousands.

FULL. Train everything. Highest ceiling, most data-hungry, and the one that goes
wrong. The failure mode is catastrophic forgetting: with a normal learning rate your
first few gradient steps on 300 molecules will wreck weights that encode knowledge
from a billion. The fixes are standard — learning rate ten to a hundred times smaller
than you would use from scratch, a warm-up, and often a lower rate for early layers
than late ones.

Practical advice: run frozen first, always. It takes two minutes and it is your
sanity check.
""")
fig_three_knobs(s)

s = S("Where pre-training genuinely pays", """
This is the most important figure in the lecture. If you photograph one slide, this
one.

Han and Choi, predicting NMR chemical shifts. Pre-train a GNN on DFT-computed
shielding constants — cheap, you can generate as much as you like. Then fine-tune on
experimental shifts, which are expensive and scarce.

Follow the two curves. At about a hundred experimental molecules, the from-scratch
model has an error of 1.35 ppm; the pre-trained one is at 0.43. Three times better.
That is the difference between useless and useful.

Now follow them right. At about 400 molecules the gap has narrowed to almost nothing.
By a thousand, they have converged. And — this is in their supplementary and it is the
honest part — for carbon-13 at the larger training sizes the transferred model is
actually slightly WORSE than training from scratch.

So the shape to internalise: the value of pre-training is largest when you have almost
nothing, and it decays towards zero, and it can go negative.

This makes sense if you think about what pre-training is. It is a prior. When you have
no data, a decent prior is everything. When you have plenty, the prior is at best
irrelevant and at worst a bias you now have to overcome.

Note the domain shift here too: the DFT set was small molecules with H, C, N, O, F.
The experimental set goes up to forty-plus heavy atoms with sulfur and chlorine. It
transferred anyway. That is encouraging.
""")
fig_nmr_crossover(s)
ref(s, "Han & Choi, J. Phys. Chem. Lett. 2021, 12, 3662 — ¹H MAE vs experimental "
       "training-set size (SI Table S2)")

s = S("The same shape, in three different fields", """
Three independent confirmations that the low-data regime is where this lives.

REACTION YIELD. Schwaller's Yield-BERT, pre-trained on unlabelled reaction SMILES,
fine-tuned on the Buchwald-Hartwig HTE set. Ninety-eight reactions — about 2.5% of the
plate — is enough to match DFT descriptors plus a random forest. Think about what that
saves: the DFT route needs you to build and compute descriptors for every ligand,
base and additive. The pre-trained route needs the reaction SMILES.

INTERATOMIC POTENTIALS. MatterSim, pre-trained on 17 million structures. To specialise
it to liquid water at DFT quality you need 3% of the data a from-scratch model needs.
They quote up to a 97% reduction in data requirements.

SUBLIMATION ENTHALPIES. Fine-tuning MACE-MP-0 needs, in the authors' words, a few tens
of training structures for sub-kJ/mol accuracy. Tens. For a property that requires
careful periodic DFT.

Different fields, different architectures, same shape. When labels cost you money or
a week of cluster time, pre-training is the single highest-leverage thing available.

Aside: notice the second and third are potentials, not properties. Same recipe.
""")
fig_low_data_wins(s)

s = S("Foundation models for atoms — the same play, at scale", """
Worth its own slide because several of you work on materials and this is moving fast.

The universal machine-learned interatomic potentials are the most successful example
of pre-training in the chemical sciences right now. M3GNet in 2022 trained on about
190 thousand structures. MACE-MP-0 in 2023, 1.6 million frames from the Materials
Project trajectories. MatterSim, 17 million. Then OMat24 and friends, and Meta's UMA
was trained on roughly 459 million samples.

Roughly six hundred times more training data in three years, and the Matbench
Discovery F1 goes from 0.57 to about 0.92 while the thermal conductivity error metric
drops by more than an order of magnitude.

The practical point is the box on the right. You will essentially never train one of
these. You download it. Then, because your system is a surface with an adsorbate that
was never in the Materials Project, you fine-tune on the fifty to five hundred
structures you can afford to compute yourself.

That is exactly the recipe from two slides ago, applied to potentials rather than
properties. Michael covered MLIPs on Wednesday morning — this is the transfer-learning
view of the same objects.

Fair warning: this leaderboard moves monthly. Check Matbench Discovery rather than
trusting a number from a talk in August 2026.
""")
fig_mlip_scaling(s)
ref(s, "Matbench Discovery (matbench-discovery.materialsproject.org), values as of "
       "11 Aug 2026 · Riebesell et al., Nat. Mach. Intell. 2025, 7, 836")

# =====================================================================
# PART 6
# =====================================================================
section_slide(6, "When it fails", [
    "Negative transfer and the replication problem",
    "Activity cliffs",
    "The baseline you must always run",
])

s = S("The uncomfortable benchmark", """
I want to end on this rather than on the success stories, because it is the part that
will keep you out of trouble.

Praski, Adamczyk and Czech, August 2025. They took twenty-five pre-trained molecular
embedding models and twenty-five datasets, and re-evaluated everything under a
consistent protocol with hierarchical Bayesian testing rather than comparing
leaderboard means.

The result is the quote. Nearly all of the neural models show negligible or no
improvement over plain ECFP fingerprints. Exactly one model was significantly better
— CLAMP — and CLAMP is itself fingerprint-based.

This is consistent with a run of earlier work. Jiang and co-workers found
descriptor-based models beat graph-based ones on average across eleven datasets. Deng
and colleagues trained sixty-two thousand models and found random forest on RDKit
descriptors significantly best on BACE, BBBP, ESOL and Lipophilicity under scaffold
splits.

How to hold this. It does not mean learned representations are worthless — the NMR
and MLIP results two slides ago are real. It means the published gains are much more
fragile and much more dataset-specific than the abstracts suggest, and that the field
has a benchmarking problem: random splits, cherry-picked datasets, baselines copied
rather than tuned.

The actionable conclusion is in the green box, and it is the single most useful
sentence in this lecture: always run ECFP plus random forest first. If your fancy
model cannot beat it, you have learned something valuable and cheap.
""")
fig_benchmark_reality(s)
ref(s, "Praski, Adamczyk & Czech, arXiv:2508.06199 (2025) · Jiang et al., "
       "J. Cheminform. 2021, 13, 12 · Deng et al., Nat. Commun. 2023, 14, 6395")

s = S("Activity cliffs: where smoothness is a lie", """
The specific failure mode that matters most for anyone doing medicinal chemistry, and
it is a direct attack on the central assumption of learned representations.

Everything we have built today assumes similar molecules should have similar
embeddings and therefore similar properties. Activity cliffs are pairs of molecules
that violate that: Tanimoto similarity 0.95, and a two- or three-order-of-magnitude
difference in potency. One methyl group that happens to break a hydrogen bond.

A smooth representation puts these two molecules in nearly the same place, so by
construction it cannot predict both correctly.

Van Tilborg, Alenicheva and Grisoni quantified it across thirty targets and
twenty-four methods. Errors on cliff compounds run from 0.68 to 1.44 log units. And
SVM on ECFP was the best method overall — better than every deep model tested.

Two findings from that paper worth repeating. They tried four self-supervised
pre-training schemes on their GNNs; none gave a notable improvement, so they dropped
transfer learning from the study. And transformers pre-trained on ten million SMILES
did not beat LSTMs pre-trained on thirty-six thousand.

Why this matters practically: your overall RMSE hides this. It looks fine because
most pairs are not cliffs. But the cliffs are exactly the compounds a med chemist
cares about, because they are where the SAR is. Report cliff performance separately.
""")
fig_activity_cliff(s)
ref(s, "van Tilborg, Alenicheva & Grisoni, J. Chem. Inf. Model. 2022, 62, 5938 "
       "(MoleculeACE)")

s = S("So when is a learned representation worth it?", """
Let me try to put the whole lecture into one picture. And I want to be explicit: the
SHAPES here are well supported, the exact position of the crossover is not.

Orange, fingerprints plus a random forest: good immediately, because there is almost
nothing to fit, and it plateaus early because the representation is fixed.

Teal, a deep model from scratch: terrible with little data, because you are fitting
millions of parameters from a few hundred examples, and eventually the best, because
it can learn features tuned to your problem.

Purple, a pre-trained encoder fine-tuned: it starts high, because the features are
already good, and it keeps most of the deep model's ceiling.

Read off the three regimes. Below roughly a thousand labels, fingerprints win or tie
and cost you nothing. Between roughly a thousand and ten thousand is where
pre-training earns its keep — this is the band most of you are in. Above ten thousand
everything converges and the choice stops mattering much.

Where does the crossover really sit? Deng and colleagues put it around six to ten
thousand for the deep models, and noted that pre-trained models were competitive far
earlier. A companion comment in the same issue says deep learning only became
competitive above about a thousand.

And it moves. Noisier labels push it right. Scaffold splits push it right. Narrow,
homogeneous chemistry pushes it left. So measure it on your own data — which is
exactly what the tutorial has you do.
""")
fig_crossover(s)

s = S("What to do on Monday", """
The practical decision, reduced to one question and three answers. This is the slide
to photograph if you did not photograph the NMR one.

Under a hundred labelled examples: do not train a deep model, you will fool yourself.
ECFP plus random forest, or a Gaussian process if you want uncertainty — Ashley covers
that next week with Bayesian optimisation. If you want to try something clever, use
frozen pre-trained embeddings as EXTRA FEATURES alongside your descriptors, not as a
replacement.

A hundred to five thousand: this is the sweet spot. Frozen embeddings first. If that
beats the baseline, try unfreezing the top layers. Report the baseline in your paper
regardless of what happens.

Over ten thousand: train on your own data. Pre-training becomes a convenience — a
better initialisation, faster convergence — rather than a necessity.

The bottom bar applies to all three and it is where most published chemistry ML goes
wrong. Run the baseline. Split by scaffold, not at random. If those two things are in
your workflow you are already ahead of a good fraction of the literature.

And one meta-point: everything in the middle column is testable in an afternoon. The
cost of checking whether pre-training helps YOUR problem is much lower than the cost
of assuming it does.
""")
fig_decision(s)

# =====================================================================
# WRAP-UP
# =====================================================================
s = new_slide("Take-home messages")
bullets(s, [
    "**Labels are the bottleneck, not molecules.** Everything today is a way of "
    "spending unlabelled data to make up for scarce labels.",
    "**Unsupervised methods find real structure** — reaction classes, the periodic "
    "table — but a t-SNE plot tells you about your fingerprint, not about chemistry.",
    "**The VAE's decoder disappointed; its encoder changed the field.** "
    "Pretext task → keep the encoder → reuse it. That is the whole pattern.",
    "**Validity was the easy metric.** 100% valid is achieved by construction and "
    "says nothing about quality, novelty or synthesizability.",
    "**Pre-training is a prior.** Worth ~3× at a hundred labels, worth nothing at "
    "ten thousand, occasionally worth less than nothing.",
    "**Always run ECFP + random forest, and always split by scaffold.** "
    "In the largest independent replication, almost nothing beat that baseline.",
], 0.85, 1.42, 11.7, size=15.5, gap=0.20, lh=0.275)
notes(s, """
Read the six, slowly. Then the closing frame:

The honest summary of this field in 2026 is that learned representations are a
genuine advance whose benefits are much narrower and much more conditional than the
headline papers suggest. They are transformative for interatomic potentials. They are
valuable in the hundreds-to-low-thousands label regime. They are frequently no better
than a 2010 fingerprint on standard property prediction benchmarks.

Knowing which of those three situations you are in is the skill. That is what I
wanted to give you today.

This afternoon at 15:15 you will build a chemical space map, compare a hand-crafted
representation against a pre-trained one on the same task, and plot the learning
curve that decides which one you should use. Bring the question from your own
research.
""")

s = new_slide("Further reading")
bullets(s, [
    "**Chemical VAE** — Gómez-Bombarelli et al., *ACS Cent. Sci.* **2018**, 4, 268",
    "**SELFIES** — Krenn et al., *Mach. Learn.: Sci. Technol.* **2020**, 1, 045024 · "
    "and the critique: Skinnider, *Nat. Mach. Intell.* **2024**, 6, 437",
    "**Pre-training GNNs** — Hu et al., *ICLR* **2020**, arXiv:1905.12265",
    "**MoLFormer** — Ross et al., *Nat. Mach. Intell.* **2022**, 4, 1256 · "
    "**MolCLR** — Wang et al., *Nat. Mach. Intell.* **2022**, 4, 279",
    "**Reaction space** — Schwaller et al., *Nat. Mach. Intell.* **2021**, 3, 144",
    "**Transfer for NMR** — Han & Choi, *J. Phys. Chem. Lett.* **2021**, 12, 3662",
    "**Do they actually help?** — Deng et al., *Nat. Commun.* **2023**, 14, 6395 · "
    "Praski et al., arXiv:2508.06199 (**2025**) · van Tilborg et al., *JCIM* "
    "**2022**, 62, 5938",
    "**Evaluation guidelines** — Bender et al., *Nat. Rev. Chem.* **2022**, 6, 428",
], 0.80, 1.40, 11.8, size=14.5, gap=0.17, lh=0.26)
notes(s, """
If you read only two: Hu et al. for how pre-training is done and how it fails, and
Praski et al. for the current reality check.

If you want the most enjoyable one: Skinnider's paper arguing that invalid SMILES are
actively beneficial. He deliberately broke SELFIES by allowing pentavalent carbon and
the models got better. It is a lovely piece of scientific mischief and it will teach
you more about benchmark design than any methods paper.

All of these are linked from the lecture page on the bootcamp site.
""")

s = new_slide("Questions")
centered(s, "Learned Representations", 2.55, size=30, color=INK, bold=True)
centered(s, "Tutorial · 15:15 · RSC 275", 3.35, size=17, color=TEAL, bold=True)
centered(s, "Chemical space maps · frozen vs learned embeddings · "
            "the learning-curve crossover", 3.85, size=14, color=GRAY, italic=True)
centered(s, "jul@caltech.edu", 4.80, size=14, color=GRAY)
notes(s, """
Questions I usually get, with short answers:

"Which pre-trained model should I actually download?" For SMILES, ChemBERTa-77M-MTR
is a reasonable small default and it is what the tutorial uses. For materials,
MACE-MP-0 or whatever is currently top of Matbench Discovery. But run the frozen
probe before committing.

"Can I pre-train on my own in-house data?" Yes, and it is often better than a public
model if your chemistry is unusual — recall the diversity result. You need roughly
10^5 molecules to make it worthwhile.

"Is a fingerprint a learned representation?" No — but CLAMP shows the line is blurry.
Learned fingerprint-based models are doing well.

"What about LLMs?" Next week, twice: Thursday's assistants lecture and the
transformers lecture.
""")

save("../lecture_07-learned-representations.pptx")
