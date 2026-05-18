# Option & Structured Product Pricing Dashboard

Application web locale en Flask. Elle fournit une page HTML interactive adossée à un backend Python de pricing.

## Fonctionnalités

- Recherche de sous-jacent via `yfinance.Search`
- Spot, volatilité réalisée 1 an, dividend yield et échéances d’options Yahoo Finance
- Consultation simplifiée de chaînes d’options
- Onglet de volatilité implicite :
  - visualisation de la smile pour une échéance ;
  - IV Yahoo Finance ;
  - IV recalculée en Python à partir du midpoint bid/ask par inversion de Black-Scholes ;
  - synthèse ATM, minimum, maximum et disponibilité des points.
- Options vanilles :
  - Black-Scholes
  - Greeks analytiques
  - Volatilité implicite
  - Arbre binomial CRR, européen ou américain
  - Monte Carlo européen
  - Longstaff-Schwartz pour options américaines
- Options exotiques :
  - Asiatiques arithmétiques et géométriques
  - Barrières knock-in / knock-out
  - Gap options
- Pricing multiple par lot
- Produits structurés Monte Carlo simplifiés :
  - Capital protected note
  - Reverse convertible
  - Autocallable note avec barrière de coupon, barrière d’autocall, protection du capital et coupon à mémoire

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Sous Windows :

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Lancement

```bash
python app.py
```

Puis ouvrez :

```text
http://127.0.0.1:5000
```

## Remarques méthodologiques

Les prix de marché et les chaînes d’options proviennent de Yahoo Finance via `yfinance`. Le module convient à l’analyse, au prototypage et à un usage pédagogique. Les produits structurés inclus sont des schémas de valorisation simplifiés, construits pour l’expérimentation quantitative ; ils ne constituent pas un moteur de valorisation transactionnel de salle des marchés.
