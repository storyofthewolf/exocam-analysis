#!/usr/bin/env python

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# make_plot.py
#
# Config-driven plot replay from a saved Diagnostics cache.
# Loads diagnostics.pkl (or a specified cache file) and reruns plots
# defined in a YAML config — no netCDF re-reading required.
#
# Usage:
#   python make_plot.py --cache diagnostics.pkl --config configs/study.yaml
#   python make_plot.py --cache diagnostics.pkl   # runs vert_1x3 by default
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

import sys
import argparse

from core import cache as cache_io
# Import plot modules to trigger @register_plot decorators
import plots.vertical   # noqa: F401
import plots.contour    # noqa: F401
from plots.registry import get_plot, list_plots


parser = argparse.ArgumentParser(
    description='Replay plots from a saved Diagnostics cache.')
parser.add_argument('--cache',  type=str, default='diagnostics.pkl',
                    help='path to Diagnostics cache file (default: diagnostics.pkl)')
parser.add_argument('--config', type=str, default=None,
                    help='YAML study config file defining plots to run')
args = parser.parse_args()


# Load cache
diagnostics = cache_io.load(args.cache)

# Load plot specs from config (or fall back to default)
plot_specs = []
if args.config is not None:
    try:
        import yaml
    except ImportError:
        sys.exit('PyYAML is required for --config: pip install pyyaml')
    with open(args.config, 'r') as f:
        cfg = yaml.safe_load(f)
    plot_specs = cfg.get('plots', [])

if not plot_specs:
    # Default: vert_1x3 if profiles are available, otherwise list what's in cache
    if any(d.profile is not None for d in diagnostics):
        print('no plot config provided — running default vert_1x3')
        plot_specs = [{'type': 'vert_1x3', 'output': 'vert_profiles.png'}]
    else:
        print('no plot config provided and no vertical profiles in cache.')
        print(f'available plot types: {list_plots()}')
        sys.exit(0)

# Run each plot
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
