# ROCKFRAME – Motor de cálculo (sin interfaz gráfica)
# Análisis matricial de pórticos planos 2D y análisis sísmico iterativo NSR-10.
# Unidades internas de la solución: N, m. Cargas y pesos de entrada: kN, kN/m.

from __future__ import annotations
from dataclasses import dataclass
from functools import lru_cache
from typing import Dict, Optional
import numpy as np

# ===== Utilidades de unidades =====
def kN_to_N(x_kN: float) -> float: return x_kN * 1_000.0
def kNpm_to_Npm(x_kNpm: float) -> float: return x_kNpm * 1_000.0
def N_to_kN(x_N: float) -> float: return x_N / 1_000.0

# ===== Datos base =====
@dataclass
class Node:
    id: int; x: float; y: float

@dataclass
class Element:
    id: int; i: int; j: int; A: float; E: float; I: float
    w_kNpm: float = 0.0
    Pmid_kN: float = 0.0
    def length_and_cs(self, nodes: Dict[int, "Node"]):
        xi, yi = nodes[self.i].x, nodes[self.i].y
        xj, yj = nodes[self.j].x, nodes[self.j].y
        L = float(np.hypot(xj - xi, yj - yi))
        if L < 1e-9: raise ValueError(f"Elemento {self.id} con longitud nula o muy pequeña: L={L}")
        c = (xj - xi)/L;  s = (yj - yi)/L
        return L, c, s

class DOFMap:
    def __init__(self, nodes: Dict[int, Node]):
        self.nodes = nodes; self.ndof = 3*len(nodes); self.node_dofs={}
        self._rev=[]  # (nid, comp) por índice 0..ndof-1
        for k, nid in enumerate(sorted(nodes.keys())):
            base = 3*k; self.node_dofs[nid]=(base, base+1, base+2)
            self._rev.extend([(nid,0),(nid,1),(nid,2)])
    def elem_dofs(self, e: Element):
        di=self.node_dofs[e.i]; dj=self.node_dofs[e.j]
        return [di[0],di[1],di[2],dj[0],dj[1],dj[2]]
    def idx_to_node_comp(self, idx0: int):
        return self._rev[idx0]

# ===== Matrices y transformaciones =====
@lru_cache(maxsize=512)
def k_local_frame(E,A,I,L):
    EA_L=E*A/L; EI=E*I; L2=L*L; L3=L2*L
    k=np.array([
        [ EA_L, 0, 0, -EA_L, 0, 0],
        [ 0, 12*EI/L3, 6*EI/L2, 0, -12*EI/L3, 6*EI/L2],
        [ 0, 6*EI/L2, 4*EI/L, 0, -6*EI/L2, 2*EI/L],
        [-EA_L, 0, 0, EA_L, 0, 0],
        [ 0, -12*EI/L3, -6*EI/L2, 0, 12*EI/L3, -6*EI/L2],
        [ 0, 6*EI/L2, 2*EI/L, 0, -6*EI/L2, 4*EI/L]
    ], dtype=float); return k

@lru_cache(maxsize=512)
def T_matrix(c,s):
    return np.array([[c,s,0,0,0,0],[-s,c,0,0,0,0],[0,0,1,0,0,0],[0,0,0,c,s,0],[0,0,0,-s,c,0],[0,0,0,0,0,1]],dtype=float)

# ===== FEQ (cargas a extremos locales) =====
def feql_uniform_w_local(w_Npm,L):
    wL=w_Npm*L
    return np.array([0, wL/2, wL*L/12, 0, wL/2, -wL*L/12], dtype=float)

def feql_point_midspan_local(P_N, L):
    return np.array([0.0, P_N/2.0,  P_N*L/8.0,  0.0, P_N/2.0, -P_N*L/8.0], dtype=float)

def element_fixed_end_local(e,L,c,s,gamma=0.0):
    fe=np.zeros(6)
    if abs(e.w_kNpm)>0: fe+=feql_uniform_w_local(kNpm_to_Npm(e.w_kNpm),L)
    if abs(e.Pmid_kN)>0: fe+=feql_point_midspan_local(kN_to_N(e.Pmid_kN), L)
    if gamma>0:
        # Peso propio γ·A, vertical hacia abajo: componente transversal q·c y axial q·s
        q=kNpm_to_Npm(gamma*e.A)
        fe+=feql_uniform_w_local(q*c,L)
        fe[[0,3]]+=q*s*L/2
    return fe

# ===== Ensamble (con factores de fisuración) =====
def effective_I(e, s, factor_vigas=1.0, factor_columnas=1.0):
    # Determinar si es viga (horizontal) o columna (vertical)
    is_beam = abs(s) < 0.01  # s ≈ 0 → horizontal → viga
    return e.I * (factor_vigas if is_beam else factor_columnas)

def assemble_global_K(nodes, elements, dof, factor_vigas=1.0, factor_columnas=1.0):
    ndof=dof.ndof; K=np.zeros((ndof,ndof))
    for e in elements.values():
        L,c,s=e.length_and_cs(nodes)
        I_eff = effective_I(e, s, factor_vigas, factor_columnas)
        kl=k_local_frame(e.E, e.A, I_eff, L)
        T=T_matrix(c,s); kg=T.T@kl@T
        ed=dof.elem_dofs(e)
        for a in range(6):
            A_=ed[a]
            for b in range(6):
                B_=ed[b]; K[A_,B_]+=kg[a,b]
    return K

def assemble_PqG(nodes,elements,dof,gamma=0.0):
    P=np.zeros(dof.ndof)
    for e in elements.values():
        L,c,s=e.length_and_cs(nodes); T=T_matrix(c,s)
        fe_global=T.T@element_fixed_end_local(e,L,c,s,gamma); ed=dof.elem_dofs(e)
        for a in range(6): P[ed[a]]+=fe_global[a]
    return P

# ===== Propiedades y E =====
def section_props_rectangular(b,h): A=b*h; I=b*h**3/12.0; return A,I
def compute_E(fc_MPa, override=None):
    return float(override) if (override is not None) else 1e6*4700.0*np.sqrt(fc_MPa)

def _ensure_list_len(item,n):
    if isinstance(item,(int,float)): return [item]*n
    return list(item)

def build_case_gen(p:dict, fc_MPa:float=21.0, E_override:Optional[float]=None):
    M=int(p["n_bays"]); N=int(p["n_stories"])
    if "bay_widths" in p and p["bay_widths"] is not None:
        Ls=_ensure_list_len(p["bay_widths"], M)
        if len(Ls)!=M: Ls=Ls[:M] if len(Ls)>M else Ls+[Ls[-1]]*(M-len(Ls))
    else:
        Ls=[float(p["bay_width"])]*M
    Hs=_ensure_list_len(p["story_heights"],N); E=compute_E(fc_MPa,E_override)
    col=_ensure_list_len(p["columns_sections"],N); beam=_ensure_list_len(p["beams_sections"],N)
    y=[0.0]
    for j in range(N): y.append(y[-1]+Hs[j])
    x=[0.0]
    for i in range(M): x.append(x[-1]+float(Ls[i]))
    def nid(i,j): return 1+i+(M+1)*j
    nodes={}
    for j in range(N+1):
        for i in range(M+1): nodes[nid(i,j)]=Node(nid(i,j), x[i], y[j])
    elements={}; eid=1
    for j in range(1,N+1):
        bcol,hcol=col[j-1]; Acol,Icol=section_props_rectangular(bcol,hcol)
        for i in range(M+1): elements[eid]=Element(eid,nid(i,j-1),nid(i,j),Acol,E,Icol); eid+=1
        bbeam,hbeam=beam[j-1]; Abeam,Ibeam=section_props_rectangular(bbeam,hbeam)
        wlv=_ensure_list_len(p.get("w_level_kNpm",0.0),N)
        for i in range(M): elements[eid]=Element(eid,nid(i,j),nid(i+1,j),Abeam,E,Ibeam,w_kNpm=wlv[j-1]); eid+=1
    custom=p.get("supports")
    if isinstance(custom,dict):
        # Las claves pueden llegar como texto desde un proyecto JSON
        supports={int(k):tuple(v) for k,v in custom.items()}
    else:
        supports={nid(i,0):("FX","FY","M") for i in range(M+1)}
    return nodes, elements, p.get("nodal_loads",{}), supports, E

# ===== Cargas nodales y restricciones =====
def assemble_Pext_nodal(dof, nodal):
    P=np.zeros(dof.ndof)
    for nid,(Px,Py,Mz) in nodal.items():
        ux,uy,th=dof.node_dofs[nid]; P[ux]+=kN_to_N(Px); P[uy]+=kN_to_N(Py); P[th]+=kN_to_N(Mz)
    return P

def supports_to_restrained_gdls(dof,supports):
    out=[]
    for nid, comps in supports.items():
        if nid not in dof.node_dofs: raise ValueError(f"El apoyo refiere al nodo {nid}, que no existe.")
        ux,uy,th=dof.node_dofs[nid]; tags={c.upper() for c in comps}
        if ("FX" in tags) or ("UX" in tags) or ("X" in tags): out.append(ux+1)
        if ("FY" in tags) or ("UY" in tags) or ("Y" in tags): out.append(uy+1)
        if ("M" in tags) or ("THETA" in tags) or ("RZ" in tags): out.append(th+1)
    return sorted(out)

# ===== Solución =====
def solve_with_bc(K,P_ext,PqG,restr_1based, dof: DOFMap):
    ndof=K.shape[0]; Ptot=P_ext-PqG
    r0=sorted([g-1 for g in restr_1based]); f0=[i for i in range(ndof) if i not in r0]
    Kll=K[np.ix_(f0,f0)]; Pll=Ptot[f0]
    if f0 and np.linalg.cond(Kll)>1e14: raise np.linalg.LinAlgError("Kll singular: la estructura es un mecanismo.")
    Ull=np.linalg.solve(Kll,Pll)
    U=np.zeros(ndof); U[f0]=Ull; resid=K@U-Ptot; R=resid[r0]
    reactions_by_node={}
    for ridx0, rN in zip(r0, R):
        nid, comp = dof.idx_to_node_comp(ridx0)
        rx, ry, rm = reactions_by_node.get(nid, (0.0,0.0,0.0))
        if comp==0: rx += rN
        elif comp==1: ry += rN
        else: rm += rN
        reactions_by_node[nid]=(rx,ry,rm)
    return U,R,[i+1 for i in f0],[i+1 for i in r0], reactions_by_node, Kll, Ptot

def element_end_forces_local(e,nodes,dof,U,factor_vigas=1.0,factor_columnas=1.0,incluir_cargas=True,gamma=0.0):
    L,c,s=e.length_and_cs(nodes); T=T_matrix(c,s)
    kl=k_local_frame(e.E,e.A,effective_I(e,s,factor_vigas,factor_columnas),L)
    ed=dof.elem_dofs(e); u_l=T @ U[ed]; fe=np.zeros(6)
    if incluir_cargas: fe=element_fixed_end_local(e,L,c,s,gamma)
    return kl@u_l + fe

# ===== Análisis estático =====
def run_static_analysis(inputs, fc_MPa, E_override, factor_vigas=1.0, factor_columnas=1.0, gamma=0.0):
    # gamma > 0 agrega el peso propio γ·A de vigas y columnas [kN/m³]
    nodes,elements,_,supports,_E=build_case_gen(inputs, fc_MPa, E_override)
    dof=DOFMap(nodes)
    K=assemble_global_K(nodes,elements,dof, factor_vigas=factor_vigas, factor_columnas=factor_columnas)
    PqG=assemble_PqG(nodes,elements,dof,gamma)
    Pext=assemble_Pext_nodal(dof, inputs['nodal_loads'])
    restr=supports_to_restrained_gdls(dof, supports)
    U,R,free,rest,reac_by_node,Kll,Ptot=solve_with_bc(K,Pext,PqG,restr,dof)
    elem_forces=[]
    for e in elements.values():
        f_loc=element_end_forces_local(e, nodes, dof, U, factor_vigas, factor_columnas, gamma=gamma)
        elem_forces.append((e.id, *f_loc))
    return {
        "nodes": nodes, "elements": elements, "dof": dof, "K": K, "K_ll": Kll,
        "P_ext": Pext, "P_qG": PqG, "P_total": Ptot, "U": U, "R_restr": R,
        "free": free, "rest": rest, "reactions_by_node": reac_by_node,
        "elem_forces_local": elem_forces, "E_used_Pa": _E,
        "E_input_MPa": (E_override/1e6 if E_override is not None else None),
        "gamma_peso_propio": gamma,
        "fc_MPa": fc_MPa,
    }

# ===== Espectro de diseño =====
def spectral_acceleration(T, Aa, Av, Fa, Fv, I):
    # NSR-10 A.2.6.1: ec. A.2.6-3 (T ≤ Tc), A.2.6-1 (Tc < T ≤ TL) y A.2.6-5 (T > TL)
    Tc = 0.48 * (Av * Fv) / (Aa * Fa)
    TL = 2.40 * Fv
    if T <= Tc:
        return 2.5 * Aa * Fa * I
    if T <= TL:
        return 1.2 * Av * Fv * I / T
    return 1.2 * Av * Fv * TL * I / T ** 2

def compute_design_spectrum(ciudad, amenaza, suelo, Aa, Av, Ae, Ad, Fa, Fv, I, h_m, grupo_label="") -> dict:
    Sa_max = 2.5 * Aa * Fa * I
    denom = (Aa * Fa)
    if denom <= 0:
        raise ValueError("Aa·Fa debe ser > 0.")
    T0 = 0.10 * (Av * Fv) / denom
    Tc = 0.48 * (Av * Fv) / denom
    TL = 2.40 * Fv
    if T0 <= 0 or Tc <= 0 or TL <= 0:
        raise ValueError("T0, Tc y TL deben ser > 0.")
    if not (T0 <= Tc):
        raise ValueError("Debe cumplirse T0 ≤ Tc.")
    if h_m <= 0:
        raise ValueError("La altura h debe ser > 0.")

    Ta = 0.047 * (h_m ** 0.9)
    Tmax = max(4.0, TL * 1.8, Ta * 1.5, Tc * 1.5)
    T = np.linspace(0.0, Tmax, 1400)
    Sa = np.zeros_like(T)

    mask_plateau = (T <= Tc)
    Sa[mask_plateau] = Sa_max
    mask_decay_1 = (T > Tc) & (T <= TL)
    Sa[mask_decay_1] = (1.2 * Av * Fv * I) / np.maximum(T[mask_decay_1], 1e-9)
    mask_decay_2 = T > TL
    Sa[mask_decay_2] = (1.2 * Av * Fv * TL * I) / np.maximum(T[mask_decay_2] ** 2, 1e-12)

    Sa_Ta = spectral_acceleration(Ta, Aa, Av, Fa, Fv, I)
    return {
        "meta": {
            "ciudad": ciudad,
            "amenaza": amenaza,
            "suelo": suelo,
            "Aa": Aa,
            "Av": Av,
            "Fa": Fa,
            "Fv": Fv,
            "I": I,
            "grupo": grupo_label,
        },
        "T": T,
        "Sa": Sa,
        "Sa_max": float(Sa_max),
        "T0": float(T0),
        "Tc": float(Tc),
        "TL": float(TL),
        "Ta": float(Ta),
        "Sa_Ta": Sa_Ta,
    }

def get_k_exponent(T_value: float) -> float:
    if T_value <= 0.5:
        return 1.0
    if T_value >= 2.5:
        return 2.0
    return 1.0 + (T_value - 0.5) / 2.0

# ===== Análisis sísmico iterativo =====
def seismic_story_weights(nodes, elements, levels, gamma):
    Wi = np.zeros(len(levels), dtype=float)
    for e in elements.values():
        L, c, s = e.length_and_cs(nodes)
        yi = nodes[e.i].y
        yj = nodes[e.j].y
        y_mid = 0.5 * (yi + yj)
        peso_propio = gamma * e.A * L
        is_beam = abs(s) < 0.01
        if is_beam:
            w_load = abs(e.w_kNpm) * L
            total_beam_weight = w_load + peso_propio
            for k, lev in enumerate(levels):
                if abs(y_mid - lev) < 1e-6:
                    Wi[k] += total_beam_weight
                    break
        else:
            y_bot = min(yi, yj)
            y_top = max(yi, yj)
            half_w = peso_propio / 2.0
            for k, lev in enumerate(levels):
                if abs(lev - y_top) < 1e-6:
                    Wi[k] += half_w
                if abs(lev - y_bot) < 1e-6:
                    Wi[k] += half_w
    return Wi

LIMITE_DERIVA_PCT = 1.0  # NSR-10 tabla A.6.4-1, concreto reforzado

def evaluate_drifts(drift, I, usar_I_unitario=False, reducir_fisuradas=False):
    # A.6.2.1.2: permite I = 1.0 en grupos II a IV; la respuesta es lineal, así que basta escalar por 1/I.
    # A.6.4.1.1: con secciones fisuradas se multiplica por 0.7; es equivalente y más transparente
    # conservar la deriva calculada y comparar contra el límite dividido por 0.7.
    factor = 1.0 / I if usar_I_unitario else 1.0
    drift_eval_pct = 100.0 * factor * np.asarray(drift, dtype=float)
    drift_max = float(np.max(drift_eval_pct))
    limite = LIMITE_DERIVA_PCT / 0.7 if reducir_fisuradas else LIMITE_DERIVA_PCT
    return {
        "drift_evaluacion_pct": drift_eval_pct.tolist(),
        "drift_max_evaluacion_pct": drift_max,
        "limite_deriva_pct": limite,
        "cumple_deriva": bool(drift_max <= limite),
    }

def stability_index(Wi, Fi, disp_piso, hi, base_y, carga_viva_kN=None):
    # NSR-10 ec. A.6.2-2: Qi = Pi·Δcm / (Vi·hpi). Pi incluye carga muerta y viva del piso i y los superiores;
    # sin carga_viva_kN (por piso, en kN) Qi queda como cota inferior. Solo se reporta; no modifica las derivas.
    Wi = np.asarray(Wi, dtype=float); Fi = np.asarray(Fi, dtype=float); hi = np.asarray(hi, dtype=float)
    carga = Wi if carga_viva_kN is None else Wi + np.asarray(carga_viva_kN, dtype=float)
    Pi = np.cumsum(carga[::-1])[::-1]
    Vi = np.cumsum(Fi[::-1])[::-1]
    delta = np.diff(np.asarray(disp_piso, dtype=float), prepend=0.0)
    hp = np.diff(hi, prepend=base_y)
    Qi = Pi * np.abs(delta) / (Vi * hp)
    Q_max = float(np.max(Qi))
    return {
        "Qi": Qi.tolist(),
        "Q_max": Q_max,
        "carga_viva_incluida": carga_viva_kN is not None,
        "requiere_pdelta": bool(Q_max > 0.10),
        "Q_excede_limite": bool(Q_max > 0.30),
    }

PERIODOS_DISENO = ("limite_CuTa", "sin_limite", "Ta")

def compute_Cu(Av, Fv):
    # NSR-10 ec. A.4.2-2, con mínimo 1.2
    return max(1.75 - 1.2 * Av * Fv, 1.2)

def run_seismic_iterative(inputs, fc_MPa, E_override, gamma, factor_vigas, factor_columnas,
                          spectrum_params, h_total, Ct, alpha, max_iter, tol_pct,
                          periodo_diseno="limite_CuTa", usar_I_unitario_derivas=False,
                          reducir_derivas_fisuradas=False, carga_viva_kN=None):
    # periodo_diseno: "limite_CuTa" aplica T ≤ Cu·Ta (A.4.2.1, también para derivas según A.6.2.1.1);
    # "Ta" usa el período aproximado (A.4.2.2); "sin_limite" no cumple la norma y solo sirve para comparar.
    if periodo_diseno not in PERIODOS_DISENO:
        raise ValueError(f"periodo_diseno debe ser uno de {PERIODOS_DISENO}.")
    if reducir_derivas_fisuradas and min(factor_vigas, factor_columnas) >= 1.0:
        raise ValueError("El factor 0.7 de A.6.4.1.1 solo aplica con secciones fisuradas.")
    T_aprox_inicial = Ct * (h_total ** alpha)
    Cu = compute_Cu(spectrum_params["Av"], spectrum_params["Fv"])
    T_limite = Cu * T_aprox_inicial

    def siguiente_periodo(T_R):
        if periodo_diseno == "Ta":
            return float(T_aprox_inicial)
        if periodo_diseno == "limite_CuTa":
            return min(float(T_R), float(T_limite))
        return float(T_R)

    nodes, elements, _, supports, _E = build_case_gen(inputs, fc_MPa, E_override)
    dof = DOFMap(nodes)
    K = assemble_global_K(nodes, elements, dof, factor_vigas=factor_vigas, factor_columnas=factor_columnas)
    restr = supports_to_restrained_gdls(dof, supports)

    y_values = sorted(set(round(n.y, 6) for n in nodes.values()))
    base_y = y_values[0]
    levels = [y for y in y_values if y > base_y + 1e-6]
    nodes_by_level = {lev: [nid for nid, n in nodes.items() if abs(n.y - lev) < 1e-6] for lev in levels}
    N_pisos = len(levels)
    hi = np.array(levels, dtype=float)

    Wi = seismic_story_weights(nodes, elements, levels, gamma)

    W_total = float(np.sum(Wi))
    if W_total <= 0:
        raise ValueError("El peso sísmico total es cero. Revisa cargas distribuidas y densidad del concreto.")

    iterations = []
    final_state = None
    T_in = float(T_aprox_inicial)
    g = 9.8  # NSR-10 A.4.5 y A.5.0

    cierre = False
    for i in range(1, max_iter + 2):
        Sa_iter = spectral_acceleration(
            T_in, spectrum_params["Aa"], spectrum_params["Av"], spectrum_params["Fa"],
            spectrum_params["Fv"], spectrum_params["I"],
        )
        V_iter = Sa_iter * W_total
        k_exp = get_k_exponent(T_in)
        Wi_hi_k = Wi * (hi ** k_exp)
        denom = float(np.sum(Wi_hi_k))
        if denom <= 1e-12:
            raise ValueError("Σ(Wi·hi^k) es cero. Revisa pesos y alturas.")
        Fi = (Wi_hi_k / denom) * V_iter

        Pext_sismo = np.zeros(dof.ndof)
        for k, lev in enumerate(levels):
            nids_level = nodes_by_level[lev]
            n_nodos = len(nids_level)
            if n_nodos == 0:
                continue
            f_nodo = kN_to_N(Fi[k]) / n_nodos
            for nid in nids_level:
                ux_idx = dof.node_dofs[nid][0]
                Pext_sismo[ux_idx] += f_nodo

        U_s, R_s, free_s, rest_s, reac_s, Kll_s, Ptot_s = solve_with_bc(K, Pext_sismo, np.zeros(dof.ndof), restr, dof)

        disp_piso = np.zeros(N_pisos, dtype=float)
        for k, lev in enumerate(levels):
            ux_vals = [U_s[dof.node_dofs[nid][0]] for nid in nodes_by_level[lev]]
            disp_piso[k] = float(np.mean(ux_vals)) if ux_vals else 0.0

        drift = np.zeros(N_pisos, dtype=float)
        for k in range(N_pisos):
            if k == 0:
                delta_u = disp_piso[k]
                delta_h = hi[k] - base_y
            else:
                delta_u = disp_piso[k] - disp_piso[k - 1]
                delta_h = hi[k] - hi[k - 1]
            drift[k] = abs(delta_u) / delta_h if delta_h > 1e-12 else 0.0

        num_T = float(np.sum(Wi * disp_piso ** 2))
        den_T = float(g * np.sum(Fi * disp_piso))
        T_rayleigh = 2.0 * np.pi * np.sqrt(num_T / den_T) if den_T > 1e-15 else T_in
        T_siguiente = siguiente_periodo(T_rayleigh)
        error_pct = abs(T_siguiente - T_in) / max(abs(T_in), 1e-12) * 100.0
        converged = error_pct < tol_pct

        iter_data = {
            "iter": i,
            "T_in": float(T_in),
            "Sa": float(Sa_iter),
            "V": float(V_iter),
            "T_rayleigh": float(T_rayleigh),
            "error_pct": float(error_pct),
            "converged": bool(converged),
            "k_exp": float(k_exp),
            "Wi": Wi.tolist(),
            "Fi": Fi.tolist(),
            "hi": hi.tolist(),
            "disp_piso": disp_piso.tolist(),
            "drift": drift.tolist(),
            "drift_pct": (100.0 * drift).tolist(),
        }
        iterations.append(iter_data)
        final_state = {
            "U": U_s,
            "reactions": reac_s,
            "iter_data": iter_data,
        }

        if cierre:
            break
        if converged:
            if T_siguiente == T_in:
                break
            cierre = True  # pasada final: V, Fi y derivas deben corresponder al período definitivo
        elif i == max_iter:
            break
        T_in = T_siguiente

    if final_state is None:
        raise ValueError("No se pudo completar ninguna iteración sísmica.")

    last = final_state["iter_data"]
    # Fuerzas Fs sin dividir por R (A.4.4.2-d); la carga w no pertenece a este caso lateral
    elem_forces = []
    for e in elements.values():
        f_loc = element_end_forces_local(e, nodes, dof, final_state["U"], factor_vigas, factor_columnas,
                                         incluir_cargas=False)
        elem_forces.append((e.id, *f_loc))
    return {
        "U": final_state["U"],
        "reactions": final_state["reactions"],
        "elem_forces_local": elem_forces,
        "iterations": iterations,
        "iteration_count": len(iterations),
        "converged": bool(last["converged"]),
        "tol_pct": tol_pct,
        "max_iter": max_iter,
        "T_aprox_inicial": float(T_aprox_inicial),
        "Wi": last["Wi"],
        "W_total": W_total,
        "Fi": last["Fi"],
        "V": last["V"],
        "Sa": last["Sa"],
        "T_in_final": last["T_in"],
        "Ta": float(T_aprox_inicial),
        "T_detallado": last["T_rayleigh"],
        "periodo_diseno": periodo_diseno,
        "Cu": float(Cu),
        "T_limite": float(T_limite),
        "T_diseno": last["T_in"],
        "limite_activo": bool(periodo_diseno == "limite_CuTa" and last["T_rayleigh"] > T_limite),
        "hi": last["hi"],
        "disp_piso": last["disp_piso"],
        "drift": last["drift"],
        "drift_pct": last["drift_pct"],
        **evaluate_drifts(last["drift"], spectrum_params["I"], usar_I_unitario_derivas, reducir_derivas_fisuradas),
        **stability_index(last["Wi"], last["Fi"], last["disp_piso"], last["hi"], base_y, carga_viva_kN),
        "k_exp": last["k_exp"],
        "gamma": gamma,
        "factor_vigas": factor_vigas,
        "factor_columnas": factor_columnas,
        "N_pisos": N_pisos,
        "error_pct_final": last["error_pct"],
    }
