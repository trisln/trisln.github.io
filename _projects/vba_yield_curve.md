---
layout: page
title: Yield curve - VBA
description: Linear interpolation and Nelson-Siegel
img: assets/img/courbe taux exemple.jpg
importance: 2
category: Extra
giscus_comments: false
---
---

## Overview

This project implements a **yield curve calibration engine** in Excel using
**object-oriented VBA** and an external **Access database**.
The tool builds zero-coupon yield curves for a given country and date,
using both **linear regression** and the **Nelson–Siegel parametric model**.

The objective is to reproduce professional fixed-income modelling practices
within a constrained Excel/VBA environment.

---

## Financial Motivation

Yield curve modelling is a core component of:
- fixed-income pricing,
- interest rate risk management,
- macro-financial analysis.

A well-calibrated term structure allows market participants to analyse
expectations, risk premia and monetary conditions across maturities.

---

## Models Implemented

We modeled two types of yield curve :

### Linear regression
A simple benchmark calibration of zero-coupon rates across maturities.

### Nelson–Siegel model
A parametric representation of the yield curve capturing:
- level,
- slope,
- curvature.

The model is defined as:
$
\
y(\tau) = \beta_0 + \beta_1 \frac{1 - e^{-\tau/\lambda}}{\tau/\lambda} + \beta_2 \left(\frac{1 - e^{-\tau/\lambda}}{\tau/\lambda} - e^{-\tau/\lambda}\right)
\
$

---

## Software Architecture

The project follows a modular, object-oriented design:

- **Database layer**: Access database storing historical zero-coupon rates
- **Domain layer**: Yield curve abstraction and data formatting
- **Model layer**: Calibration engines (Linear, Nelson–Siegel)
- **Interface layer**: Excel UserForm orchestrating execution

This structure ensures clarity, extensibility and separation of concerns. Since, we followed those different steps :

---

### Step 1 — User interface initialization

The process starts with the initialization of an Excel UserForm, which serves as the single entry point for the user.

At this stage:

- available countries are loaded,

- available dates are retrieved,

- the choice of calibration method (linear or Nelson–Siegel) is enabled.

This design ensures that all user inputs are validated before any computation starts.

(We added before a dynamic in the sheet to allow to find the database of anyone to be connected to the UserForm.)

<div class="row justify-content-center">
    <div class="col-sm-6 mt-3 mt-md-0">
        {% include figure.liquid loading="eager" path="assets/img/userform.png" title="example image" class="img-fluid rounded z-depth-1" %}
    </div>
</div>
<div class="caption">
    UserForm available for the user.
</div>

--- 

### Step 2 — Connection to the market data database

Once the user confirms their selection, the application establishes a connection to an Access database containing historical zero-coupon yield data.

The database layer is fully isolated from the rest of the application:

- it handles data storage,

- it performs SQL queries,

- it exports raw yield data to Excel.

This separation improves maintainability and allows easy updates of market data without modifying the pricing logic.

<details markdown="1">
<summary><strong>Show VBA implementation</strong></summary>

```vb
' Open the connection to the Access database
Public Sub Ouverture_Connexion()

    Dim chemin As String
    Dim fd As FileDialog

    ' Create the box to select the database file
    Set fd = Application.FileDialog(msoFileDialogFilePicker)

    With fd
        .Title = "Sélectionnez la base de données Access (.accdb)"
        .Filters.Clear
        .Filters.Add "Access Database", "*.accdb"
        .AllowMultiSelect = False

        ' If user cancels.
        If .Show <> -1 Then
            MsgBox "Aucune base de données sélectionnée.", vbExclamation
            Exit Sub
        End If

        ' Get the path file
        chemin = .SelectedItems(1)
    End With

    ' Open the connection
    Set conn = CreateObject("ADODB.Connection")
    conn.ConnectionString = _
        "Provider=Microsoft.ACE.OLEDB.12.0;Data Source=" & chemin
    conn.Open

End Sub


' Verify the connexion
Public Property Get Connecté() As Boolean
    Connecté = Not (conn Is Nothing)
End Property

' Execute SQL request
Public Function Executer_Requête(sql As String) As Object

    Dim rs As Object
    Set rs = CreateObject("ADODB.Recordset")
    rs.Open sql, conn, 1, 1
    Set Executer_Requête = rs
    
End Function

' Close database connection.
Public Sub Fermeture_Connexion()

    If Not (conn Is Nothing) Then
        conn.Close
    End If
    Set conn = Nothing
    
End Sub
```
</details>

---

### Step 3 — Yield curve object construction

The extracted market data is then passed to a YieldCurve (CourbeDeTaux) object, which acts as the core data structure of the project.

This object:

- Store yield curve data as maturity–rate pairs

- Convert market tenors (e.g. 6M, 10Y) into numerical maturities (years)

- Load and clean market data from an Access database

- Provide sorted maturities for interpolation, calibration, and plotting

- Expose a unified interface for downstream models (linear interpolation, Nelson–Siegel)-

By centralizing all yield-related operations, the project avoids code duplication and ensures consistency across models.

---

### Step 4 — Linear regression and Nelson-siegel calibration

If the user selects the **linear regression** approach, the application calls the LinearRegression model.

This step:

- estimates a linear relationship between yields and maturities,

- serves as a baseline calibration method,

- produces regression outputs and a fitted yield curve.

- The results are displayed in dedicated Excel sheets:

- one sheet for regression coefficients,

- one sheet for the calibrated yield curve and chart.

<details markdown="1">
<summary><strong>Show VBA implementation</strong></summary>

```vb
Option Explicit

' Calibre les paramètres du modèle via LinEst

Public Sub Calibrer(tenors() As Double, yields() As Double, ws As Worksheet) 
' Feuille qu'on nommera "Reg_Linéaire" qui contiendra les données et les résultats de l'optimisation via LinEst
    Dim i As Long, n As Long
    Dim Formule_Linéaire As String
    Dim coef As Variant
    
    n = UBound(tenors) - LBound(tenors) + 1
    
    ' Stockage des données
    ws.Range("A1").Value = "Ténors (années)"
    ws.Range("B1").Value = "Taux observés (%)"
    ws.Range("C1").Value = "Taux prédits (%)"
    
    Dim ligne_données As Long
    ligne_données = 2 'Première ligne de stockage des valeurs des taux et ténors
    
    For i = 1 To n
        ws.Cells(ligne_données + i - 1, 1).Value = tenors(i - 1) 'Stocke les ténors
        ws.Cells(ligne_données + i - 1, 2).Value = yields(i - 1) 'Stocke les taux observés
    Next i
    
    ws.Columns.AutoFit
    
    ' Régression linéaire avec LinEst (DROITEREG)
    coef = Application.WorksheetFunction.LinEst(ws.Range("B2:B" & ligne_données + n - 1), ws.Range("A2:A" & ligne_données + n - 1), True, True)

    ' Application de la régression pour prédire les taux (y = a * x + b)
    For i = 1 To n
        ws.Cells(ligne_données + i - 1, 3).Value = coef(1, 1) * ws.Cells(ligne_données + i - 1, 1).Value + coef(1, 2)
    Next i
    
    ' Affichage direct des résultats finaux
     MsgBox "Calibration réussie. Paramètres obtenus :" & vbCrLf & _
           "Pente (a) : " & coef(1, 1) & vbCrLf & _
           "Ordonnée à l'origine (b): " & coef(1, 2)
    
End Sub
```
</details>

---
### Step 5 — Nelson–Siegel parametric calibration

Alternatively, the user can select **the Nelson–Siegel parametric model**, a standard approach in fixed-income modelling.

In this step:

- the Nelson–Siegel parameters are estimated,

- the model captures level, slope and curvature of the yield curve,

- a smooth term structure is generated across maturities.

The outputs are written to:

- a dedicated Nelson–Siegel regression sheet,

- a yield curve visualization sheet.

<details markdown="1">
<summary><strong>Show VBA implementation</strong></summary>

```vb
Option Explicit

Private pBeta0 As Double
Private pBeta1 As Double
Private pBeta2 As Double
Private pLambda As Double

Public Property Get Beta0() As Double
    Beta0 = pBeta0
End Property

Public Property Let Beta0(ByVal val As Double)
    pBeta0 = val
End Property


Public Property Get Beta1() As Double
    Beta1 = pBeta1
End Property

Public Property Let Beta1(ByVal val As Double)
    pBeta1 = val
End Property


Public Property Get Beta2() As Double
    Beta2 = pBeta2
End Property

Public Property Let Beta2(ByVal val As Double)
    pBeta2 = val
End Property


Public Property Get Lambda() As Double
    Lambda = pLambda
End Property

Public Property Let Lambda(ByVal val As Double)
    pLambda = val
End Property


' Calibre les paramètres du modèle via Solver

Public Sub Calibrer(tenors() As Double, yields() As Double, ws As Worksheet) 
' Feuille qu'on nommera "Reg_NelsonSiegel" qui contiendra les données et les résultats de l'optimisation via Solver
                                                                                                                         

    Dim i As Long, n As Long
    Dim Formule_NS As String
    
    n = UBound(tenors) - LBound(tenors) + 1
    
    ' Stockage des données
    ws.Range("A1").Value = "Ténors (années)"
    ws.Range("B1").Value = "Taux observés (%)"
    ws.Range("C1").Value = "Taux prédits (%)"
    
    Dim ligne_données As Long
    ligne_données = 2 'Première ligne de stockage des valeurs des taux et ténors
    
    For i = 1 To n
        ws.Cells(ligne_données + i - 1, 1).Value = tenors(i - 1)
        ws.Cells(ligne_données + i - 1, 2).Value = yields(i - 1)
    Next i
    
    ' Initialisation des paramètres du modèle de Nelson-Siegel
    '
    ' Selon Diebold et Li (2006), les trois facteurs de la courbe des taux
    ' - le niveau, la pente et la courbure - peuvent être approximés par :
    '   - Niveau (B0) : le taux long terme (30 ans)
    '   - Pente (B1) : l'écart entre le taux long terme et le taux court terme (30 ans - 3 mois)
    '   - Courbure (B2) : une combinaison des taux moyen, court et long terme
    '     définie comme : 2 * Taux(15 ans) - (Taux(10 ans) + Taux(3 mois))
    '
    ' On utilisera ces valeurs comme valeurs initiales pour la calibration
    ' du modèle de Nelson-Siegel via Solver. La calibration étant sensible aux
    ' valeurs initiales, leur choix basé sur cette méthode permet d'améliorer
    ' la convergence et la stabilité de l'optimisation.

    Dim j As Long
    Dim taux30 As Double, taux15 As Double, taux10 As Double, taux3m As Double
    
    ' Parcourir la colonne A pour trouver les taux correspondants
    For j = 2 To n + 1
        Select Case ws.Cells(j, 1).Value
            Case 30: taux30 = ws.Cells(j, 2).Value
            Case 15: taux15 = ws.Cells(j, 2).Value
            Case 10: taux10 = ws.Cells(j, 2).Value
            Case 0.25: taux3m = ws.Cells(j, 2).Value ' 0.25 an = 3 mois
        End Select
    Next j
    
    ws.Range("E1").Value = "Beta0"
    ws.Range("E2").Value = "Beta1"
    ws.Range("E3").Value = "Beta2"
    ws.Range("E4").Value = "Lambda"

    ' Initialisation des paramètres de Nelson-Siegel
    ws.Range("F1").Value = taux30 ' B0 = Taux 30 ans
    ws.Range("F2").Value = taux30 - taux3m ' B1 = Taux 30 ans - Taux 3 mois
    ws.Range("F3").Value = 2 * taux15 - (taux10 + taux3m) ' B2 = 2*Taux 15 ans - (Taux 10 ans + Taux 3 mois)
    ws.Range("F4").Value = 1   ' Lambda
        
    ' Formule du taux prédit par le modèle
    Dim r As Long
    For i = 1 To n
        r = ligne_données + i - 1
        Formule_NS = "= $F$1 + $F$2*((1-EXP(-$F$4*A" & r & "))/($F$4*A" & r & "))" & _
                          " + $F$3*(((1-EXP(-$F$4*A" & r & "))/($F$4*A" & r & "))-EXP(-$F$4*A" & r & "))"
        ws.Cells(r, 3).Formula = Formule_NS
    Next i
    
    ' Somme des carrés des écarts entre taux observés et coourbe ajustée en I1
    ws.Range("H1").Value = "Min écarts"
    ws.Range("I1").Formula = "=SUMXMY2(B" & ligne_données & ":B" & ligne_données + n - 1 & _
                             ", C" & ligne_données & ":C" & ligne_données + n - 1 & ")"
    ws.Columns.AutoFit
    
    ' Configuration Solver
    SolverReset
    SolverOk SetCell:=ws.Range("I1"), MaxMinVal:=2, ByChange:=ws.Range("F1:F4")
    
    ' On impose Lambda >= 0.0001 et <= 10 pour éviter des valeurs extrêmes
    SolverAdd CellRef:=ws.Range("F4"), Relation:=3, FormulaText:="0.0001"
    SolverAdd CellRef:=ws.Range("F4"), Relation:=1, FormulaText:="10"
    
    SolverOptions Precision:=0.001, AssumeNonNeg:=False
    SolverSolve UserFinish:=True
    
    ' Récupère les paramètres calibrés
    pBeta0 = ws.Range("F1").Value
    pBeta1 = ws.Range("F2").Value
    pBeta2 = ws.Range("F3").Value
    pLambda = ws.Range("F4").Value
    
    ' Affichage direct des résultats finaux
    MsgBox "Calibration réussie. Paramètres obtenus :" & vbCrLf & _
           "Beta0 = " & pBeta0 & vbCrLf & _
           "Beta1 = " & pBeta1 & vbCrLf & _
           "Beta2 = " & pBeta2 & vbCrLf & _
           "Lambda = " & pLambda
           
End Sub
```
</details>
---
### Final Step — Automated Sheet Management and End-to-End Demonstration

<div style="text-align: justify; text-justify: inter-word;margin-bottom: 2rem;">

To ensure clarity, robustness, and usability, the application automatically manages Excel worksheets during execution. Obsolete sheets are deleted, and only those relevant to the selected calibration model are regenerated, preventing clutter and duplicated outputs. As a result, the workbook always reflects the most recent calibration results.

</div>
<div style="text-align: justify; text-justify: inter-word;">
The project concludes with a full end-to-end functional demonstration. The user selects the input parameters, the model executes the complete pipeline, and the calibrated yield curve is displayed graphically. Two calibration methods are implemented and demonstrated: linear regression and Nelson–Siegel. This final step validates the correctness, consistency, and practical usability of the tool.
</div>

<div class="row" style="margin-top: 2rem;">
    <div class="col-sm-4 mt-3 mt-md-0">
        {% include figure.liquid loading="eager" path="assets/img/reg_lin_feuille.png" title="example image" class="img-fluid rounded z-depth-1" %}
    </div>
    <div class="col-sm mt-3 mt-md-0">
        {% include figure.liquid loading="eager" path="assets/img/reg_lin_courbe.png" title="example image" class="img-fluid rounded z-depth-1" %}
    </div>
</div>
<div class="caption">
    Linear regression obtained : sheet and curve.
</div>

<div class="row" style="margin-top: 2rem;">
    <div class="col-sm mt-3 mt-md-0">
        {% include figure.liquid loading="eager" path="assets/img/reg_NS_feuille.png" title="example image" class="img-fluid rounded z-depth-1" %}
    </div>
    <div class="col-sm mt-3 mt-md-0">
        {% include figure.liquid loading="eager" path="assets/img/reg_NS_curve.png" title="example image" class="img-fluid rounded z-depth-1" %}
    </div>
</div>
<div class="caption">
    Nelson-Siegel regression obtained : sheet and curve.
</div>

<!-- col-sm-6 = 50 %
col-sm-4 = 33 %
col-sm-3 = 25 % -->
---

⚠️ Warning : 
Due to the use of an Access database and ADODB (ACE OLEDB provider), this project is designed to run on Excel for Windows.
Access databases are not supported on Excel for macOS.

---

## Appendix :

📥 [Download the Excel implementation](assets/code/Yield Curve - LE NEST.xlsm)

📥 [Download the Access database](assets/code/Base de données Access - LE NEST.accdb)