---
layout: page
title: Option pricing library
description: Python
img: assets/img/MC_Sim.jpg
importance: 3
category: Extra
---
This project is a comprehensive Python-based options pricing library designed to value vanilla and exotic derivatives using industry-standard quantitative models. The library emphasizes numerical accuracy, performance, and extensibility, and is complemented by an interactive user interface for real-time analysis.

---
## Overview

The objective of this project is to build a robust, modular, and scalable pricing engine capable of handling a wide range of derivative products. The implementation follows best practices in quantitative finance and numerical methods, making it suitable for both academic and professional use.

The library supports multiple pricing methodologies, Greeks computation, implied volatility extraction, and advanced option structures, while ensuring computational efficiency through vectorization and optimized algorithms.

---
## Pricing Models Implemented

Black–Scholes model
- Closed-form pricing for European options
- Analytical Greeks (Delta, Gamma, Vega, Theta, Rho)
- Implied volatility extraction

Monte Carlo simulations
- Pricing of path-dependent options
- Variance reduction techniques
- Convergence diagnostics

Binomial trees
- European and American options
- Flexible time discretization

Longstaff–Schwartz algorithm
- Least-squares Monte Carlo pricing for American options
- Early exercise feature modeling

---
## Supported derivative products

Vanilla options
- European calls and puts
- American calls and puts

Exotic options
- Asian options (arithmetic and geometric)
- Barrier options
- Gap options

Option strategies
- Multi-leg strategies
- Portfolio-level payoff aggregation

---
## Performance and Optimization

- Vectorized computations using NumPy
- Efficient simulation pipelines for large-scale Monte Carlo runs
- Modular architecture enabling easy extension to new products or models
 
---
## Testing and Validation Framework

A comprehensive testing framework ensures:
- Numerical accuracy of pricing formulas
- Stability and convergence of stochastic methods
- Consistency between analytical and numerical Greeks
- Robustness across parameter regimes
 
---
## Interactive Dashboard

An interactive Streamlit dashboard is provided to:
- Input option parameters dynamically
- Run pricing models end-to-end
- Visualize prices, Greeks, and convergence behavior in real time
- Compare pricing methods across models
This feature transforms the library into a practical experimentation and demonstration tool.
 
--- 
Technologies Used
- Python : NumPy, SciPy, Pandas, Streamlit, Matplotlib / Plotly, PyTest

---
📥 [Download the Python Notebook](assets/code/python_BSM_and_others.ipynb)

---
## Currently working on

The following extensions are currently under development to further enhance the realism and market relevance of the library:

**Implied Volatility Surface Analysis**
- Construction and visualization of implied volatility surfaces across strikes and maturities, including volatility skew and term structure analysis. This module will enable 2D and 3D representations of implied volatility dynamics.

**Market Data Ingestion Pipeline**
- Automated retrieval and processing of real option chain data (e.g. via Yahoo Finance or equivalent sources), including filtering by maturity and strike and systematic implied volatility extraction.

**Model vs Market Comparisons**
- Explicit comparison between theoretical model outputs and observed market prices and implied volatilities, highlighting model limitations and calibration errors through dedicated visualizations.

These additions aim to bridge the gap between theoretical pricing models and real-world option markets, further strengthening the analytical depth of the project.


<!-- Vincent Courtehoux 
Bibliothèque de pricing d'options juin 2025 - aujourd'hui
• Développement d'une bibliothèque de valorisation d'options en Python couvrant les produits vanilles et exotiques, en s'appuyant sur des modèles quantitatifs reconnus
• Implémentation de plusieurs méthodes de pricing : Black-Scholes, simulations de Monte Carlo, arbres binomiaux, et
Longstaff-Schwartz pour les options américaines
• Valorisation d'options européennes et américaines avec prise en charge de l'extraction de volatilité implicite et du calcul des Greeks
• Extension de la librairie aux dérivés exotiques tels que options asiatiques, options barrières et gap options
• Vectorisation des calculs de pricing pour améliorer significativement les performances et la scalabilité
• Implémentation de stratégies sur options
• Mise en place d'un framework de tests robuste garantissant l'exactitude numérique, la stabilité de convergence et la fiabilité des modèles
• Développement d'un tableau de bord interactif sous Streamlit permettant la saisie des paramètres, l'exécution des simulations et la visualisation en temps réel des prix et sensibilités-->
