# Figura 1. Razón de derivas frente al período del modelo NSR-10

## Qué muestra
Cada punto es un pórtico, de 1 a 7 luces y de 1 a 10 pisos, 70 en total. El eje horizontal es el período de diseño del modelo NSR-10 (1 %), en segundos. El eje vertical es la razón deriva AIS fisurada / deriva NSR-10, sin unidades, calculada con la misma sección: la mínima que cumple NSR-10 (1 %). El color es el número de pisos. La línea punteada marca la equivalencia en 1.50, la línea vertical marca TC y la banda va de 0.8·TC a 1.2·TC. Los datos salen de `results.csv`, filas `misma_seccion`, con tope Cu·Ta.

## Cómo leerla
Mira primero la línea de 1.50: si un punto está encima, la sección que cumple 1 % no cumple 1.5 %. Luego sigue los colores de claro a oscuro para ver qué pasa al aumentar los pisos.

## Qué tendencia tiene
Todos los puntos quedan encima de 1.50 (mínimo 1.72). Medianas por pisos: de 2 a 5 pisos la razón está entre 2.08 y 2.22; con 6 pisos es 2.08; con 7 es 1.87; de 8 a 10 está entre 1.75 y 1.75. Los pórticos de 1 piso aparecen en gris porque quedan en la columna mínima de 30 cm y no se comparan.

## Por qué pasa
La razón depende de dos cosas: cuánto más flexible es el modelo fisurado y cuánta fuerza recibe. Mientras los dos períodos están antes de TC (0.702 s), ambos modelos reciben la misma aceleración y la misma fuerza, y la razón solo refleja la pérdida de rigidez. Cuando el período del modelo fisurado pasa de TC, su aceleración baja y recibe menos fuerza, mientras el modelo NSR-10 sigue en la meseta. Por eso la razón cae. Cuando ambos períodos ya pasaron de TC, la diferencia de fuerza se estabiliza y la razón deja de caer.

## Qué conclusión permite y cuál no
Permite afirmar que, en estos pórticos, la deriva crece más que el límite. No permite afirmar que pase en todas las edificaciones, ni que esa sección sea un diseño final: solo se comparó rigidez lateral.

## Frase de 20 segundos
Cada punto es un pórtico con la misma sección en los dos modelos. Todos quedan encima de 1.5, así que el modelo fisurado deriva más de lo que el nuevo límite compensa. La razón ronda 2.2 hasta 5 pisos y baja a 1.75 en 10 pisos.
