"""ROCKFRAME contra ETABS por su API oficial. Tolerancia 0.1 %.

Requiere Python 3.12, numpy, pythonnet y ETABS con licencia. Uso:
    python validation/compare_etabs.py [casos separados por coma]

El modelo de ETABS se ajusta a la teoría de ROCKFRAME: pórtico en el plano XZ, sin deformación por
cortante, sin zonas rígidas, sin diafragma, sin P-Delta y con masas puntuales iguales a Wi/g.
"""
import json
import os
import sys

import clr
import numpy as np

RUTA = os.environ.get("ETABS_DIR", r"D:\2. UNIVERSIDAD\PROGRAMAS")
TRABAJO = os.environ.get("ETABS_TRABAJO", os.path.join(os.environ["TEMP"], "rf_etabs"))
clr.AddReference(os.path.join(RUTA, "ETABSv1.dll"))
import ETABSv1 as E  # noqa: E402
from System import Array, Boolean, Double, Int32, String  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rockframe import engine as m  # noqa: E402

FC, GAMMA, G = 28.0, 24.0, 9.8
OBJ = E.eItemType.Objects
MOD_E = 4700 * np.sqrt(FC) * 1e3  # kN/m²
ESP = dict(Aa=0.25, Av=0.25, Fa=1.3, Fv=1.9, I=1.0)
CASOS = {
    "1x2": dict(L=[5.0], H=[3.5, 3.0], w=[25.0, 20.0], col=(0.4, 0.4), vig=(0.3, 0.45)),
    "3x3": dict(L=[5.0, 6.0, 5.0], H=[4.0, 3.0, 3.0], w=[30.0, 30.0, 20.0], col=(0.5, 0.5), vig=(0.35, 0.5)),
    "3x6": dict(L=[5.0] * 3, H=[4.0] + [3.0] * 5, w=[35.0] * 5 + [25.0], col=(0.6, 0.6), vig=(0.4, 0.55)),
}
FACTORES = {"bruta": (1.0, 1.0), "fisurada": (0.35, 0.70)}


def ok(r, que):
    codigo = r[0] if isinstance(r, tuple) else r
    if codigo != 0:
        raise RuntimeError(f"ETABS devolvió error en {que}: {r}")
    return r


def param(c):
    N = len(c["H"])
    return dict(n_bays=len(c["L"]), n_stories=N, bay_widths=c["L"], bay_width=c["L"][0], story_heights=c["H"],
                columns_sections=[c["col"]] * N, beams_sections=[c["vig"]] * N, w_level_kNpm=c["w"], nodal_loads={})


def construir(sm, c, fv, fc, s, ruta):
    x = np.r_[0, np.cumsum(c["L"])]; z = np.r_[0, np.cumsum(c["H"])]
    nx, nz = len(x), len(z)
    ok(sm.InitializeNewModel(E.eUnits.kN_m_C), "InitializeNewModel")
    ok(cFile(sm).NewGridOnly(nz - 1, c["H"][-1], c["H"][0], 2, 2, 5.0, 5.0), "NewGridOnly")
    ok(sm.SetPresentUnits(E.eUnits.kN_m_C), "unidades")
    pm = E.cPropMaterial(sm.PropMaterial)
    ok(pm.SetMaterial("RF", E.eMatType.Concrete), "material")
    ok(pm.SetMPIsotropic("RF", MOD_E, 0.2, 1e-5, 0.0), "E")
    ok(pm.SetWeightAndMass("RF", 1, 0.0, 0.0), "peso nulo")
    pf = E.cPropFrame(sm.PropFrame)
    for nombre, (b, h), fi in (("COL", c["col"], fc), ("VIG", c["vig"], fv)):
        ok(pf.SetRectangle(nombre, "RF", h, b, -1, "", ""), "sección")
        # A, As2, As3, J, I22, I33, masa, peso: As = 0 elimina la deformación por cortante
        ok(pf.SetModifiers(nombre, Array[Double]([1.0, 0.0, 0.0, 1.0, 1.0, fi, 0.0, 0.0])), "modificadores")
    pat = E.cLoadPatterns(sm.LoadPatterns)
    ok(pat.Add("RFG", E.eLoadPatternType.Other, 0.0, True), "patrón gravedad")
    ok(pat.Add("RFS", E.eLoadPatternType.Other, 0.0, True), "patrón sismo")

    po = E.cPointObj(sm.PointObj); fo = E.cFrameObj(sm.FrameObj)
    nudos = {}
    for j in range(nz):
        for i in range(nx):
            n = ok(po.AddCartesian(float(x[i]), 0.0, float(z[j]), "", f"N{i}_{j}", "Global", False, 0), "nudo")[1]
            nudos[i, j] = n
    elementos = []  # (nombre, tipo) en el mismo orden que build_case_gen
    for j in range(1, nz):
        Ac = c["col"][0] * c["col"][1]; Av = c["vig"][0] * c["vig"][1]
        for i in range(nx):
            n = ok(fo.AddByPoint(nudos[i, j - 1], nudos[i, j], "", "COL", f"C{i}_{j}"), "columna")[1]
            elementos.append(n)
            ok(fo.SetLoadDistributed(n, "RFG", 1, 10, 0.0, 1.0, GAMMA * Ac, GAMMA * Ac, "Global", True, True, OBJ), "peso columna")
        for i in range(nx - 1):
            n = ok(fo.AddByPoint(nudos[i, j], nudos[i + 1, j], "", "VIG", f"V{i}_{j}"), "viga")[1]
            elementos.append(n)
            q = c["w"][j - 1] + GAMMA * Av
            ok(fo.SetLoadDistributed(n, "RFG", 1, 10, 0.0, 1.0, q, q, "Global", True, True, OBJ), "carga viga")
    for n in elementos:
        ok(fo.SetEndLengthOffset(n, False, 0.0, 0.0, 0.0, OBJ), "sin zona rígida")
    for i in range(nx):
        ok(po.SetRestraint(nudos[i, 0], Array[Boolean]([True] * 6), OBJ), "apoyo")
    Fi, Wi = s["Fi"], s["Wi"]
    for j in range(1, nz):
        for i in range(nx):
            ok(po.SetLoadForce(nudos[i, j], "RFS", Array[Double]([Fi[j - 1] / nx, 0.0, 0.0, 0.0, 0.0, 0.0]), True, "Global", OBJ), "fuerza piso")
            ok(po.SetMass(nudos[i, j], Array[Double]([Wi[j - 1] / G / nx, 0.0, 0.0, 0.0, 0.0, 0.0]), OBJ, False, True), "masa")
    ok(E.cAnalyze(sm.Analyze).SetActiveDOF(Array[Boolean]([True, False, True, False, True, False])), "plano XZ")
    ok(cFile(sm).Save(ruta), "guardar")
    return nudos, elementos


def cFile(sm):
    return E.cFile(sm.File)


def _vacios(n_s, n_d):
    return [Array[String]([])] * n_s, [Array[Double]([])] * n_d


def desplazamiento(res, nudo):
    s, d = _vacios(4, 7)
    r = ok(res.JointDispl(nudo, E.eItemTypeElm.ObjectElm, 0, s[0], s[1], s[2], s[3], d[0], d[1], d[2], d[3], d[4], d[5], d[6]), "JointDispl")
    return r


def correr(sm, c, fv, fc, s, ruta):
    nudos, elementos = construir(sm, c, fv, fc, s, ruta)
    ok(E.cAnalyze(sm.Analyze).RunAnalysis(), "RunAnalysis")
    res = E.cAnalysisResults(sm.Results)
    setup = E.cAnalysisResultsSetup(res.Setup)
    salida = {}
    for caso in ("RFG", "RFS"):
        ok(setup.DeselectAllCasesAndCombosForOutput(), "deseleccionar")
        ok(setup.SetCaseSelectedForOutput(caso), "seleccionar")
        ud = {}
        for (i, j), n in nudos.items():
            r = desplazamiento(res, n)
            # (ret, NumberResults, Obj, Elm, Case, StepType, StepNum, U1, U2, U3, R1, R2, R3)
            ud[f"{i},{j}"] = [r[-6][0], r[-4][0], r[-2][0]]
        fz = {}
        for n in elementos:
            s_, d_ = _vacios(4, 6)
            r = ok(res.FrameForce(n, E.eItemTypeElm.ObjectElm, 0, s_[0], Array[Double]([]), s_[1], Array[Double]([]), s_[2], s_[3], Array[Double]([]),
                                  d_[0], d_[1], d_[2], d_[3], d_[4], d_[5]), "FrameForce")
            # P, V2, V3, T, M2, M3 son los seis últimos arreglos
            P, V2, M3 = r[-6], r[-5], r[-1]
            fz[n] = [abs(P[0]), abs(V2[0]), abs(M3[0]), abs(P[len(P) - 1]), abs(V2[len(V2) - 1]), abs(M3[len(M3) - 1])]
        salida[caso] = dict(u=ud, f=[fz[n] for n in elementos])
    ok(setup.DeselectAllCasesAndCombosForOutput(), "deseleccionar")
    ok(setup.SetCaseSelectedForOutput("Modal"), "modal")
    s_, d_ = _vacios(2, 4)
    r = ok(res.ModalPeriod(0, s_[0], s_[1], Array[Double]([]), d_[0], d_[1], d_[2], d_[3]), "ModalPeriod")
    salida["T1"] = max(float(t) for t in r[5])
    return salida


def main():
    os.makedirs(TRABAJO, exist_ok=True)
    elegidos = sys.argv[1].split(",") if len(sys.argv) > 1 else list(CASOS)
    helper = E.cHelper(E.Helper())
    obj = E.cOAPI(helper.CreateObject(os.path.join(RUTA, "ETABS.exe")))
    ok(obj.ApplicationStart(), "ApplicationStart")
    print("ETABS abierto:", obj.GetOAPIVersionNumber(), flush=True)
    sm = E.cSapModel(obj.SapModel)
    todo = {}
    try:
        for nc in elegidos:
            c = CASOS[nc]
            for nf, (fv, fc) in FACTORES.items():
                h = float(sum(c["H"]))
                sp = dict(ciudad="", amenaza="", suelo="", Ae=None, Ad=None, h_m=h, grupo_label="", **ESP)
                s = m.run_seismic_iterative(param(c), FC, None, GAMMA, fv, fc, sp, h, 0.047, 0.9, 20, 0.01)
                e = m.run_static_analysis(param(c), FC, None, fv, fc, gamma=GAMMA)
                print(f"--- {nc} {nf}: construyendo", flush=True)
                r = correr(sm, c, fv, fc, s, os.path.join(TRABAJO, f"RF_{nc}_{nf}.edb"))
                nx, ny = len(c["L"]) + 1, len(c["H"]) + 1
                nid = lambda i, j: 1 + i + nx * j
                filas = {}

                def err(a, b):
                    a, b = np.asarray(a, float), np.asarray(b, float)
                    return float(np.max(np.abs(a - b)) / np.max(np.abs(b)) * 100)

                for caso, U, F in (("RFG", e["U"], e["elem_forces_local"]), ("RFS", s["U"], s["elem_forces_local"])):
                    ua = []; ub = []; ta = []; tb = []
                    for j in range(1, ny):
                        for i in range(nx):
                            g = e["dof"].node_dofs[nid(i, j)]
                            ux, uz, ry = r[caso]["u"][f"{i},{j}"]
                            ua += [U[g[0]], U[g[1]]]; ub += [ux, uz]; ta.append(U[g[2]]); tb.append(-ry)
                    Fa = np.abs(np.array([f[1:] for f in F])) / 1e3
                    Fb = np.array(r[caso]["f"])
                    filas[caso] = dict(despl=err(ua, ub), giro=err(ta, tb), N=err(Fa[:, [0, 3]], Fb[:, [0, 3]]), V=err(Fa[:, [1, 4]], Fb[:, [1, 4]]),
                                       M=err(Fa[:, [2, 5]], Fb[:, [2, 5]]), umax_mm=float(np.max(np.abs(ub)) * 1000))
                filas["T_ETABS"] = r["T1"]; filas["T_Rayleigh"] = s["T_detallado"]
                filas["T_dif_pct"] = (s["T_detallado"] / r["T1"] - 1) * 100
                todo[f"{nc}|{nf}"] = filas
                print(json.dumps(filas, indent=None), flush=True)
    finally:
        with open(os.path.join(TRABAJO, "resultados.json"), "w", encoding="utf-8") as f:
            json.dump(todo, f, indent=1)
        obj.ApplicationExit(False)
    print("TERMINADO", flush=True)


if __name__ == "__main__":
    main()
