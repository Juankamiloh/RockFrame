"""Verifica portico_1x1.md: fórmula cerrada frente a ROCKFRAME, con la misma fuerza en ambos modelos.

Uso: python studies/armenia_nsr10_vs_ais/demostracion_manual/verificar_portico_1x1.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
from rockframe import engine as m  # noqa: E402

E = 4700 * 28 ** 0.5 * 1e6
h, L, c = 3.0, 5.0, 0.30
Ic, Iv = c ** 4 / 12, 0.75 * c * c ** 3 / 12


def rigidez_cerrada(Ic_, Iv_):
    g = (Iv_ / L) / (Ic_ / h)
    return 24 * E * Ic_ / h ** 3 * (1 + 6 * g) / (4 + 6 * g)


def razon_cerrada(g):
    return (1 / 0.7) * (1 + 6 * g) * (4 + 3 * g) / ((4 + 6 * g) * (1 + 3 * g))


def razon_piso_intermedio(g):
    return (g / 0.7 + 1 / 0.35) / (1 + g)


def rockframe(fv, fc, A_col, A_vig):
    nodes = {1: m.Node(1, 0, 0), 2: m.Node(2, L, 0), 3: m.Node(3, 0, h), 4: m.Node(4, L, h)}
    elems = {1: m.Element(1, 1, 3, A_col, E, Ic), 2: m.Element(2, 2, 4, A_col, E, Ic), 3: m.Element(3, 3, 4, A_vig, E, Iv)}
    dof = m.DOFMap(nodes)
    K = m.assemble_global_K(nodes, elems, dof, fv, fc)
    P = m.assemble_Pext_nodal(dof, {3: (50.0, 0, 0), 4: (50.0, 0, 0)})
    U, *_ = m.solve_with_bc(K, P, P * 0, [1, 2, 3, 4, 5, 6], dof)
    return 0.5 * (U[dof.node_dofs[3][0]] + U[dof.node_dofs[4][0]])


g = (Iv / L) / (Ic / h)
print(f"gamma = {g:.4f}")
print(f"Razón cerrada = {razon_cerrada(g):.4f}")
for nombre, Ac, Av in (("sin deformación axial", 1e3, 1e3), ("con áreas reales", c * c, 0.75 * c * c)):
    d0, d1 = rockframe(1, 1, Ac, Av), rockframe(0.35, 0.70, Ac, Av)
    print(f"ROCKFRAME {nombre}: delta NSR-10 = {d0 * 1000:.4f} mm, delta AIS fisurada = {d1 * 1000:.4f} mm, razón = {d1 / d0:.4f}")
d0 = rockframe(1, 1, 1e3, 1e3)
print(f"delta cerrada NSR-10 = {100e3 / rigidez_cerrada(Ic, Iv) * 1000:.4f} mm")
gmax = (4 / 18) ** 0.5
print(f"Máximo de la razón en pórtico de 1 piso: {razon_cerrada(gmax):.4f} con gamma = {gmax:.4f}")
print(f"Límites: gamma pequeño {razon_cerrada(1e-9):.4f}; gamma grande {razon_cerrada(1e9):.4f}")
print(f"Piso intermedio: gamma {g:.2f} = {razon_piso_intermedio(g):.4f}; gamma pequeño {razon_piso_intermedio(1e-9):.4f}; gamma grande {razon_piso_intermedio(1e9):.4f}")
assert abs(rockframe(0.35, 0.70, 1e3, 1e3) / d0 / razon_cerrada(g) - 1) < 1e-3
assert abs(100e3 / rigidez_cerrada(Ic, Iv) / d0 - 1) < 1e-3
print("Coincide dentro de 0.1 %")
