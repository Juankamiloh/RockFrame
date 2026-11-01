"""ROCKFRAME contra OpenSees (elasticBeamColumn). Tolerancia 0.1 %.

Requiere Python 3.12, numpy y openseespy. Las fuerzas sísmicas se recalculan aquí con las
fórmulas de la NSR-10, sin usar funciones del motor. Usa los mismos ids de nudo y elemento.
"""
import os
import sys

import numpy as np
import openseespy.opensees as ops

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rockframe import engine as m

G, TOL, FC, GAMMA = 9.8, 0.1, 28.0, 24.0
E = 4700 * np.sqrt(FC) * 1e6
CASOS = {
    "1x2": dict(L=[5.0], H=[3.5, 3.0], w=[25.0, 20.0], col=[(0.4, 0.4)] * 2, vig=[(0.3, 0.45)] * 2),
    "3x3": dict(L=[5.0, 6.0, 5.0], H=[4.0, 3.0, 3.0], w=[30.0, 30.0, 20.0], col=[(0.5, 0.5)] * 3, vig=[(0.35, 0.5)] * 3),
    "3x6": dict(L=[5.0] * 3, H=[4.0] + [3.0] * 5, w=[35.0] * 5 + [25.0], col=[(0.6, 0.6)] * 6, vig=[(0.4, 0.55)] * 6),
    "irregular 4x5": dict(L=[4.0, 7.0, 5.5, 3.0], H=[4.5, 3.2, 3.6, 3.0, 2.8], w=[40.0, 32.0, 28.0, 25.0, 15.0],
                          col=[(0.7, 0.6), (0.6, 0.6), (0.55, 0.5), (0.5, 0.5), (0.4, 0.4)],
                          vig=[(0.4, 0.6), (0.4, 0.55), (0.35, 0.5), (0.3, 0.45), (0.3, 0.4)]),
}
FACTORES = {"bruta": (1.0, 1.0), "fisurada": (0.35, 0.70)}
ESPECTROS = {"Aa.25 I1": dict(Aa=0.25, Av=0.25, Fa=1.3, Fv=1.9, I=1.0), "Aa.15 I1.5": dict(Aa=0.15, Av=0.20, Fa=1.5, Fv=2.2, I=1.5)}
peor = {}


def anota(clave, a, b, escala):
    e = float(np.max(np.abs(np.asarray(a, float) - np.asarray(b, float)))) / escala * 100
    peor[clave] = max(peor.get(clave, 0.0), e)


def nid(c, i, j):
    return 1 + i + (len(c["L"]) + 1) * j


def modelo(c, fv, fc, gravedad=False, nodales=None, laterales=None, masas=None):
    """Construye el pórtico en N y m, con los mismos ids que build_case_gen."""
    ops.wipe(); ops.model("basic", "-ndm", 2, "-ndf", 3)
    x = np.r_[0, np.cumsum(c["L"])]; y = np.r_[0, np.cumsum(c["H"])]
    nx, ny = len(x), len(y)
    for j in range(ny):
        for i in range(nx):
            ops.node(nid(c, i, j), float(x[i]), float(y[j]))
            if j == 0:
                ops.fix(nid(c, i, j), 1, 1, 1)
    ops.geomTransf("Linear", 1)
    ops.timeSeries("Constant", 1); ops.pattern("Plain", 1, 1)
    eid = 1
    for j in range(1, ny):
        bc, hc = c["col"][j - 1]; bv, hv = c["vig"][j - 1]
        for i in range(nx):
            ops.element("elasticBeamColumn", eid, nid(c, i, j - 1), nid(c, i, j), bc * hc, E, fc * bc * hc ** 3 / 12, 1)
            if gravedad:
                ops.eleLoad("-ele", eid, "-type", "-beamUniform", 0.0, -GAMMA * bc * hc * 1e3)
            eid += 1
        for i in range(nx - 1):
            ops.element("elasticBeamColumn", eid, nid(c, i, j), nid(c, i + 1, j), bv * hv, E, fv * bv * hv ** 3 / 12, 1)
            if gravedad:
                ops.eleLoad("-ele", eid, "-type", "-beamUniform", -(c["w"][j - 1] + GAMMA * bv * hv) * 1e3, 0.0)
            eid += 1
    for n, carga in (nodales or {}).items():
        ops.load(n, *carga)
    for n, f in (laterales or {}).items():
        ops.load(n, f, 0.0, 0.0)
    for n, masa in (masas or {}).items():
        ops.mass(n, masa, 0.0, 0.0)
    return eid - 1


def resolver():
    ops.constraints("Plain"); ops.numberer("RCM"); ops.system("BandGeneral"); ops.test("NormUnbalance", 1e-6, 10)
    ops.algorithm("Linear"); ops.integrator("LoadControl", 1.0); ops.analysis("Static")
    assert ops.analyze(1) == 0
    ops.reactions()


def param(c, nodal=None):
    N = len(c["H"])
    return dict(n_bays=len(c["L"]), n_stories=N, bay_widths=c["L"], bay_width=c["L"][0], story_heights=c["H"],
                columns_sections=c["col"], beams_sections=c["vig"], w_level_kNpm=c["w"], nodal_loads=nodal or {})


def Sa_manual(T, e):
    AF, VF = e["Aa"] * e["Fa"], e["Av"] * e["Fv"]; Tc = 0.48 * VF / AF; TL = 2.4 * e["Fv"]
    if T < Tc:
        return 2.5 * AF * e["I"]
    return 1.2 * VF * e["I"] / T if T <= TL else 1.2 * VF * TL * e["I"] / T ** 2


def k_manual(T):
    return 1.0 if T <= 0.5 else (2.0 if T > 2.5 else 0.75 + 0.5 * T)


def W_manual(c):
    nx = len(c["L"]) + 1; L = sum(c["L"]); N = len(c["H"]); W = []
    for j in range(N):
        bv, hv = c["vig"][j]; bc, hc = c["col"][j]
        arriba = GAMMA * c["col"][j + 1][0] * c["col"][j + 1][1] * c["H"][j + 1] * nx / 2 if j + 1 < N else 0.0
        W.append((c["w"][j] + GAMMA * bv * hv) * L + GAMMA * bc * hc * c["H"][j] * nx / 2 + arriba)
    return np.array(W)


corridas = 0
print(f"OpenSees {ops.version()}")
for nc, c in CASOS.items():
    nx, ny = len(c["L"]) + 1, len(c["H"]) + 1
    hi = np.cumsum(c["H"]); Wi = W_manual(c); h = float(hi[-1])
    for nf, (fv, fc) in FACTORES.items():
        # ---------- matricial: w, peso propio y cargas en nudos ----------
        nodales = {nid(c, nx - 1, ny - 1): (15e3, -10e3, 5e3), nid(c, 0, 1): (40e3, 0.0, 0.0)}
        n_el = modelo(c, fv, fc, True, nodales); resolver()
        r = m.run_static_analysis(param(c, {k: tuple(v / 1e3 for v in f) for k, f in nodales.items()}), FC, None, fv, fc, gamma=GAMMA)
        ids = [nid(c, i, j) for j in range(ny) for i in range(nx)]
        Ua = np.array([[r["U"][g] for g in r["dof"].node_dofs[n]] for n in ids])
        Ub = np.array([ops.nodeDisp(n) for n in ids])
        anota("desplazamientos", Ua[:, :2], Ub[:, :2], np.abs(Ub[:, :2]).max()); anota("rotaciones", Ua[:, 2], Ub[:, 2], np.abs(Ub[:, 2]).max())
        Ra = np.array([r["reactions_by_node"][nid(c, i, 0)] for i in range(nx)])
        Rb = np.array([ops.nodeReaction(nid(c, i, 0)) for i in range(nx)])
        anota("reacciones (con signo)", Ra, Rb, np.abs(Rb).max())
        fa = {e[0]: np.array(e[1:]) for e in r["elem_forces_local"]}
        Fa = np.array([fa[e] for e in range(1, n_el + 1)])
        Fb = np.array([ops.eleResponse(e, "localForce") for e in range(1, n_el + 1)])
        for nom, col in (("axial N (con signo)", [0, 3]), ("cortante V (con signo)", [1, 4]), ("momento M (con signo)", [2, 5])):
            anota(nom, Fa[:, col], Fb[:, col], np.abs(Fb[:, col]).max())
        corridas += 1

        # ---------- sísmico ----------
        for ne, e in ESPECTROS.items():
            sp = dict(ciudad="", amenaza="", suelo="", Ae=None, Ad=None, h_m=h, grupo_label="", **e)
            for modo in ("limite_CuTa", "sin_limite"):
                s = m.run_seismic_iterative(param(c), FC, None, GAMMA, fv, fc, sp, h, 0.047, 0.9, 20, 0.01, periodo_diseno=modo)
                T = s["T_diseno"]; Ta = 0.047 * h ** 0.9; Cu = max(1.75 - 1.2 * e["Av"] * e["Fv"], 1.2)
                Sa = Sa_manual(T, e); V = Sa * Wi.sum(); kx = k_manual(T)
                Fi = Wi * hi ** kx / np.sum(Wi * hi ** kx) * V
                anota("Wi", s["Wi"], Wi, Wi.max()); anota("Sa", [s["Sa"]], [Sa], Sa); anota("V", [s["V"]], [V], V); anota("Fi", s["Fi"], Fi, Fi.max())
                lat = {nid(c, i, j): Fi[j - 1] * 1e3 / nx for j in range(1, ny) for i in range(nx)}
                modelo(c, fv, fc, laterales=lat); resolver()
                dp = np.array([np.mean([ops.nodeDisp(nid(c, i, j), 1) for i in range(nx)]) for j in range(1, ny)])
                anota("despl. por piso", s["disp_piso"], dp, dp.max())
                dr = np.abs(np.diff(np.r_[0, dp])) / np.array(c["H"]) * 100
                anota("deriva", s["drift_pct"], dr, dr.max())
                TR = 2 * np.pi * np.sqrt(np.sum(Wi * dp ** 2) / (G * np.sum(Fi * dp)))
                anota("T Rayleigh", [s["T_detallado"]], [TR], TR)
                anota("T diseño", [T], [min(TR, Cu * Ta) if modo == "limite_CuTa" else TR], T)
                Fs = {x[0]: np.array(x[1:]) for x in s["elem_forces_local"]}
                n_e = len(Fs)
                Sa_ = np.array([Fs[q] for q in range(1, n_e + 1)]); Sb_ = np.array([ops.eleResponse(q, "localForce") for q in range(1, n_e + 1)])
                anota("fuerzas sísmicas (con signo)", Sa_, Sb_, np.abs(Sb_).max())
                corridas += 1

        # ---------- modal propio de OpenSees ----------
        masas = {nid(c, i, j): Wi[j - 1] * 1e3 / G / nx for j in range(1, ny) for i in range(nx)}
        modelo(c, fv, fc, masas=masas)
        T1 = 2 * np.pi / np.sqrt(ops.eigen("-fullGenLapack", 1)[0])
        s = m.run_seismic_iterative(param(c), FC, None, GAMMA, fv, fc,
                                    dict(ciudad="", amenaza="", suelo="", Ae=None, Ad=None, h_m=h, grupo_label="", **ESPECTROS["Aa.25 I1"]),
                                    h, 0.047, 0.9, 20, 0.01, periodo_diseno="sin_limite")
        print(f"{nc:14s} {nf:9s} T_Rayleigh={s['T_detallado']:.4f}  T_modo1={T1:.4f}  dif={(s['T_detallado'] / T1 - 1) * 100:+.3f}%")

print(f"\n{corridas} corridas. Error máximo por resultado (tolerancia {TOL} %):")
mal = 0
for clave, v in sorted(peor.items(), key=lambda t: -t[1]):
    print(f"  {clave:30s} {v:.6f} %  {'OK' if v <= TOL else 'FALLA'}"); mal += v > TOL
print("RESULTADO:", "TODO DENTRO DE TOLERANCIA" if not mal else f"{mal} FUERA DE TOLERANCIA")
