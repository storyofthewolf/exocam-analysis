# CLAUDE.md — ExoCAM Analysis Package

## Project purpose

Python analysis package for small batches of CESM/ExoCAM equilibrium climate model output
(netCDF files). Computes global mean diagnostics, vertical profiles, and 2D spatial plots.
Designed for exoplanet climate science, including support for tidally locked planets
(substellar/antistellar hemisphere means) and non-Earth atmospheric compositions (custom
gravity and dry air molecular weight).

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

- **`contour.py`** — Three new plot types for 2D spatial data:
  - `map_latlon`: lon×lat filled contour map. Source: `Diagnostics.fields_2d[var]`
    or a pressure-level slice of `fields_3d[var]`.
  - `section_latpres`: lat×pressure cross-section with zonal mean option.
    Source: `Diagnostics.fields_3d[var]`, averaged over longitude.
  - `section_lonpres`: lon×pressure cross-section at a specified latitude (default:
    equator). Particularly useful for tidally locked exoplanets.
  All three use `contourf` + `contour` overlay with a right-side colorbar.
  Fields must be explicitly listed in `cache_fields` in the YAML config (on-demand).

### Driver scripts updated

- **`run_analysis.py`** — Thinned to ~160 lines. All original CLI flags retained.
  New flags: `--config`, `--save-cache`, `--save-fields-2d`, `--save-fields-3d`.
  Supports three input modes: `--filename`, `files.in`, or YAML config.
  Inline plot generation driven by YAML `plots:` list; defaults to `vert_1x3` when
  `--vert` is set without a config.

- **`make_plot.py`** — Rewritten as a config-driven cache-replay script. Loads a
  Diagnostics pickle and runs any plots defined in the YAML `plots:` list. No netCDF
  re-reading. Default behavior (no config): runs `vert_1x3` if profiles are in cache.

- **`analysis_utils.py`** — Removed `calc_gmean_profiles` and `exocampy_tools` import.
  `print_data_to_file` updated to accept `list[Diagnostics]` instead of `datacube`.
  Added `print_diagnostics()` for formatted screen output.

### Files deleted
- `exocampy_tools.py` (functions absorbed into `core/coords.py`)
- `plotting.py` (superseded by `plots/vertical.py`)

---

## Architecture overview

```
analysis/
├── core/
│   ├── data_model.py   # Diagnostics, VerticalProfile dataclasses
│   ├── coords.py       # hybrid2pressure, hybrid2height (vectorized),
│   │                   # area_weighted_avg (vectorized), calc_gmean_profiles
│   ├── reader.py       # netCDF → raw dict
│   ├── compute.py      # raw dict → Diagnostics; tprofile_diags
│   └── cache.py        # pickle save/load
├── plots/
│   ├── base.py         # abstract Plot + setup_pressure_axis, get_colors, get_labels
│   ├── registry.py     # @register_plot decorator, get_plot(), list_plots()
│   ├── vertical.py     # vert_1x3, vert_2x2
│   └── contour.py      # map_latlon, section_latpres, section_lonpres
├── configs/
│   └── example.yaml    # fully annotated YAML template
├── analysis_utils.py   # read_file_list, print_diagnostics, print_data_to_file
├── run_analysis.py     # main driver
└── make_plot.py        # cache-replay entry point
```

### Key data flow

```
files.in / --filename / YAML
        │
        ▼
core/reader.py           read_ncfile() → raw dict
        │
        ▼
core/compute.py          compute_all(raw, label, options) → Diagnostics
        │
        ├── analysis_utils.print_diagnostics()   → screen
        ├── analysis_utils.print_data_to_file()  → analysis_output.txt
        ├── core/cache.save()                    → diagnostics.pkl
        └── plots/*.render()                     → PNG files
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
- [ ] Run `python run_analysis.py --vert --cf --synch` on a known file and compare
      screen output numerically against the pre-refactor version (global means should
      match to floating-point precision)
- [ ] Verify `--printdata` produces `analysis_output.txt` with correct column alignment
      and values
- [ ] Check `Q_STRAT` in output file uses scientific notation; all others use fixed

### Vectorization correctness
- [ ] Compare `hybrid2height` output against the old triple-loop version on the same
      input — lev_Z and ilev_Z arrays should be numerically identical
- [ ] Compare `area_weighted_avg` against the old double-loop version — results should
      match to floating-point precision for a standard 2D ExoCAM field

### Cache round-trip
- [ ] Run with `--save-cache diagnostics.pkl`, load in a Python session, verify
      `global_means` values and `profile` arrays are intact
- [ ] Run `make_plot.py --cache diagnostics.pkl` and confirm `vert_profiles.png` is
      reproduced correctly

### Contour plots
- [ ] Run with `--save-fields-2d TS,CLDTOT --save-fields-3d T,Q` and confirm fields
      land in `diagnostics.pkl` under `Diagnostics.fields_2d` / `fields_3d`
- [ ] Run `map_latlon` for `TS` — verify lon×lat orientation is correct (not transposed),
      colorbar is present, output PNG is saved
- [ ] Run `section_latpres` for `T` with `zonal_mean: true` — verify lat axis goes
      -90 to 90, pressure axis is log-scale and inverted (TOA at top)
- [ ] Run `section_lonpres` for `T` at `lat_deg: 0.0` — verify equatorial slice is
      correct, especially for a tidally locked simulation (substellar point should be
      near lon 180° or wherever FDS peaks)
- [ ] Test `map_latlon` on a 3D variable with `lev_index` set — verify correct level
      is sliced

### YAML config mode
- [ ] Run `python run_analysis.py --config configs/example.yaml` (after editing root/files)
      end-to-end: reads files, computes, saves cache, generates all listed plots
- [ ] Run `python make_plot.py --cache diagnostics.pkl --config configs/example.yaml`
      and confirm all plot specs execute

### Edge cases
- [ ] Single file with non-Earth gravity: `--filename foo.nc --grav 9.8 --mwdry 44.01`
- [ ] File without `FSDTOA` variable (optional field) — should skip silently
- [ ] `make_plot.py` with a cache that has no profiles (no `--vert`) but requests
      `vert_1x3` — should skip with a clear message
- [ ] `get_plot('unknown_type')` — should raise `ValueError` listing available types

---

## External dependencies to be aware of

- `netCDF4` — reads `.nc` files; ExoCAM output uses CESM/CAM conventions
- `numpy`, `matplotlib` — core scientific stack
- `pyyaml` — YAML config parsing (optional unless using `--config`)
- No longer depends on `exocampy_tools` from the ExoCAM repository
