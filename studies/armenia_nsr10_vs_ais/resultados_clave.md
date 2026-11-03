# Resultados clave del estudio v2

Todas las cifras salen de `results.csv`, generado por `run_study.py`. Las medianas excluyen los pórticos de 1 piso, que quedan en la columna mínima de 30 cm.

Sitio: Armenia, Quindío, suelo D. Aa = Av = 0.25, Fa = 1.3, Fv = 1.9, I = 1.0. T0 = 0.146 s, TC = 0.702 s, TL = 4.56 s, Sa en la meseta = 0.8125.

## Medianas y rangos

| Grupo | Pórticos | Razón deriva AIS fisurada / deriva NSR-10 | Concreto adicional AIS fisurada (1.5 %) | Concreto adicional NSR-10 fisurada (1.43 %) | Columna AIS / NSR-10 |
|---|---:|---:|---:|---:|---:|
| Caso base, con tope Cu·Ta | 63 | 2.08 (1.72 a 2.23) | +21.0 % (+8.9 a +25.8) | +24.3 % | 1.100 |
| Caso base, sin tope | 63 | 1.70 (1.55 a 2.26) | +14.7 % (+4.4 a +24.8) | +21.3 % | 1.071 |
| 2 a 6 pisos, con tope | 35 | 2.19 (2.06 a 2.23) | +23.1 % (+20.3 a +25.8) | +26.4 % | 1.110 |
| 7 a 10 pisos, con tope | 28 | 1.75 (1.72 a 1.89) | +9.7 % (+8.9 a +14.5) | +13.1 % | 1.048 |

Origen: `results.csv`, columnas `deriva_max_pct`, `deriva_bruta_pct` y `volumen_cont_m3`.

## Variantes

| Variante | Relación de rigidez viga/columna | Razón, mediana | Concreto adicional AIS, con tope | Concreto adicional AIS, sin tope |
|---|---:|---:|---:|---:|
| Viga de altura c, luz de 5 m | 0.45 | 2.08 | +21.0 % | +14.7 % |
| Viga de altura 1.25c, luz de 5 m | 0.88 | 1.89 | +13.1 % | +10.5 % |
| Viga de altura c, luz de 4 m | 0.56 | 2.03 | +19.1 % | +12.7 % |
| Viga de altura c, luz de 6 m | 0.38 | 2.13 | +22.6 % | +16.8 % |

Origen: `results.csv`, columna `rigidez_viga_columna`. Es la relación (EI/L) de vigas / (EI/L) de columnas en un nudo interior.

## Columna mínima con 3 luces, en cm

| Pisos | NSR-10 (1 %) | AIS fisurada (1.5 %) | NSR-10 fisurada (1.43 %) |
|---|---:|---:|---:|
| 2 | 35.2 | 39.1 | 39.6 |
| 6 | 57.0 | 62.7 | 63.7 |
| 10 | 64.1 | 67.1 | 68.1 |

Origen: `results.csv`, filas `seccion_minima`, columna `c`.

## Por número de pisos, con tope

| Pisos | Límite que igualaría ambos criterios [%] | Razón con la misma fuerza | Reducción de fuerza del modelo fisurado | T diseño NSR-10 [s] | T diseño AIS fisurado [s] |
|---|---:|---:|---:|---:|---:|
| 2 | 2.20 | 2.20 | 0.0 % | 0.283 | 0.283 |
| 3 | 2.16 | 2.16 | 0.0 % | 0.407 | 0.407 |
| 4 | 2.19 | 2.19 | 0.0 % | 0.528 | 0.528 |
| 5 | 2.22 | 2.21 | 0.0 % | 0.578 | 0.645 |
| 6 | 2.08 | 2.23 | 7.7 % | 0.628 | 0.760 |
| 7 | 1.87 | 2.31 | 19.7 % | 0.675 | 0.874 |
| 8 | 1.75 | 2.33 | 25.7 % | 0.732 | 0.985 |
| 9 | 1.75 | 2.33 | 25.9 % | 0.812 | 1.095 |
| 10 | 1.75 | 2.33 | 25.6 % | 0.896 | 1.204 |

Origen: `results.csv`, filas `misma_seccion`. El límite equivalente es la razón misma, porque NSR-10 se evalúa con 1.00 %. Los períodos son medianas de 1 a 7 luces; la Figura 4 usa los pórticos de 3 luces, por eso con 10 pisos dice 0.899 s y esta tabla 0.896 s.

## Alineación de la caída con TC

La razón cae de 2.22 a 2.08 entre 5 y 6 pisos. En ese tramo, el período de diseño AIS fisurado va de 0.645 a 0.760 s y cruza TC = 0.702 s. El de NSR-10 va de 0.578 a 0.628 s y no lo cruza. La caída queda mejor alineada con el período del modelo AIS fisurado.

## Demostraciones manuales

- Pórtico 1×1: razón de 1.796 con γ = 0.45, igual a ROCKFRAME sin deformación axial. Origen: `demostracion_manual/portico_1x1.md`.
- Pórtico 3×6: todos los valores de la hoja coinciden con ROCKFRAME. Origen: `demostracion_manual/portico_3x6.xlsx`.

## Contexto sísmico

- 25 de enero de 1999: el Servicio Geológico Colombiano reporta magnitud 6.1 Mw y 21 km de profundidad en su infografía del sismo del Eje Cafetero. Otra publicación del SGC indica 6.2. `[PENDIENTE: definir la cifra con el catálogo del SGC]`
- 10 de agosto de 2026: la OPS, citando al SGC, reporta 7.4 Mw y 103 km de profundidad, con epicentro en San José del Palmar. El boletín inicial decía 6.7 y 82 km. `[PENDIENTE: confirmar en el boletín definitivo del SGC, y los daños en Armenia]`
- `[PENDIENTE: confirmar con el autor si "el sismo de noviembre" se refiere a otro evento]`
