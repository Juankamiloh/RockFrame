"""ROCKFRAME contra PyNite (solucionador de terceros). Tolerancia 0.1 %.

Lo sísmico se recalcula aquí con las fórmulas de la NSR-10, sin usar funciones del motor.
Requiere: pip install --no-deps PyNiteFEA prettytable wcwidth
"""
import os, sys
import numpy as np
import scipy.linalg as sl
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from Pynite import FEModel3D
from rockframe import engine as m

G = 9.8; TOL = 0.1
CASOS = {
 "1x2": dict(L=[5.0], H=[3.5, 3.0], w=[25.0, 20.0], col=[(0.4, 0.4)]*2, vig=[(0.3, 0.45)]*2),
 "3x3": dict(L=[5.0, 6.0, 5.0], H=[4.0, 3.0, 3.0], w=[30.0, 30.0, 20.0], col=[(0.5, 0.5)]*3, vig=[(0.35, 0.5)]*3),
 "3x6": dict(L=[5.0]*3, H=[4.0]+[3.0]*5, w=[35.0]*5+[25.0], col=[(0.6, 0.6)]*6, vig=[(0.4, 0.55)]*6),
 "irregular 4x5": dict(L=[4.0, 7.0, 5.5, 3.0], H=[4.5, 3.2, 3.6, 3.0, 2.8], w=[40.0, 32.0, 28.0, 25.0, 15.0],
                       col=[(0.7, 0.6), (0.6, 0.6), (0.55, 0.5), (0.5, 0.5), (0.4, 0.4)],
                       vig=[(0.4, 0.6), (0.4, 0.55), (0.35, 0.5), (0.3, 0.45), (0.3, 0.4)]),
}
FACT = {"bruta": (1.0, 1.0), "fisurada": (0.35, 0.70)}
ESP = {"Aa.25 I1": dict(Aa=0.25, Av=0.25, Fa=1.3, Fv=1.9, I=1.0), "Aa.15 I1.5": dict(Aa=0.15, Av=0.20, Fa=1.5, Fv=2.2, I=1.5)}
FC = 28.0; GAMMA = 24.0
peor = {}


def anota(cl, a, b, escala):
    """Error relativo a la magnitud máxima de esa familia de resultados."""
    e = float(np.max(np.abs(np.asarray(a, float)-np.asarray(b, float))))/escala*100
    peor[cl] = max(peor.get(cl, 0.0), e)


def malla(c):
    x = np.r_[0, np.cumsum(c["L"])]; y = np.r_[0, np.cumsum(c["H"])]
    return x, y


def pynite(c, fv, fc, gravedad=False, nodales=None):
    """Modelo plano en PyNite, en N y m. Devuelve el modelo y nombres de nudos por (i, j)."""
    E = 4700*np.sqrt(FC)*1e6
    M = FEModel3D(); M.add_material("c", E, E/2.4, 0.2, 0.0)
    x, y = malla(c)
    nom = {}
    for j, yy in enumerate(y):
        for i, xx in enumerate(x):
            nom[i, j] = f"N{i}_{j}"; M.add_node(nom[i, j], float(xx), float(yy), 0.0)
            M.def_support(nom[i, j], j == 0, j == 0, True, True, True, j == 0)
    for j in range(1, len(y)):
        bc, hc = c["col"][j-1]; bv, hv = c["vig"][j-1]
        Ac, Ic = bc*hc, bc*hc**3/12; Av, Iv = bv*hv, bv*hv**3/12
        M.add_section(f"C{j}", Ac, Ic*fc, Ic*fc, 1.0); M.add_section(f"V{j}", Av, Iv*fv, Iv*fv, 1.0)
        for i in range(len(x)):
            n = f"col{i}_{j}"; M.add_member(n, nom[i, j-1], nom[i, j], "c", f"C{j}")
            if gravedad: M.add_member_dist_load(n, "FY", -GAMMA*Ac*1e3, -GAMMA*Ac*1e3)
        for i in range(len(x)-1):
            n = f"vig{i}_{j}"; M.add_member(n, nom[i, j], nom[i+1, j], "c", f"V{j}")
            if gravedad:
                q = -(c["w"][j-1]+GAMMA*Av)*1e3; M.add_member_dist_load(n, "FY", q, q)
    for (i, j), (px, py, mz) in (nodales or {}).items():
        if px: M.add_node_load(nom[i, j], "FX", px)
        if py: M.add_node_load(nom[i, j], "FY", py)
        if mz: M.add_node_load(nom[i, j], "MZ", mz)
    return M, nom


def param(c, nodal=None):
    N = len(c["H"])
    return dict(n_bays=len(c["L"]), n_stories=N, bay_widths=c["L"], bay_width=c["L"][0], story_heights=c["H"],
                columns_sections=c["col"], beams_sections=c["vig"], w_level_kNpm=c["w"], nodal_loads=nodal or {})


def nid(c, i, j):
    return 1+i+(len(c["L"])+1)*j


def Sa_manual(T, e):
    AF, VF = e["Aa"]*e["Fa"], e["Av"]*e["Fv"]; Tc = 0.48*VF/AF; TL = 2.4*e["Fv"]
    if T < Tc: return 2.5*AF*e["I"]
    if T <= TL: return 1.2*VF*e["I"]/T
    return 1.2*VF*TL*e["I"]/T**2


def k_manual(T):
    return 1.0 if T <= 0.5 else (2.0 if T > 2.5 else 0.75+0.5*T)


def W_manual(c):
    nx = len(c["L"])+1; L = sum(c["L"]); N = len(c["H"]); W = []
    for j in range(N):
        bv, hv = c["vig"][j]; bc, hc = c["col"][j]
        pc = GAMMA*bc*hc*c["H"][j]*nx/2
        arriba = 0.0
        if j+1 < N:
            b2, h2 = c["col"][j+1]; arriba = GAMMA*b2*h2*c["H"][j+1]*nx/2
        W.append((c["w"][j]+GAMMA*bv*hv)*L+pc+arriba)
    return np.array(W)


n_comp = 0
for nc, c in CASOS.items():
    nx, ny = len(c["L"])+1, len(c["H"])+1
    x, y = malla(c)
    Pn = {(nx-1, ny-1): (15e3, -10e3, 5e3), (0, 1): (40e3, 0.0, 0.0)}
    for nf, (fv, fc) in FACT.items():
        # ---------- matricial: gravedad, peso propio y nodales ----------
        M, nom = pynite(c, fv, fc, True, Pn); M.analyze_linear(check_statics=False)
        nod = {nid(c, i, j): tuple(v/1e3 for v in f) for (i, j), f in Pn.items()}
        r = m.run_static_analysis(param(c, nod), FC, None, fv, fc, gamma=GAMMA)
        d = r["dof"]; U = r["U"]
        a, b, ar, br, ath, bth = [], [], [], [], [], []
        for (i, j), n in nom.items():
            nd = M.nodes[n]; u = d.node_dofs[nid(c, i, j)]
            a += [U[u[0]], U[u[1]]]; b += [nd.DX["Combo 1"], nd.DY["Combo 1"]]
            ath.append(U[u[2]]); bth.append(nd.RZ["Combo 1"])
        anota("desplazamientos", a, b, np.max(np.abs(b))); anota("rotaciones", ath, bth, np.max(np.abs(bth)))
        for i in range(nx):
            nd = M.nodes[nom[i, 0]]; R = r["reactions_by_node"][nid(c, i, 0)]
            ar += list(R); br += [nd.RxnFX["Combo 1"], nd.RxnFY["Combo 1"], nd.RxnMZ["Combo 1"]]
        ar, br = np.array(ar), np.array(br)
        anota("reacciones", ar, br, np.max(np.abs(br)))
        # fuerzas de extremo por elemento: mismo orden que build_case_gen
        ef = {e[0]: e[1:] for e in r["elem_forces_local"]}
        eid = 1; Fa, Fb = [], []
        for j in range(1, ny):
            nombres = [f"col{i}_{j}" for i in range(nx)]+[f"vig{i}_{j}" for i in range(nx-1)]
            for n in nombres:
                f = np.asarray(M.members[n].f("Combo 1")).ravel()
                Fb.append([abs(f[0]), abs(f[1]), abs(f[5]), abs(f[6]), abs(f[7]), abs(f[11])])
                Fa.append(np.abs(ef[eid])); eid += 1
        Fa, Fb = np.array(Fa), np.array(Fb)
        anota("axial N", Fa[:, [0, 3]], Fb[:, [0, 3]], Fb[:, [0, 3]].max())
        anota("cortante V", Fa[:, [1, 4]], Fb[:, [1, 4]], Fb[:, [1, 4]].max())
        anota("momento M", Fa[:, [2, 5]], Fb[:, [2, 5]], Fb[:, [2, 5]].max())
        n_comp += 1

        # ---------- sísmico ----------
        h = float(sum(c["H"])); hi = y[1:]; Wi = W_manual(c)
        for ne, e in ESP.items():
            sp = dict(ciudad="", amenaza="", suelo="", Ae=None, Ad=None, h_m=h, grupo_label="", **e)
            for modo in ("limite_CuTa", "sin_limite"):
                s = m.run_seismic_iterative(param(c), FC, None, GAMMA, fv, fc, sp, h, 0.047, 0.9, 20, 0.01, periodo_diseno=modo)
                T = s["T_diseno"]; Ta = 0.047*h**0.9
                Cu = max(1.75-1.2*e["Av"]*e["Fv"], 1.2)
                anota("Ta", [s["T_aprox_inicial"]], [Ta], Ta); anota("Cu", [s["Cu"]], [Cu], Cu)
                anota("Wi", s["Wi"], Wi, Wi.max())
                Sa = Sa_manual(T, e); V = Sa*Wi.sum(); k = k_manual(T)
                Cv = Wi*hi**k/np.sum(Wi*hi**k); Fi = Cv*V
                anota("Sa", [s["Sa"]], [Sa], Sa); anota("V", [s["V"]], [V], V); anota("Fi", s["Fi"], Fi, Fi.max())
                Ms, nm = pynite(c, fv, fc)
                for j in range(1, ny):
                    for i in range(nx):
                        Ms.add_node_load(nm[i, j], "FX", Fi[j-1]*1e3/nx)
                Ms.analyze_linear(check_statics=False)
                dp = np.array([np.mean([Ms.nodes[nm[i, j]].DX["Combo 1"] for i in range(nx)]) for j in range(1, ny)])
                anota("despl. piso", s["disp_piso"], dp, dp.max())
                dr = np.abs(np.diff(np.r_[0, dp]))/np.array(c["H"])*100
                anota("deriva", s["drift_pct"], dr, dr.max())
                TR = 2*np.pi*np.sqrt(np.sum(Wi*dp**2)/(G*np.sum(Fi*dp)))
                anota("T Rayleigh", [s["T_detallado"]], [TR], TR)
                esp = min(TR, Cu*Ta) if modo == "limite_CuTa" else TR
                anota("T diseño", [T], [esp], esp)
                Vb = -sum(Ms.nodes[nm[i, 0]].RxnFX["Combo 1"] for i in range(nx))/1e3
                anota("cortante basal PyNite", [Vb], [V], V)
                n_comp += 1

        # ---------- primer modo con la K de PyNite ----------
        lat = [(i, j) for j in range(1, ny) for i in range(nx)]
        mas = np.array([Wi[j-1]*1e3/G/nx for (i, j) in lat])
        Fl = np.zeros((len(lat), len(lat)))
        for q, (i, j) in enumerate(lat):
            Mk, nk = pynite(c, fv, fc); Mk.add_node_load(nk[i, j], "FX", 1e3); Mk.analyze_linear(check_statics=False)
            Fl[:, q] = [Mk.nodes[nk[a_, b_]].DX["Combo 1"]/1e3 for (a_, b_) in lat]
        Fl = 0.5*(Fl+Fl.T)
        w2 = sl.eigh(np.linalg.inv(Fl), np.diag(mas), eigvals_only=True)
        T1 = 2*np.pi/np.sqrt(w2[0])
        s = m.run_seismic_iterative(param(c), FC, None, GAMMA, fv, fc,
                                    dict(ciudad="", amenaza="", suelo="", Ae=None, Ad=None, h_m=sum(c["H"]), grupo_label="", **ESP["Aa.25 I1"]),
                                    float(sum(c["H"])), 0.047, 0.9, 20, 0.01, periodo_diseno="sin_limite")
        print(f"{nc:14s} {nf:9s} T_Rayleigh={s['T_detallado']:.4f}  T_modo1={T1:.4f}  dif={(s['T_detallado']/T1-1)*100:+.3f}%")

print(f"\nComparaciones: {n_comp} corridas. Error máximo por resultado (tolerancia {TOL} %):")
mal = 0
for k, v in sorted(peor.items(), key=lambda t: -t[1]):
    print(f"  {k:24s} {v:.6f} %  {'OK' if v <= TOL else 'FALLA'}"); mal += v > TOL
print("RESULTADO:", "TODO DENTRO DE TOLERANCIA" if not mal else f"{mal} FUERA DE TOLERANCIA")
