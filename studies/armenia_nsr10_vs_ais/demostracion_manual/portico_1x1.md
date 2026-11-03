# Demostración manual: pórtico de 1 luz y 1 piso

Compara la deriva del modelo AIS fisurado con la del modelo NSR-10, con la misma fuerza. Se verifica con `verificar_portico_1x1.py`.

## Datos

Pórtico con base empotrada, altura h = 3 m, luz L = 5 m, columna c × c con c = 0.30 m, viga 0.75c × c y fuerza lateral total V = 100 kN.

## 1. Rigidez lateral

Se define k_c = E·Ic/h, k_b = E·Ib/L y γ = k_b/k_c. Por antisimetría, los dos nudos superiores giran igual, θ.

- Momento en la cabeza de la columna: M = k_c·(4θ − 6Δ/h)
- Momento de la viga en el nudo: M_b = 6·k_b·θ
- Equilibrio del nudo: 4k_c·θ − 6k_c·Δ/h + 6k_b·θ = 0, de donde θ = 6k_c·Δ / [h·(4k_c + 6k_b)]
- Cortante de una columna: V_c = 12k_c·Δ/h² − 6k_c·θ/h

Sumando las dos columnas:

K = (24·E·Ic/h³) · (1 + 6γ) / (4 + 6γ)

## 2. Razón de derivas con la misma fuerza

El modelo fisurado usa 0.70·Ic y 0.35·Ib, así que su γ es la mitad. Entonces:

Razón = K_NSR / K_AIS = (1/0.70) · [(1 + 6γ)(4 + 3γ)] / [(4 + 6γ)(1 + 3γ)]

## 3. Valor con las proporciones del estudio

γ = (0.75·5⁻¹) / (1·3⁻¹) = 0.45, y la razón es **1.796**.

| Resultado | Fórmula cerrada | ROCKFRAME sin deformación axial | ROCKFRAME con áreas reales |
|---|---:|---:|---:|
| Δ NSR-10 [mm] | 12.1351 | 12.1351 | 12.1480 |
| Δ AIS fisurada [mm] | | 21.7951 | 21.8031 |
| Razón | 1.7960 | 1.7960 | 1.7948 |

La pequeña diferencia de la última columna es la deformación axial de los elementos. La fórmula cerrada no la incluye, y como no se reduce en el modelo fisurado, baja un poco la razón.

## 4. Límites de la razón

**Corrección a la instrucción original.** Se pidió mostrar que la razón va de 1.43 a 2.86 en este pórtico. La fórmula muestra otra cosa:

| Caso | Razón |
|---|---:|
| γ muy grande, viga muy rígida | 1.43 |
| γ = 0.47, valor máximo | 1.80 |
| γ muy pequeño, viga muy flexible | 1.43 |

En un pórtico de un piso con base empotrada la razón nunca llega a 2.86. La base empotrada hace que las columnas siempre controlen buena parte de la deformación, y con una viga casi sin rigidez las columnas trabajan como voladizos, de nuevo con 1/0.70.

## 5. Dónde aparece el 2.86

El valor 2.86 corresponde a un piso intermedio de un pórtico alto, con puntos de inflexión a media altura de las columnas y a media luz de las vigas. Allí, con dos columnas y dos vigas en el nudo:

- Equilibrio: θ = (Δ/h) · k_c / (k_c + k_b)
- Deriva: Δ = (V·h²/12) · (1/k_c + 1/k_b)

La flexibilidad de columnas y vigas se suma, y por eso:

Razón = (γ/0.70 + 1/0.35) / (1 + γ)

| Caso | Razón |
|---|---:|
| γ muy grande, las columnas controlan | 1.43 |
| γ = 0.45, proporciones del estudio | 2.41 |
| γ muy pequeño, las vigas controlan | 2.86 |

Este modelo simplificado explica por qué los pórticos del estudio están por encima del pórtico de un piso, con razones de hasta 2.33 con la misma fuerza.
