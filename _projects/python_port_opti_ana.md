---
layout: page
title: Portfolio optimization and analysis
description: Python
img: assets/img/python1.png
importance: 2
category: Academical
giscus_comments: false
---

# Project Overview

---

## Portfolio Analysis and Optimization by Sector Using Python

This project implements a comprehensive sector-based portfolio analysis and optimization framework using Python and common data science libraries. The goal is to leverage financial market data (via yfinance), pandas for data manipulation, and SciPy, matplotlib, seaborn, and scikit-learn for optimization and visualization to explore portfolio performance across asset classes and sectors. 

---

## Key Objectives

#### Data Collection and Preparation
Retrieve financial instrument data (ETFs, equities, mutual funds) for major sectors using yfinance. Download historical price data for the period 2010–2024, clean and structure it into analysis-ready formats. 

#### Performance Analysis by Sector
Calculate historical returns and compare performance across instruments within each sector. Generate visualizations to illustrate differences between ETFs, companies, and mutual funds within sectors. 

#### Intrasector Portfolio Optimization
Apply optimization routines to determine optimal intra-sector portfolios using objectives such as variance minimization, Sharpe ratio maximization, and diversification maximization. Rebalance quarterly based on historical return windows. 

#### Intersector and Global Optimization
Construct sector-level aggregated portfolios and optimize asset allocations both between sectors and across all instruments regardless of sector. Benchmark results against standard strategies such as the S&P 500 and equal-weighted portfolios. 

#### Clustering and Group-Based Optimization
Use machine learning (e.g., K-means) to identify homogeneous groups of instruments based on historical returns and perform optimization under group constraints. 


#### Visualization and Interpretation
Produce charts and tables to illustrate portfolio evolution, optimized weights over time, and cluster structures, accompanied by interpretive commentary on methodology and results. 

---

## Methodology

#### Instrument Selection
For each sector, construct lists of top ETFs, mutual funds, and equities via yf.Sector(...). 


#### Time Series Returns
Compute daily returns and apply data quality filters to ensure robust return histories.

#### Optimization Frameworks
Use optimization functions from SciPy to compute efficient portfolios under multiple risk-reward criteria.

#### Clustering Analysis
Apply clustering techniques (e.g., K-means) to group instruments and observe whether group structures improve optimization outcomes.

#### Benchmarks
Compare optimized portfolios to common benchmarks like the S&P 500 and equal-weight portfolios.

---

## Tools and Libraries

The following tools and libraries are used in the project:

- Data Collection: yfinance
- Data Manipulation: pandas, numpy
- Optimization: SciPy.optimize
- Visualization: matplotlib, seaborn
- Machine Learning: scikit-learn

Notebook Environment: Jupyter Notebook 

--- 
## Output

The main deliverable is a fully executable Jupyter Notebook (.ipynb) that performs the entire analysis end-to-end. The notebook includes installation instructions, code cells with commentary, visualizations, and final portfolios with performance summaries. 
Rémi Genet – Research & Teaching

--- 
### Link to Notebook

Notebook (Python) implementation - the file is currently under an improvement :
[Download the Python implementation](assets/code/Opti_portfolio_LE_NEST (1).ipynb)
