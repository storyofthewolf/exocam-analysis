# analysis

Analysis of small batches of CESM/ExoCAM equilibrium climate simulations.
For timeseries analysis see the `trend` package.
https://github.com/storyofthewolf/trend

## Dependencies

- `netCDF4`, `numpy`, `matplotlib`
- `pyyaml` (required for `--config` / YAML study mode)
- `exocampy_tools` is **no longer required** — coordinate utilities are now bundled in `core/coords.py`

## Usage

### Single file (quick inspection)
```bash
python run_analysis.py --filename /path/to/file.nc [options]
python run_analysis.py --filename /path/to/file.nc --grav 9.8 --mwdry 44.01
```

### Batch from `files.in`
```bash
python run_analysis.py [options]
```

### Batch from YAML study config
```bash
python run_analysis.py --config configs/study.yaml [options]
```

### Replay plots from saved cache (no netCDF re-reading)
```bash
python make_plot.py --cache diagnostics.pkl --config configs/study.yaml
python make_plot.py --cache diagnostics.pkl          # default: vert_1x3
```

## CLI Options

| Option | Description |
|--------|-------------|
| `--quiet` | suppress per-file diagnostic output to screen |
| `--printdata` | write global means to `analysis_output.txt` |
| `--vert` | compute vertical profiles (slow; enables vert plot types) |
| `--synch` | compute substellar/antistellar hemisphere means |
| `--cf` | compute clear-sky fluxes and cloud radiative effect |
| `--nostrout` | omit simulation names from output text file |
| `--filename PATH` | single netCDF file (overrides `files.in` and `--config`) |
| `--grav VALUE` | gravity for `--filename` mode (default: 9.81 m/s²) |
| `--mwdry VALUE` | dry air molecular weight for `--filename` mode (default: 28.966 g/mol) |
| `--config PATH` | YAML study configuration file |
| `--save-cache PATH` | save Diagnostics cache to pickle file |
| `--save-fields-2d VARS` | comma-separated 2D field names to cache for contour plots |
| `--save-fields-3d VARS` | comma-separated 3D field names to cache for contour plots |

## `files.in` format
```
/path/to/data/root
8
filename1.cam.h0.avg.nc
filename2.cam.h0.avg.nc [grav] [mwdry]
...
```

## YAML study config format
See `configs/example.yaml` for a fully annotated template.

```yaml
root: /path/to/data/
files:
  - modern_earth.cam.h0.avg.nc
  - trappist1e.cam.h0.avg.nc
options:
  vert: true
  synch: false
  cf: false
cache:
  save: diagnostics.pkl
  fields_2d: [TS, CLDTOT]
  fields_3d: [T, Q]
plots:
  - type: vert_1x3
    output: profiles.png
  - type: section_lonpres
    var: T
    sim_index: 1
    lat_deg: 0.0
    output: equator_T.png
```

## Plot types

| Type | Description |
|------|-------------|
| `vert_1x3` | 1×3 panel: Temperature, Water Vapor, Lapse Rate profiles |
| `vert_2x2` | 2×2 panel: two groups of profiles (T and Q columns) |
| `map_latlon` | lon×lat filled contour map of a 2D (or level-sliced 3D) field |
| `section_latpres` | lat×pressure zonal mean cross-section of a 3D field |
| `section_lonpres` | lon×pressure cross-section at a specified latitude |

## Architecture

```
core/
  data_model.py   Diagnostics and VerticalProfile dataclasses
  coords.py       Coordinate utilities (hybrid2pressure, hybrid2height,
                  area_weighted_avg, calc_gmean_profiles) — vectorized
  reader.py       Pure netCDF extraction → raw dict
  compute.py      All derived quantities → Diagnostics
  cache.py        Pickle save/load for Diagnostics lists

plots/
  base.py         Abstract Plot class + shared axis helpers
  registry.py     @register_plot decorator + get_plot() factory
  vertical.py     vert_1x3, vert_2x2
  contour.py      map_latlon, section_latpres, section_lonpres

configs/          Per-study YAML configuration files
analysis_utils.py File list parsing, screen/file output
run_analysis.py   Main driver (thin orchestrator)
make_plot.py      Cache-replay plotting entry point
```

## Notes
- [April 14, 2026] Major refactor: modular core/ and plots/ packages, YAML config, 3 new contour plot types, vectorized coordinate utilities, Diagnostics cache system. `exocampy_tools.py` dependency removed.
- [March 23, 2026] Added global mean vertical profile plotting
