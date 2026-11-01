# ROCKFRAME – Interfaz gráfica
# Toda la matemática está en engine.py; este archivo solo lee datos y muestra resultados.

import json
import re
import tkinter as tk
from tkinter import filedialog, ttk

import customtkinter as ctk
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from matplotlib.patches import Polygon
import numpy as np

from rockframe.export import exportar_excel
from rockframe.engine import (
    N_to_kN, build_case_gen, compute_Cu, compute_E, compute_design_spectrum, run_seismic_iterative,
    run_static_analysis, spectral_acceleration,
)

# ===== Identidad visual =====
PIEDRA = "#F1EEE8"
PAPEL = "#FFFFFF"
TINTA = "#1C2326"
GRIS = "#6A7377"
LINEA = "#DFDAD1"
SUAVE = "#F7F5F1"
TERRACOTA = "#B4532A"
TERRACOTA_OSCURA = "#94431F"
ACERO = "#2F5D73"
VERDE = "#2E7D5B"
ROJO = "#B3261E"
FUENTE = "Segoe UI"
TITULAR = "Bahnschrift"

PERIODOS = {"Rayleigh ≤ Cu·Ta": "limite_CuTa", "Ta aproximado": "Ta", "Rayleigh sin límite": "sin_limite"}
GRUPOS = {"I": 1.0, "II": 1.1, "III": 1.25, "IV": 1.5}
BASES = ("Empotrada", "Articulada", "Personalizada")
CT, ALFA = 0.047, 0.9  # Tabla A.4.2-1, pórticos de concreto reforzado
VISTAS = ("Pórtico", "Sismo", "Derivas", "Espectro", "Fuerzas")

EJEMPLO = {
    "M": "3", "N": "6", "L": "5, 5, 5", "H": "4, 3, 3, 3, 3, 3", "bc": "0.6", "hc": "0.6", "bv": "0.4", "hv": "0.55",
    "fv": "0.35", "fcol": "0.70", "fc": "28", "E": "", "gamma": "24", "w": "35, 35, 35, 35, 35, 25",
    "Aa": "0.25", "Av": "0.25", "Fa": "1.3", "Fv": "1.9", "I": "1.0", "iter": "10", "tol": "1.0", "viva": "", "h": "",
    "ciudad": "", "nodo": "", "Px": "0", "Py": "0", "Mz": "0", "apoyos": "",
}


def kN(x):
    # Convierte N a kN sin mostrar "-0.00"
    return f"{round(N_to_kN(x), 2) + 0.0:.2f}"


class RockFrameUI(ctk.CTk):
    def __init__(self):
        ctk.set_appearance_mode("light")
        super().__init__(fg_color=PIEDRA)
        self.title("ROCKFRAME · Análisis de pórticos 2D con NSR-10")
        self.geometry("1500x930")
        self.minsize(1240, 780)
        self.v = {}
        self.campos = {}
        self.fallas = {}
        self.nodales = {}
        self.res = None
        self.cargando = True
        self._espera = None
        self._nodos_dibujo = {}
        self.f = {
            "marca": ctk.CTkFont(TITULAR, 24, "bold"), "h2": ctk.CTkFont(TITULAR, 15, "bold"),
            "kpi": ctk.CTkFont(TITULAR, 29, "bold"), "texto": ctk.CTkFont(FUENTE, 13),
            "peq": ctk.CTkFont(FUENTE, 12), "fuerte": ctk.CTkFont(FUENTE, 13, "bold"),
        }
        self._estilo_tablas()
        self._encabezado()
        cuerpo = ctk.CTkFrame(self, fg_color="transparent")
        cuerpo.pack(fill="both", expand=True, padx=16, pady=(0, 14))
        self._panel_datos(cuerpo)
        self._panel_resultados(cuerpo)
        self.cargando = False
        self._redibujar()

    # ---------- Armazón ----------
    def _estilo_tablas(self):
        st = ttk.Style(self)
        st.theme_use("clam")
        st.configure("RF.Treeview", background=PAPEL, fieldbackground=PAPEL, foreground=TINTA, rowheight=30,
                     borderwidth=0, font=(FUENTE, 11))
        st.configure("RF.Treeview.Heading", background=SUAVE, foreground=GRIS, relief="flat", font=(FUENTE, 10, "bold"), padding=(6, 7))
        st.map("RF.Treeview", background=[("selected", "#EFE3DB")], foreground=[("selected", TINTA)])
        st.map("RF.Treeview.Heading", background=[("active", SUAVE)])

    def _encabezado(self):
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(fill="x", padx=20, pady=(14, 12))
        marca = ctk.CTkFrame(bar, fg_color="transparent")
        marca.pack(side="left")
        ctk.CTkLabel(marca, text="ROCKFRAME", font=self.f["marca"], text_color=TINTA).pack(anchor="w")
        ctk.CTkLabel(marca, text="Pórticos planos de concreto · NSR-10", font=self.f["peq"], text_color=GRIS, height=16).pack(anchor="w")

        self.btn_calcular = ctk.CTkButton(bar, text="Calcular", width=150, height=42, corner_radius=8, font=self.f["fuerte"],
                                          fg_color=TERRACOTA, hover_color=TERRACOTA_OSCURA, command=self.calcular)
        self.btn_calcular.pack(side="right")
        self.btn_excel = self._boton_sec(bar, "Exportar Excel", self.exportar, 130)
        self.btn_excel.pack(side="right", padx=(0, 18))
        self.btn_excel.configure(state="disabled")
        for texto, cmd in (("Guardar", self.guardar), ("Abrir", self.abrir), ("Ejemplo", self.cargar_ejemplo)):
            self._boton_sec(bar, texto, cmd, 82).pack(side="right", padx=(0, 6))

        self.estado = ctk.CTkLabel(bar, text="Sin calcular", font=self.f["peq"], text_color=GRIS)
        self.estado.pack(side="left", padx=26)

    def _boton_sec(self, padre, texto, cmd, ancho=100):
        return ctk.CTkButton(padre, text=texto, width=ancho, height=34, corner_radius=8, font=self.f["texto"], fg_color=PAPEL,
                             hover_color=SUAVE, text_color=TINTA, border_width=1, border_color=LINEA, command=cmd)

    def _tarjeta(self, padre, titulo=None):
        t = ctk.CTkFrame(padre, fg_color=PAPEL, corner_radius=10, border_width=1, border_color=LINEA)
        t.pack(fill="x", pady=(0, 10), padx=(0, 4))
        cuerpo = ctk.CTkFrame(t, fg_color="transparent")
        cuerpo.pack(fill="x", padx=14, pady=12)
        if titulo:
            ctk.CTkLabel(cuerpo, text=titulo, font=self.f["h2"], text_color=TINTA, anchor="w").pack(fill="x", pady=(0, 8))
        return cuerpo

    def _campo(self, padre, clave, titulo, unidad="", ayuda=""):
        caja = ctk.CTkFrame(padre, fg_color="transparent")
        ctk.CTkLabel(caja, text=titulo + (f"  [{unidad}]" if unidad else ""), font=self.f["peq"], text_color=GRIS, anchor="w", height=18).pack(fill="x")
        var = tk.StringVar(self, value=EJEMPLO.get(clave, ""))
        var.trace_add("write", lambda *_: self._al_cambiar())
        ent = ctk.CTkEntry(caja, textvariable=var, height=32, corner_radius=6, font=self.f["texto"], fg_color=SUAVE,
                           border_color=LINEA, border_width=1, text_color=TINTA)
        ent.pack(fill="x", pady=(1, 0))
        msg = ctk.CTkLabel(caja, text=ayuda, font=self.f["peq"], text_color=GRIS, anchor="w", height=16, wraplength=330, justify="left")
        if ayuda:
            msg.pack(fill="x")
        self.v[clave] = var
        self.campos[clave] = (ent, msg, ayuda)
        return caja

    def _rejilla(self, padre, *cajas_fn):
        fila = ctk.CTkFrame(padre, fg_color="transparent")
        fila.pack(fill="x", pady=(0, 8))
        for i, fn in enumerate(cajas_fn):
            fila.grid_columnconfigure(i, weight=1, uniform="col")
            fn(fila).grid(row=0, column=i, sticky="new", padx=(0 if i == 0 else 8, 0))

    def _combo(self, padre, clave, titulo, valores, inicial, cmd=None):
        caja = ctk.CTkFrame(padre, fg_color="transparent")
        ctk.CTkLabel(caja, text=titulo, font=self.f["peq"], text_color=GRIS, anchor="w", height=18).pack(fill="x")
        var = tk.StringVar(self, value=inicial)
        var.trace_add("write", lambda *_: self._al_cambiar())
        ctk.CTkComboBox(caja, values=list(valores), variable=var, state="readonly", height=32, corner_radius=6, font=self.f["texto"],
                        fg_color=SUAVE, border_color=LINEA, border_width=1, button_color=LINEA, button_hover_color=GRIS,
                        text_color=TINTA, dropdown_fg_color=PAPEL, dropdown_text_color=TINTA, dropdown_font=self.f["texto"],
                        command=cmd).pack(fill="x", pady=(1, 0))
        self.v[clave] = var
        return caja

    def _casilla(self, padre, clave, texto, inicial=False):
        var = tk.BooleanVar(self, value=inicial)
        var.trace_add("write", lambda *_: self._al_cambiar())
        ctk.CTkCheckBox(padre, text=texto, variable=var, font=self.f["texto"], text_color=TINTA, checkbox_width=20, checkbox_height=20,
                        corner_radius=5, border_width=2, border_color=GRIS, fg_color=TERRACOTA, hover_color=TERRACOTA_OSCURA).pack(anchor="w", pady=(2, 6))
        self.v[clave] = var

    # ---------- Panel de datos ----------
    def _panel_datos(self, padre):
        self.tabs = ctk.CTkTabview(padre, width=410, fg_color=PIEDRA, corner_radius=10, border_width=0,
                                   segmented_button_fg_color=LINEA, segmented_button_selected_color=PAPEL,
                                   segmented_button_selected_hover_color=PAPEL, segmented_button_unselected_color=LINEA,
                                   segmented_button_unselected_hover_color="#D2CDC3", text_color=TINTA,
                                   text_color_disabled=GRIS)
        self.tabs.pack(side="left", fill="y", padx=(0, 14))
        self.tabs.pack_propagate(False)
        pag = {}
        for nombre in ("Pórtico", "Cargas", "Sismo"):
            self.tabs.add(nombre)
            pag[nombre] = ctk.CTkScrollableFrame(self.tabs.tab(nombre), fg_color="transparent", scrollbar_button_color=LINEA, scrollbar_button_hover_color=GRIS)
            pag[nombre].pack(fill="both", expand=True)
        self.tabs._segmented_button.configure(font=self.f["fuerte"])
        self._pagina_portico(pag["Pórtico"])
        self._pagina_cargas(pag["Cargas"])
        self._pagina_sismo(pag["Sismo"])

    def _pagina_portico(self, p):
        g = self._tarjeta(p, "Geometría")
        self._rejilla(g, lambda m: self._campo(m, "M", "Luces"), lambda m: self._campo(m, "N", "Pisos"))
        self._campo(g, "L", "Longitud de luces", "m", "Una por luz, o una sola para repetir").pack(fill="x", pady=(0, 8))
        self._campo(g, "H", "Altura de pisos", "m", "De abajo hacia arriba, o una sola para repetir").pack(fill="x")

        s = self._tarjeta(p, "Secciones")
        self._rejilla(s, lambda m: self._campo(m, "bc", "Columna b", "m"), lambda m: self._campo(m, "hc", "Columna h", "m"))
        self._rejilla(s, lambda m: self._campo(m, "bv", "Viga b", "m"), lambda m: self._campo(m, "hv", "Viga h", "m"))
        self._rejilla(s, lambda m: self._campo(m, "fv", "Factor I vigas", "", "Bruta = 1.0"),
                      lambda m: self._campo(m, "fcol", "Factor I columnas", "", "Bruta = 1.0"))

        c = self._tarjeta(p, "Concreto")
        self._rejilla(c, lambda m: self._campo(m, "fc", "f'c", "MPa"), lambda m: self._campo(m, "gamma", "Peso unitario γ", "kN/m³"))
        self._campo(c, "E", "Módulo E", "MPa", "Vacío usa E = 4700·√f'c").pack(fill="x")

        a = self._tarjeta(p, "Apoyos en la base")
        self.v["base"] = tk.StringVar(self, value=BASES[0])
        self.v["base"].trace_add("write", lambda *_: self._al_cambiar())
        ctk.CTkSegmentedButton(a, values=list(BASES), variable=self.v["base"], font=self.f["peq"], fg_color=LINEA, unselected_color=LINEA,
                               unselected_hover_color="#D2CDC3", selected_color=PAPEL, selected_hover_color=PAPEL,
                               text_color=TINTA).pack(fill="x", pady=(0, 8))
        self._campo(a, "apoyos", "Apoyos personalizados", "", "Ej.: 1:FX,FY,M; 2:FX,FY. M restringe el giro").pack(fill="x")

    def _pagina_cargas(self, p):
        w = self._tarjeta(p, "Carga distribuida en vigas")
        self._campo(w, "w", "w por piso, hacia abajo", "kN/m", "Sin peso propio: se suma aparte con γ").pack(fill="x", pady=(0, 6))
        self._casilla(w, "pp", "Sumar peso propio en el análisis estático", True)

        n = self._tarjeta(p, "Cargas en nudos")
        ctk.CTkLabel(n, text="Solo afectan el análisis estático. Toca un nudo en el dibujo para elegirlo.", font=self.f["peq"], text_color=GRIS,
                     wraplength=330, justify="left", anchor="w").pack(fill="x", pady=(0, 6))
        self._rejilla(n, lambda m: self._campo(m, "nodo", "Nudo"), lambda m: self._campo(m, "Px", "Px", "kN"),
                      lambda m: self._campo(m, "Py", "Py", "kN"), lambda m: self._campo(m, "Mz", "Mz", "kN·m"))
        fila = ctk.CTkFrame(n, fg_color="transparent")
        fila.pack(fill="x", pady=(0, 8))
        self._boton_sec(fila, "Agregar", self.agregar_nodal, 100).pack(side="left", padx=(0, 6))
        self._boton_sec(fila, "Quitar", self.quitar_nodal, 100).pack(side="left")
        marco = tk.Frame(n, bg=PAPEL)
        marco.pack(fill="x")
        self.tabla_nodal = self._tabla(marco, (("n", "Nudo", 54), ("px", "Px", 70), ("py", "Py", 70), ("mz", "Mz", 70)), 5, barra=False)

    def _pagina_sismo(self, p):
        e = self._tarjeta(p, "Espectro de diseño (A.2.6)")
        self._campo(e, "ciudad", "Ciudad").pack(fill="x", pady=(0, 8))
        self._rejilla(e, lambda m: self._combo(m, "amenaza", "Amenaza", ("Alta", "Intermedia", "Baja"), "Alta"),
                      lambda m: self._combo(m, "suelo", "Suelo", ("A", "B", "C", "D", "E", "F"), "D"))
        self._rejilla(e, lambda m: self._campo(m, "Aa", "Aa"), lambda m: self._campo(m, "Av", "Av"))
        self._rejilla(e, lambda m: self._campo(m, "Fa", "Fa"), lambda m: self._campo(m, "Fv", "Fv"))
        self._rejilla(e, lambda m: self._combo(m, "grupo", "Grupo de uso", GRUPOS, "I", self._al_grupo), lambda m: self._campo(m, "I", "Coeficiente I"))

        t = self._tarjeta(p, "Período")
        self._combo(t, "periodo", "Período de diseño", PERIODOS, "Rayleigh ≤ Cu·Ta").pack(fill="x", pady=(0, 2))
        self.txt_periodo = ctk.CTkLabel(t, text="", font=self.f["peq"], text_color=GRIS, wraplength=330, justify="left", anchor="w")
        self.txt_periodo.pack(fill="x", pady=(0, 8))
        self._casilla(t, "h_manual", "Definir la altura h a mano")
        self._campo(t, "h", "Altura h", "m", "Solo se usa si activas la casilla").pack(fill="x", pady=(0, 8))
        self._rejilla(t, lambda m: self._campo(m, "iter", "Iteraciones máx."), lambda m: self._campo(m, "tol", "Tolerancia", "%"))

        d = self._tarjeta(p, "Evaluación de derivas (A.6)")
        self._casilla(d, "red07", "Límite 1.0/0.7 = 1.43 % con secciones fisuradas", True)
        self._casilla(d, "I1", "Usar I = 1.0: grupos II a IV")
        self._campo(d, "viva", "Carga viva por piso para Qi", "kN", "Vacío: Qi sin carga viva (cota inferior)").pack(fill="x")

    def _al_grupo(self, valor):
        self.v["I"].set(str(GRUPOS[valor]))

    # ---------- Panel de resultados ----------
    def _panel_resultados(self, padre):
        lado = ctk.CTkFrame(padre, fg_color="transparent")
        lado.pack(side="left", fill="both", expand=True)
        self.nav_var = tk.StringVar(self, value=VISTAS[0])
        ctk.CTkSegmentedButton(lado, values=list(VISTAS), variable=self.nav_var, command=self.ver, height=36, font=self.f["fuerte"], fg_color=LINEA,
                               unselected_color=LINEA, unselected_hover_color="#D2CDC3", selected_color=PAPEL, selected_hover_color=PAPEL,
                               text_color=TINTA).pack(anchor="w", pady=(6, 10))
        self.aviso = ctk.CTkLabel(lado, text="", font=self.f["fuerte"], text_color="#FFFFFF", fg_color=ROJO, corner_radius=8, height=36, anchor="w", padx=14)
        self.lado = lado
        self.hoja = ctk.CTkFrame(lado, fg_color=PAPEL, corner_radius=12, border_width=1, border_color=LINEA)
        self.hoja.pack(fill="both", expand=True)
        self.vistas = {n: ctk.CTkFrame(self.hoja, fg_color="transparent") for n in VISTAS}
        self._vista_portico(self.vistas["Pórtico"])
        self._vista_sismo(self.vistas["Sismo"])
        self._vista_derivas(self.vistas["Derivas"])
        self._vista_espectro(self.vistas["Espectro"])
        self._vista_fuerzas(self.vistas["Fuerzas"])
        self.ver(VISTAS[0])

    def ver(self, nombre):
        self.nav_var.set(nombre)
        for n, f in self.vistas.items():
            f.pack_forget()
        self.vistas[nombre].pack(fill="both", expand=True, padx=14, pady=12)

    def _lienzo(self, padre, figura):
        c = FigureCanvasTkAgg(figura, master=padre)
        c.get_tk_widget().configure(highlightthickness=0, bg=PAPEL)
        c.get_tk_widget().pack(fill="both", expand=True)
        return c

    def _tabla(self, padre, columnas, alto, barra=True):
        t = ttk.Treeview(padre, columns=[c[0] for c in columnas], show="headings", height=alto, style="RF.Treeview", selectmode="browse")
        for clave, titulo, ancho in columnas:
            t.heading(clave, text=titulo)
            t.column(clave, width=ancho, anchor="center", stretch=True)
        t.tag_configure("par", background=SUAVE)
        t.tag_configure("mal", foreground=ROJO)
        if barra:
            b = ctk.CTkScrollbar(padre, command=t.yview, button_color=LINEA, button_hover_color=GRIS)
            t.configure(yscrollcommand=b.set)
            b.pack(side="right", fill="y")
        t.pack(side="left", fill="both", expand=True)
        return t

    def _llenar(self, tabla, filas):
        tabla.delete(*tabla.get_children())
        for i, (fila, mal) in enumerate(filas):
            etiquetas = (["par"] if i % 2 else []) + (["mal"] if mal else [])
            tabla.insert("", "end", values=fila, tags=etiquetas)

    def _vista_portico(self, v):
        barra = ctk.CTkFrame(v, fg_color="transparent")
        barra.pack(fill="x")
        self.caso = tk.StringVar(self, value="Modelo")
        ctk.CTkSegmentedButton(barra, values=["Modelo", "Deformada gravedad", "Deformada sismo"], variable=self.caso, command=lambda _: self._redibujar(),
                               font=self.f["peq"], fg_color=LINEA, unselected_color=LINEA, unselected_hover_color="#D2CDC3", selected_color=PAPEL,
                               selected_hover_color=PAPEL, text_color=TINTA).pack(side="left")
        self.ver_nudos = tk.BooleanVar(self, value=True)
        ctk.CTkCheckBox(barra, text="Números de nudo", variable=self.ver_nudos, command=self._redibujar, font=self.f["peq"], text_color=TINTA, checkbox_width=18,
                        checkbox_height=18, corner_radius=4, border_width=2, border_color=GRIS, fg_color=ACERO, hover_color=ACERO).pack(side="right")
        self.txt_escala = ctk.CTkLabel(barra, text="", font=self.f["peq"], text_color=GRIS)
        self.txt_escala.pack(side="right", padx=14)
        self.fig_m = Figure(facecolor=PAPEL, layout="constrained")
        self.ax_m = self.fig_m.add_subplot(111)
        self.can_m = self._lienzo(v, self.fig_m)
        self.can_m.mpl_connect("button_press_event", self._clic_nudo)

    def _kpi(self, padre, col, titulo):
        c = ctk.CTkFrame(padre, fg_color=SUAVE, corner_radius=10)
        c.grid(row=0, column=col, sticky="nsew", padx=(0 if col == 0 else 10, 0))
        padre.grid_columnconfigure(col, weight=1, uniform="k")
        ctk.CTkLabel(c, text=titulo, font=self.f["peq"], text_color=GRIS, anchor="w", height=18).pack(fill="x", padx=14, pady=(10, 0))
        valor = ctk.CTkLabel(c, text="—", font=self.f["kpi"], text_color=TINTA, anchor="w", height=38)
        valor.pack(fill="x", padx=14)
        nota = ctk.CTkLabel(c, text="", font=self.f["peq"], text_color=GRIS, anchor="w", height=18)
        nota.pack(fill="x", padx=14, pady=(0, 10))
        return valor, nota

    def _vista_sismo(self, v):
        fila = ctk.CTkFrame(v, fg_color="transparent")
        fila.pack(fill="x", pady=(0, 10))
        self.k_T = self._kpi(fila, 0, "Período de diseño")
        self.k_V = self._kpi(fila, 1, "Cortante basal")
        self.k_D = self._kpi(fila, 2, "Deriva máxima evaluada")
        self.k_Q = self._kpi(fila, 3, "Índice de estabilidad")
        self.txt_avisos = ctk.CTkLabel(v, text="", font=self.f["peq"], text_color=ROJO, anchor="w", justify="left", wraplength=980)
        self.txt_avisos.pack(fill="x")
        ctk.CTkLabel(v, text="Resultados por piso", font=self.f["h2"], text_color=TINTA, anchor="w").pack(fill="x", pady=(2, 4))
        m1 = tk.Frame(v, bg=PAPEL); m1.pack(fill="both", expand=True)
        self.tabla_pisos = self._tabla(m1, (("p", "Piso", 50), ("h", "Altura [m]", 80), ("W", "Wi [kN]", 90), ("C", "Cvx", 70), ("F", "Fx [kN]", 90), ("Vp", "Vi [kN]", 90),
                                            ("d", "Despl. [mm]", 90), ("r", "Deriva [%]", 90), ("e", "Evaluada [%]", 90), ("q", "Qi", 70)), 7)
        ctk.CTkLabel(v, text="Iteración del período", font=self.f["h2"], text_color=TINTA, anchor="w").pack(fill="x", pady=(10, 4))
        m2 = tk.Frame(v, bg=PAPEL); m2.pack(fill="x")
        self.tabla_iter = self._tabla(m2, (("i", "Iter.", 50), ("t", "T entrada [s]", 100), ("s", "Sa [g]", 90), ("k", "k", 70), ("V", "V [kN]", 100),
                                           ("r", "T Rayleigh [s]", 110), ("e", "Cambio [%]", 90), ("c", "Convergió", 80)), 4)

    def _vista_derivas(self, v):
        self.fig_d = Figure(facecolor=PAPEL, layout="constrained")
        self.ax_d = self.fig_d.add_subplot(111)
        self.can_d = self._lienzo(v, self.fig_d)

    def _vista_espectro(self, v):
        self.fig_e = Figure(facecolor=PAPEL, layout="constrained")
        self.ax_e = self.fig_e.add_subplot(111)
        self.can_e = self._lienzo(v, self.fig_e)

    def _vista_fuerzas(self, v):
        barra = ctk.CTkFrame(v, fg_color="transparent")
        barra.pack(fill="x", pady=(0, 8))
        self.caso_f = tk.StringVar(self, value="Sismo")
        ctk.CTkSegmentedButton(barra, values=["Sismo", "Gravedad"], variable=self.caso_f, command=lambda _: self._mostrar_fuerzas(), font=self.f["peq"], fg_color=LINEA,
                               unselected_color=LINEA, unselected_hover_color="#D2CDC3", selected_color=PAPEL, selected_hover_color=PAPEL, text_color=TINTA).pack(side="left")
        self.txt_fuerzas = ctk.CTkLabel(barra, text="", font=self.f["peq"], text_color=GRIS)
        self.txt_fuerzas.pack(side="left", padx=14)
        ctk.CTkLabel(v, text="Fuerzas en los extremos de cada elemento, ejes locales", font=self.f["h2"], text_color=TINTA, anchor="w").pack(fill="x", pady=(0, 4))
        m1 = tk.Frame(v, bg=PAPEL); m1.pack(fill="both", expand=True)
        self.tabla_el = self._tabla(m1, (("e", "Elem.", 50), ("t", "Tipo", 70), ("n", "Nudos", 70), ("Ni", "Ni [kN]", 85), ("Vi", "Vi [kN]", 85), ("Mi", "Mi [kN·m]", 85),
                                         ("Nj", "Nj [kN]", 85), ("Vj", "Vj [kN]", 85), ("Mj", "Mj [kN·m]", 85)), 12)
        ctk.CTkLabel(v, text="Reacciones", font=self.f["h2"], text_color=TINTA, anchor="w").pack(fill="x", pady=(10, 4))
        m2 = tk.Frame(v, bg=PAPEL); m2.pack(fill="x")
        self.tabla_rx = self._tabla(m2, (("n", "Nudo", 60), ("x", "Rx [kN]", 110), ("y", "Ry [kN]", 110), ("m", "M [kN·m]", 110)), 5)

    # ---------- Lectura y validación ----------
    def _falla(self, clave, msg):
        self.fallas.setdefault(clave, msg)

    def _numero(self, clave, positivo=True, opcional=False):
        t = self.v[clave].get().strip().replace(",", ".")
        if not t:
            if not opcional:
                self._falla(clave, "Dato requerido")
            return None
        try:
            x = float(t)
        except ValueError:
            self._falla(clave, "Número inválido")
            return None
        if positivo and x <= 0:
            self._falla(clave, "Debe ser mayor que 0")
            return None
        return x

    def _entero(self, clave):
        x = self._numero(clave)
        if x is None:
            return None
        if x != int(x):
            self._falla(clave, "Debe ser entero")
            return None
        return int(x)

    def _lista(self, clave, n, positivo=True, opcional=False):
        partes = [t for t in re.split(r"[,;\s]+", self.v[clave].get().strip()) if t]
        if not partes:
            if not opcional:
                self._falla(clave, "Dato requerido")
            return None
        try:
            vals = [float(t) for t in partes]
        except ValueError:
            self._falla(clave, "Usa números separados por coma; decimales con punto")
            return None
        if positivo and any(x <= 0 for x in vals):
            self._falla(clave, "Todos deben ser mayores que 0")
            return None
        if n is None:
            return vals
        if len(vals) == 1:
            return vals * n
        if len(vals) != n:
            self._falla(clave, f"Se esperaban {n} valores y hay {len(vals)}")
            return None
        return vals

    def _apoyos(self, M):
        base = self.v["base"].get()
        if base == BASES[0]:
            return "fixed_bases"
        if base == BASES[1]:
            return {1 + i: ("FX", "FY") for i in range(M + 1)}
        try:
            out = {}
            for trozo in filter(str.strip, self.v["apoyos"].get().split(";")):
                nodo, comps = trozo.split(":")
                tags = tuple(c.strip().upper() for c in comps.split(",") if c.strip())
                if not tags or not set(tags) <= {"FX", "FY", "M"}:
                    raise ValueError
                out[int(nodo)] = tags
            if not out:
                raise ValueError
            return out
        except ValueError:
            self._falla("apoyos", "Formato: 1:FX,FY,M; 2:FX,FY")
            return "fixed_bases"

    def leer(self):
        """Devuelve los datos del modelo, o None si hay campos inválidos."""
        self.fallas = {}
        M = self._entero("M"); N = self._entero("N")
        Ls = self._lista("L", M) if M else None
        Hs = self._lista("H", N) if N else None
        secciones = [self._numero(k) for k in ("bc", "hc", "bv", "hv")]
        fv = self._numero("fv"); fcol = self._numero("fcol")
        for clave, f in (("fv", fv), ("fcol", fcol)):
            if f is not None and f > 2:
                self._falla(clave, "Debe estar entre 0 y 2")
        fc = self._numero("fc"); gamma = self._numero("gamma")
        E_MPa = self._numero("E", opcional=True)
        w = self._lista("w", N, positivo=False) if N else None
        if w and any(x < 0 for x in w):
            self._falla("w", "Usa valores positivos: w actúa hacia abajo")
        apoyos = self._apoyos(M) if M else "fixed_bases"
        esp = {k: self._numero(k) for k in ("Aa", "Av", "Fa", "Fv", "I")}
        max_iter = self._entero("iter"); tol = self._numero("tol")
        viva = self._lista("viva", N, positivo=False, opcional=True) if N else None
        h_manual = bool(self.v["h_manual"].get())
        h = self._numero("h") if h_manual else (sum(Hs) if Hs else None)
        self._marcar_fallas()
        if self.fallas:
            return None
        bc, hc, bv, hv = secciones
        inputs = {
            "n_bays": M, "n_stories": N, "bay_widths": Ls, "bay_width": Ls[0], "story_heights": Hs,
            "columns_sections": [(bc, hc)] * N, "beams_sections": [(bv, hv)] * N, "w_level_kNpm": w,
            "nodal_loads": dict(self.nodales), "supports": apoyos,
        }
        return dict(inputs=inputs, fc=fc, E=(E_MPa * 1e6 if E_MPa else None), gamma=gamma, fv=fv, fcol=fcol, h=h, viva=viva,
                    esp=esp, max_iter=max_iter, tol=tol)

    def _marcar_fallas(self):
        for clave, (ent, msg, ayuda) in self.campos.items():
            texto = self.fallas.get(clave)
            ent.configure(border_color=ROJO if texto else LINEA)
            msg.configure(text=texto or ayuda, text_color=ROJO if texto else GRIS)
            if texto and not msg.winfo_ismapped():
                msg.pack(fill="x")
            elif not texto and not ayuda:
                msg.pack_forget()

    # ---------- Cambios en los datos ----------
    def _al_cambiar(self):
        if self.cargando:
            return
        if self.res is not None:
            self.res = None
            self._limpiar_resultados()
            self.estado.configure(text="El modelo cambió: vuelve a calcular", text_color=TERRACOTA)
        if self._espera:
            self.after_cancel(self._espera)
        self._espera = self.after(180, self._redibujar)

    def _limpiar_resultados(self):
        self.btn_excel.configure(state="disabled")
        self.caso.set("Modelo")
        for valor, nota in (self.k_T, self.k_V, self.k_D, self.k_Q):
            valor.configure(text="—", text_color=TINTA)
            nota.configure(text="")
        self.txt_avisos.configure(text="")
        for t in (self.tabla_pisos, self.tabla_iter, self.tabla_el, self.tabla_rx):
            t.delete(*t.get_children())
        self.txt_fuerzas.configure(text="")
        self.ax_d.clear(); self.ax_d.set_axis_off(); self.can_d.draw_idle()

    def _mensaje(self, texto=None):
        if texto:
            self.aviso.configure(text=texto)
            self.aviso.pack(fill="x", pady=(0, 10), before=self.hoja)
        else:
            self.aviso.pack_forget()

    def _redibujar(self):
        self._espera = None
        d = self.leer()
        self._mensaje()
        if d is None:
            return
        Cu = compute_Cu(d["esp"]["Av"], d["esp"]["Fv"])
        Ta = CT * d["h"] ** ALFA
        self.txt_periodo.configure(text=f"Ta = {Ta:.3f} s · Cu = {Cu:.3f} · Cu·Ta = {Cu * Ta:.3f} s")
        self._dibujar_modelo(d)
        self._dibujar_espectro(d)

    # ---------- Dibujos ----------
    def _dibujar_modelo(self, d):
        nodes, elements, _, supports, _ = build_case_gen(d["inputs"], d["fc"], d["E"])
        self._nodos_dibujo = nodes
        ax = self.ax_m
        ax.clear()
        ax.set_aspect("equal")
        ax.set_axis_off()
        xs = [n.x for n in nodes.values()]; ys = [n.y for n in nodes.values()]
        ancho, alto = max(xs), max(ys)
        r = 0.018 * max(ancho, alto)
        caso = self.caso.get()
        U = None
        if self.res and caso != "Modelo":
            U = self.res["estatico"]["U"] if caso == "Deformada gravedad" else self.res["sismico"]["U"]
        color = "#A9B0B3" if U is not None else TINTA
        for e in elements.values():
            a, b = nodes[e.i], nodes[e.j]
            ax.plot([a.x, b.x], [a.y, b.y], color=color, lw=2.6, solid_capstyle="round", zorder=2)
        if U is None:
            self.txt_escala.configure(text="")
            niveles = sorted({n.y for n in nodes.values() if n.y > 0})
            for y, w in zip(niveles, d["inputs"]["w_level_kNpm"]):
                if w:
                    ax.plot([0, ancho], [y + 3 * r, y + 3 * r], color=TERRACOTA, lw=1.2, zorder=1)
                    for xk in np.linspace(0, ancho, max(5, int(ancho / (6 * r)))):
                        ax.annotate("", xy=(xk, y + 0.3 * r), xytext=(xk, y + 3 * r), arrowprops=dict(arrowstyle="-|>", color=TERRACOTA, lw=0.9, shrinkA=0, shrinkB=0), zorder=1)
                    ax.text(ancho + 3 * r, y + 1.6 * r, f"{w:g} kN/m", fontsize=9.5, color=TERRACOTA, va="center")
            for nid, (Px, Py, Mz) in d["inputs"]["nodal_loads"].items():
                n = nodes.get(nid)
                if n and (Px or Py or Mz):
                    ax.plot(n.x, n.y, "o", ms=11, mfc="none", mec=ACERO, mew=2, zorder=5)
                    ax.text(n.x + 2 * r, n.y + 2 * r, f"P{nid}", fontsize=9, color=ACERO)
        else:
            dof = self.res["estatico"]["dof"]
            maximo = max(abs(float(U[i])) for u in dof.node_dofs.values() for i in u[:2])
            esc = 0.09 * max(ancho, alto) / maximo if maximo > 0 else 1.0
            self.txt_escala.configure(text=f"Desplazamientos × {esc:.0f}   ·   máximo {maximo * 1000:.2f} mm")
            pos = {nid: (n.x + esc * U[dof.node_dofs[nid][0]], n.y + esc * U[dof.node_dofs[nid][1]]) for nid, n in nodes.items()}
            for e in elements.values():
                ax.plot([pos[e.i][0], pos[e.j][0]], [pos[e.i][1], pos[e.j][1]], color=TERRACOTA, lw=2.2, zorder=3)
        for nid, n in nodes.items():
            ax.plot(n.x, n.y, "o", ms=4.5, color=color, zorder=4)
            if self.ver_nudos.get():
                ax.text(n.x + 0.7 * r, n.y + 0.7 * r, str(nid), fontsize=8.5, color=GRIS, zorder=6)
        for nid, comps in supports.items():
            n = nodes.get(nid)
            if n is None:
                continue
            if "M" in comps:
                ax.plot([n.x - 1.8 * r, n.x + 1.8 * r], [n.y, n.y], color=TINTA, lw=3, zorder=5)
                for k in range(5):
                    x0 = n.x - 1.8 * r + k * 0.9 * r
                    ax.plot([x0, x0 - 0.7 * r], [n.y, n.y - 0.9 * r], color=TINTA, lw=1)
            else:
                ax.add_patch(Polygon([(n.x, n.y), (n.x - 1.2 * r, n.y - 1.8 * r), (n.x + 1.2 * r, n.y - 1.8 * r)], closed=True, fc=PAPEL, ec=TINTA, lw=1.4, zorder=5))
        # Cotas
        base_x = sorted({n.x for n in nodes.values()})
        for a, b in zip(base_x, base_x[1:]):
            ax.annotate("", xy=(a, -6 * r), xytext=(b, -6 * r), arrowprops=dict(arrowstyle="<->", color=GRIS, lw=0.8, shrinkA=0, shrinkB=0))
            ax.text((a + b) / 2, -7.6 * r, f"{b - a:g} m", fontsize=9, color=GRIS, ha="center", va="top")
        cotas = [0.0] + sorted({n.y for n in nodes.values() if n.y > 0})
        for a, b in zip(cotas, cotas[1:]):
            ax.annotate("", xy=(-5 * r, a), xytext=(-5 * r, b), arrowprops=dict(arrowstyle="<->", color=GRIS, lw=0.8, shrinkA=0, shrinkB=0))
            ax.text(-6 * r, (a + b) / 2, f"{b - a:g} m", fontsize=9, color=GRIS, ha="right", va="center")
        ax.set_xlim(-11 * r, ancho + 11 * r)
        ax.set_ylim(-10 * r, alto + 7 * r)
        self.can_m.draw_idle()

    def _dibujar_espectro(self, d):
        e = d["esp"]
        esp = compute_design_spectrum("", "", "", e["Aa"], e["Av"], None, None, e["Fa"], e["Fv"], e["I"], d["h"])
        ax = self.ax_e
        ax.clear()
        s = self.res["sismico"] if self.res else None
        Tfin = max(4.0, esp["TL"] * 1.15, (s["T_detallado"] * 1.15 if s else 0))
        T = np.unique(np.r_[np.linspace(0.0, Tfin, 700), esp["Tc"], esp["TL"]])
        Sa = [spectral_acceleration(t, e["Aa"], e["Av"], e["Fa"], e["Fv"], e["I"]) for t in T]
        ax.plot(T, Sa, color=TINTA, lw=2.2)
        tope = esp["Sa_max"] * 1.2
        ax.axvline(esp["Tc"], color=GRIS, lw=0.9, ls=":", label=f"Tc = {esp['Tc']:.3f} s")
        ax.axvline(esp["TL"], color=GRIS, lw=0.9, ls="-.", label=f"TL = {esp['TL']:.3f} s")
        if s:
            ax.axvline(s["T_aprox_inicial"], color=ACERO, lw=1.1, ls=":", label=f"Ta = {s['T_aprox_inicial']:.3f} s")
            ax.axvline(s["T_detallado"], color=ACERO, lw=1.1, ls="--", label=f"T Rayleigh = {s['T_detallado']:.3f} s")
            ax.plot([s["T_diseno"]], [s["Sa"]], "o", ms=10, color=TERRACOTA, zorder=5, ls="none",
                    label=f"T diseño = {s['T_diseno']:.3f} s · Sa = {s['Sa']:.4f} g")
        ax.legend(loc="upper right", frameon=True, facecolor=PAPEL, edgecolor="none", framealpha=1, fontsize=10, labelcolor=TINTA)
        ax.set_xlim(0, Tfin); ax.set_ylim(0, tope)
        self._ejes(ax, "Período T [s]", "Sa [g]")
        self.can_e.draw_idle()

    def _ejes(self, ax, xl, yl):
        ax.set_facecolor(PAPEL)
        ax.set_xlabel(xl, color=GRIS, fontsize=10); ax.set_ylabel(yl, color=GRIS, fontsize=10)
        ax.grid(True, color=LINEA, lw=0.7); ax.set_axisbelow(True)
        for lado in ("top", "right"):
            ax.spines[lado].set_visible(False)
        for lado in ("left", "bottom"):
            ax.spines[lado].set_color(LINEA)
        ax.tick_params(colors=GRIS, labelsize=9, length=0)

    def _dibujar_derivas(self):
        s = self.res["sismico"]
        ax = self.ax_d
        ax.clear(); ax.set_axis_on()
        lim = s["limite_deriva_pct"]
        pisos = np.arange(1, s["N_pisos"] + 1)
        vals = np.array(s["drift_evaluacion_pct"])
        barras = ax.barh(pisos, vals, height=0.6, color=[ROJO if x > lim else VERDE for x in vals])
        ax.axvline(lim, color=TINTA, lw=1.6, ls="--")
        ax.text(lim, s["N_pisos"] + 0.62, f"  Límite {lim:.2f} %", color=TINTA, fontsize=10, fontweight="bold", va="center")
        for b, x in zip(barras, vals):
            ax.text(x, b.get_y() + b.get_height() / 2, f" {x:.3f} % ", va="center", fontsize=10, color=TINTA, zorder=6, bbox=dict(fc=PAPEL, ec="none", pad=1.5))
        ax.set_yticks(pisos, [f"Piso {p}" for p in pisos])
        ax.set_xlim(0, max(lim, vals.max()) * 1.2); ax.set_ylim(0.4, s["N_pisos"] + 0.9)
        self._ejes(ax, "Deriva evaluada [% de la altura de piso]", "")
        ax.grid(True, axis="x", color=LINEA, lw=0.7); ax.grid(False, axis="y")
        self.can_d.draw_idle()

    def _clic_nudo(self, ev):
        if ev.xdata is None or not self._nodos_dibujo:
            return
        nid, n = min(self._nodos_dibujo.items(), key=lambda p: (p[1].x - ev.xdata) ** 2 + (p[1].y - ev.ydata) ** 2)
        self.cargando = True
        self.v["nodo"].set(str(nid))
        self.cargando = False
        self.tabs.set("Cargas")

    # ---------- Cargas nodales ----------
    def agregar_nodal(self):
        self.fallas = {}
        nid = self._entero("nodo")
        vals = [self._numero(k, positivo=False) for k in ("Px", "Py", "Mz")]
        self._marcar_fallas()
        if self.fallas:
            return
        if nid not in self._nodos_dibujo:
            self.fallas = {"nodo": "Ese nudo no existe"}
            self._marcar_fallas()
            return
        self.nodales[nid] = tuple(vals)
        self._refrescar_nodales()
        self._al_cambiar()

    def quitar_nodal(self):
        for item in self.tabla_nodal.selection():
            self.nodales.pop(int(self.tabla_nodal.item(item, "values")[0]), None)
        self._refrescar_nodales()
        self._al_cambiar()

    def _refrescar_nodales(self):
        self._llenar(self.tabla_nodal, [((n, *v), False) for n, v in sorted(self.nodales.items())])

    # ---------- Cálculo ----------
    def calcular(self):
        d = self.leer()
        if d is None:
            primero = next(iter(self.fallas))
            pagina = "Sismo" if primero in ("Aa", "Av", "Fa", "Fv", "I", "h", "iter", "tol", "viva") else ("Cargas" if primero == "w" else "Pórtico")
            self.tabs.set(pagina)
            self._mensaje(f"Revisa los {len(self.fallas)} campos marcados en rojo." if len(self.fallas) > 1 else "Revisa el campo marcado en rojo.")
            return
        e = d["esp"]
        params = dict(ciudad=self.v["ciudad"].get(), amenaza=self.v["amenaza"].get(), suelo=self.v["suelo"].get(), Aa=e["Aa"], Av=e["Av"],
                      Ae=None, Ad=None, Fa=e["Fa"], Fv=e["Fv"], I=e["I"], h_m=d["h"], grupo_label=self.v["grupo"].get())
        try:
            est = run_static_analysis(d["inputs"], d["fc"], d["E"], d["fv"], d["fcol"], d["gamma"] if self.v["pp"].get() else 0.0)
            sis = run_seismic_iterative(
                d["inputs"], d["fc"], d["E"], d["gamma"], d["fv"], d["fcol"], params, d["h"], CT, ALFA, d["max_iter"], d["tol"],
                periodo_diseno=PERIODOS[self.v["periodo"].get()], usar_I_unitario_derivas=bool(self.v["I1"].get()),
                reducir_derivas_fisuradas=bool(self.v["red07"].get()) and min(d["fv"], d["fcol"]) < 1.0, carga_viva_kN=d["viva"],
            )
        except np.linalg.LinAlgError:
            self._mensaje("La estructura es inestable: revisa los apoyos.")
            return
        except ValueError as ex:
            self._mensaje(str(ex))
            return
        self.res = {"estatico": est, "sismico": sis, "datos": d}
        self._mensaje()
        self.btn_excel.configure(state="normal")
        self.estado.configure(text=f"Resultados al día · {sis['iteration_count']} iteraciones", text_color=VERDE)
        self._mostrar_sismo()
        self._dibujar_derivas()
        self._dibujar_espectro(d)
        self._mostrar_fuerzas()
        self.caso.set("Deformada sismo")
        self._dibujar_modelo(d)
        self.ver("Sismo")

    def _mostrar_sismo(self):
        s = self.res["sismico"]
        self.k_T[0].configure(text=f"{s['T_diseno']:.4f} s")
        self.k_T[1].configure(text=f"Rayleigh {s['T_detallado']:.4f} s · Cu·Ta {s['T_limite']:.4f} s")
        self.k_V[0].configure(text=f"{s['V']:.2f} kN")
        self.k_V[1].configure(text=f"Sa {s['Sa']:.4f} g · W {s['W_total']:.1f} kN · k {s['k_exp']:.3f}")
        ok = s["cumple_deriva"]
        self.k_D[0].configure(text=f"{s['drift_max_evaluacion_pct']:.3f} %", text_color=VERDE if ok else ROJO)
        self.k_D[1].configure(text=("Cumple" if ok else "No cumple") + f" el límite de {s['limite_deriva_pct']:.2f} %", text_color=VERDE if ok else ROJO)
        self.k_Q[0].configure(text=f"{s['Q_max']:.4f}", text_color=ROJO if s["requiere_pdelta"] else TINTA)
        self.k_Q[1].configure(text="Con carga viva" if s["carga_viva_incluida"] else "Sin carga viva: cota inferior")

        avisos = []
        if s["limite_activo"]:
            avisos.append(f"T Rayleigh excede Cu·Ta: el diseño usa T = {s['T_limite']:.4f} s (A.4.2.1 y A.6.2.1.1).")
        if s["periodo_diseno"] == "sin_limite" and s["T_detallado"] > s["T_limite"]:
            avisos.append("Este criterio no cumple A.4.2.1 porque T excede Cu·Ta: úsalo solo para comparar.")
        if not s["converged"]:
            avisos.append("La iteración no convergió: aumenta las iteraciones máximas.")
        if s["Q_excede_limite"]:
            avisos.append("Qi > 0.30: estructura potencialmente inestable, debe rigidizarse (A.6.2.3).")
        elif s["requiere_pdelta"]:
            avisos.append("Qi > 0.10: la deriva mostrada no incluye P-Delta (A.6.2.3).")
        self.txt_avisos.configure(text="\n".join(avisos), text_color=TERRACOTA)

        Vi = np.cumsum(np.array(s["Fi"])[::-1])[::-1]
        filas = []
        for k in range(s["N_pisos"]):
            filas.append(((k + 1, f"{s['hi'][k]:.2f}", f"{s['Wi'][k]:.2f}", f"{s['Fi'][k] / s['V']:.4f}", f"{s['Fi'][k]:.2f}", f"{Vi[k]:.2f}",
                           f"{s['disp_piso'][k] * 1000:.3f}", f"{s['drift_pct'][k]:.4f}", f"{s['drift_evaluacion_pct'][k]:.4f}", f"{s['Qi'][k]:.4f}"),
                          s["drift_evaluacion_pct"][k] > s["limite_deriva_pct"]))
        self._llenar(self.tabla_pisos, filas)
        self._llenar(self.tabla_iter, [((it["iter"], f"{it['T_in']:.4f}", f"{it['Sa']:.4f}", f"{it['k_exp']:.3f}", f"{it['V']:.2f}", f"{it['T_rayleigh']:.4f}",
                                         f"{it['error_pct']:.3f}", "Sí" if it["converged"] else "No"), False) for it in s["iterations"]])

    def _mostrar_fuerzas(self):
        if not self.res:
            return
        sismo = self.caso_f.get() == "Sismo"
        e = self.res["estatico"]
        fuerzas = self.res["sismico"]["elem_forces_local"] if sismo else e["elem_forces_local"]
        reacciones = self.res["sismico"]["reactions"] if sismo else e["reactions_by_node"]
        self.txt_fuerzas.configure(text="Fuerzas Fs sin dividir por R" if sismo else "Cargas w, peso propio y cargas en nudos")
        filas = []
        for (eid, *f) in fuerzas:
            el = e["elements"][eid]
            _, _, s = el.length_and_cs(e["nodes"])
            filas.append(((eid, "Viga" if abs(s) < 0.01 else "Columna", f"{el.i}–{el.j}", *(kN(x) for x in f)), False))
        self._llenar(self.tabla_el, filas)
        self._llenar(self.tabla_rx, [((n, *(kN(x) for x in r)), False) for n, r in sorted(reacciones.items())])

    # ---------- Archivos ----------
    def _resumen(self):
        d = self.res["datos"]; i = d["inputs"]
        modelo = {
            "Número de luces": i["n_bays"], "Número de pisos": i["n_stories"], "Luces [m]": ", ".join(map(str, i["bay_widths"])),
            "Alturas [m]": ", ".join(map(str, i["story_heights"])), "Columna b×h [m]": f"{i['columns_sections'][0][0]}×{i['columns_sections'][0][1]}",
            "Viga b×h [m]": f"{i['beams_sections'][0][0]}×{i['beams_sections'][0][1]}", "f'c [MPa]": d["fc"], "E [MPa]": compute_E(d["fc"], d["E"]) / 1e6,
            "γ [kN/m³]": d["gamma"], "Factor I vigas": d["fv"], "Factor I columnas": d["fcol"], "w por piso [kN/m]": ", ".join(map(str, i["w_level_kNpm"])),
            "Peso propio en estático": "Sí" if self.v["pp"].get() else "No", "Apoyos": "Empotrados" if i["supports"] == "fixed_bases" else str(i["supports"]),
            "Cargas en nudos": str(i["nodal_loads"]),
        }
        e = d["esp"]
        espectro = {"Ciudad": self.v["ciudad"].get(), "Amenaza": self.v["amenaza"].get(), "Suelo": self.v["suelo"].get(), "Grupo de uso": self.v["grupo"].get(),
                    "Aa": e["Aa"], "Av": e["Av"], "Fa": e["Fa"], "Fv": e["Fv"], "I": e["I"], "Altura h [m]": d["h"], "Ct": CT, "α": ALFA,
                    "Tc [s]": 0.48 * e["Av"] * e["Fv"] / (e["Aa"] * e["Fa"]), "TL [s]": 2.4 * e["Fv"]}
        return modelo, espectro

    def exportar(self):
        if not self.res:
            return
        ruta = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")], initialfile="RockFrame_resultados.xlsx", title="Exportar resultados")
        if not ruta:
            return
        try:
            exportar_excel(ruta, *self._resumen(), self.res["estatico"], self.res["sismico"])
            self.estado.configure(text="Excel exportado", text_color=VERDE)
        except Exception as ex:
            self._mensaje(f"No se pudo exportar: {ex}")

    def _proyecto(self):
        g = lambda k: self.v[k].get()
        d = self.leer()
        if d is None:
            return None
        i = dict(d["inputs"])
        i["spectrum"] = {
            "ciudad": g("ciudad"), "amenaza": g("amenaza"), "suelo": g("suelo"), "Aa": d["esp"]["Aa"], "Av": d["esp"]["Av"], "Fa": d["esp"]["Fa"], "Fv": d["esp"]["Fv"],
            "grupo_label": g("grupo"), "grupo_uso": d["esp"]["I"], "altura_m": d["h"], "altura_manual": bool(g("h_manual")), "iter_max": d["max_iter"], "tol_pct": d["tol"],
            "Ct": CT, "alpha": ALFA, "periodo_label": g("periodo"), "I_unitario_derivas": bool(g("I1")), "reducir_derivas_fisuradas": bool(g("red07")), "carga_viva": g("viva"),
        }
        return {"inputs": i, "fc_MPa": d["fc"], "E_override_Pa": d["E"],
                "seismic_params": {"gamma": g("gamma"), "factor_vigas": g("fv"), "factor_columnas": g("fcol"), "peso_propio_estatico": bool(g("pp"))}}

    def guardar(self):
        datos = self._proyecto()
        if datos is None:
            self._mensaje("Corrige los campos en rojo antes de guardar.")
            return
        ruta = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("Proyecto ROCKFRAME", "*.json")], initialfile="RockFrame_proyecto.json", title="Guardar proyecto")
        if ruta:
            with open(ruta, "w", encoding="utf-8") as f:
                json.dump(datos, f, ensure_ascii=False, indent=2)
            self.estado.configure(text="Proyecto guardado", text_color=VERDE)

    def abrir(self):
        ruta = filedialog.askopenfilename(filetypes=[("Proyecto ROCKFRAME", "*.json")], title="Abrir proyecto")
        if not ruta:
            return
        try:
            with open(ruta, encoding="utf-8") as f:
                self.aplicar_proyecto(json.load(f))
        except (OSError, ValueError, KeyError, IndexError, TypeError) as ex:
            self._mensaje(f"No se pudo abrir el proyecto: {ex}")

    def aplicar_proyecto(self, datos):
        i = datos["inputs"]; s = i.get("spectrum", {}); p = datos.get("seismic_params", {})
        E = datos.get("E_override_Pa")
        lista = lambda x: ", ".join(f"{v:g}" for v in x)
        col = i["columns_sections"][0]; vig = i["beams_sections"][0]
        apoyos = i.get("supports", "fixed_bases")
        valores = {
            "M": i["n_bays"], "N": i["n_stories"], "L": lista(i["bay_widths"]), "H": lista(i["story_heights"]), "bc": col[0], "hc": col[1], "bv": vig[0], "hv": vig[1],
            "fv": p.get("factor_vigas", 1.0), "fcol": p.get("factor_columnas", 1.0), "fc": datos.get("fc_MPa", 21.0), "E": "" if E is None else f"{E / 1e6:g}",
            "gamma": p.get("gamma", 24.0), "w": lista(i["w_level_kNpm"]), "ciudad": s.get("ciudad", ""), "amenaza": s.get("amenaza", "Alta"), "suelo": s.get("suelo", "D"),
            "Aa": s.get("Aa", 0.25), "Av": s.get("Av", 0.25), "Fa": s.get("Fa", 1.0), "Fv": s.get("Fv", 1.0), "I": s.get("grupo_uso", 1.0), "grupo": s.get("grupo_label", "I") if s.get("grupo_label") in GRUPOS else "I",
            "h": s.get("altura_m", "") if s.get("altura_manual") else "", "iter": s.get("iter_max", 10), "tol": s.get("tol_pct", 1.0),
            "periodo": s.get("periodo_label", "Rayleigh ≤ Cu·Ta") if s.get("periodo_label") in PERIODOS else "Rayleigh ≤ Cu·Ta", "viva": s.get("carga_viva", ""),
            "base": BASES[0] if not isinstance(apoyos, dict) else BASES[2],
            "apoyos": "; ".join(f"{k}:{','.join(v)}" for k, v in apoyos.items()) if isinstance(apoyos, dict) else "",
        }
        self.cargando = True
        for k, x in valores.items():
            self.v[k].set(str(x))
        self.v["pp"].set(bool(p.get("peso_propio_estatico", True)))
        self.v["h_manual"].set(bool(s.get("altura_manual", False)))
        self.v["I1"].set(bool(s.get("I_unitario_derivas", False)))
        self.v["red07"].set(bool(s.get("reducir_derivas_fisuradas", True)))
        self.nodales = {int(k): tuple(v) for k, v in i.get("nodal_loads", {}).items()}
        self._refrescar_nodales()
        self._reiniciar()

    def _reiniciar(self):
        self.res = None
        self._limpiar_resultados()
        self.cargando = False
        self.estado.configure(text="Sin calcular", text_color=GRIS)
        self.ver("Pórtico")
        self._redibujar()

    def cargar_ejemplo(self):
        self.cargando = True
        for k, x in EJEMPLO.items():
            self.v[k].set(x)
        for k, x in (("pp", True), ("h_manual", False), ("I1", False), ("red07", True)):
            self.v[k].set(x)
        self.v["base"].set(BASES[0]); self.v["amenaza"].set("Alta"); self.v["suelo"].set("D"); self.v["grupo"].set("I"); self.v["periodo"].set("Rayleigh ≤ Cu·Ta")
        self.nodales = {}
        self._refrescar_nodales()
        self._reiniciar()


if __name__ == "__main__":
    RockFrameUI().mainloop()
