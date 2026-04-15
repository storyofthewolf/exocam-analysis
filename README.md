# exocam_analysis

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

### Batch from YAML study config
```bash
python run_analysis.py --config configs/study.yaml [options]
```

### Replay plots from saved cache (no netCDF re-reading)
```bash
# YAML-driven
python make_plot.py --cache data/diagnostics.pkl --config configs/study.yaml

# CLI-driven (no YAML needed)
python make_plot.py --cache data/diagnostics.pkl --type map_latlon --var TS
python make_plot.py --cache data/diagnostics.pkl --type latpres --var T
python make_plot.py --cache data/diagnostics.pkl --type latpres --var T --lon 180.0
python make_plot.py --cache data/diagnostics.pkl --type lonpres --var T --lat 0.0 --sim 1
python make_plot.py --cache data/diagnostics.pkl          # default: vert_1x3
```

### Inspect a cache file
```bash
python inspect_cache.py                          # reads data/diagnostics.pkl
python inspect_cache.py data/my_study.pkl
python inspect_cache.py data/my_study.pkl --sim 2
python inspect_cache.py --values                 # include actual global mean values
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
| `--filename PATH` | single netCDF file (overrides `--config`) |
| `--grav VALUE` | gravity for `--filename` mode (default: 9.81 m/s²) |
| `--mwdry VALUE` | dry air molecular weight for `--filename` mode (default: 28.966 g/mol) |
| `--config PATH` | YAML study configuration file |
| `--save-cache PATH` | save Diagnostics cache to pickle file |
| `--save-fields-2d VARS` | comma-separated 2D field names to cache for contour plots |
| `--save-fields-3d VARS` | comma-separated 3D field names to cache for contour plots |

## YAML study config format
See `configs/example.yaml` for a fully annotated template.

```yaml
root: /path/to/data/
files:
  - modern_earth.cam.h0.avg.nc
  - trappist1e.cam.h0.avg.nc
  # non-Earth gravity/mwdry — requires name: key
  - name: venus_run.cam.h0.avg.nc
    grav: 8.87
    mwdry: 43.45
options:
  vert: true
  synch: false
  cf: false
cache:
  save: data/diagnostics.pkl
  fields_2d: [TS, CLDTOT]
  fields_3d: [T, Q]
plots:
  - type: vert_1x3
    output: results/profiles.png
  - type: lonpres
    var: T
    sim_index: 1
    lat_deg: 0.0
    output: results/equator_T.png
```

## Plot types

| Type | Description |
|------|-------------|
| `vert_1x3` | 1×3 panel: Temperature, Water Vapor, Lapse Rate profiles |
| `vert_2x2` | 2×2 panel: two groups of profiles (T and Q columns) |
| `map_latlon` | lon×lat filled contour map of a 2D (or level-sliced 3D) field |
| `latpres` | lat×pressure cross-section; zonal mean by default, or lon slice via `lon_deg` |
| `lonpres` | lon×pressure cross-section at a specified latitude (`lat_deg`, default 0°) |

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
  base.py         Abstract Plot class + save_figure + shared axis helpers
  registry.py     @register_plot decorator + get_plot() factory
  vertical.py     vert_1x3, vert_2x2
  contour.py      map_latlon, latpres, lonpres

configs/          Per-study YAML configuration files
data/             Default output directory for .pkl cache files
results/          Default output directory for .png plot files
analysis_utils.py Screen/file output utilities
run_analysis.py   Main driver (thin orchestrator)
make_plot.py      Cache-replay / CLI plotting entry point
inspect_cache.py  Standalone cache metadata utility
```

## Notes
- [April 15, 2026] `make_plot.py` CLI plot mode; `latpres`/`lonpres` type renames; `files.in` mode removed; output directories (`data/`, `results/`); coordinate-encoded default filenames; `inspect_cache.py` utility; YAML `name:` key required for per-file grav/mwdry; `cache.load()` sys.path fix.
- [April 14, 2026] Major refactor: modular core/ and plots/ packages, YAML config, 3 new contour plot types, vectorized coordinate utilities, Diagnostics cache system. `exocampy_tools.py` dependency removed.
- [March 23, 2026] Added global mean vertical profile plotting
