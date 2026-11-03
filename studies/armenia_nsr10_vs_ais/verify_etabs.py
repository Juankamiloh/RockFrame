"""Comprueba en ETABS dos pórticos extremos del estudio, con su sección NSR-10 bruta.

Requiere Python 3.12, numpy, pandas, pythonnet y ETABS. Uso: python studies/armenia_nsr10_vs_ais/verify_etabs.py
"""
import os
import sys

import pandas as pd

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(AQUI)), "validation"))
import compare_etabs as ce  # noqa: E402

d = pd.read_csv(os.path.join(AQUI, "results.csv"))
d = d[(d.variante == "base") & (d.tipo == "seccion_minima") & (d.modo == "limite_CuTa") & (d.criterio == "NSR10_bruta")]
ce.CASOS.clear()
for M, N in ((7, 10), (1, 10)):
    c = float(d[(d.luces == M) & (d.pisos == N)].c.iloc[0])
    ce.CASOS[f"{M}x{N}"] = dict(L=[5.0] * M, H=[3.0] * N, w=[35.0] * (N - 1) + [25.0], col=(c, c), vig=(0.75 * c, c))
ce.main()
