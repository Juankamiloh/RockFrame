"""Datos y utilidades compartidos por las pruebas. Todos los modelos son pórticos planos 2D."""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rockframe import engine as m  # noqa: E402

TOL = 1e-3  # 0.1 % contra soluciones exactas o el solucionador independiente
FC, GAMMA, G = 28.0, 24.0, 9.8
E_PA = 4700 * np.sqrt(FC) * 1e6  # C.8.5.1, en Pa
ESPECTRO = dict(Aa=0.25, Av=0.25, Fa=1.3, Fv=1.9, I=1.0)
FACTORES = {"bruta": (1.0, 1.0), "fisurada": (0.35, 0.70)}
PORTICOS = {
    "1x2": dict(L=[5.0], H=[3.5, 3.0], w=[25.0, 20.0], col=[(0.4, 0.4)] * 2, vig=[(0.3, 0.45)] * 2),
    "3x3": dict(L=[5.0, 6.0, 5.0], H=[4.0, 3.0, 3.0], w=[30.0, 30.0, 20.0], col=[(0.5, 0.5)] * 3, vig=[(0.35, 0.5)] * 3),
    "3x6": dict(L=[5.0] * 3, H=[4.0] + [3.0] * 5, w=[35.0] * 5 + [25.0], col=[(0.6, 0.6)] * 6, vig=[(0.4, 0.55)] * 6),
    "irregular 4x5": dict(L=[4.0, 7.0, 5.5, 3.0], H=[4.5, 3.2, 3.6, 3.0, 2.8], w=[40.0, 32.0, 28.0, 25.0, 15.0],
                          col=[(0.7, 0.6), (0.6, 0.6), (0.55, 0.5), (0.5, 0.5), (0.4, 0.4)],
                          vig=[(0.4, 0.6), (0.4, 0.55), (0.35, 0.5), (0.3, 0.45), (0.3, 0.4)]),
}


def inputs(c, nodal=None):
    N = len(c["H"])
    return dict(n_bays=len(c["L"]), n_stories=N, bay_widths=c["L"], bay_width=c["L"][0], story_heights=c["H"],
                columns_sections=c["col"], beams_sections=c["vig"], w_level_kNpm=c["w"], nodal_loads=nodal or {})


def sismo(c, fv=1.0, fc=1.0, espectro=ESPECTRO, modo="sin_limite", tol=0.01, **op):
    h = float(sum(c["H"]))
    sp = dict(ciudad="", amenaza="", suelo="", Ae=None, Ad=None, h_m=h, grupo_label="", **espectro)
    return m.run_seismic_iterative(inputs(c), FC, None, GAMMA, fv, fc, sp, h, 0.047, 0.9, 30, tol, periodo_diseno=modo, **op)


def cerca(obtenido, esperado, tol=TOL):
    """Error relativo a la mayor magnitud esperada de la familia de resultados."""
    a, b = np.asarray(obtenido, float), np.asarray(esperado, float)
    return float(np.max(np.abs(a - b)) / np.max(np.abs(b))) <= tol


def nudos_elementos(alturas, luces, Ic, Iv, A=1e2, E=E_PA):
    """Pórtico con I y A impuestos. A grande anula la deformación axial de la solución cerrada."""
    x = np.r_[0.0, np.cumsum(luces)]; y = np.r_[0.0, np.cumsum(alturas)]
    nx = len(x)
    nid = lambda i, j: 1 + i + nx * j
    nodes = {nid(i, j): m.Node(nid(i, j), float(x[i]), float(y[j])) for j in range(len(y)) for i in range(nx)}
    elems = {}; e = 1
    for j in range(1, len(y)):
        for i in range(nx):
            elems[e] = m.Element(e, nid(i, j - 1), nid(i, j), A, E, Ic); e += 1
        for i in range(nx - 1):
            elems[e] = m.Element(e, nid(i, j), nid(i + 1, j), A, E, Iv); e += 1
    restr = sorted(3 * i + k for i in range(nx) for k in (1, 2, 3))
    return nodes, elems, restr, nid


def desplazar(nodes, elems, restr, P_kN):
    """Resuelve con cargas nodales {nudo: (Px, Py, Mz)} en kN y devuelve el vector U."""
    dof = m.DOFMap(nodes)
    K = m.assemble_global_K(nodes, elems, dof)
    U, *_ = m.solve_with_bc(K, m.assemble_Pext_nodal(dof, P_kN), np.zeros(dof.ndof), restr, dof)
    return U, dof


def modelo_real(c, fv, fc):
    nodes, elems, _, sup, _ = m.build_case_gen(inputs(c), FC, None)
    dof = m.DOFMap(nodes)
    return nodes, elems, sup, dof, m.assemble_global_K(nodes, elems, dof, fv, fc)
