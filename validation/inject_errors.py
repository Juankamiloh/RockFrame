"""Comprueba que la suite detecta errores: los inyecta uno a uno en una copia temporal del motor.

Uso: python validation/inject_errors.py
"""
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

RAIZ = pathlib.Path(__file__).resolve().parent.parent
MUTANTES = [
    ("Rigidez 12EI/L³ alterada", "[ 0, 12*EI/L3, 6*EI/L2, 0, -12*EI/L3, 6*EI/L2]", "[ 0, 11.9*EI/L3, 6*EI/L2, 0, -11.9*EI/L3, 6*EI/L2]"),
    ("Signo de la transformación", "[-s,c,0,0,0,0]", "[s,c,0,0,0,0]"),
    ("Empotramiento wL²/12 cambiado", "wL*L/12, 0, wL/2, -wL*L/12", "wL*L/10, 0, wL/2, -wL*L/10"),
    ("H1: fuerzas con inercia bruta", "kl=k_local_frame(e.E,e.A,effective_I(e,s,factor_vigas,factor_columnas),L)", "kl=k_local_frame(e.E,e.A,e.I,L)"),
    ("H2: sin límite Cu·Ta", "return min(float(T_R), float(T_limite))", "return float(T_R)"),
    ("Cu sin el mínimo 1.2", "return max(1.75 - 1.2 * Av * Fv, 1.2)", "return 1.75 - 1.2 * Av * Fv"),
    ("Tc con 0.47 en vez de 0.48", "Tc = 0.48 * (Av * Fv) / (Aa * Fa)\n    TL", "Tc = 0.47 * (Av * Fv) / (Aa * Fa)\n    TL"),
    ("TL con 2.5 en vez de 2.4", "TL = 2.40 * Fv\n    if T <= Tc:", "TL = 2.50 * Fv\n    if T <= Tc:"),
    ("Rama T > TL con T en vez de T²", "return 1.2 * Av * Fv * TL * I / T ** 2", "return 1.2 * Av * Fv * I / T"),
    ("Exponente k mal interpolado", "return 1.0 + (T_value - 0.5) / 2.0", "return 1.0 + (T_value - 0.5) / 2.2"),
    ("H7: g = 9.81", "g = 9.8  # NSR-10", "g = 9.81  # NSR-10"),
    ("Peso de columna sin repartir", "half_w = peso_propio / 2.0", "half_w = peso_propio / 1.9"),
    ("Peso sin la carga w", "total_beam_weight = w_load + peso_propio", "total_beam_weight = peso_propio"),
    ("H8: sin pasada final", "cierre = True  #", "break  #"),
    ("Deriva sin dividir por la altura correcta", "delta_h = hi[k] - hi[k - 1]", "delta_h = hi[k]"),
    ("Límite 1/0.7 cambiado", "LIMITE_DERIVA_PCT / 0.7 if", "LIMITE_DERIVA_PCT / 0.75 if"),
]


def correr(carpeta):
    r = subprocess.run([sys.executable, "-m", "pytest", "tests", "-q", "--tb=no", "-p", "no:cacheprovider", "-x"],
                       cwd=carpeta, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode, r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr[-200:]


def main():
    original = (RAIZ / "rockframe" / "engine.py").read_bytes().decode("utf-8").replace("\r\n", "\n")
    vivos = 0
    with tempfile.TemporaryDirectory() as t:
        shutil.copytree(RAIZ / "tests", os.path.join(t, "tests"), ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copytree(RAIZ / "rockframe", os.path.join(t, "rockframe"), ignore=shutil.ignore_patterns("__pycache__"))
        destino = pathlib.Path(t) / "rockframe" / "engine.py"
        destino.write_text(original, encoding="utf-8")
        cod, linea = correr(t)
        print(f"Sin errores: {linea}")
        assert cod == 0
        for nombre, a, b in MUTANTES:
            assert original.count(a) >= 1, f"No se encontró el texto de: {nombre}"
            destino.write_text(original.replace(a, b), encoding="utf-8")
            cod, _ = correr(t)
            vivos += cod == 0
            print(f"{'DETECTADO' if cod else 'NO DETECTADO':13s} {nombre}", flush=True)
    print(f"\n{len(MUTANTES) - vivos} de {len(MUTANTES)} errores detectados")


if __name__ == "__main__":
    main()
