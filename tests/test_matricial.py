"""Análisis matricial de pórticos planos: soluciones cerradas, equilibrio y propiedades de K."""
import numpy as np
import pytest

from comun import FACTORES, GAMMA, FC, PORTICOS, cerca, desplazar, inputs, m, modelo_real, nudos_elementos

E = 25e9


def K_portico(Ic, Iv, h, L):
    """Rigidez lateral del pórtico de una luz y un piso con base empotrada, sin deformación axial.

    Pendiente-deflexión con k_c = EI_c/h, k_v = EI_v/L y giro θ igual en ambos nudos superiores
    (antisimetría; la viga trabaja con M = 6·k_v·θ):

        M_columna,sup = k_c·(4θ − 6Δ/h)
        Equilibrio del nudo: 4k_c·θ − 6k_c·Δ/h + 6k_v·θ = 0   →   θ = 6k_c·Δ / [h·(4k_c + 6k_v)]
        Cortante de columna: V = 12k_c·Δ/h² − 6k_c·θ/h

    Con ρ = k_v/k_c y K = 2V/Δ:

        K = (24 EI_c/h³) · (1 + 6ρ) / (4 + 6ρ)

    Límites: ρ → ∞ da 24EI_c/h³ (viga rígida); ρ = 0 da 6EI_c/h³ (dos voladizos 3EI/h³).
    """
    rho = (Iv / L) / (Ic / h)
    return 24 * E * Ic / h ** 3 * (1 + 6 * rho) / (4 + 6 * rho)


@pytest.mark.parametrize("Iv_sobre_Ic", [0.05, 0.5, 1.0, 5.0])
def test_portico_viga_flexible_contra_solucion_cerrada(Iv_sobre_Ic):
    """Valor esperado: K_portico, derivada por pendiente-deflexión en su docstring."""
    Ic, h, L, F = 2e-3, 3.5, 6.0, 100.0
    nodes, elems, restr, nid = nudos_elementos([h], [L], Ic, Iv_sobre_Ic * Ic, E=E)
    U, dof = desplazar(nodes, elems, restr, {nid(0, 1): (F / 2, 0, 0), nid(1, 1): (F / 2, 0, 0)})
    delta = U[dof.node_dofs[nid(0, 1)][0]]
    assert cerca(F * 1e3 / delta, K_portico(Ic, Iv_sobre_Ic * Ic, h, L))


def test_portico_viga_rigida_tiende_a_24EI_h3():
    """Valor esperado: límite ρ → ∞ de K_portico, K = 24EI_c/h³ (doble empotramiento por columna)."""
    Ic, h, L, F = 2e-3, 3.5, 6.0, 100.0
    nodes, elems, restr, nid = nudos_elementos([h], [L], Ic, 1e6 * Ic, E=E)
    U, dof = desplazar(nodes, elems, restr, {nid(0, 1): (F / 2, 0, 0), nid(1, 1): (F / 2, 0, 0)})
    assert cerca(F * 1e3 / U[dof.node_dofs[nid(0, 1)][0]], 24 * E * Ic / h ** 3)


def test_portico_viga_sin_rigidez_tiende_a_dos_voladizos():
    """Valor esperado: límite ρ → 0 de K_portico, K = 2·3EI_c/h³."""
    Ic, h, L, F = 2e-3, 3.5, 6.0, 100.0
    nodes, elems, restr, nid = nudos_elementos([h], [L], Ic, 1e-7 * Ic, E=E)
    U, dof = desplazar(nodes, elems, restr, {nid(0, 1): (F / 2, 0, 0), nid(1, 1): (F / 2, 0, 0)})
    assert cerca(F * 1e3 / U[dof.node_dofs[nid(0, 1)][0]], 6 * E * Ic / h ** 3)


@pytest.mark.parametrize("n_col", [2, 4])
def test_varios_pisos_con_vigas_rigidas_contra_modelo_de_cortante(n_col):
    """Valor esperado: modelo de cortante. k_i = n·12EI_c/h_i³ y Δ_i = V_i/k_i, con V_i acumulado."""
    H = [4.0, 3.0, 3.0, 3.0]; F = np.array([50.0, 80.0, 110.0, 140.0]); Ic = 2e-3
    nodes, elems, restr, nid = nudos_elementos(H, [5.0] * (n_col - 1), Ic, 1e6 * Ic, E=E)
    cargas = {nid(i, j + 1): (F[j] / n_col, 0, 0) for j in range(4) for i in range(n_col)}
    U, dof = desplazar(nodes, elems, restr, cargas)
    obtenido = np.diff([0.0] + [U[dof.node_dofs[nid(0, j + 1)][0]] for j in range(4)])
    V = np.cumsum(F[::-1])[::-1] * 1e3
    esperado = V / (n_col * 12 * E * Ic / np.array(H) ** 3)
    assert cerca(obtenido, esperado)


def test_viga_empotrada_carga_uniforme_y_puntual():
    """Valor esperado: tablas de empotramiento perfecto, R = wL/2 + P/2 y M = wL²/12 + PL/8."""
    nodes = {1: m.Node(1, 0, 0), 2: m.Node(2, 6, 0)}
    elems = {1: m.Element(1, 1, 2, 0.1, E, 1e-3, w_kNpm=10.0, Pmid_kN=40.0)}
    dof = m.DOFMap(nodes)
    _, R, *_ = m.solve_with_bc(m.assemble_global_K(nodes, elems, dof), np.zeros(6), m.assemble_PqG(nodes, elems, dof), [1, 2, 3, 4, 5, 6], dof)
    assert cerca(R / 1e3, [0, 50, 60, 0, 50, -60])


def test_columna_peso_propio_acortamiento_exacto():
    """Valor esperado: acortamiento de barra vertical bajo su peso, δ = γ·H²/(2E), con A cancelada."""
    nodes = {1: m.Node(1, 0, 0), 2: m.Node(2, 0, 3)}
    elems = {1: m.Element(1, 1, 2, 0.1, E, 1e-3)}
    dof = m.DOFMap(nodes)
    U, *_ = m.solve_with_bc(m.assemble_global_K(nodes, elems, dof), np.zeros(6), m.assemble_PqG(nodes, elems, dof, 24.0), [1, 2, 3], dof)
    assert cerca(-U[4], 24e3 * 9 / (2 * E))


@pytest.mark.parametrize("nf", FACTORES)
@pytest.mark.parametrize("nc", PORTICOS)
def test_K_simetrica_positiva_y_modos_rigidos(nc, nf):
    """Propiedades teóricas: K = Kᵀ, K_ll definida positiva y K·u = 0 para movimientos de cuerpo rígido."""
    nodes, _, sup, dof, K = modelo_real(PORTICOS[nc], *FACTORES[nf])
    assert np.allclose(K, K.T, rtol=0, atol=1e-9 * np.abs(K).max())
    libres = [i for i in range(dof.ndof) if i + 1 not in m.supports_to_restrained_gdls(dof, sup)]
    assert np.linalg.eigvalsh(K[np.ix_(libres, libres)])[0] > 0
    rb = np.zeros((dof.ndof, 3))
    for n, nd in nodes.items():
        ux, uy, th = dof.node_dofs[n]
        rb[ux, 0] = rb[uy, 1] = rb[th, 2] = 1.0
        rb[ux, 2] = -nd.y; rb[uy, 2] = nd.x
    assert np.abs(K @ rb).max() < 1e-9 * np.abs(K).max()


@pytest.mark.parametrize("nf", FACTORES)
@pytest.mark.parametrize("nc", PORTICOS)
def test_equilibrio_global_y_por_nudo(nc, nf):
    """Valor esperado: ΣF = 0 y ΣM = 0 entre cargas y reacciones, y equilibrio de fuerzas en cada nudo."""
    c = PORTICOS[nc]; fv, fc = FACTORES[nf]
    tope = (len(c["L"]) + 1) * (len(c["H"]) + 1)
    r = m.run_static_analysis(inputs(c, {tope: (80.0, -20.0, 15.0)}), FC, None, fv, fc, gamma=GAMMA)
    nodes, elems, dof = r["nodes"], r["elements"], r["dof"]

    peso = sum((e.w_kNpm + GAMMA * e.A) * 1e3 * e.length_and_cs(nodes)[0] if e.w_kNpm else GAMMA * e.A * 1e3 * e.length_and_cs(nodes)[0] for e in elems.values())
    Rx = sum(v[0] for v in r["reactions_by_node"].values()); Ry = sum(v[1] for v in r["reactions_by_node"].values())
    assert abs(Rx + 80e3) < 1e-3
    assert abs(Ry - peso - 20e3) < 1e-3

    M = sum(v[2] + nodes[n].x * v[1] - nodes[n].y * v[0] for n, v in r["reactions_by_node"].items())
    M += 15e3 + nodes[tope].x * (-20e3) - nodes[tope].y * 80e3
    for e in elems.values():
        L, _, _ = e.length_and_cs(nodes)
        q = (e.w_kNpm + GAMMA * e.A) * 1e3 * L if e.w_kNpm else GAMMA * e.A * 1e3 * L
        M -= q * (nodes[e.i].x + nodes[e.j].x) / 2
    assert abs(M) < 1e-2

    P = np.zeros(dof.ndof)
    for eid, *f in r["elem_forces_local"]:
        e = elems[eid]; _, cs, sn = e.length_and_cs(nodes)
        P[dof.elem_dofs(e)] += m.T_matrix(cs, sn).T @ np.array(f)
    libres = [g - 1 for g in r["free"]]
    assert np.abs(P[libres] - r["P_ext"][libres]).max() < 1e-4


def test_base_articulada_no_tiene_momento():
    """Valor esperado: un apoyo sin restricción de giro tiene reacción de momento nula."""
    c = PORTICOS["3x3"]; p = inputs(c)
    p["supports"] = {i: ("FX", "FY") for i in range(1, 5)}
    r = m.run_static_analysis(p, FC, None)
    assert all(abs(v[2]) < 1e-6 for v in r["reactions_by_node"].values())


def test_mecanismo_se_rechaza():
    """Una estructura inestable debe dar error, no resultados."""
    p = inputs(PORTICOS["3x3"]); p["supports"] = {1: ("FX",)}
    with pytest.raises(np.linalg.LinAlgError):
        m.run_static_analysis(p, FC, None)
