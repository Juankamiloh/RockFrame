"""Comparación contra OpenSees con elasticBeamColumn, inercia bruta y fisurada.

Requiere Python 3.12 con openseespy; en otra versión estas pruebas se omiten.
"""
import numpy as np
import pytest

from comun import E_PA, FACTORES, FC, G, GAMMA, PORTICOS, cerca, inputs, m, sismo

try:
    import openseespy.opensees as ops
except (ImportError, RuntimeError):
    pytest.skip("OpenSeesPy no está disponible en este Python", allow_module_level=True)


def nid(c, i, j):
    return 1 + i + (len(c["L"]) + 1) * j


def modelo(c, fv, fc, gravedad=False, nodales=None, laterales=None):
    """Mismo pórtico en N y m, con los ids de build_case_gen."""
    ops.wipe(); ops.model("basic", "-ndm", 2, "-ndf", 3)
    x = np.r_[0, np.cumsum(c["L"])]; y = np.r_[0, np.cumsum(c["H"])]
    for j in range(len(y)):
        for i in range(len(x)):
            ops.node(nid(c, i, j), float(x[i]), float(y[j]))
            if j == 0:
                ops.fix(nid(c, i, j), 1, 1, 1)
    ops.geomTransf("Linear", 1); ops.timeSeries("Constant", 1); ops.pattern("Plain", 1, 1)
    e = 1
    for j in range(1, len(y)):
        bc, hc = c["col"][j - 1]; bv, hv = c["vig"][j - 1]
        for i in range(len(x)):
            ops.element("elasticBeamColumn", e, nid(c, i, j - 1), nid(c, i, j), bc * hc, E_PA, fc * bc * hc ** 3 / 12, 1)
            if gravedad:
                ops.eleLoad("-ele", e, "-type", "-beamUniform", 0.0, -GAMMA * bc * hc * 1e3)
            e += 1
        for i in range(len(x) - 1):
            ops.element("elasticBeamColumn", e, nid(c, i, j), nid(c, i + 1, j), bv * hv, E_PA, fv * bv * hv ** 3 / 12, 1)
            if gravedad:
                ops.eleLoad("-ele", e, "-type", "-beamUniform", -(c["w"][j - 1] + GAMMA * bv * hv) * 1e3, 0.0)
            e += 1
    for n, carga in (nodales or {}).items():
        ops.load(n, *carga)
    for n, f in (laterales or {}).items():
        ops.load(n, f, 0.0, 0.0)
    ops.constraints("Plain"); ops.numberer("RCM"); ops.system("BandGeneral"); ops.test("NormUnbalance", 1e-6, 10)
    ops.algorithm("Linear"); ops.integrator("LoadControl", 1.0); ops.analysis("Static")
    assert ops.analyze(1) == 0
    ops.reactions()
    return e - 1


CASOS = [(nc, nf) for nc in PORTICOS for nf in FACTORES]


@pytest.mark.parametrize("nc,nf", CASOS)
def test_gravedad_y_nodales_contra_opensees(nc, nf):
    """Valor esperado: OpenSees. Desplazamientos, giros, reacciones y fuerzas internas con signo."""
    c = PORTICOS[nc]; fv, fc = FACTORES[nf]
    nx, ny = len(c["L"]) + 1, len(c["H"]) + 1
    cargas = {nid(c, nx - 1, ny - 1): (15e3, -10e3, 5e3), nid(c, 0, 1): (40e3, 0.0, 0.0)}
    n_e = modelo(c, fv, fc, True, cargas)
    r = m.run_static_analysis(inputs(c, {k: tuple(x / 1e3 for x in v) for k, v in cargas.items()}), FC, None, fv, fc, gamma=GAMMA)
    ids = sorted(r["nodes"])
    Ua = np.array([[r["U"][g] for g in r["dof"].node_dofs[n]] for n in ids]); Ub = np.array([ops.nodeDisp(n) for n in ids])
    assert cerca(Ua[:, :2], Ub[:, :2]) and cerca(Ua[:, 2], Ub[:, 2])
    base = [nid(c, i, 0) for i in range(nx)]
    assert cerca([r["reactions_by_node"][n] for n in base], [ops.nodeReaction(n) for n in base])
    Fa = np.array([e[1:] for e in r["elem_forces_local"]]); Fb = np.array([ops.eleResponse(e, "localForce") for e in range(1, n_e + 1)])
    for col in ([0, 3], [1, 4], [2, 5]):
        assert cerca(Fa[:, col], Fb[:, col])


@pytest.mark.parametrize("modo", ["limite_CuTa", "sin_limite"])
@pytest.mark.parametrize("nc,nf", CASOS)
def test_sismo_contra_opensees(nc, nf, modo):
    """Valor esperado: OpenSees con las Fx del motor. Desplazamientos, derivas, Rayleigh y fuerzas con signo."""
    c = PORTICOS[nc]; fv, fc = FACTORES[nf]
    s = sismo(c, fv, fc, modo=modo)
    nx, ny = len(c["L"]) + 1, len(c["H"]) + 1
    lat = {nid(c, i, j): s["Fi"][j - 1] * 1e3 / nx for j in range(1, ny) for i in range(nx)}
    n_e = modelo(c, fv, fc, laterales=lat)
    d = np.array([np.mean([ops.nodeDisp(nid(c, i, j), 1) for i in range(nx)]) for j in range(1, ny)])
    assert cerca(s["disp_piso"], d)
    assert cerca(s["drift_pct"], np.abs(np.diff(d, prepend=0.0)) / np.array(c["H"]) * 100)
    W, F = np.array(s["Wi"]), np.array(s["Fi"])
    assert cerca(s["T_detallado"], 2 * np.pi * np.sqrt(np.sum(W * d ** 2) / (G * np.sum(F * d))))
    assert cerca([e[1:] for e in s["elem_forces_local"]], [ops.eleResponse(q, "localForce") for q in range(1, n_e + 1)])
