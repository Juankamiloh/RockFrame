"""Genera las figuras del estudio, sus explicaciones y las tablas.

Uso: python studies/armenia_nsr10_vs_ais/make_figures.py
"""
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import BoundaryNorm, ListedColormap
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
import numpy as np
import pandas as pd

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import run_study as r  # noqa: E402
from rockframe import engine as m  # noqa: E402

FIG = os.path.join(AQUI, "figures")
os.makedirs(FIG, exist_ok=True)
for viejo in os.listdir(FIG):
    os.remove(os.path.join(FIG, viejo))

TINTA, GRIS, LINEA = "#1C2326", "#5F686C", "#DFDAD1"
AZUL, TERRACOTA, VIOLETA = "#0B7FB0", "#C2552D", "#7A4FC4"
plt.rcParams.update({"font.family": "Segoe UI", "font.size": 16, "axes.edgecolor": LINEA, "axes.labelcolor": TINTA, "xtick.color": TINTA, "ytick.color": TINTA,
                     "xtick.major.size": 0, "ytick.major.size": 0, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": LINEA,
                     "grid.linewidth": 0.7, "axes.axisbelow": True, "figure.facecolor": "white", "savefig.dpi": 300, "figure.constrained_layout.use": True})

SITIO = r.leer_sitio(r.CIUDAD)
Tc = 0.48 * SITIO["Av"] * SITIO["Fv"] / (SITIO["Aa"] * SITIO["Fa"])
TL = 2.4 * SITIO["Fv"]
d = pd.read_csv(os.path.join(AQUI, "results.csv"))
base = d[d.variante == "base"]
misma = base[base.tipo == "misma_seccion"].copy()
misma["razon"] = misma.deriva_max_pct / misma.deriva_bruta_pct
misma["razon_misma_fuerza"] = misma.deriva_fis_misma_fuerza_pct / misma.deriva_bruta_pct
misma["fuerza"] = misma.V / misma.V_bruta
tope = misma[misma.modo == "limite_CuTa"]
libre = misma[misma.modo == "sin_limite"]
sec = base[(base.tipo == "seccion_minima") & (base.modo == "limite_CuTa")]
ETIQUETAS = {"NSR10_bruta": "NSR-10 (1 %)", "AIS100_fisurada": "AIS fisurada (1.5 %)", "NSR10_fisurada": "NSR-10 fisurada (1.43 %)"}
med = tope[tope.pisos >= 2].groupby("pisos").agg(razon=("razon", "median"), misma_fuerza=("razon_misma_fuerza", "median"), fuerza=("fuerza", "median"),
                                                  T_nsr=("T_diseno_bruta", "median"), T_ais=("T_diseno", "median"))
med_libre = libre[libre.pisos >= 2].groupby("pisos").agg(razon=("razon", "median"), T_nsr=("T_diseno_bruta", "median"), T_ais=("T_diseno", "median"))
EJE_Y = "Deriva AIS fisurada / deriva NSR-10"


def explicar(nombre, titulo, que, leer, tendencia, porque, permite, frase):
    texto = f"""# {titulo}

## Qué muestra
{que}

## Cómo leerla
{leer}

## Qué tendencia tiene
{tendencia}

## Por qué pasa
{porque}

## Qué conclusión permite y cuál no
{permite}

## Frase de 20 segundos
{frase}
"""
    with open(os.path.join(FIG, f"{nombre}_explicacion.md"), "w", encoding="utf-8") as f:
        f.write(texto)


def nube(nombre, datos, eje_x, xlabel):
    tonos = ListedColormap(plt.get_cmap("Blues")(np.linspace(0.3, 1.0, 9)))
    escala = BoundaryNorm(np.arange(1.5, 11.5), 9)
    uno = datos.pisos == 1
    fig, ax = plt.subplots(figsize=(11, 6.6))
    ax.axvspan(0.8 * Tc, 1.2 * Tc, color="#F4E3B5", alpha=0.75, lw=0, zorder=0)
    ax.axvline(Tc, color=TERRACOTA, lw=2.2, zorder=1)
    pts = ax.scatter(datos[eje_x][~uno], datos.razon[~uno], c=datos.pisos[~uno], cmap=tonos, norm=escala, s=110, edgecolor=TINTA, linewidth=0.6, zorder=3)
    ax.scatter(datos[eje_x][uno], datos.razon[uno], s=90, color="#C9CDCF", edgecolor=GRIS, linewidth=0.6, zorder=2)
    ax.annotate("1 piso: no comparables", (datos[eje_x][uno].max(), datos.razon[uno].median()), xytext=(14, -2), textcoords="offset points", color=GRIS, fontsize=14, va="center")
    ax.axhline(1.5, color=TINTA, lw=1.8, ls="--")
    ax.set_ylim(1.3, 2.45)
    ax.text(ax.get_xlim()[1], 1.47, "Equivalencia: 1.50", va="top", ha="right", color=TINTA, fontsize=15, fontweight="bold")
    ax.text(Tc, 2.43, f" TC = {Tc:.3f} s", color=TERRACOTA, fontsize=15, fontweight="bold", va="top")
    ax.text(0.8 * Tc, 1.34, " Zona de transición", color=TINTA, fontsize=14, va="bottom")
    ax.set_xlabel(xlabel); ax.set_ylabel(EJE_Y)
    fig.colorbar(pts, ax=ax, ticks=range(2, 11), label="Número de pisos", shrink=0.92)
    fig.savefig(os.path.join(FIG, f"{nombre}.png")); plt.close(fig)


nube("fig1_nube_T_NSR_con_tope", tope, "T_diseno_bruta", "Período de diseño del modelo NSR-10 (1 %) [s]")
nube("fig1b_nube_T_NSR_sin_tope", libre, "T_diseno_bruta", "Período del modelo NSR-10 (1 %), sin tope [s]")
nube("fig2_nube_T_AIS_con_tope", tope, "T_diseno", "Período de diseño del modelo AIS fisurado [s]")
nube("fig2b_nube_T_AIS_sin_tope", libre, "T_diseno", "Período del modelo AIS fisurado, sin tope [s]")

caidas = med.razon.diff()
inicio = next(p for p in med.index[1:] if caidas[p] < -0.10)
ant = inicio - 1
alineado_ais = med.T_ais[ant] < Tc <= med.T_ais[inicio]
alineado_nsr = med.T_nsr[ant] < Tc <= med.T_nsr[inicio]
ALINEACION = (f"La caída empieza entre {ant} y {inicio} pisos: la razón pasa de {med.razon[ant]:.2f} a {med.razon[inicio]:.2f}. En ese tramo el período del modelo AIS fisurado va de "
              f"{med.T_ais[ant]:.3f} a {med.T_ais[inicio]:.3f} s y {'cruza' if alineado_ais else 'no cruza'} TC = {Tc:.3f} s. El período del modelo NSR-10 va de {med.T_nsr[ant]:.3f} a "
              f"{med.T_nsr[inicio]:.3f} s y {'cruza' if alineado_nsr else 'no cruza'} TC. Por eso la caída queda mejor alineada con TC en la versión con el período del modelo "
              f"{'AIS fisurado' if alineado_ais and not alineado_nsr else 'NSR-10'}.")
TRAMOS = f"de 2 a 5 pisos la razón está entre {med.razon[2:5].min():.2f} y {med.razon[2:5].max():.2f}; con 6 pisos es {med.razon[6]:.2f}; con 7 es {med.razon[7]:.2f}; de 8 a 10 está entre {med.razon[8:10].min():.2f} y {med.razon[8:10].max():.2f}"
MECANISMO = (f"La razón depende de dos cosas: cuánto más flexible es el modelo fisurado y cuánta fuerza recibe. Mientras los dos períodos están antes de TC ({Tc:.3f} s), ambos modelos reciben "
             f"la misma aceleración y la misma fuerza, y la razón solo refleja la pérdida de rigidez. Cuando el período del modelo fisurado pasa de TC, su aceleración baja y recibe menos fuerza, "
             f"mientras el modelo NSR-10 sigue en la meseta. Por eso la razón cae. Cuando ambos períodos ya pasaron de TC, la diferencia de fuerza se estabiliza y la razón deja de caer.")
explicar("fig1_nube_T_NSR_con_tope", "Figura 1. Razón de derivas frente al período del modelo NSR-10",
         "Cada punto es un pórtico, de 1 a 7 luces y de 1 a 10 pisos, 70 en total. El eje horizontal es el período de diseño del modelo NSR-10 (1 %), en segundos. El eje vertical es la razón deriva AIS fisurada / deriva NSR-10, sin unidades, calculada con la misma sección: la mínima que cumple NSR-10 (1 %). El color es el número de pisos. La línea punteada marca la equivalencia en 1.50, la línea vertical marca TC y la banda va de 0.8·TC a 1.2·TC. Los datos salen de `results.csv`, filas `misma_seccion`, con tope Cu·Ta.",
         "Mira primero la línea de 1.50: si un punto está encima, la sección que cumple 1 % no cumple 1.5 %. Luego sigue los colores de claro a oscuro para ver qué pasa al aumentar los pisos.",
         f"Todos los puntos quedan encima de 1.50 (mínimo {tope.razon.min():.2f}). Medianas por pisos: {TRAMOS}. Los pórticos de 1 piso aparecen en gris porque quedan en la columna mínima de 30 cm y no se comparan.",
         MECANISMO, "Permite afirmar que, en estos pórticos, la deriva crece más que el límite. No permite afirmar que pase en todas las edificaciones, ni que esa sección sea un diseño final: solo se comparó rigidez lateral.",
         f"Cada punto es un pórtico con la misma sección en los dos modelos. Todos quedan encima de 1.5, así que el modelo fisurado deriva más de lo que el nuevo límite compensa. La razón ronda 2.2 hasta 5 pisos y baja a {med.razon[10]:.2f} en 10 pisos.")
explicar("fig1b_nube_T_NSR_sin_tope", "Figura 1b. Razón de derivas frente al período del modelo NSR-10, sin tope",
         "Es la misma nube de la Figura 1, pero sin aplicar el tope Cu·Ta: cada modelo usa su período calculado. Es una versión secundaria. Los datos salen de `results.csv`, filas `misma_seccion`, modo `sin_limite`.",
         "Compárala con la Figura 1 y mira cuánto se acercan los puntos a la línea de 1.50.",
         f"Todos siguen encima de 1.50 (mínimo {libre.razon.min():.2f}, mediana {libre[libre.pisos >= 2].razon.median():.2f}). De 8 a 10 pisos la mediana queda entre {med_libre.razon[8:10].min():.2f} y {med_libre.razon[8:10].max():.2f}.",
         "Sin tope, el modelo fisurado usa un período más largo, recibe menos fuerza y deriva menos. Por eso la razón baja antes y queda más cerca de 1.50.",
         "Permite ver cuánto pesa el tope Cu·Ta. No es el criterio de la norma: la verificación usa el tope.",
         f"Si quitamos el tope, los pórticos altos se acercan a 1.5, pero ninguno cruza la línea. El mínimo es {libre.razon.min():.2f}.")
explicar("fig2_nube_T_AIS_con_tope", "Figura 2. Razón de derivas frente al período del modelo AIS fisurado",
         "Es la misma razón de la Figura 1, pero el eje horizontal es el período de diseño del modelo AIS fisurado. Los datos salen de `results.csv`, filas `misma_seccion`, con tope Cu·Ta.",
         "Mira dónde empieza a bajar la nube respecto a la línea vertical de TC.",
         ALINEACION, MECANISMO, "Permite ubicar la caída alrededor de TC. No permite generalizar el valor de TC: depende del espectro de Armenia con suelo D.",
         "La razón empieza a caer cuando el período del modelo fisurado pasa de TC, porque ese modelo sale de la meseta del espectro y recibe menos fuerza.")
explicar("fig2b_nube_T_AIS_sin_tope", "Figura 2b. Razón de derivas frente al período del modelo AIS fisurado, sin tope",
         "Es la Figura 2 sin aplicar el tope Cu·Ta. Los datos salen de `results.csv`, filas `misma_seccion`, modo `sin_limite`.",
         "Mira la caída respecto a TC y compárala con la Figura 2.",
         f"La mediana pasa de {med_libre.razon[3]:.2f} con 3 pisos ({med_libre.T_ais[3]:.3f} s) a {med_libre.razon[4]:.2f} con 4 pisos ({med_libre.T_ais[4]:.3f} s) y sigue bajando hasta {med_libre.razon[10]:.2f} con 10 pisos.",
         "Sin tope, el período del modelo fisurado llega antes a TC, así que la caída empieza con menos pisos.",
         "Es una figura de apoyo. La comparación principal usa el tope.", "Sin tope, la caída ocurre con menos pisos porque el período fisurado es más largo.")

# Figura 3: razón por pisos y efecto de la fuerza
fig, ax = plt.subplots(figsize=(11, 6.4))
ax.plot(med.index, med.razon, color=TERRACOTA, lw=2.6, marker="o", ms=10, label="Con la fuerza de cada modelo")
ax.plot(med.index, med.misma_fuerza, color=AZUL, lw=2.6, marker="s", ms=10, label="Si ambos modelos recibieran la misma fuerza")
ax.axhline(1.5, color=TINTA, lw=1.8, ls="--")
ax.text(10, 1.47, "Equivalencia: 1.50", ha="right", va="top", color=TINTA, fontsize=15, fontweight="bold")
ax.set_xlabel("Número de pisos"); ax.set_ylabel(EJE_Y); ax.set_xticks(range(2, 11)); ax.set_ylim(1.3, 2.45); ax.grid(False, axis="x")
ax.legend(frameon=False, loc="lower left", labelcolor=TINTA)
fig.savefig(os.path.join(FIG, "fig3_razon_por_pisos.png")); plt.close(fig)
explicar("fig3_razon_por_pisos", "Figura 3. Razón de derivas por número de pisos",
         "Cada punto es la mediana de los pórticos con ese número de pisos, de 1 a 7 luces. La curva naranja usa la fuerza de cada modelo, con tope Cu·Ta. La curva azul aplica al modelo fisurado las mismas fuerzas del modelo NSR-10 (1 %). Los datos salen de `results.csv`, columnas `deriva_max_pct`, `deriva_bruta_pct` y `deriva_fis_misma_fuerza_pct`.",
         "Compara las dos curvas: la distancia entre ellas es el efecto de la fuerza.",
         f"Con la misma fuerza, la razón queda entre {med.misma_fuerza.min():.2f} y {med.misma_fuerza.max():.2f}. Con la fuerza de cada modelo baja desde {med.razon[5]:.2f} con 5 pisos hasta {med.razon[10]:.2f} con 10.",
         "La curva azul mide solo la pérdida de rigidez. La naranja se separa porque el modelo fisurado recibe menos fuerza cuando su período pasa de TC. En 10 pisos recibe " + f"{(1 - med.fuerza[10]) * 100:.0f} % menos.",
         "Permite separar el efecto de la rigidez del efecto de la fuerza. No describe pórticos con otra relación de rigidez entre vigas y columnas.",
         "La línea azul es lo que perdemos en rigidez. La línea naranja muestra que, en pórticos más altos, una fuerza menor compensa parte de esa pérdida.")

# Figura 4: espectro de Armenia
fig, ax = plt.subplots(figsize=(11, 6.4))
T = np.unique(np.r_[np.linspace(0.01, 2.0, 600), Tc])
Sa = [m.spectral_acceleration(t, SITIO["Aa"], SITIO["Av"], SITIO["Fa"], SITIO["Fv"], SITIO["I"]) for t in T]
ax.axvspan(0.8 * Tc, 1.2 * Tc, color="#F4E3B5", alpha=0.75, lw=0, label="Banda de ±20 % alrededor de TC")
ax.plot(T, Sa, color=TINTA, lw=2.8, label="Espectro de Armenia, suelo D")
ax.axvline(Tc, color=TERRACOTA, lw=2)
ax.text(Tc + 0.015, 0.93, f"TC = {Tc:.3f} s", color=TERRACOTA, fontsize=15, fontweight="bold", va="top")
marcas = []
for N, marcador in ((6, "o"), (10, "s")):
    x = tope[(tope.pisos == N) & (tope.luces == 3)].iloc[0]
    for t, color, nombre in ((x.T_diseno_bruta, AZUL, "NSR-10 (1 %)"), (x.T_diseno, TERRACOTA, "AIS fisurado")):
        s_a = m.spectral_acceleration(t, SITIO["Aa"], SITIO["Av"], SITIO["Fa"], SITIO["Fv"], SITIO["I"])
        ax.plot([t], [s_a], marker=marcador, ms=13, color=color, ls="none", markeredgecolor="white", label=f"3 luces, {N} pisos, {nombre}: T = {t:.3f} s", zorder=4)
        marcas.append((N, nombre, t, s_a))
ax.set_xlim(0, 2); ax.set_ylim(0, 0.95); ax.set_xlabel("Período [s]"); ax.set_ylabel("Sa [g]")
ax.legend(frameon=False, loc="upper right", labelcolor=TINTA, fontsize=13.5)
fig.savefig(os.path.join(FIG, "fig4_espectro_armenia.png")); plt.close(fig)
explicar("fig4_espectro_armenia", "Figura 4. Espectro de Armenia y períodos de los modelos",
         f"La curva es el espectro de diseño de Armenia con suelo D (Aa = Av = 0.25, Fa = 1.3, Fv = 1.9, I = 1.0). El eje horizontal es el período y el vertical la aceleración Sa. Los puntos son los períodos de diseño de los pórticos de 3 luces con 6 y 10 pisos, con la sección de NSR-10 (1 %). Son valores de esos pórticos, no medianas: la mediana con 10 pisos, de 1 a 7 luces, es {med.T_nsr[10]:.3f} s en NSR-10. La meseta vale {2.5 * SITIO['Aa'] * SITIO['Fa'] * SITIO['I']:.4f}.",
         "Ubica los puntos de un mismo número de pisos y compara su altura: esa diferencia es la diferencia de fuerza.",
         "Valores: " + "; ".join(f"{a} pisos {b}: T = {c_:.3f} s y Sa = {e:.3f}" for a, b, c_, e in marcas) + ".",
         "Pasado TC, la aceleración baja a medida que el período crece. El modelo fisurado tiene un período más largo y por eso queda más abajo en la curva.",
         "Permite explicar la diferencia de fuerza entre modelos en este sitio. El resultado cambia con otro espectro.",
         "Con 6 pisos, el modelo NSR-10 sigue en la meseta y el fisurado ya bajó. Con 10 pisos, los dos pasaron de TC.")

# Figura 5: columna mínima
fig, ax = plt.subplots(figsize=(11, 6.4))
c = sec[sec.pisos >= 2].groupby(["pisos", "criterio"]).c.median().unstack()
for nombre, color, marca in (("NSR10_bruta", AZUL, "o"), ("AIS100_fisurada", TERRACOTA, "s"), ("NSR10_fisurada", VIOLETA, "^")):
    ax.plot(c.index, c[nombre] * 100, color=color, lw=2.6, marker=marca, ms=10, label=ETIQUETAS[nombre])
ax.set_xlabel("Número de pisos"); ax.set_ylabel("Lado de columna mínimo [cm]"); ax.set_xticks(range(2, 11)); ax.grid(False, axis="x")
ax.legend(frameon=False, loc="lower right", labelcolor=TINTA)
fig.savefig(os.path.join(FIG, "fig5_columna_minima.png")); plt.close(fig)
explicar("fig5_columna_minima", "Figura 5. Columna mínima por criterio",
         "Cada punto es la mediana, de 1 a 7 luces, del lado de la columna cuadrada mínima que cumple cada criterio. La viga mide 0.75c × c. Los datos salen de `results.csv`, filas `seccion_minima`.",
         "Compara la distancia vertical entre las curvas para un mismo número de pisos.",
         f"Con 2 pisos: {c.NSR10_bruta[2] * 100:.1f}, {c.AIS100_fisurada[2] * 100:.1f} y {c.NSR10_fisurada[2] * 100:.1f} cm. Con 10 pisos: {c.NSR10_bruta[10] * 100:.1f}, {c.AIS100_fisurada[10] * 100:.1f} y {c.NSR10_fisurada[10] * 100:.1f} cm, en el orden de la leyenda.",
         "Un modelo con menos rigidez necesita una sección mayor para cumplir. La curva AIS va un poco por debajo de NSR-10 fisurada porque su límite es 1.5 % frente a 1.43 %.",
         "Permite comparar secciones por rigidez lateral. No son secciones de diseño final, porque no se revisó resistencia.",
         "Para cumplir el 1.5 % con secciones fisuradas se necesita una columna mayor que para cumplir el 1 % actual.")

# Figura 6: concreto adicional
v = sec[sec.pisos >= 2].pivot_table(index=["pisos", "luces"], columns="criterio", values="volumen_cont_m3")
inc = ((v.AIS100_fisurada / v.NSR10_bruta - 1) * 100).unstack("luces")
fig, ax = plt.subplots(figsize=(10.5, 7))
im = ax.imshow(inc.values[::-1], cmap="Oranges", vmin=0, vmax=30, aspect="auto")
ax.grid(False)
ax.set_xticks(range(7), inc.columns); ax.set_yticks(range(9), inc.index[::-1])
ax.set_xlabel("Número de luces"); ax.set_ylabel("Número de pisos")
for i, fila in enumerate(inc.values[::-1]):
    for j, x in enumerate(fila):
        ax.text(j, i, f"{x:.0f}", ha="center", va="center", fontsize=16, color="white" if x > 18 else TINTA)
fig.colorbar(im, ax=ax, label="Concreto adicional frente a NSR-10 (1 %) [%]", shrink=0.9)
fig.savefig(os.path.join(FIG, "fig6_concreto_adicional.png")); plt.close(fig)
porp = inc.median(axis=1)
explicar("fig6_concreto_adicional", "Figura 6. Concreto adicional de AIS fisurada (1.5 %)",
         "Cada casilla es un pórtico. El número es el porcentaje de concreto adicional de AIS fisurada (1.5 %) frente a NSR-10 (1 %), con la columna mínima de cada criterio. El concreto se mide en los elementos del pórtico, centro a centro. No se incluyen los pórticos de 1 piso.",
         "Lee de abajo hacia arriba para ver el efecto de los pisos, y de izquierda a derecha para ver el de las luces.",
         f"La mediana es {inc.stack().median():+.1f} %, con rango de {inc.stack().min():+.1f} % a {inc.stack().max():+.1f} %. Por pisos: de 2 a 5 pisos está entre {porp[2:5].min():.1f} % y {porp[2:5].max():.1f} %, y de 8 a 10 cerca de {porp[8:10].median():.1f} %. Entre luces cambia muy poco.",
         "El número de pisos cambia el período y la fuerza. El número de luces casi no cambia la deriva de cada piso, porque rigidez y peso crecen juntos.",
         "Permite estimar el cambio de concreto por rigidez lateral. No es un costo de construcción ni incluye acero, losas ni cimentación.",
         "Con el 1.5 % fisurado se necesita más concreto en todos los pórticos comparados, alrededor de 21 % en la mediana. Las luces casi no cambian ese número; los pisos sí.")

# Figura 7: diagrama de flujo
fig, ax = plt.subplots(figsize=(13, 6.6)); ax.set_axis_off(); ax.set_xlim(0, 13); ax.set_ylim(0, 6.6)
cajas = {"a": (1.65, 5.2, "Datos del pórtico\ny del sitio"), "b": (4.85, 5.2, "Matriz de rigidez\ndel pórtico"), "c": (8.05, 5.2, "Peso por piso y\nperíodo inicial Ta"), "d": (11.25, 5.2, "Espectro NSR-10:\nSa y cortante V"),
         "e": (11.25, 3.0, "Fuerzas por piso"), "f": (8.05, 3.0, "Desplazamientos"), "g": (4.85, 3.0, "Período de Rayleigh\ncon tope Cu·Ta"), "h": (1.65, 3.0, "¿El período\nconvergió?"),
         "i": (1.65, 0.9, "Derivas de piso"), "j": (4.85, 0.9, "Comparación con\nel límite de deriva"), "k": (8.05, 0.9, "Tablas, gráficas\ny Excel")}
for x, y, texto in cajas.values():
    ax.add_patch(FancyBboxPatch((x - 1.35, y - 0.65), 2.7, 1.3, boxstyle="round,pad=0.02,rounding_size=0.12", fc="#F7F5F1", ec=TINTA, lw=1.5))
    ax.text(x, y, texto, ha="center", va="center", fontsize=15.5, color=TINTA)
for a, b in (("a", "b"), ("b", "c"), ("c", "d"), ("d", "e"), ("e", "f"), ("f", "g"), ("g", "h"), ("h", "i"), ("i", "j"), ("j", "k")):
    ax1, ay1, _ = cajas[a]; bx, by, _ = cajas[b]
    if ay1 == by:
        p1, p2 = (ax1 + (1.38 if bx > ax1 else -1.38), ay1), (bx - (1.38 if bx > ax1 else -1.38), by)
    else:
        p1, p2 = (ax1, ay1 - 0.68), (bx, by + 0.68)
    ax.add_patch(FancyArrowPatch(p1, p2, arrowstyle="-|>", mutation_scale=22, color=TINTA, lw=1.8))
ax.plot([1.65, 1.65, 11.25 - 0.9, 11.25 - 0.9], [3.68, 4.1, 4.1, 4.32], color=TERRACOTA, lw=1.8)
ax.add_patch(FancyArrowPatch((11.25 - 0.9, 4.28), (11.25 - 0.9, 4.54), arrowstyle="-|>", mutation_scale=22, color=TERRACOTA, lw=1.8))
ax.text(6.2, 3.92, "No: repetir con el nuevo período", color=TERRACOTA, fontsize=14, ha="center", va="top")
ax.text(1.9, 2.05, "Sí", color=TINTA, fontsize=15)
fig.savefig(os.path.join(FIG, "fig7_flujo_rockframe.png")); plt.close(fig)
explicar("fig7_flujo_rockframe", "Figura 7. Flujo de cálculo de ROCKFRAME",
         "Es el camino que sigue el programa desde los datos del pórtico hasta los resultados.",
         "Sigue las flechas desde la esquina superior izquierda. La flecha de regreso es la iteración del período.",
         "El proceso repite el cálculo hasta que el período deja de cambiar.",
         "Las fuerzas dependen del período y el período depende de los desplazamientos que causan esas fuerzas. Por eso se itera.",
         "Describe el flujo del programa. No es un resultado del estudio.",
         "ROCKFRAME arma el pórtico, calcula las fuerzas con el espectro, obtiene los desplazamientos, ajusta el período hasta que converge y compara las derivas con el límite.")

# Figura 8: deformadas con la misma sección y la misma escala
M, N = 3, 6
c0 = float(tope[(tope.luces == M) & (tope.pisos == N)].c.iloc[0])
g = r.analizar(M, N, c0, "bruta", "limite_CuTa"); f_ = r.analizar(M, N, c0, "fisurada", "limite_CuTa")
p = dict(n_bays=M, n_stories=N, bay_widths=[r.LUZ] * M, bay_width=r.LUZ, story_heights=[r.ALTURA] * N, columns_sections=[(c0, c0)] * N, beams_sections=[(0.75 * c0, c0)] * N, w_level_kNpm=[0.0] * N, nodal_loads={})
nodes, elems, _, _, _ = m.build_case_gen(p, r.FC, None)
dof = m.DOFMap(nodes)
esc = 15.0
fig, ejes = plt.subplots(1, 2, figsize=(13, 7), sharey=True)
for ax, s, color, nombre, limite in ((ejes[0], g, AZUL, "Modelo NSR-10 (1 %)", 1.0), (ejes[1], f_, TERRACOTA, "Modelo AIS fisurado", 1.5)):
    U = s["U"]
    for e in elems.values():
        a, b = nodes[e.i], nodes[e.j]
        ax.plot([a.x, b.x], [a.y, b.y], color="#B8BEC1", lw=2)
        ua, ub = dof.node_dofs[e.i], dof.node_dofs[e.j]
        ax.plot([a.x + esc * U[ua[0]], b.x + esc * U[ub[0]]], [a.y + esc * U[ua[1]], b.y + esc * U[ub[1]]], color=color, lw=2.6)
    der = max(s["drift_pct"]); ax.set_aspect("equal"); ax.set_axis_off()
    ax.set_title(nombre, color=TINTA, fontsize=19, fontweight="bold")
    ax.text(7.5, -1.3, f"Deriva máxima: {der:.2f} %\nLímite: {limite:.1f} %", ha="center", va="top", fontsize=18, color=TINTA)
    ax.set_xlim(-1, 21); ax.set_ylim(-3.6, 19)
fig.suptitle(f"Deformación exagerada × {esc:.0f}, con la misma escala en los dos modelos", color=TINTA, fontsize=17)
fig.savefig(os.path.join(FIG, "fig8_deformadas_3x6.png")); plt.close(fig)
r_8 = max(f_["drift_pct"]) / max(g["drift_pct"])
explicar("fig8_deformadas_3x6", "Figura 8. Deformadas del pórtico de 3 luces y 6 pisos",
         f"Las dos imágenes muestran el mismo pórtico con la misma sección (columna de {c0 * 100:.1f} cm) y la misma escala de desplazamientos (× {esc:.0f}). En gris está el pórtico sin deformar y en color el deformado. Cada modelo recibe sus fuerzas de diseño.",
         "Compara cuánto se mueve la parte alta en cada imagen.",
         f"La deriva máxima pasa de {max(g['drift_pct']):.2f} % a {max(f_['drift_pct']):.2f} %, es decir {r_8:.2f} veces. El desplazamiento superior pasa de {g['disp_piso'][-1] * 1000:.0f} mm a {f_['disp_piso'][-1] * 1000:.0f} mm.",
         "Es la misma estructura, pero el modelo fisurado usa 0.35 Ig en vigas y 0.70 Ig en columnas. Con menos rigidez se desplaza más.",
         "Muestra un solo pórtico. Las tendencias generales salen de las figuras 1 a 6.",
         "Es el mismo pórtico y la misma escala. Con secciones fisuradas se deforma casi el doble, pero el límite solo sube de 1 a 1.5.")

# Tablas
with pd.ExcelWriter(os.path.join(AQUI, "results_tables.xlsx"), engine="openpyxl") as xw:
    nube_t = tope.merge(libre[["luces", "pisos", "razon", "T_diseno", "T_diseno_bruta"]], on=["luces", "pisos"], suffixes=("", "_sin_tope")).sort_values(["pisos", "luces"])
    pd.DataFrame({"Luces": nube_t.luces, "Pisos": nube_t.pisos, "Columna c [m]": nube_t.c, "T diseño NSR-10 (1 %) [s]": nube_t.T_diseno_bruta, "T diseño AIS fisurado [s]": nube_t.T_diseno,
                  "V NSR-10 (1 %) [kN]": nube_t.V_bruta, "V AIS fisurado [kN]": nube_t.V, "Deriva NSR-10 [%]": nube_t.deriva_bruta_pct, "Deriva AIS fisurada [%]": nube_t.deriva_max_pct,
                  "Razón deriva AIS fisurada / deriva NSR-10": nube_t.razon, "Razón con la misma fuerza": nube_t.razon_misma_fuerza, "Razón sin tope": nube_t.razon_sin_tope,
                  "Relación rigidez viga/columna": nube_t.rigidez_viga_columna}).round(4).to_excel(xw, sheet_name="nube_puntos", index=False)
    for nombre, col in (("columna_NSR_1pct_cm", "NSR10_bruta"), ("columna_AIS_1.5pct_cm", "AIS100_fisurada"), ("columna_NSR_1.43pct_cm", "NSR10_fisurada")):
        (sec[sec.criterio == col].pivot(index="pisos", columns="luces", values="c") * 100).round(1).to_excel(xw, sheet_name=nombre)
    inc.round(1).to_excel(xw, sheet_name="concreto_adicional_AIS_pct")
print(ALINEACION)
print(med.round(3).to_string())
print(med_libre.round(3).to_string())
