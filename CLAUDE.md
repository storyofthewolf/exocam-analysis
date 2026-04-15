# CLAUDE.md — ExoCAM Analysis Package

## Project purpose

Python analysis package for small batches of CESM/ExoCAM equilibrium climate model output
(netCDF files). Computes global mean diagnostics, vertical profiles, and 2D spatial plots.
Designed for exoplanet climate science, including support for tidally locked planets
(substellar/antistellar hemisphere means) and non-Earth atmospheric compositions (custom
gravity and dry air molecular weight).

---

## What was accomplished (April 15, 2026)

### `make_plot.py` CLI plot mode

`make_plot.py` was previously config-only. A full CLI plot mode was added via `--type`,
allowing any plot type to be driven directly from the command line without a YAML file:

```bash
python make_plot.py --cache data/diagnostics.pkl --type map_latlon --var TS
python make_plot.py --cache data/diagnostics.pkl --type latpres --var T --lon 180.0
python make_plot.py --cache data/diagnostics.pkl --type lonpres --var T --sim 1 --lat 0.0
python make_plot.py --cache data/diagnostics.pkl --type vert_2x2 --top 0,1 --bottom 2,3
```

Pre-render validation checks `--sim`, `--var`, `--lev`, `--lat`, and `--lon` against
the loaded cache before any plotting begins, exiting with descriptive messages on error.
`--lat` and `--lon` use nearest-match logic with info/warning lines reporting the actual
grid coordinate used (warning threshold: >5° offset).

### Plot type renames

`section_latpres` → `latpres`, `section_lonpres` → `lonpres` in the plot registry,
YAML configs, CLI, and all documentation. `latpres` now accepts `lon_deg` for a
longitude slice; omitting it gives the zonal mean (default).

### `files.in` mode removed

Single-file (`--filename`) and YAML (`--config`) are the only supported input modes.
`read_file_list()` removed from `analysis_utils.py`. Running without either flag exits
with a clear error.

### Output directory structure

All outputs are now written to subdirectories rather than the project root:

| Output | Default path |
|--------|-------------|
| Diagnostics cache | `data/diagnostics.pkl` |
| All plot types | `results/<filename>.png` |

Directories are created automatically (`os.makedirs(..., exist_ok=True)`). A shared
`save_figure(fig, outfile)` helper in `plots/base.py` handles directory creation and
`plt.close()` for all plot types. `cache.save()` handles directory creation for `.pkl`.
Explicit `output:` paths in YAML or `--output` on the CLI go wherever specified, with
their parent directories created as needed.

### Default filename conventions

Plot filenames now encode the relevant coordinate:

| Plot | Example default filename |
|------|--------------------------|
| `map_latlon` (2D var) | `results/TS_map.png` |
| `map_latlon` (3D var) | `results/T_map_lev5_532.3hPa.png` |
| `latpres` (zonal mean) | `results/T_latpres_zonalavg.png` |
| `latpres` (lon slice) | `results/T_latpres_lon180.0.png` |
| `lonpres` | `results/T_lonpres_lat0.0.png` |

For `map_latlon` on 3D variables, the pressure level in hPa also appears in the plot title.
For `latpres` lon slices and `lonpres`, the actual grid-snapped coordinate is used in
both the filename and title.

### `inspect_cache.py` utility

New standalone script that prints metadata for a Diagnostics `.pkl` file without
re-reading any netCDF:

```bash
python inspect_cache.py                        # reads data/diagnostics.pkl
python inspect_cache.py data/my_study.pkl
python inspect_cache.py data/my_study.pkl --sim 2
python inspect_cache.py --values               # print actual global mean values
```

Output includes: simulation labels, coordinate grids (lon/lat/lev ranges), global mean
variable list, vertical profile presence and ranges, synch mean variable list, and
cached 2D/3D field names with shapes and value ranges.

### YAML dict-entry fix (`name:` key required)

When specifying per-file `grav`/`mwdry` in a YAML config, the filename must use the
`name:` key. Plain strings and dict entries cannot be mixed in the same list item:

```yaml
# correct
files:
  - name: simulation.cam.h0.avg.nc
    grav: 9.12
    mwdry: 28.0
  - plain_earth.cam.h0.avg.nc   # plain string still works when no grav/mwdry needed
```

### `core/cache.py` sys.path fix

`cache.load()` now inserts the package root onto `sys.path` before unpickling, so
`core.data_model` classes resolve correctly when loading from scripts in any directory.

---

## What was accomplished (April 14, 2026)

### Architecture refactor

The original codebase was a 627-line monolith (`run_analysis.py`) mixing netCDF I/O,
computation, and output. It was restructured into a clean pipeline:

```
netCDF → core/reader.py → core/compute.py → Diagnostics → core/cache.py → plots/
```

### `core/` package (new)

- **`data_model.py`** — `Diagnostics` and `VerticalProfile` dataclasses. The old rigid
  `datacube` (50-row numpy array + parallel `varnames` list) is replaced by
  `Diagnostics.global_means: dict[str, float]`. Adding a diagnostic is now just adding
  a dict key.

- **`coords.py`** — Absorbs all coordinate utilities previously imported from the external
  `exocampy_tools` package. Two functions were vectorized:
  - `hybrid2height`: triple Python loop (O(nlev × nlat × nlon) iterations) replaced with
    `np.cumsum` on the flipped delta-Z array — zero Python loops.
  - `area_weighted_avg`: double Python loop replaced with a 2D outer-product area array
    and masked `np.sum` — zero Python loops. Also fixed a latent bug in
    `calc_gmean_profiles` (called `exo.area_weighted_avg` which only worked when imported
    as a module alias).
  - `exocampy_tools.py` is deleted; `exocampy_tools` is no longer an external dependency.

- **`reader.py`** — Pure netCDF extraction; no computation. Returns a raw dict of arrays.
  Handles on-demand caching of 2D/3D fields for downstream contour plots.

- **`compute.py`** — All derived quantities. Synch hemisphere masking and cloud forcing
  computation are vectorized with `np.where`. `tprofile_diags` moved here from
  `analysis_utils.py`. Main entry point: `compute_all(raw, label, options) → Diagnostics`.

- **`cache.py`** — Pickle save/load for `list[Diagnostics]`. The cache is the hand-off
  between expensive netCDF processing and fast downstream plotting/bespoke scripts.

### `plots/` package (new)

- **`registry.py`** — `@register_plot('name')` decorator and `get_plot('name')` factory.
  Adding a new plot type = drop a new file with a decorated class; no edits to existing code.

- **`vertical.py`** — `vert_1x3` and `vert_2x2` refactored from `plotting.py`
  (now deleted). Uses `VerticalProfile` objects from `Diagnostics.profile`.

- **`contour.py`** — Three plot types for 2D spatial data:
  - `map_latlon`: lon×lat filled contour map. Source: `Diagnostics.fields_2d[var]`
    or a pressure-level slice of `fields_3d[var]`. For 3D variables, level index and
    pressure in hPa are appended to the default filename and shown in the plot title.
  - `latpres`: lat×pressure cross-section. Default: zonal mean. If `lon_deg` is
    provided, slices at the nearest grid longitude instead. Source: `fields_3d[var]`.
  - `lonpres`: lon×pressure cross-section at a specified latitude (`lat_deg`, default
    0° = equator). Particularly useful for tidally locked exoplanets.
  All three use `contourf` + `contour` overlay with a right-side colorbar.
  Default filenames encode the relevant coordinate (e.g. `T_latpres_zonalavg.png`,
  `T_latpres_lon180.0.png`, `T_lonpres_lat0.0.png`).
  Fields must be explicitly listed in `cache_fields` in the YAML config (on-demand).

### Driver scripts updated

- **`run_analysis.py`** — Thin orchestrator. All original CLI flags retained.
  New flags: `--config`, `--save-cache`, `--save-fields-2d`, `--save-fields-3d`.
  Supports two input modes: `--filename` (single file) or `--config` (YAML batch).
  `files.in` mode removed — use YAML configs for batch runs.
  Exits with a clear error if neither `--filename` nor `--config` is provided.
  Inline plot generation driven by YAML `plots:` list; defaults to `vert_1x3` when
  `--vert` is set without a config.

- **`make_plot.py`** — Cache-replay entry point. Supports two modes:
  - `--config`: YAML-driven, runs all plots listed in the config.
  - `--type`: CLI-driven single plot; flags `--var`, `--sim`, `--lev`, `--lat`, `--lon`
    control what to plot. Validates all arguments against the cache before rendering,
    with descriptive error messages and nearest-match warnings for `--lat` and `--lon`.
  Default (no config, no type): runs `vert_1x3` if profiles are in cache.

- **`analysis_utils.py`** — `read_file_list` removed (files.in mode dropped).
  `print_data_to_file` accepts `list[Diagnostics]`. `print_diagnostics()` for screen output.

- **`core/cache.py`** — `load()` inserts the package root onto `sys.path` so the
  `core.data_model` classes resolve correctly when loading from scripts outside the
  project directory.

### Files deleted
- `exocampy_tools.py` (functions absorbed into `core/coords.py`)
- `plotting.py` (superseded by `plots/vertical.py`)

---

## Architecture overview

```
exocam_analysis/
├── core/
│   ├── data_model.py   # Diagnostics, VerticalProfile dataclasses
│   ├── coords.py       # hybrid2pressure, hybrid2height (vectorized),
│   │                   # area_weighted_avg (vectorized), calc_gmean_profiles
│   ├── reader.py       # netCDF → raw dict
│   ├── compute.py      # raw dict → Diagnostics; tprofile_diags
│   └── cache.py        # pickle save/load; sys.path fix for external scripts
├── plots/
│   ├── base.py         # abstract Plot + save_figure, setup_pressure_axis,
│   │                   # get_colors, get_labels
│   ├── registry.py     # @register_plot decorator, get_plot(), list_plots()
│   ├── vertical.py     # vert_1x3, vert_2x2
│   └── contour.py      # map_latlon, latpres, lonpres
├── configs/
│   └── example.yaml    # fully annotated YAML template
├── data/               # default output directory for .pkl cache files
├── results/            # default output directory for .png plot files
├── analysis_utils.py   # print_diagnostics, print_data_to_file
├── run_analysis.py     # main driver
├── make_plot.py        # cache-replay / CLI plotting entry point
└── inspect_cache.py    # standalone cache metadata utility
```

### Key data flow

```
--filename / --config (YAML)
        │
        ▼
core/reader.py           read_ncfile() → raw dict
        │
        ▼
core/compute.py          compute_all(raw, label, options) → Diagnostics
        │
        ├── analysis_utils.print_diagnostics()   → screen
        ├── analysis_utils.print_data_to_file()  → analysis_output.txt
        ├── core/cache.save()                    → data/diagnostics.pkl
        └── plots/*.render()                     → results/*.png
                                                        ▲
                                              make_plot.py loads pkl
                                              and re-runs plots without
                                              re-reading netCDF
```

### `Diagnostics` object fields

| Field | Type | Contents |
|-------|------|----------|
| `label` | str | simulation short name |
| `coords` | dict | lon, lat, lev, Pmid (mean pressure profile, Pa) |
| `global_means` | dict[str, float] | all scalar diagnostics |
| `profile` | VerticalProfile \| None | global mean profiles (if `--vert`) |
| `synch_means` | dict \| None | substellar/antistellar means (if `--synch`) |
| `fields_2d` | dict[str, ndarray] | on-demand (nlat, nlon) arrays for contour plots |
| `fields_3d` | dict[str, ndarray] | on-demand (nlev, nlat, nlon) arrays for contour plots |

### On-demand field caching

`fields_2d` and `fields_3d` are only populated when explicitly requested via
`cache_fields` in the YAML config or `--save-fields-2d/3d` on the CLI. The cache is
the hand-off point to bespoke publication-quality scripts — load `diagnostics.pkl`
directly in any standalone script to access the arrays without re-reading netCDF.

---

## What should be tested next

### Regression / correctness
- [x] Run `python run_analysis.py --vert --cf --synch` on a known file and compare
      screen output numerically against the pre-refactor version (global means should
      match to floating-point precision)
- [x] Verify `--printdata` produces `analysis_output.txt` with correct column alignment
      and values
- [x] Check `Q_STRAT` in output file uses scientific notation; all others use fixed

### Vectorization correctness
- [x] Compare `hybrid2height` output against the old triple-loop version on the same
      input — lev_Z and ilev_Z arrays should be numerically identical
- [x] Compare `area_weighted_avg` against the old double-loop version — results should
      match to floating-point precision for a standard 2D ExoCAM field

### Cache round-trip
- [x] Run with `--save-cache diagnostics.pkl`, load in a Python session, verify
      `global_means` values and `profile` arrays are intact
- [x] Run `make_plot.py --cache diagnostics.pkl` and confirm `vert_profiles.png` is
      reproduced correctly

### Contour plots
- [x]] Run with `--save-fields-2d TS,CLDTOT --save-fields-3d T,Q` and confirm fields
      land in `diagnostics.pkl` under `Diagnostics.fields_2d` / `fields_3d`
- [x] Run `map_latlon` for `TS` — verify lon×lat orientation is correct (not transposed),
      colorbar is present, output PNG is saved
- [x] Run `section_latpres` for `T` with `zonal_mean: true` — verify lat axis goes
      -90 to 90, pressure axis is log-scale and inverted (TOA at top)
- [x] Run `section_lonpres` for `T` at `lat_deg: 0.0` — verify equatorial slice is
      correct, especially for a tidally locked simulation (substellar point should be
      near lon 180° or wherever FDS peaks)
- [x] Test `map_latlon` on a 3D variable with `lev_index` set — verify correct level
      is sliced

### YAML config mode
- [x] Run `python run_analysis.py --config configs/example.yaml` (after editing root/files)
      end-to-end: reads files, computes, saves cache, generates all listed plots
- [x] Run `python make_plot.py --cache diagnostics.pkl --config configs/example.yaml`
      and confirm all plot specs execute

### Edge cases
- [ ] Single file with non-Earth gravity: `--filename foo.nc --grav 9.8 --mwdry 44.01`
- [ ] File without `FSDTOA` variable (optional field) — should skip silently
- [ ] `make_plot.py` with a cache that has no profiles (no `--vert`) but requests
      `vert_1x3` — should skip with a clear message
- [ ] `get_plot('unknown_type')` — should raise `ValueError` listing available types
- [ ] `make_plot.py --type latpres --var BADVAR` — should exit with cached field list
- [ ] `make_plot.py --type lonpres --lat 999` — should warn about poor nearest-match
- [ ] YAML with `name:`/`grav:`/`mwdry:` dict entries — confirmed working (thai.yaml)

---

## External dependencies to be aware of

- `netCDF4` — reads `.nc` files; ExoCAM output uses CESM/CAM conventions
- `numpy`, `matplotlib` — core scientific stack
- `pyyaml` — YAML config parsing (optional unless using `--config`)
- No longer depends on `exocampy_tools` from the ExoCAM repository
