# ROCKFRAME

[Español](README.es.md)

ROCKFRAME is a free Python program for the analysis of plane reinforced concrete frames with seismic checks under the Colombian code NSR-10.

![Seismic results](docs/img/results.png)

## Install

1. Install [Python 3.10 or later](https://www.python.org/downloads/). On Windows, check **Add python.exe to PATH**.
2. Install [Git](https://git-scm.com/downloads).
3. Open a terminal and run:

```bash
pip install git+https://github.com/Juankamiloh/RockFrame.git
```

## Run

```bash
rockframe
```

If the command is not found, use `python -m rockframe`. Press **Ejemplo** and then **Calcular** to run a 3-bay, 6-story frame. The interface is in Spanish.

## What it does

- **Frame analysis:** matrix stiffness method with axial deformation, gross or cracked inertia, fixed, pinned or custom supports, distributed loads, self-weight and nodal loads.
- **NSR-10 seismic analysis:** design spectrum, Rayleigh period with the Cu·Ta limit, equivalent lateral forces, story drifts and stability index.
- **Results:** tables per story, element forces, reactions, charts and an Excel report.

## Validation

| Check | Cases | Largest difference |
|---|---|---|
| ETABS 22.6: displacements, rotations, N, V, M | 12 comparisons on 3 frames, gross and cracked | 4×10⁻¹¹ % |
| OpenSees 3.8: same quantities, forces with sign | 40 runs on 4 frames | below 10⁻⁵ % |
| PyNite: same quantities, forces in magnitude | 40 runs on 4 frames | below 10⁻⁵ % |
| Rayleigh period against the first mode | OpenSees, 8 cases; ETABS, 6 cases | 0.062 % |

Rayleigh is an approximate method: in 10-story frames, its difference from the first mode reaches 0.14 %.

The test suite also has to prove it can fail: it detects 16 out of 16 deliberately injected errors. ETABS received the story forces computed by ROCKFRAME, so it confirms the structural response; weights, spectral values and story forces are checked against hand calculations from the NSR-10 equations. Comparisons used matching models: no shear deformation, rigid end zones, rigid diaphragm or P-Delta.

To repeat the checks from a copy of this repository:

```bash
pip install -r requirements.txt -r requirements-dev.txt
python -m pytest tests -q
python validation/inject_errors.py
```

OpenSeesPy needs Python 3.12; on other versions its 24 tests are skipped. [`validation/`](validation/) holds the comparison scripts, and ETABS requires its own license.

## Limitations

- Plane frames only: no torsion, irregularity checks or orthogonal direction.
- Linear elastic analysis. P-Delta is flagged through the stability index but not included in drifts.
- Sections are uniform along the height.
- Fa and Fv are user inputs and are not validated against the NSR-10 tables.
- The NSR-10 equations were read from the text of Decree 926 of 2010.

## Disclaimer

ROCKFRAME is a research and educational tool. It does not replace the judgment of a licensed engineer and must not be the sole basis for the design of a real structure. Results are provided without warranty.

## Authors

Juan Camilo Buitrago Hurtado and Diego Martínez Pineda (project director), GEMA structures research group, Universidad de La Sabana. Developed with the help of ChatGPT and Claude Code. To cite it, see [`CITATION.cff`](CITATION.cff).
