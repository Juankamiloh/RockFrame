"""Estudio paramétrico NSR-10 frente a AIS 100-24 en pórticos planos, para un sitio de sites.csv.

Para 70 geometrías (1 a 7 luces, 1 a 10 pisos) busca la columna cuadrada mínima que cumple cada
criterio de deriva. Las secciones escalan con una sola variable c, así que la relación de rigidez
entre vigas y columnas es constante y cada criterio se compara en igualdad de condiciones.

Uso: python studies/armenia_nsr10_vs_ais/run_study.py [ciudad]
"""
import csv
import multiprocessing as mp
import os
import sys

import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(AQUI)))
from rockframe import engine as m  # noqa: E402

# Datos comunes del pórtico residencial típico; el sitio se lee de sites.csv
LUZ = 5.0            # m
ALTURA = 3.0         # m
W_PISO = 35.0        # kN/m: 7 kN/m² de carga muerta sobrepuesta en 5 m de ancho aferente
W_CUBIERTA = 25.0    # kN/m
VIVA_KNPM = 9.0      # kN/m: 1.8 kN/m² en 5 m de ancho aferente, solo para Qi
FC, GAMMA = 28.0, 24.0
I_USO = 1.0          # grupo de uso I
CIUDAD = "Armenia"
CT, ALFA = 0.047, 0.9
ANCHO_VIGA = 0.75    # b_viga/c
PERALTE_VIGA = 1.0   # h_viga/c
PASO, C_MIN, C_MAX = 0.05, 0.30, 3.00

FACTORES = {"bruta": (1.0, 1.0), "fisurada": (0.35, 0.70)}
CRITERIOS = {  # nombre: (rigidez, límite de deriva en %)
    "NSR10_bruta": ("bruta", 1.0),
    "NSR10_fisurada": ("fisurada", 1.0 / 0.7),   # A.6.4.1.1
    "AIS100_fisurada": ("fisurada", 1.5),        # AIS 100-24 Tabla A.6.4-1, grupos I o II con particiones de mampostería
}
MODOS = ("limite_CuTa", "sin_limite")
VARIANTES = {  # base y sensibilidad a la rigidez relativa viga-columna y a la luz
    "base": dict(),
    "viga_h_1.25c": dict(PERALTE_VIGA=1.25),
    "luz_4m": dict(LUZ=4.0),
    "luz_6m": dict(LUZ=6.0),
}


def leer_sitio(ciudad):
    with open(os.path.join(AQUI, "sites.csv"), encoding="utf-8") as f:
        for fila in csv.DictReader(f):
            if fila["ciudad"] == ciudad:
                return dict(Aa=float(fila["Aa"]), Av=float(fila["Av"]), Fa=float(fila["Fa"]), Fv=float(fila["Fv"]), I=I_USO)
    raise ValueError(f"{ciudad} no está en sites.csv")


def aplicar_variante(nombre):
    globals().update(VARIANTES[nombre])


def rigidez_viga_columna():
    """Relación (EI/L) viga / (EI/L) columna en un nudo interior: dos vigas y dos columnas iguales."""
    return (ANCHO_VIGA * PERALTE_VIGA ** 3 / LUZ) / (1.0 / ALTURA)


def analizar(M, N, c, rigidez, modo):
    fv, fc = FACTORES[rigidez]
    H = [ALTURA] * N
    p = dict(n_bays=M, n_stories=N, bay_widths=[LUZ] * M, bay_width=LUZ, story_heights=H,
             columns_sections=[(c, c)] * N, beams_sections=[(ANCHO_VIGA * c, PERALTE_VIGA * c)] * N,
             w_level_kNpm=[W_PISO] * (N - 1) + [W_CUBIERTA], nodal_loads={})
    h = float(sum(H))
    sp = dict(ciudad=CIUDAD, amenaza="", suelo="D", Ae=None, Ad=None, h_m=h, grupo_label="I", **leer_sitio(CIUDAD))
    viva = [VIVA_KNPM * LUZ * M] * N
    return m.run_seismic_iterative(p, FC, None, GAMMA, fv, fc, sp, h, CT, ALFA, 30, 0.1, periodo_diseno=modo, carga_viva_kN=viva)


def deriva_con_fuerzas(M, N, c, rigidez, Fi):
    """Deriva máxima del pórtico si recibe las fuerzas por piso Fi, en kN."""
    fv, fc = FACTORES[rigidez]
    H = [ALTURA] * N
    p = dict(n_bays=M, n_stories=N, bay_widths=[LUZ] * M, bay_width=LUZ, story_heights=H, columns_sections=[(c, c)] * N,
             beams_sections=[(ANCHO_VIGA * c, PERALTE_VIGA * c)] * N, w_level_kNpm=[W_PISO] * (N - 1) + [W_CUBIERTA], nodal_loads={})
    nodes, elements, _, supports, _ = m.build_case_gen(p, FC, None)
    dof = m.DOFMap(nodes)
    K = m.assemble_global_K(nodes, elements, dof, factor_vigas=fv, factor_columnas=fc)
    P = np.zeros(dof.ndof)
    niveles = sorted({n.y for n in nodes.values() if n.y > 0})
    for k, y in enumerate(niveles):
        ids = [i for i, n in nodes.items() if abs(n.y - y) < 1e-6]
        for i in ids:
            P[dof.node_dofs[i][0]] = Fi[k] * 1e3 / len(ids)
    U, *_ = m.solve_with_bc(K, P, np.zeros(dof.ndof), m.supports_to_restrained_gdls(dof, supports), dof)
    d = [np.mean([U[dof.node_dofs[i][0]] for i, n in nodes.items() if abs(n.y - y) < 1e-6]) for y in niveles]
    return float(np.max(np.abs(np.diff(d, prepend=0.0))) / ALTURA * 100)


def volumen(M, N, c):
    """Concreto del pórtico en m³, centro a centro."""
    return (M + 1) * N * ALTURA * c * c + M * N * LUZ * ANCHO_VIGA * PERALTE_VIGA * c * c


def deriva(M, N, c, rigidez, modo):
    return max(analizar(M, N, c, rigidez, modo)["drift_pct"])


def seccion_minima(M, N, rigidez, limite, modo):
    """Primera columna de la malla que cumple, y su refinamiento continuo a 1 mm."""
    c = C_MIN
    if deriva(M, N, c, rigidez, modo) <= limite:
        return c, c
    while c < C_MAX:
        c = round(c + PASO, 2)
        if deriva(M, N, c, rigidez, modo) <= limite:
            bajo, alto = c - PASO, c
            while alto - bajo > 0.001:
                medio = 0.5 * (alto + bajo)
                if deriva(M, N, medio, rigidez, modo) <= limite:
                    alto = medio
                else:
                    bajo = medio
            return c, alto
    raise RuntimeError(f"Sin solución: {M}x{N} {rigidez} {modo}")


def caso(args):
    M, N, variante = args
    aplicar_variante(variante)
    filas = []
    for modo in MODOS:
        base = {}
        for nombre, (rigidez, limite) in CRITERIOS.items():
            c_malla, c_cont = seccion_minima(M, N, rigidez, limite, modo)
            s = analizar(M, N, c_cont, rigidez, modo)
            base[nombre] = c_cont
            filas.append(dict(tipo="seccion_minima", modo=modo, luces=M, pisos=N, criterio=nombre, rigidez=rigidez, limite_pct=round(limite, 4),
                              c_malla=c_malla, c=round(c_cont, 4), volumen_m3=round(volumen(M, N, c_malla), 3), volumen_cont_m3=round(volumen(M, N, c_cont), 3),
                              Ta=s["T_aprox_inicial"], CuTa=s["T_limite"], T_rayleigh=s["T_detallado"], T_diseno=s["T_diseno"], limite_activo=s["limite_activo"],
                              Sa=s["Sa"], k=s["k_exp"], W=s["W_total"], V=s["V"], deriva_max_pct=max(s["drift_pct"]), Q_max=s["Q_max"], convergio=s["converged"]))
        # Misma sección en ambos modelos: la definida por la NSR-10 con inercia bruta
        c0 = base["NSR10_bruta"]
        g = analizar(M, N, c0, "bruta", modo); f = analizar(M, N, c0, "fisurada", modo)
        filas.append(dict(tipo="misma_seccion", modo=modo, luces=M, pisos=N, criterio="", rigidez="", limite_pct="", c_malla="", c=round(c0, 4), volumen_m3="", volumen_cont_m3="",
                          Ta=g["T_aprox_inicial"], CuTa=g["T_limite"], T_rayleigh=f["T_detallado"], T_diseno=f["T_diseno"], limite_activo=f["limite_activo"], Sa=f["Sa"], k=f["k_exp"],
                          W=f["W_total"], V=f["V"], deriva_max_pct=max(f["drift_pct"]), Q_max=f["Q_max"], convergio=f["converged"], deriva_bruta_pct=max(g["drift_pct"]),
                          T_rayleigh_bruta=g["T_detallado"], T_diseno_bruta=g["T_diseno"], V_bruta=g["V"],
                          deriva_fis_misma_fuerza_pct=deriva_con_fuerzas(M, N, c0, "fisurada", g["Fi"])))
    return [dict(variante=args[2], rigidez_viga_columna=round(rigidez_viga_columna(), 3), **f) for f in filas]


def main():
    filas = []
    for variante in VARIANTES:
        casos = [(M, N, variante) for N in range(1, 11) for M in range(1, 8)]
        with mp.Pool(max(1, (os.cpu_count() or 2) - 2)) as pool:
            for r in pool.imap(caso, casos):
                filas += r
        print(variante, "listo", flush=True)
    claves = list(dict.fromkeys(k for f in filas for k in f))
    with open(os.path.join(AQUI, "results.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=claves)
        w.writeheader()
        w.writerows(filas)
    print("filas:", len(filas))


if __name__ == "__main__":
    main()
