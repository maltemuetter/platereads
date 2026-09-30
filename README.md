# platereads

Read and analyse data from microtiter plate readers (Tecan Infinite).

The package loads plate-reader exports (`.xml` or `.xlsx`), maps each well to
the experimental layout, and evaluates the measurements: optical density,
luminescence and fluorescence.

## What it does

- **Load data**: `Plate` reads all export files of one plate and merges them
  into a single table.
- **Add the plate layout**: `Setup` reads an Excel sheet that describes what is
  in each well (e.g. drug, concentration, controls).
- **Normalise**: luminescence and fluorescence are corrected with nearby
  control wells.
- **Fit growth rates**: `CurveFit` estimates growth rates from the time series.
- **Dose-response**: `PharmacoDynamicCurves` fits pharmacodynamic (Hill-type)
  curves across concentrations.
- **MIC tests**: `MicTest` determines minimum inhibitory concentrations.
- **Plot**: `PlateViewer` draws a plate map.

## Installation

```bash
git clone https://github.com/maltemuetter/platereads.git
pip install -r platereads/requirements.txt
```

Put the folder that contains `platereads/` on your Python path, then:

```python
from platereads import Plate

plate = Plate(identifier="exp1", filetype=".xml", path="data/")
plate.add_setup("setup.xlsx")
```

## Context

Written during my PhD at ETH Zurich to evaluate high-throughput antibiotic
experiments run on an automated liquid-handling platform.
