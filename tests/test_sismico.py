"""Análisis sísmico NSR-10 sobre pórticos planos: espectro, fuerzas, período, convergencia y derivas."""
import numpy as np
import pytest

from comun import FACTORES, FC, G, GAMMA, PORTICOS, cerca, m, modelo_real, sismo

A25 = (0.25, 0.25, 1.3, 1.9, 1.0)
A15 = (0.15, 0.20, 1.5, 2.2, 1.5)


@pytest.mark.parametrize("par,T,esperado", [
    # Aa Fa = 0.325, Av Fv = 0.475: Tc = 0.48·0.475/0.325 = 0.70154 s, TL = 4.56 s
    (A25, 0.05, 0.8125),          # A.2.6-3: 2.5·0.325·1 (T < T0: meseta en FHE, A.2.6-7 es solo modal)
    (A25, 0.5, 0.8125),           # A.2.6-3, entre T0 y Tc
    (A25, 0.70, 0.8125),          # A.2.6-3, justo antes de Tc = 0.70154 s
    (A25, 0.71, 0.57 / 0.71),     # A.2.6-1, justo después de Tc
    (A25, 4.55, 0.57 / 4.55),     # A.2.6-1, justo antes de TL = 4.56 s
    (A25, 4.57, 2.5992 / 4.57 ** 2),  # A.2.6-5, justo después de TL
    (A25, 1.0, 0.57),             # A.2.6-1: 1.2·0.475·1/1
    (A25, 4.0, 0.1425),           # A.2.6-1: 0.57/4
    (A25, 5.0, 0.103968),         # A.2.6-5: 1.2·0.475·4.56·1/25
    (A25, 9.1074, 0.0313365),     # A.2.6-5, más allá de la malla de la gráfica (hallazgo H3)
    # Aa Fa = 0.225, Av Fv = 0.44: Tc = 0.93867 s, TL = 5.28 s
    (A15, 0.5, 0.84375),          # A.2.6-3: 2.5·0.225·1.5
    (A15, 0.93, 0.84375),         # A.2.6-3, justo antes de Tc = 0.93867 s
    (A15, 0.95, 0.792 / 0.95),    # A.2.6-1, justo después de Tc
    (A15, 2.0, 0.396),            # A.2.6-1: 1.2·0.44·1.5/2
    (A15, 6.0, 0.11616),          # A.2.6-5: 1.2·0.44·5.28·1.5/36
])
def test_Sa_en_todas_las_ramas_contra_calculo_manual(par, T, esperado):
    """Valor esperado: ecuaciones A.2.6-1, -3 y -5 evaluadas a mano en el comentario de cada caso."""
    assert cerca(m.spectral_acceleration(T, *par), esperado, 1e-6)


def test_T0_Tc_TL_contra_calculo_manual():
    """Valores a mano: T0 = 0.1·0.475/0.325, Tc = 0.48·0.475/0.325, TL = 2.4·1.9 y Sa máx = 0.8125."""
    r = m.compute_design_spectrum("", "", "", 0.25, 0.25, None, None, 1.3, 1.9, 1.0, 19.0)
    assert cerca([r["T0"], r["Tc"], r["TL"], r["Sa_max"]], [0.146154, 0.701538, 4.56, 0.8125], 1e-5)


@pytest.mark.parametrize("par", [A25, A15])
def test_espectro_continuo_en_Tc_y_TL(par):
    """Valor esperado: las ramas de A.2.6 se igualan en Tc y TL."""
    Aa, Av, Fa, Fv, I = par
    Tc, TL = 0.48 * Av * Fv / (Aa * Fa), 2.4 * Fv
    for T in (Tc, TL):
        assert cerca(m.spectral_acceleration(T * (1 - 1e-10), *par), m.spectral_acceleration(T * (1 + 1e-10), *par), 1e-8)


@pytest.mark.parametrize("Av,Fv,esperado", [(0.25, 1.9, 1.2), (0.05, 1.0, 1.69), (0.10, 1.2, 1.606), (0.20, 2.2, 1.222)])
def test_Cu_contra_calculo_manual(Av, Fv, esperado):
    """Valor esperado: A.4.2-2, Cu = 1.75 − 1.2·Av·Fv con mínimo 1.2."""
    assert cerca(m.compute_Cu(Av, Fv), esperado, 1e-9)


@pytest.mark.parametrize("T,k", [(0.3, 1.0), (0.5, 1.0), (0.8, 1.15), (1.5, 1.5), (2.5, 2.0), (3.0, 2.0)])
def test_exponente_k_contra_A_4_3(T, k):
    """Valor esperado: A.4.3.2, k = 1 si T ≤ 0.5; 0.75 + 0.5T entre 0.5 y 2.5; 2 si T > 2.5."""
    assert cerca(m.get_k_exponent(T), k, 1e-9)


def test_peso_y_Cvx_1x2_contra_calculo_manual():
    """Valores a mano del pórtico 1×2, con T ≤ 0.5 s y por tanto k = 1.

    W1 = (25 + 24·0.3·0.45)·5 + 24·0.16·3.5 + 24·0.16·3.0 = 141.2 + 13.44 + 11.52 = 166.16 kN
    W2 = (20 + 3.24)·5 + 11.52 = 127.72 kN;  W = 293.88 kN;  V = 0.8125·293.88 = 238.7775 kN
    Cv1 = 166.16·3.5/(166.16·3.5 + 127.72·6.5) = 581.56/1411.74 = 0.411960
    Cv2 = 830.18/1411.74 = 0.588040
    """
    s = sismo(PORTICOS["1x2"])
    assert cerca(s["Wi"], [166.16, 127.72], 1e-9)
    assert s["k_exp"] == 1.0
    assert cerca(s["V"], 238.7775, 1e-9)
    assert cerca(np.array(s["Fi"]) / s["V"], [581.56 / 1411.74, 830.18 / 1411.74], 1e-9)


@pytest.mark.parametrize("modo", m.PERIODOS_DISENO)
@pytest.mark.parametrize("nf", FACTORES)
@pytest.mark.parametrize("nc", PORTICOS)
def test_fuerzas_por_piso_suman_V_y_siguen_Cvx(nc, nf, modo):
    """Valor esperado: ΣFx = V = Sa·W (A.4.3-1) y Fx = V·W_x·h_x^k/Σ(W·h^k) (A.4.3-3) con k de A.4.3.2."""
    s = sismo(PORTICOS[nc], *FACTORES[nf], modo=modo)
    Wi, hi = np.array(s["Wi"]), np.array(s["hi"])
    assert cerca(sum(s["Fi"]), s["V"], 1e-9)
    assert cerca(s["V"], m.spectral_acceleration(s["T_diseno"], *A25) * Wi.sum(), 1e-9)
    k = m.get_k_exponent(s["T_diseno"])
    assert cerca(s["Fi"], s["V"] * Wi * hi ** k / np.sum(Wi * hi ** k), 1e-9)
    assert cerca(-sum(v[0] for v in s["reactions"].values()) / 1e3, s["V"], 1e-9)


def primer_modo(c, fv, fc, Wi):
    """Período del primer modo: K condensada a los GDL laterales y masas concentradas Wi/g por nudo."""
    nodes, _, sup, dof, K = modelo_real(c, fv, fc)
    fijos = {g - 1 for g in m.supports_to_restrained_gdls(dof, sup)}
    nx = len(c["L"]) + 1
    niveles = sorted({n.y for n in nodes.values() if n.y > 0})
    masa = {dof.node_dofs[n][0]: Wi[niveles.index(nd.y)] * 1e3 / G / nx for n, nd in nodes.items() if nd.y > 0}
    a = list(masa); o = [i for i in range(dof.ndof) if i not in fijos and i not in masa]
    Kc = K[np.ix_(a, a)] - K[np.ix_(a, o)] @ np.linalg.solve(K[np.ix_(o, o)], K[np.ix_(o, a)])
    raiz = np.sqrt([masa[i] for i in a])
    w2 = np.linalg.eigvalsh(Kc / np.outer(raiz, raiz))
    return 2 * np.pi / np.sqrt(w2[0])


@pytest.mark.parametrize("nf", FACTORES)
@pytest.mark.parametrize("nc", PORTICOS)
def test_Rayleigh_contra_primer_modo(nc, nf):
    """Valor esperado: valores propios de K condensada y masas concentradas, cálculo independiente de A.4.2-1."""
    c = PORTICOS[nc]; fv, fc = FACTORES[nf]
    s = sismo(c, fv, fc)
    assert cerca(s["T_detallado"], primer_modo(c, fv, fc, s["Wi"]))


@pytest.mark.parametrize("nf", FACTORES)
@pytest.mark.parametrize("nc", PORTICOS)
def test_Rayleigh_recalculado_desde_desplazamientos(nc, nf):
    """Valor esperado: A.4.2-1 evaluada aparte con los W, F y δ de salida, con g = 9.8."""
    s = sismo(PORTICOS[nc], *FACTORES[nf])
    W, F, d = map(np.array, (s["Wi"], s["Fi"], s["disp_piso"]))
    assert cerca(s["T_detallado"], 2 * np.pi * np.sqrt(np.sum(W * d ** 2) / (G * np.sum(F * d))), 1e-9)


@pytest.mark.parametrize("nf", FACTORES)
@pytest.mark.parametrize("nc", PORTICOS)
def test_iteracion_converge_al_punto_fijo(nc, nf):
    """Valor esperado: al converger, T de diseño = T de Rayleigh, y el resultado no depende de la tolerancia."""
    a = sismo(PORTICOS[nc], *FACTORES[nf], tol=1.0)
    b = sismo(PORTICOS[nc], *FACTORES[nf], tol=1e-6)
    assert a["converged"] and b["converged"] and b["iteration_count"] <= 10
    assert cerca(b["T_diseno"], b["T_detallado"], 1e-7)
    assert cerca(a["T_detallado"], b["T_detallado"])
    assert cerca(a["V"], b["V"])


@pytest.mark.parametrize("nf", FACTORES)
@pytest.mark.parametrize("nc", PORTICOS)
def test_limite_CuTa(nc, nf):
    """Valor esperado: T diseño = mín(T Rayleigh, Cu·Ta) según A.4.2.1; Ta = 0.047·h^0.9 (A.4.2-3)."""
    c = PORTICOS[nc]
    s = sismo(c, *FACTORES[nf], modo="limite_CuTa")
    Ta = 0.047 * sum(c["H"]) ** 0.9
    assert cerca(s["T_aprox_inicial"], Ta, 1e-9)
    assert cerca(s["T_limite"], 1.2 * Ta, 1e-9)
    assert cerca(s["T_diseno"], min(s["T_detallado"], 1.2 * Ta), 1e-6)


def test_modo_Ta_usa_el_periodo_aproximado():
    """Valor esperado: con A.4.2.2, T de diseño = Ta y no hay iteración."""
    s = sismo(PORTICOS["3x6"], modo="Ta")
    assert s["iteration_count"] == 1 and cerca(s["T_diseno"], s["T_aprox_inicial"], 1e-12)


def test_derivas_a_mano_portico_pequeno():
    """Pórtico de un piso: Δ = V/K con K cerrada, deriva = Δ/h y T = 2π·√(W/(g·K)).

    Luz larga y secciones reales: la deformación axial queda muy por debajo de la tolerancia.
    Con k_c = EI_c/h, k_v = EI_v/L, ρ = k_v/k_c: K = (24EI_c/h³)(1 + 6ρ)/(4 + 6ρ).
    """
    h, L = 3.0, 12.0; b, ht = 0.4, 0.4; bv, hv = 0.5, 0.9
    c = dict(L=[L], H=[h], w=[30.0], col=[(b, ht)], vig=[(bv, hv)])
    s = sismo(c)
    E = 4700 * np.sqrt(FC) * 1e6
    Ic, Iv = b * ht ** 3 / 12, bv * hv ** 3 / 12
    rho = (Iv / L) / (Ic / h)
    K = 24 * E * Ic / h ** 3 * (1 + 6 * rho) / (4 + 6 * rho)
    W = (30.0 + GAMMA * bv * hv) * L + GAMMA * b * ht * h
    V = 0.8125 * W
    assert cerca(s["W_total"], W, 1e-9)
    assert cerca(s["disp_piso"][0], V * 1e3 / K)
    assert cerca(s["drift_pct"][0], V * 1e3 / K / h * 100)
    assert cerca(s["T_detallado"], 2 * np.pi * np.sqrt(W * 1e3 / (G * K)))


def test_derivas_son_diferencias_entre_pisos():
    """Valor esperado: Δ_i = |δ_i − δ_i−1|/hp (A.6.3.1.1) recalculado con los desplazamientos de salida."""
    c = PORTICOS["3x6"]
    s = sismo(c)
    d = np.array(s["disp_piso"])
    assert cerca(s["drift_pct"], np.abs(np.diff(d, prepend=0.0)) / np.array(c["H"]) * 100, 1e-12)


def test_evaluacion_de_derivas_factores_y_limite():
    """Valor esperado: tabla A.6.4-1 (1.0 %), A.6.4.1.1 (límite 1.0/0.7 = 1.4286 %) y A.6.2.1.2 (÷ I)."""
    assert m.evaluate_drifts([0.0140], 1.0)["cumple_deriva"] is False
    r = m.evaluate_drifts([0.0140], 1.0, reducir_fisuradas=True)
    assert cerca(r["drift_max_evaluacion_pct"], 1.40, 1e-12) and r["cumple_deriva"]
    assert cerca(r["limite_deriva_pct"], 1.0 / 0.7, 1e-12)
    assert m.evaluate_drifts([0.0143], 1.0, reducir_fisuradas=True)["cumple_deriva"] is False
    assert cerca(m.evaluate_drifts([0.012], 1.5, usar_I_unitario=True)["drift_max_evaluacion_pct"], 0.8, 1e-12)
    assert m.evaluate_drifts([0.010], 1.0)["cumple_deriva"]


def test_factor_07_rechazado_con_inercia_bruta():
    """A.6.4.1.1 solo aplica con secciones fisuradas."""
    with pytest.raises(ValueError):
        sismo(PORTICOS["1x2"], reducir_derivas_fisuradas=True)


def test_Qi_contra_calculo_manual():
    """A.6.2-2 a mano. Piso 1: 150·0.010/(30·3) = 0.016667. Piso 2: 50·0.015/(20·3) = 0.0125."""
    r = m.stability_index([100, 50], [10, 20], [0.010, 0.025], [3, 6], 0.0)
    assert cerca(r["Qi"], [1 / 60, 0.0125], 1e-12)
    assert not r["requiere_pdelta"] and not r["carga_viva_incluida"]


def test_fuerzas_sismicas_equilibradas_en_nudos():
    """Valor esperado: las fuerzas de extremo equilibran Fx/n en cada nudo libre, sin la carga w."""
    c = PORTICOS["3x3"]
    s = sismo(c, 0.35, 0.70)
    nodes, elems, sup, dof, _ = modelo_real(c, 0.35, 0.70)
    P = np.zeros(dof.ndof)
    for eid, *f in s["elem_forces_local"]:
        e = elems[eid]; _, cs, sn = e.length_and_cs(nodes)
        P[dof.elem_dofs(e)] += m.T_matrix(cs, sn).T @ np.array(f)
    ext = np.zeros(dof.ndof)
    for k, y in enumerate(s["hi"]):
        ids = [n for n, nd in nodes.items() if abs(nd.y - y) < 1e-6]
        for n in ids:
            ext[dof.node_dofs[n][0]] = s["Fi"][k] * 1e3 / len(ids)
    libres = [i for i in range(dof.ndof) if i + 1 not in m.supports_to_restrained_gdls(dof, sup)]
    assert np.abs(P[libres] - ext[libres]).max() < 1e-4
