"""Genera portico_3x6.xlsx: cálculo con fórmulas visibles del pórtico de 3 luces y 6 pisos.

Uso: python studies/armenia_nsr10_vs_ais/demostracion_manual/generar_portico_3x6.py
"""
import os
import sys

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(AQUI))
import run_study as r  # noqa: E402

M, N = 3, 6
d = pd.read_csv(os.path.join(os.path.dirname(AQUI), "results.csv"))
c0 = float(d[(d.variante == "base") & (d.tipo == "misma_seccion") & (d.modo == "limite_CuTa") & (d.luces == M) & (d.pisos == N)].c.iloc[0])
sitio = r.leer_sitio("Armenia")
ENC, NOTA = PatternFill("solid", fgColor="1C2326"), Font(italic=True, color="5F686C")


def hoja(wb, nombre, rigidez, factores):
    s = r.analizar(M, N, c0, rigidez, "limite_CuTa")
    ws = wb.create_sheet(nombre)
    ws.column_dimensions["A"].width = 38
    for col in "BCDEFGHIJ":
        ws.column_dimensions[col].width = 15
    ws["A1"] = f"{nombre}: pórtico de {M} luces y {N} pisos, Armenia, suelo D"; ws["A1"].font = Font(bold=True, size=13)
    ws["A2"] = f"Modificadores de inercia: {factores}. Los desplazamientos vienen de ROCKFRAME; todo lo demás se calcula con fórmulas en esta hoja."; ws["A2"].font = NOTA
    datos = [("Lado de columna c [m]", c0), ("Viga b = 0.75c [m]", "=0.75*B4"), ("Viga h = c [m]", "=B4"), ("Luz L [m]", r.LUZ), ("Altura de piso h [m]", r.ALTURA), ("Luces", M), ("Pisos", N),
             ("w piso [kN/m]", r.W_PISO), ("w cubierta [kN/m]", r.W_CUBIERTA), ("Peso unitario [kN/m³]", r.GAMMA), ("Aa", sitio["Aa"]), ("Av", sitio["Av"]), ("Fa", sitio["Fa"]), ("Fv", sitio["Fv"]), ("I", sitio["I"]), ("g [m/s²]", 9.8)]
    for i, (a, b) in enumerate(datos, 4):
        ws.cell(i, 1, a); ws.cell(i, 2, b)
    # B4 c, B5 bv, B6 hv, B7 L, B8 h, B9 M, B10 N, B11 w, B12 wc, B13 gamma, B14 Aa, B15 Av, B16 Fa, B17 Fv, B18 I, B19 g
    f0 = 21
    for j, t in enumerate(("Piso", "h_x [m]", "Wx [kN]", "Wx·h^k", "Cvx", "Fx [kN]", "δ ROCKFRAME [m]", "Wx·δ²", "Fx·δ", "Deriva [%]"), 1):
        x = ws.cell(f0, j, t); x.font = Font(bold=True, color="FFFFFF"); x.fill = ENC
    fin = f0 + N
    for k in range(1, N + 1):
        i = f0 + k
        ws.cell(i, 1, k); ws.cell(i, 2, f"=A{i}*$B$8")
        w = "$B$12" if k == N else "$B$11"
        col = "$B$13*$B$4^2*$B$8*($B$9+1)" + ("/2" if k == N else "")
        ws.cell(i, 3, f"=({w}+$B$13*$B$5*$B$6)*$B$7*$B$9+{col}")
        ws.cell(i, 4, f"=C{i}*B{i}^$B$33")
        ws.cell(i, 5, f"=D{i}/SUM($D${f0 + 1}:$D${fin})")
        ws.cell(i, 6, f"=E{i}*$B$32")
        ws.cell(i, 7, s["disp_piso"][k - 1])
        ws.cell(i, 8, f"=C{i}*G{i}^2"); ws.cell(i, 9, f"=F{i}*G{i}")
        ws.cell(i, 10, f"=ABS(G{i}-{'0' if k == 1 else f'G{i - 1}'})/$B$8*100")
    # La fila 28 queda libre; los resultados van de la 29 a la 37
    resultados = [("Altura total h_n [m]", "=B10*B8", float(N * r.ALTURA)), ("Ta = 0.047·h^0.9 [s]", "=0.047*B29^0.9", s["T_aprox_inicial"]), ("Cu = máx(1.75 − 1.2·Av·Fv; 1.2)", "=MAX(1.75-1.2*B15*B17,1.2)", s["Cu"])]
    ws.cell(28, 1, "Resultado").font = Font(bold=True); ws.cell(28, 2, "Hoja").font = Font(bold=True); ws.cell(28, 3, "ROCKFRAME").font = Font(bold=True); ws.cell(28, 4, "Dif. %").font = Font(bold=True)
    filas = {29: resultados[0], 30: resultados[1], 31: resultados[2],
             32: ("Cortante basal V = Sa·W [kN]", f"=B36*SUM(C{f0 + 1}:C{fin})", s["V"]),
             33: ("k", "=IF(B34<=0.5,1,IF(B34>2.5,2,0.75+0.5*B34))", s["k_exp"]),
             34: ("T de diseño usado, de la iteración final [s]", s["T_diseno"], s["T_diseno"]),
             35: ("TC [s]", "=0.48*B15*B17/(B14*B16)", 0.48 * sitio["Av"] * sitio["Fv"] / (sitio["Aa"] * sitio["Fa"])),
             36: ("Sa [g]", "=IF(B34<=B35,2.5*B14*B16*B18,1.2*B15*B17*B18/B34)", s["Sa"]),
             37: ("T Rayleigh [s]", f"=2*PI()*SQRT(SUM(H{f0 + 1}:H{fin})/(B19*SUM(I{f0 + 1}:I{fin})))", s["T_detallado"]),
             38: ("Peso total W [kN]", f"=SUM(C{f0 + 1}:C{fin})", s["W_total"]),
             39: ("Deriva máxima [%]", f"=MAX(J{f0 + 1}:J{fin})", max(s["drift_pct"])),
             40: ("Comprobación: mín(T Rayleigh; Cu·Ta) [s]", "=MIN(B37,B30*B31)", s["T_diseno"])}
    for i, (a, b, c_) in filas.items():
        ws.cell(i, 1, a); ws.cell(i, 2, b); ws.cell(i, 3, c_); ws.cell(i, 4, f"=(B{i}-C{i})/C{i}*100")
    ws.cell(42, 1, "El período es dato de la última iteración, porque las fuerzas dependen de él. La fila 40 comprueba que sea consistente con la hoja.").font = NOTA


wb = Workbook()
ws = wb.active; ws.title = "Leeme"
for i, t in enumerate(("Demostración manual del pórtico de 3 luces y 6 pisos.", "Armenia, suelo D, con la sección mínima de NSR-10 (1 %) en ambas hojas.",
                       "Selecciona cualquier celda de resultados para ver su fórmula. La columna Dif. % compara con ROCKFRAME.",
                       "Fuentes: NSR-10 A.2.6 (espectro), A.4.2 (período), A.4.3 (fuerzas), A.6 (derivas)."), 1):
    ws.cell(i, 1, t)
ws.column_dimensions["A"].width = 90
hoja(wb, "NSR-10 (1 %)", "bruta", "1.0 Ig en vigas y columnas")
hoja(wb, "AIS fisurada (1.5 %)", "fisurada", "0.35 Ig en vigas y 0.70 Ig en columnas")
wb.save(os.path.join(AQUI, "portico_3x6.xlsx"))
print("c =", c0)
