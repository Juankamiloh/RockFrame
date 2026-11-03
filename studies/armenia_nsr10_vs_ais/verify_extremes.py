"""Comprueba contra OpenSees los pórticos extremos del estudio, con sus secciones finales.

Requiere Python 3.12, numpy, pandas y openseespy. Uso: python studies/armenia_nsr10_vs_ais/verify_extremes.py
"""
import os
import sys

import numpy as np
import openseespy.opensees as ops
import pandas as pd

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import run_study as r  # noqa: E402

E = 4700 * np.sqrt(r.FC) * 1e6
CASOS = [(1, 1), (1, 10), (7, 1), (7, 10), (5, 5), (3, 6), (2, 8)]
CRITERIOS = ("NSR10_bruta", "AIS100_fisurada", "NSR10_fisurada")


def opensees(M, N, c, rigidez, s):
    fv, fc = r.FACTORES[rigidez]
    ops.wipe(); ops.model("basic", "-ndm", 2, "-ndf", 3)
    nx = M + 1
    nid = lambda i, j: 1 + i + nx * j
    for j in range(N + 1):
        for i in range(nx):
            ops.node(nid(i, j), i * r.LUZ, j * r.ALTURA)
            if j == 0:
                ops.fix(nid(i, j), 1, 1, 1)
    ops.geomTransf("Linear", 1)
    bv, hv = r.ANCHO_VIGA * c, r.PERALTE_VIGA * c
    e = 1
    for j in range(1, N + 1):
        for i in range(nx):
            ops.element("elasticBeamColumn", e, nid(i, j - 1), nid(i, j), c * c, E, fc * c ** 4 / 12, 1); e += 1
        for i in range(M):
            ops.element("elasticBeamColumn", e, nid(i, j), nid(i + 1, j), bv * hv, E, fv * bv * hv ** 3 / 12, 1); e += 1
    ops.timeSeries("Constant", 1); ops.pattern("Plain", 1, 1)
    for j in range(1, N + 1):
        for i in range(nx):
            ops.load(nid(i, j), s["Fi"][j - 1] * 1e3 / nx, 0.0, 0.0)
            ops.mass(nid(i, j), s["Wi"][j - 1] * 1e3 / 9.8 / nx, 0.0, 0.0)
    ops.constraints("Plain"); ops.numberer("RCM"); ops.system("BandGeneral"); ops.test("NormUnbalance", 1e-6, 10)
    ops.algorithm("Linear"); ops.integrator("LoadControl", 1.0); ops.analysis("Static")
    assert ops.analyze(1) == 0
    d = np.array([np.mean([ops.nodeDisp(nid(i, j), 1) for i in range(nx)]) for j in range(1, N + 1)])
    ops.wipeAnalysis()
    T1 = 2 * np.pi / np.sqrt(ops.eigen("-fullGenLapack", 1)[0])
    return d, T1


d = pd.read_csv(os.path.join(AQUI, "results.csv"))
d = d[(d.variante == "base") & (d.tipo == "seccion_minima") & (d.modo == "limite_CuTa")]
peor_d = peor_t = 0.0
print("pórtico  criterio            c      deriva %   dif. despl. %   T Rayleigh  T modo 1  dif. %")
for M, N in CASOS:
    for cr in CRITERIOS:
        c = float(d[(d.luces == M) & (d.pisos == N) & (d.criterio == cr)].c.iloc[0])
        rigidez = r.CRITERIOS[cr][0]
        s = r.analizar(M, N, c, rigidez, "limite_CuTa")
        dp, T1 = opensees(M, N, c, rigidez, s)
        e = float(np.max(np.abs(np.array(s["disp_piso"]) - dp)) / dp.max() * 100)
        dt = (s["T_detallado"] / T1 - 1) * 100
        peor_d = max(peor_d, e); peor_t = max(peor_t, abs(dt))
        print(f"{M}x{N:<6d} {cr:18s} {c:.3f} {max(s['drift_pct']):9.4f} {e:13.2e} {s['T_detallado']:11.4f} {T1:9.4f} {dt:+7.3f}")
print(f"Máxima diferencia en desplazamientos: {peor_d:.2e} %. Máxima en período: {peor_t:.3f} %.")
assert peor_d < 0.1
