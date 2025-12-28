---
layout: page
title: FX Strategies 
description: Python study on FX Momentum and PPP strategy
img: assets/img/distrib bar mom return.png
importance: 1
category: Academical
related_publications: false

---
# FX Momentum and Value Strategies

This project implements a short-horizon cross-sectional FX momentum strategy and
compares its performance to a PPP-based value strategy. The analysis follows the
steps required by a university course assignment and combines empirical portfolio
construction with realistic transaction cost adjustments.

---

## Overview

The project studies two systematic FX strategies:

- A **short-term FX momentum strategy**, based on recent currency return rankings
- A **PPP-based value strategy**, using forward–spot deviations as a proxy for
  purchasing power parity mispricing

The analysis covers data preparation, portfolio formation, transaction costs,
sub-sample performance, and strategy comparison.

---

## Main Analysis (Jupyter Notebook)

> **The core of the project is the Jupyter notebook.**

All data processing, portfolio construction, empirical analysis, and visualizations
are performed in the notebook:

- [Python strategy](assets/code/FX/Fx_mom_ppp.ipynb)

This notebook contains the complete workflow and should be consulted to fully
understand the methodology and results.

---

## Research Paper (Assignment)

The file:

- [Research paper](assets/code/FX/FX_Momentum.pdf)

is a short research paper (maximum 5 pages), written as a **group assignment** in the
context of a university course. The paper presents the methodology, empirical results,
and economic interpretation of the strategies.

**My contribution focused on the full implementation of the strategies and the
underlying code**, including data processing, portfolio construction, and transaction
cost modeling, all of which are detailed in the Jupyter
notebook.

---

## Data

The analysis uses the Excel files provided for the assignment:

- [Daily spot exchange rates](assets/code/FX/assignment_spot_rates.xlsx)
- [Daily forward exchange rates](assets/code/FX/assignment_fwd_rates.xlsx)

These files are cleaned and processed directly in the notebook.

---

## Strategies Implemented

### FX Momentum Strategy
- Cross-sectional ranking of currencies based on recent returns
- Monthly portfolio formation
- Long winners, short losers
- Equal-weighted portfolios
- Transaction costs explicitly incorporated

### PPP Value Strategy
- Proxy for PPP mispricing using forward–spot deviations
- Cross-sectional portfolio construction
- Comparison with the momentum strategy
- Gross and net performance evaluation

---

## Key Features

- Fully vectorized implementation using pandas
- Explicit and implicit transaction cost modeling
- Sub-sample analysis across major macroeconomic periods
- Comparison between momentum and value strategies

---

## Conclusion

The project provides an empirical comparison between short-term FX momentum and
PPP-based value strategies. Results highlight the importance of transaction costs,
market regimes, and cross-sectional effects in currency markets.