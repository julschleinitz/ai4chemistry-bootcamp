# AI4Chemical Sciences Bootcamp — Caltech 2026

**Website: https://julschleinitz.github.io/ai4chemistry-bootcamp/**

A two-week intensive training program at Caltech, August 10–22, 2026, on applying
machine learning and AI to the chemical sciences: 15 lectures and 14 hands-on
Google Colab tutorials, plus a hackathon and a personal-project session.

All slides, notebooks and lecture recordings are public and free to reuse.

## Lectures

Slides and recordings: https://julschleinitz.github.io/ai4chemistry-bootcamp/lectures/

| # | Lecture |
|---|---------|
| 1 | Machine learning for chemistry — bootcamp introduction |
| 2 | Molecular representations: from SMILES to graphs |
| 3 | Supervised learning: regression & classification |
| 4 | Neural networks & deep learning |
| 5 | Machine-learned interatomic potentials (MLIPs) |
| 6 | Learned representations: autoencoders, VAEs & pre-training |
| 7 | Retrieval-augmented generation (RAG) |
| 8 | Generative models: diffusion & flow matching |
| 9 | Model interpretability: SHAP, LIME & PDP |
| 10 | Research data stewardship |
| 11 | Design of experiments (DOE) |
| 12 | Bayesian optimization |
| 13 | Active learning |
| 14 | Transformers & chemical language models |
| 15 | Agentic AI for chemistry |

## Tutorials

Every tutorial runs in Google Colab, no local install needed:
https://julschleinitz.github.io/ai4chemistry-bootcamp/tutorials/

Topics include molecular fingerprints and descriptors, model training and
evaluation with scaffold splits, neural networks in PyTorch, MACE interatomic
potentials, few-shot transfer learning for NMR prediction, data stewardship,
molecular generation against a docking oracle, SHAP explanations, DOE,
active learning on DFT descriptors, Bayesian optimization of reaction
conditions, and building a chemistry RAG assistant.

There is also a one-day [OpenADMET hackathon](https://julschleinitz.github.io/ai4chemistry-bootcamp/hackathon_1/)
and a [personal-project session](https://julschleinitz.github.io/ai4chemistry-bootcamp/personnal_project_1/).

## Resources

A curated reading list by topic — representations, GNNs, generative models,
uncertainty quantification, self-driving labs, datasets and more:
https://julschleinitz.github.io/ai4chemistry-bootcamp/resources.html

## Repository layout

```
index.html              schedule / landing page
lectures/               one HTML page per lecture + slide decks
tutorials/              one HTML page per tutorial + Colab notebooks
resources/              curated reading lists by topic
hackathon_1/            OpenADMET hackathon
personnal_project_1/    personal-project session
environment.yml         conda environment for running notebooks locally
```

## Running the notebooks locally

The tutorials are designed for Colab, but you can run them locally:

```bash
conda env create -f environment.yml
conda activate mlchem-bootcamp
jupyter lab
```

## Contributing

The reading lists were built from suggestions made by the community, and they
are meant to keep growing that way.

- **Suggest a resource** — a course, notebook, dataset, paper or tool that
  belongs in the reading lists:
  [open a suggestion](https://github.com/julschleinitz/ai4chemistry-bootcamp/issues/new?template=suggest-a-resource.yml)
- **Report a broken link or an error** — [open an issue](https://github.com/julschleinitz/ai4chemistry-bootcamp/issues/new)
- **Contribute teaching material** — lectures, notebooks or exercises: email
  Jules first so we can agree on scope, then open a pull request.

All material here is free to reuse. If you teach from it, a link back is
appreciated but not required.

## Contact

Jules Schleinitz — jul@caltech.edu
