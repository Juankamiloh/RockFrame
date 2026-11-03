"""Genera resultados_clave.md a partir de results.csv.

Uso: python studies/armenia_nsr10_vs_ais/make_key_results.py
"""
import os

import pandas as pd

AQUI = os.path.dirname(os.path.abspath(__file__))
d = pd.read_csv(os.path.join(AQUI, "results.csv"))
ORIGEN = "`results.csv`"


def resumen(variante, modo, q=None):
    x = d[(d.variante == variante) & (d.modo == modo) & (d.pisos >= 2)]
    if q is not None:
        x = x[q(x)]
    m = x[x.tipo == "misma_seccion"]
    r = m.deriva_max_pct / m.deriva_bruta_pct
    s = x[x.tipo == "seccion_minima"]
    v = s.pivot_table(index=["luces", "pisos"], columns="criterio", values="volumen_cont_m3")
    c = s.pivot_table(index=["luces", "pisos"], columns="criterio", values="c")
    a = (v.AIS100_fisurada / v.NSR10_bruta - 1) * 100
    f = (v.NSR10_fisurada / v.NSR10_bruta - 1) * 100
    return dict(n=len(m), r=r, a=a, f=f, ca=(c.AIS100_fisurada / c.NSR10_bruta).median())


def fila(nombre, s):
    return f"| {nombre} | {s['n']} | {s['r'].median():.2f} ({s['r'].min():.2f} a {s['r'].max():.2f}) | {s['a'].median():+.1f} % ({s['a'].min():+.1f} a {s['a'].max():+.1f}) | {s['f'].median():+.1f} % | {s['ca']:.3f} |"


T = ["# Resultados clave del estudio v2", "",
     "Todas las cifras salen de `results.csv`, generado por `run_study.py`. Las medianas excluyen los pórticos de 1 piso, que quedan en la columna mínima de 30 cm.", "",
     "Sitio: Armenia, Quindío, suelo D. Aa = Av = 0.25, Fa = 1.3, Fv = 1.9, I = 1.0. T0 = 0.146 s, TC = 0.702 s, TL = 4.56 s, Sa en la meseta = 0.8125.", "",
     "## Medianas y rangos", "",
     "| Grupo | Pórticos | Razón deriva AIS fisurada / deriva NSR-10 | Concreto adicional AIS fisurada (1.5 %) | Concreto adicional NSR-10 fisurada (1.43 %) | Columna AIS / NSR-10 |", "|---|---:|---:|---:|---:|---:|",
     fila("Caso base, con tope Cu·Ta", resumen("base", "limite_CuTa")), fila("Caso base, sin tope", resumen("base", "sin_limite")),
     fila("2 a 6 pisos, con tope", resumen("base", "limite_CuTa", lambda x: x.pisos <= 6)), fila("7 a 10 pisos, con tope", resumen("base", "limite_CuTa", lambda x: x.pisos >= 7)), "",
     f"Origen: {ORIGEN}, columnas `deriva_max_pct`, `deriva_bruta_pct` y `volumen_cont_m3`.", "",
     "## Variantes", "", "| Variante | Relación de rigidez viga/columna | Razón, mediana | Concreto adicional AIS, con tope | Concreto adicional AIS, sin tope |", "|---|---:|---:|---:|---:|"]
NOMBRES = {"base": "Viga de altura c, luz de 5 m", "viga_h_1.25c": "Viga de altura 1.25c, luz de 5 m", "luz_4m": "Viga de altura c, luz de 4 m", "luz_6m": "Viga de altura c, luz de 6 m"}
for v, n in NOMBRES.items():
    a, b = resumen(v, "limite_CuTa"), resumen(v, "sin_limite")
    T.append(f"| {n} | {d[d.variante == v].rigidez_viga_columna.iloc[0]:.2f} | {a['r'].median():.2f} | {a['a'].median():+.1f} % | {b['a'].median():+.1f} % |")
T += ["", f"Origen: {ORIGEN}, columna `rigidez_viga_columna`. Es la relación (EI/L) de vigas / (EI/L) de columnas en un nudo interior.", "", "## Columna mínima con 3 luces, en cm", "", "| Pisos | NSR-10 (1 %) | AIS fisurada (1.5 %) | NSR-10 fisurada (1.43 %) |", "|---|---:|---:|---:|"]
s = d[(d.variante == "base") & (d.tipo == "seccion_minima") & (d.modo == "limite_CuTa") & (d.luces == 3)]
p = s.pivot(index="pisos", columns="criterio", values="c") * 100
for n in (2, 6, 10):
    T.append(f"| {n} | {p.NSR10_bruta[n]:.1f} | {p.AIS100_fisurada[n]:.1f} | {p.NSR10_fisurada[n]:.1f} |")
T += ["", f"Origen: {ORIGEN}, filas `seccion_minima`, columna `c`.", "", "## Por número de pisos, con tope", "",
      "| Pisos | Límite que igualaría ambos criterios [%] | Razón con la misma fuerza | Reducción de fuerza del modelo fisurado | T diseño NSR-10 [s] | T diseño AIS fisurado [s] |", "|---|---:|---:|---:|---:|---:|"]
m = d[(d.variante == "base") & (d.tipo == "misma_seccion") & (d.modo == "limite_CuTa") & (d.pisos >= 2)].copy()
m["razon"] = m.deriva_max_pct / m.deriva_bruta_pct
m["mf"] = m.deriva_fis_misma_fuerza_pct / m.deriva_bruta_pct
m["red"] = (1 - m.V / m.V_bruta) * 100
g = m.groupby("pisos").agg(razon=("razon", "median"), mf=("mf", "median"), red=("red", "median"), tn=("T_diseno_bruta", "median"), ta=("T_diseno", "median"))
for n, x in g.iterrows():
    T.append(f"| {n} | {x.razon:.2f} | {x.mf:.2f} | {x.red:.1f} % | {x.tn:.3f} | {x.ta:.3f} |")
T += ["", f"Origen: {ORIGEN}, filas `misma_seccion`. El límite equivalente es la razón misma, porque NSR-10 se evalúa con 1.00 %. Los períodos son medianas de 1 a 7 luces; la Figura 4 usa los pórticos de 3 luces, por eso con 10 pisos dice 0.899 s y esta tabla {g.tn[10]:.3f} s.", "",
      "## Alineación de la caída con TC", "",
      f"La razón cae de {g.razon[5]:.2f} a {g.razon[6]:.2f} entre 5 y 6 pisos. En ese tramo, el período de diseño AIS fisurado va de {g.ta[5]:.3f} a {g.ta[6]:.3f} s y cruza TC = 0.702 s. El de NSR-10 va de {g.tn[5]:.3f} a {g.tn[6]:.3f} s y no lo cruza. La caída queda mejor alineada con el período del modelo AIS fisurado.", "",
      "## Demostraciones manuales", "",
      "- Pórtico 1×1: razón de 1.796 con γ = 0.45, igual a ROCKFRAME sin deformación axial. Origen: `demostracion_manual/portico_1x1.md`.",
      "- Pórtico 3×6: todos los valores de la hoja coinciden con ROCKFRAME. Origen: `demostracion_manual/portico_3x6.xlsx`.", "",
      "## Contexto sísmico", "",
      "- 25 de enero de 1999: el Servicio Geológico Colombiano reporta magnitud 6.1 Mw y 21 km de profundidad en su infografía del sismo del Eje Cafetero. Otra publicación del SGC indica 6.2. `[PENDIENTE: definir la cifra con el catálogo del SGC]`",
      "- 10 de agosto de 2026: la OPS, citando al SGC, reporta 7.4 Mw y 103 km de profundidad, con epicentro en San José del Palmar. El boletín inicial decía 6.7 y 82 km. `[PENDIENTE: confirmar en el boletín definitivo del SGC, y los daños en Armenia]`",
      "- `[PENDIENTE: confirmar con el autor si \"el sismo de noviembre\" se refiere a otro evento]`", ""]
with open(os.path.join(AQUI, "resultados_clave.md"), "w", encoding="utf-8") as f:
    f.write("\n".join(T))
print("\n".join(T[6:32]))
