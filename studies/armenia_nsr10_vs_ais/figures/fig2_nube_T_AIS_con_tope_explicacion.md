# Figura 2. Razón de derivas frente al período del modelo AIS fisurado

## Qué muestra
Es la misma razón de la Figura 1, pero el eje horizontal es el período de diseño del modelo AIS fisurado. Los datos salen de `results.csv`, filas `misma_seccion`, con tope Cu·Ta.

## Cómo leerla
Mira dónde empieza a bajar la nube respecto a la línea vertical de TC.

## Qué tendencia tiene
La caída empieza entre 5 y 6 pisos: la razón pasa de 2.22 a 2.08. En ese tramo el período del modelo AIS fisurado va de 0.645 a 0.760 s y cruza TC = 0.702 s. El período del modelo NSR-10 va de 0.578 a 0.628 s y no cruza TC. Por eso la caída queda mejor alineada con TC en la versión con el período del modelo AIS fisurado.

## Por qué pasa
La razón depende de dos cosas: cuánto más flexible es el modelo fisurado y cuánta fuerza recibe. Mientras los dos períodos están antes de TC (0.702 s), ambos modelos reciben la misma aceleración y la misma fuerza, y la razón solo refleja la pérdida de rigidez. Cuando el período del modelo fisurado pasa de TC, su aceleración baja y recibe menos fuerza, mientras el modelo NSR-10 sigue en la meseta. Por eso la razón cae. Cuando ambos períodos ya pasaron de TC, la diferencia de fuerza se estabiliza y la razón deja de caer.

## Qué conclusión permite y cuál no
Permite ubicar la caída alrededor de TC. No permite generalizar el valor de TC: depende del espectro de Armenia con suelo D.

## Frase de 20 segundos
La razón empieza a caer cuando el período del modelo fisurado pasa de TC, porque ese modelo sale de la meseta del espectro y recibe menos fuerza.
