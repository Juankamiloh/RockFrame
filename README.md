# ROCKFRAME

[English](README.en.md)

ROCKFRAME es un programa gratuito en Python para analizar pórticos planos de concreto reforzado, con análisis sísmico según la NSR-10.

![ROCKFRAME en uso: datos del pórtico, cálculo, derivas y reporte en Excel](docs/img/demo_rockframe.gif)

## Pruébalo en 3 pasos

1. Instala [Python 3.10 o superior](https://www.python.org/downloads/) y [Git](https://git-scm.com/downloads). En Windows, marca **Add python.exe to PATH**.
2. Abre una terminal e instala ROCKFRAME:

```bash
pip install git+https://github.com/Juankamiloh/RockFrame.git
```

3. Ábrelo:

```bash
rockframe
```

Si el comando no aparece, usa `python -m rockframe`. Pulsa **Ejemplo** y luego **Calcular** para correr un pórtico de 3 luces y 6 pisos.

**Video de un minuto:** [demo_rockframe.mp4](https://github.com/Juankamiloh/RockFrame/releases/download/v0.9.0/demo_rockframe.mp4)

## Estudio: NSR-10 frente a AIS 100-24 en Armenia

¿Permitir 1.5 % de deriva con secciones fisuradas equivale al 1 % de la NSR-10? Se analizaron 70 pórticos planos de concreto en Armenia, suelo D, de 1 a 7 luces y de 1 a 10 pisos, con período de Rayleigh y tope Cu·Ta. Los 7 de 1 piso quedan en la columna mínima y no se comparan.

![Razón de derivas frente al período](studies/armenia_nsr10_vs_ais/figures/fig1_nube_T_NSR_con_tope.png)

| Cifra | Qué significa |
|---|---|
| **×2.08** | Con la misma sección, la deriva del modelo AIS fisurada (1.5 %) es en mediana 2.08 veces la del modelo NSR-10 (1 %), de 1.72 a 2.23, mientras el límite solo sube 1.5 veces. |
| **+21 %** | Cumplir AIS fisurada (1.5 %) exige en mediana 21.0 % más concreto que cumplir NSR-10 (1 %). |
| **−26 %** | Desde 8 pisos, el modelo fisurado tiene un período más largo y recibe cerca de 26 % menos fuerza sísmica; por eso la razón baja a 1.75. |

![Razón por número de pisos](studies/armenia_nsr10_vs_ais/figures/fig3_razon_por_pisos.png)

![Concreto adicional por pórtico](studies/armenia_nsr10_vs_ais/figures/fig6_concreto_adicional.png)

Datos, scripts, figuras con su explicación y demostraciones a mano: [`studies/armenia_nsr10_vs_ais/`](studies/armenia_nsr10_vs_ais/). Todas las cifras y su origen están en [`resultados_clave.md`](studies/armenia_nsr10_vs_ais/resultados_clave.md).

## Qué hace

- **Análisis del pórtico:** método matricial de rigidez con deformación axial, inercia sin reducir o fisurada, apoyos empotrados, articulados o personalizados, cargas distribuidas, peso propio y cargas en nudos.
- **Análisis sísmico NSR-10:** espectro de diseño, período de Rayleigh con el límite Cu·Ta, fuerzas horizontales equivalentes, derivas de piso e índice de estabilidad.
- **Resultados:** tablas por piso, fuerzas por elemento, reacciones, gráficas y reporte en Excel.

## Validación

| Comprobación | Casos | Diferencia máxima |
|---|---|---|
| ETABS 22.6: desplazamientos, giros, N, V, M | 12 comparaciones en 3 pórticos, inercia sin reducir y fisurada | 4×10⁻¹¹ % |
| OpenSees 3.8: mismas magnitudes, fuerzas con signo | 40 corridas en 4 pórticos | menos de 10⁻⁵ % |
| PyNite: mismas magnitudes, fuerzas en valor absoluto | 40 corridas en 4 pórticos | menos de 10⁻⁵ % |
| Período de Rayleigh contra primer modo | OpenSees, 8 casos; ETABS, 6 casos | 0.062 % |

Rayleigh es un método aproximado: en pórticos de 10 pisos, su diferencia con el primer modo llega a 0.14 %.

Las pruebas también demuestran que pueden fallar: detectan 16 de 16 errores inyectados a propósito. ETABS recibió las fuerzas por piso calculadas por ROCKFRAME, así que confirma la respuesta estructural; pesos, espectro y fuerzas se comprueban contra cálculos manuales con las ecuaciones de la NSR-10. Las comparaciones usaron modelos equivalentes: sin deformación por cortante, zonas rígidas, diafragma rígido ni P-Delta.

Para repetir las comprobaciones desde una copia de este repositorio:

```bash
pip install -r requirements.txt -r requirements-dev.txt
python -m pytest tests -q
python validation/inject_errors.py
```

OpenSeesPy necesita Python 3.12; en otras versiones sus 24 pruebas se omiten. [`validation/`](validation/) tiene los scripts de comparación, y ETABS requiere su propia licencia.

## Limitaciones

- Solo pórticos planos: sin torsión, irregularidades ni dirección ortogonal.
- Análisis elástico lineal. P-Delta se avisa con el índice de estabilidad, pero no se incluye en las derivas.
- Las secciones son iguales en todos los pisos.
- Fa y Fv son datos de entrada y no se validan contra las tablas de la NSR-10.
- Las ecuaciones de la NSR-10 se tomaron del texto del Decreto 926 de 2010.

## Aviso

ROCKFRAME es una herramienta de investigación y educación. No reemplaza el criterio de un ingeniero con matrícula y no debe ser la única base para diseñar una estructura real. Los resultados se entregan sin garantía.

## Autores

Juan Camilo Buitrago Hurtado y Diego Martínez Pineda (director del proyecto), Semillero de Estructuras GEMA, Universidad de La Sabana. Desarrollado con ayuda de ChatGPT y Claude Code. Para citarlo, consulta [`CITATION.cff`](CITATION.cff).

## Licencia

ROCKFRAME se distribuye con la licencia [MIT](LICENSE).
