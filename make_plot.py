#!/usr/bin/env python

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# make_plot.py
#
# Config-driven or CLI-driven plot replay from a saved Diagnostics cache.
# Loads diagnostics.pkl (or a specified cache file) and reruns plots
# defined in a YAML config or via command line flags — no netCDF re-reading.
#
# Usage:
#   python make_plot.py --cache diagnostics.pkl --config configs/study.yaml
#   python make_plot.py --cache diagnostics.pkl                   # default vert_1x3
#   python make_plot.py --cache diagnostics.pkl --type map_latlon --var TS
#   python make_plot.py --cache diagnostics.pkl --type section_latpres --var T --sim 1
#   python make_plot.py --cache diagnostics.pkl --type section_lonpres --var T --lat 0.0
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

import sys
import argparse

from core import cache as cache_io
# Import plot modules to trigger @register_plot decorators
import plots.vertical   # noqa: F401
import plots.contour    # noqa: F401
from plots.registry import get_plot, list_plots


parser = argparse.ArgumentParser(
    description='Replay plots from a saved Diagnostics cache.',
    formatter_class=argparse.RawDescriptionHelpFormatter,
    epilog="""
CLI plot mode (--type):
  --type map_latlon  --var TS [--sim 0] [--lev 0] [--output map_TS.png]
  --type latpres     --var T  [--sim 0] [--output T_latpres.png]        # zonal mean
  --type latpres     --var T  [--sim 0] [--lon 180.0]                   # lon slice
  --type lonpres     --var T  [--sim 0] [--lat 0.0] [--output T_lonpres.png]
  --type vert_1x3
  --type vert_2x2    [--top 0,1] [--bottom 2,3]
""")
parser.add_argument('--cache',  type=str, default='data/diagnostics.pkl',
                    help='path to Diagnostics cache file (default: data/diagnostics.pkl)')
parser.add_argument('--config', type=str, default=None,
                    help='YAML study config file defining plots to run')
# CLI plot mode
parser.add_argument('--type',   type=str, default=None,
                    help='plot type to run (overrides --config)')
parser.add_argument('--var',    type=str, default=None,
                    help='variable name for contour plots')
parser.add_argument('--sim',    type=int, default=0,
                    help='simulation index (default: 0)')
parser.add_argument('--lev',    type=int, default=0,
                    help='level index for map_latlon on a 3D variable (default: 0)')
parser.add_argument('--lat',    type=float, default=0.0,
                    help='latitude in degrees for lonpres (default: 0.0)')
parser.add_argument('--lon',    type=float, default=None,
                    help='longitude in degrees for latpres slice (omit for zonal mean)')
parser.add_argument('--top',    type=str, default=None,
                    help='comma-separated sim indices for vert_2x2 top row')
parser.add_argument('--bottom', type=str, default=None,
                    help='comma-separated sim indices for vert_2x2 bottom row')
parser.add_argument('--output', type=str, default=None,
                    help='output filename (overrides default)')
args = parser.parse_args()


# Load cache
diagnostics = cache_io.load(args.cache)


# ----------------------------------------------------------------
# CLI argument validation (only in --type mode)
# ----------------------------------------------------------------

def _validate_cli(args, diagnostics):
    """Validate --sim, --var, --lev, --lat, --lon before building the plot spec.
    Exits with a descriptive message on any problem."""
    import numpy as np

    CONTOUR_TYPES = {'map_latlon', 'latpres', 'lonpres'}

    # --sim range check
    if args.sim < 0 or args.sim >= len(diagnostics):
        sys.exit(
            f"error: --sim {args.sim} is out of range. "
            f"Cache contains {len(diagnostics)} simulation(s) "
            f"(valid indices: 0–{len(diagnostics)-1}).")

    diag = diagnostics[args.sim]

    # --var required and present for contour plot types
    if args.type in CONTOUR_TYPES:
        if not args.var:
            sys.exit(f"error: --var is required for plot type '{args.type}'.")

        in_2d = args.var in diag.fields_2d
        in_3d = args.var in diag.fields_3d
        if not in_2d and not in_3d:
            avail_2d = sorted(diag.fields_2d.keys())
            avail_3d = sorted(diag.fields_3d.keys())
            sys.exit(
                f"error: variable '{args.var}' not found in cache for "
                f"simulation '{diag.label}'.\n"
                f"  cached 2D fields: {avail_2d}\n"
                f"  cached 3D fields: {avail_3d}")

        # --lev range check (only meaningful for map_latlon on a 3D variable)
        if args.type == 'map_latlon' and in_3d and not in_2d:
            nlev = diag.fields_3d[args.var].shape[0]
            if args.lev < 0 or args.lev >= nlev:
                sys.exit(
                    f"error: --lev {args.lev} is out of range for '{args.var}' "
                    f"(shape: {diag.fields_3d[args.var].shape}, "
                    f"valid level indices: 0–{nlev-1}).")

        # --lon nearest-match info for latpres (only when a slice is requested)
        if args.type == 'latpres' and args.lon is not None:
            lon = diag.coords['lon']
            lon_idx    = int(np.argmin(np.abs(lon - args.lon)))
            lon_actual = float(lon[lon_idx])
            if abs(lon_actual - args.lon) > 5.0:
                print(f"warning: --lon {args.lon}° has no close match; "
                      f"using nearest grid longitude {lon_actual:.2f}°.")
            else:
                print(f"info: --lon {args.lon}° → nearest grid longitude {lon_actual:.2f}°.")

        # --lat nearest-match info for lonpres
        if args.type == 'lonpres':
            lat = diag.coords['lat']
            lat_idx    = int(np.argmin(np.abs(lat - args.lat)))
            lat_actual = float(lat[lat_idx])
            if abs(lat_actual - args.lat) > 5.0:
                print(f"warning: --lat {args.lat}° has no close match; "
                      f"using nearest grid latitude {lat_actual:.2f}°.")
            else:
                print(f"info: --lat {args.lat}° → nearest grid latitude {lat_actual:.2f}°.")


# ----------------------------------------------------------------
# Build plot spec list
# ----------------------------------------------------------------
plot_specs = []

if args.type is not None:
    _validate_cli(args, diagnostics)
    # CLI mode: build a single spec from flags
    spec = {'type': args.type, 'sim_index': args.sim}
    if args.var:
        spec['var'] = args.var
    if args.output:
        spec['output'] = args.output
    if args.type == 'map_latlon':
        spec['lev_index'] = args.lev
    if args.type == 'latpres' and args.lon is not None:
        spec['lon_deg'] = args.lon
    if args.type == 'lonpres':
        spec['lat_deg'] = args.lat
    if args.type == 'vert_2x2':
        if args.top:
            spec['top']    = [int(i) for i in args.top.split(',')]
        if args.bottom:
            spec['bottom'] = [int(i) for i in args.bottom.split(',')]
    plot_specs = [spec]

elif args.config is not None:
    # YAML config mode
    try:
        import yaml
    except ImportError:
        sys.exit('PyYAML is required for --config: pip install pyyaml')
    with open(args.config, 'r') as f:
        cfg = yaml.safe_load(f)
    plot_specs = cfg.get('plots', [])

if not plot_specs:
    # Default fallback
    if any(d.profile is not None for d in diagnostics):
        print('no plot config provided — running default vert_1x3')
        plot_specs = [{'type': 'vert_1x3', 'output': 'results/vert_profiles.png'}]
    else:
        print('no plot config provided and no vertical profiles in cache.')
        print(f'available plot types: {list_plots()}')
        sys.exit(0)

# ----------------------------------------------------------------
# Run each plot
# ----------------------------------------------------------------
for spec in plot_specs:
    plot_type = spec.get('type')
    if plot_type is None:
        print(f'warning: plot spec missing "type" key, skipping: {spec}')
        continue
    try:
        plotter = get_plot(plot_type)
        plotter.render(diagnostics, spec)
    except Exception as e:
        print(f'warning: plot "{plot_type}" failed: {e}')
