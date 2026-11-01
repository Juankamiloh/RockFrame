"""Genera docs/etabs_reference_cases.xlsx con los casos de la Etapa 5.

Uso: python validation/generate_etabs_cases.py
"""
import os
import sys

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "tests"))
from comun import ESPECTRO, FACTORES, FC, G, GAMMA, PORTICOS, m, sismo  # noqa: E402

CASOS = ("1x2", "3x3", "3x6")
GRUPO = "I"
TINTA, PIEDRA, ETABS, LINEA = "1C2326", "F1EEE8", "FFF4D6", "DFDAD1"
FINO = Side(style="thin", color=LINEA)
BORDE = Border(left=FINO, right=FINO, top=FINO, bottom=FINO)


def encabezado(ws, fila, textos, col=1):
    for i, t in enumerate(textos):
        c = ws.cell(fila, col + i, t)
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor=TINTA)
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        c.border = BORDE
    ws.row_dimensions[fila].height = 32


def titulo(ws, fila, texto):
    ws.cell(fila, 1, texto).font = Font(bold=True, size=12, color=TINTA)


def dato(ws, fila, col, valor, formato=None):
    c = ws.cell(fila, col, valor)
    c.border = BORDE
    c.alignment = Alignment(horizontal="center")
    if formato:
        c.number_format = formato
    return c


def entrada_etabs(ws, fila, col):
    """Celda vacía para ETABS y al lado la diferencia, que se calcula al escribir el valor."""
    c = dato(ws, fila, col, None)
    c.fill = PatternFill("solid", fgColor=ETABS)
    r, e = f"{get_column_letter(col - 1)}{fila}", f"{get_column_letter(col)}{fila}"
    dato(ws, fila, col + 1, f'=IF(ISBLANK({e}),"",({e}-{r})/{r}*100)', "0.000")


def hoja_instrucciones(wb):
    ws = wb.active
    ws.title = "Instrucciones"
    ws.column_dimensions["A"].width = 112
    filas = [
        ("ROCKFRAME: casos de referencia para ETABS", True),
        ("Tres pórticos planos, cada uno con inercia bruta y fisurada. Cada caso tiene su hoja.", False),
        ("", False),
        ("Cómo usar este archivo", True),
        ("1. Modela el pórtico con los datos de la hoja Datos y aplica las fuerzas y masas por nudo de la hoja del caso.", False),
        ("2. Escribe los resultados de ETABS en las celdas amarillas. La diferencia en % se calcula sola.", False),
        ("", False),
        ("Configuración necesaria en ETABS para que sea comparable", True),
        ("• Pórtico en el plano XZ, con grados de libertad activos UX, UZ y RY.", False),
        ("• Sin deformación por cortante: modificadores de área de cortante As2 y As3 iguales a 0.", False),
        ("• Sin zonas rígidas en los extremos, sin diafragma rígido y sin P-Delta.", False),
        ("• Material con peso y masa nulos. La masa entra como masa puntual por nudo, en la dirección X.", False),
        ("• Modificador I33: 0.35 en vigas y 0.70 en columnas para los casos fisurados. No modifiques el área.", False),
        ("• Carga lateral: la fuerza Fx por nudo indicada en cada hoja. Sin autoseísmico: ROCKFRAME entrega las fuerzas.", False),
        ("", False),
        ("Cómo leer los resultados", True),
        ("• T de ETABS es el modo 1, exacto. T Rayleigh es una aproximación: se espera una diferencia cercana a −0.1 % o menor.", False),
        ("• Los desplazamientos de piso de ROCKFRAME son el promedio de los nudos del nivel, sin diafragma.", False),
        ("• Con secciones fisuradas, la deriva calculada se compara contra 1.0/0.7 = 1.43 % (A.6.4.1.1).", False),
        ("• Los valores de esta hoja son fuerzas Fs, sin dividir por R.", False),
        ("• El período de diseño aplica el límite T ≤ Cu·Ta (A.4.2.1 y A.6.2.1.1).", False),
    ]
    for i, (t, negrita) in enumerate(filas, 1):
        c = ws.cell(i, 1, t)
        c.font = Font(bold=negrita, size=14 if i == 1 else 11, color=TINTA)
        c.alignment = Alignment(wrap_text=True, vertical="top")


def hoja_datos(wb):
    ws = wb.create_sheet("Datos")
    for col, ancho in zip("ABCDE", (34, 20, 20, 20, 20)):
        ws.column_dimensions[col].width = ancho
    fila = 1
    titulo(ws, fila, "Material y peso"); fila += 1
    encabezado(ws, fila, ["Parámetro", "Valor", "Unidad"]); fila += 1
    for a, b, c, fmt in (("f'c", FC, "MPa", "0.00"), ("E = 4700·√f'c", m.compute_E(FC) / 1e6, "MPa", "0.00"), ("Módulo de Poisson", 0.2, "", "0.00"),
                         ("Peso unitario γ", GAMMA, "kN/m³", "0.00"), ("g", G, "m/s²", "0.00")):
        dato(ws, fila, 1, a); dato(ws, fila, 2, b, fmt); dato(ws, fila, 3, c); fila += 1
    fila += 1
    titulo(ws, fila, "Espectro NSR-10"); fila += 1
    encabezado(ws, fila, ["Parámetro", "Valor"]); fila += 1
    e = ESPECTRO
    Tc = 0.48 * e["Av"] * e["Fv"] / (e["Aa"] * e["Fa"])
    for a, b in (("Aa", e["Aa"]), ("Av", e["Av"]), ("Fa", e["Fa"]), ("Fv", e["Fv"]), ("Grupo de uso", GRUPO), ("I", e["I"]), ("Tc [s]", Tc), ("TL [s]", 2.4 * e["Fv"]),
                 ("Ct", 0.047), ("α", 0.9), ("Cu", m.compute_Cu(e["Av"], e["Fv"]))):
        dato(ws, fila, 1, a); dato(ws, fila, 2, b, "0.0000" if isinstance(b, float) else None); fila += 1
    fila += 1
    titulo(ws, fila, "Inercia"); fila += 1
    encabezado(ws, fila, ["Caso", "Factor I vigas", "Factor I columnas", "Área"]); fila += 1
    for nf, (fv, fc) in FACTORES.items():
        dato(ws, fila, 1, nf.capitalize()); dato(ws, fila, 2, fv, "0.00"); dato(ws, fila, 3, fc, "0.00"); dato(ws, fila, 4, 1.0, "0.00"); fila += 1
    fila += 1
    titulo(ws, fila, "Geometría y cargas (bases empotradas)"); fila += 1
    encabezado(ws, fila, ["Pórtico", "Luces [m]", "Alturas de piso [m]", "Columna b×h [m]", "Viga b×h [m]"]); fila += 1
    for nc in CASOS:
        c = PORTICOS[nc]
        for col, v in enumerate((nc, ", ".join(f"{x:g}" for x in c["L"]), ", ".join(f"{x:g}" for x in c["H"]), f"{c['col'][0][0]}×{c['col'][0][1]}", f"{c['vig'][0][0]}×{c['vig'][0][1]}"), 1):
            dato(ws, fila, col, v)
        fila += 1
    fila += 1
    encabezado(ws, fila, ["Pórtico", "w por piso [kN/m]"]); fila += 1
    for nc in CASOS:
        dato(ws, fila, 1, nc); dato(ws, fila, 2, ", ".join(f"{x:g}" for x in PORTICOS[nc]["w"])); fila += 1
    ws.cell(fila + 1, 1, "w no incluye peso propio: se suma aparte con γ. El peso por piso incluye la viga completa y media columna arriba y abajo.")


def hoja_caso(wb, nc, nf):
    c = PORTICOS[nc]; fv, fc = FACTORES[nf]
    s = sismo(c, fv, fc, modo="limite_CuTa", tol=1.0, reducir_derivas_fisuradas=fc < 1.0)
    n_nudos = len(c["L"]) + 1
    ws = wb.create_sheet(f"{nc} {nf}")
    ws.sheet_view.showGridLines = False
    for i in range(1, 14):
        ws.column_dimensions[get_column_letter(i)].width = 14
    ws.column_dimensions["A"].width = 26
    ws.cell(1, 1, f"Pórtico {nc}, inercia {nf}").font = Font(bold=True, size=14, color=TINTA)

    titulo(ws, 3, "Resumen")
    encabezado(ws, 4, ["Resultado", "ROCKFRAME", "ETABS", "Dif. %"])
    resumen = (("Ta [s]", s["T_aprox_inicial"], "0.0000", False), ("Cu", s["Cu"], "0.0000", False), ("Cu·Ta [s]", s["T_limite"], "0.0000", False),
               ("T Rayleigh [s]", s["T_detallado"], "0.0000", True), ("T de diseño [s]", s["T_diseno"], "0.0000", False), ("Sa [g]", s["Sa"], "0.0000", False),
               ("k", s["k_exp"], "0.000", False), ("W total [kN]", s["W_total"], "0.00", False), ("Cortante basal V [kN]", s["V"], "0.00", True),
               ("Deriva máxima [%]", max(s["drift_pct"]), "0.0000", True), ("Límite de deriva [%]", s["limite_deriva_pct"], "0.00", False),
               ("Cumple", "Sí" if s["cumple_deriva"] else "No", None, False))
    fila = 5
    for nombre, valor, fmt, compara in resumen:
        dato(ws, fila, 1, nombre); dato(ws, fila, 2, valor, fmt)
        if compara:
            entrada_etabs(ws, fila, 3)
        else:
            dato(ws, fila, 3, None); dato(ws, fila, 4, None)
        fila += 1

    fila += 1
    titulo(ws, fila, "Datos para ETABS por nudo de cada nivel"); fila += 1
    encabezado(ws, fila, ["Piso", "Altura [m]", "Wi [kN]", "Fx por nudo [kN]", "Masa por nudo [kN·s²/m]"]); fila += 1
    for k in reversed(range(s["N_pisos"])):
        dato(ws, fila, 1, k + 1); dato(ws, fila, 2, s["hi"][k], "0.00"); dato(ws, fila, 3, s["Wi"][k], "0.000")
        dato(ws, fila, 4, s["Fi"][k] / n_nudos, "0.0000"); dato(ws, fila, 5, s["Wi"][k] / G / n_nudos, "0.00000"); fila += 1

    fila += 1
    titulo(ws, fila, "Resultados por piso"); fila += 1
    encabezado(ws, fila, ["Piso", "Fx ROCKFRAME [kN]", "Fx ETABS [kN]", "Dif. %", "Desp. ROCKFRAME [mm]", "Desp. ETABS [mm]", "Dif. %", "Deriva ROCKFRAME [%]", "Deriva ETABS [%]", "Dif. %"]); fila += 1
    for k in reversed(range(s["N_pisos"])):
        dato(ws, fila, 1, k + 1)
        for col, valor, fmt in ((2, s["Fi"][k], "0.00"), (5, s["disp_piso"][k] * 1000, "0.000"), (8, s["drift_pct"][k], "0.0000")):
            dato(ws, fila, col, valor, fmt)
            entrada_etabs(ws, fila, col + 1)
        fila += 1

    fila += 1
    titulo(ws, fila, "Período por iteración"); fila += 1
    encabezado(ws, fila, ["Iteración", "T entrada [s]", "Sa [g]", "k", "V [kN]", "T Rayleigh [s]", "Cambio [%]", "Convergió"]); fila += 1
    for it in s["iterations"]:
        for col, (valor, fmt) in enumerate(((it["iter"], None), (it["T_in"], "0.0000"), (it["Sa"], "0.0000"), (it["k_exp"], "0.000"), (it["V"], "0.00"),
                                            (it["T_rayleigh"], "0.0000"), (it["error_pct"], "0.000"), ("Sí" if it["converged"] else "No", None)), 1):
            dato(ws, fila, col, valor, fmt)
        fila += 1
    return s


def main():
    wb = Workbook()
    hoja_instrucciones(wb)
    hoja_datos(wb)
    resultados = {f"{nc} {nf}": hoja_caso(wb, nc, nf) for nc in CASOS for nf in FACTORES}
    ruta = os.path.join(RAIZ, "docs", "etabs_reference_cases.xlsx")
    wb.save(ruta)
    print("Archivo:", ruta)
    for nombre, s in resultados.items():
        print(f"{nombre:14s} T_R={s['T_detallado']:.4f} T_dis={s['T_diseno']:.4f} V={s['V']:.2f} deriva={max(s['drift_pct']):.3f}% límite={s['limite_deriva_pct']:.2f}")


if __name__ == "__main__":
    main()
