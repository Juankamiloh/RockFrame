# Figura 3. Razón de derivas por número de pisos

## Qué muestra
Cada punto es la mediana de los pórticos con ese número de pisos, de 1 a 7 luces. La curva naranja usa la fuerza de cada modelo, con tope Cu·Ta. La curva azul aplica al modelo fisurado las mismas fuerzas del modelo NSR-10 (1 %). Los datos salen de `results.csv`, columnas `deriva_max_pct`, `deriva_bruta_pct` y `deriva_fis_misma_fuerza_pct`.

## Cómo leerla
Compara las dos curvas: la distancia entre ellas es el efecto de la fuerza.

## Qué tendencia tiene
Con la misma fuerza, la razón queda entre 2.16 y 2.33. Con la fuerza de cada modelo baja desde 2.22 con 5 pisos hasta 1.75 con 10.

## Por qué pasa
La curva azul mide solo la pérdida de rigidez. La naranja se separa porque el modelo fisurado recibe menos fuerza cuando su período pasa de TC. En 10 pisos recibe 26 % menos.

## Qué conclusión permite y cuál no
Permite separar el efecto de la rigidez del efecto de la fuerza. No describe pórticos con otra relación de rigidez entre vigas y columnas.

## Frase de 20 segundos
La línea azul es lo que perdemos en rigidez. La línea naranja muestra que, en pórticos más altos, una fuerza menor compensa parte de esa pérdida.
