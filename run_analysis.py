#!/usr/bin/env python

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# run_analysis.py
#
# Author: Eric Wolf
# June 2023 (refactored 2025)
#
# Purpose: Analysis of a single file or batch of ExoCAM netCDF files.
#          Computes global mean diagnostics, optional vertical profiles,
#          optional cloud forcings, and optional substellar/antistellar means.
#          Results are printed to screen, optionally written to a text file,
#          and cached to disk for downstream plotting.
#
# Usage:
#   # Single file:
#   python run_analysis.py --filename /path/to/file.nc [--vert] [--cf] [--synch]
#
#   # Batch from YAML config:
#   python run_analysis.py --config configs/study.yaml
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

import os
import sys
import argparse
import numpy as np

import analysis_utils
from core import reader, compute, cache
# Import plot modules to trigger @register_plot decorators
import plots.vertical   # noqa: F401
import plots.contour    # noqa: F401
from plots.registry import get_plot


# ================================================================
#  Argument parsing
# ================================================================

parser = argparse.ArgumentParser(
    description='ExoCAM netCDF analysis: global means, profiles, and plots.')
parser.add_argument('--quiet',      action='store_true',
                    help='suppress per-file diagnostic output to screen')
parser.add_argument('--printdata',  action='store_true',
                    help='write global means to analysis_output.txt')
parser.add_argument('--vert',       action='store_true',
                    help='compute vertical profiles (slow)')
parser.add_argument('--synch',      action='store_true',
                    help='compute substellar/antistellar hemisphere means')
parser.add_argument('--cf',         action='store_true',
                    help='compute clear-sky fluxes and cloud radiative effect')
parser.add_argument('--nostrout',   action='store_true',
                    help='omit simulation names from output text file')
parser.add_argument('--filename',   type=str, default=None,
                    help='single netCDF file (overrides --config)')
parser.add_argument('--grav',       type=float, default=9.81,
                    help='gravity for --filename mode (default: 9.81 m/s²)')
parser.add_argument('--mwdry',      type=float, default=28.966,
                    help='dry air molecular weight for --filename mode (default: 28.966 g/mol)')
parser.add_argument('--config',     type=str, default=None,
                    help='YAML study configuration file')
parser.add_argument('--save-cache', type=str, default=None, metavar='PATH',
                    help='save Diagnostics cache to this path (e.g. diagnostics.pkl)')
parser.add_argument('--save-fields-2d', type=str, default=None, metavar='VARS',
                    help='comma-separated 2D field names to cache for contour plots')
parser.add_argument('--save-fields-3d', type=str, default=None, metavar='VARS',
                    help='comma-separated 3D field names to cache for contour plots')

args = parser.parse_args()


# ================================================================
#  Load configuration
# ================================================================

yaml_config  = None
plot_specs   = []
cache_path   = args.save_cache
fields_2d    = [v.strip() for v in args.save_fields_2d.split(',')] \
               if args.save_fields_2d else []
fields_3d    = [v.strip() for v in args.save_fields_3d.split(',')] \
               if args.save_fields_3d else []

if args.config is not None:
    try:
        import yaml
    except ImportError:
        sys.exit('PyYAML is required for --config mode: pip install pyyaml')
    with open(args.config, 'r') as f:
        yaml_config = yaml.safe_load(f)

    # Merge YAML options with CLI flags (CLI takes precedence where both given)
    cfg_opts = yaml_config.get('options', {})
    if not any([args.vert, args.synch, args.cf]):
        args.vert  = cfg_opts.get('vert',  False)
        args.synch = cfg_opts.get('synch', False)
        args.cf    = cfg_opts.get('cf',    False)
    if not args.quiet:
        args.quiet = cfg_opts.get('quiet', False)
    if not args.printdata:
        args.printdata = cfg_opts.get('printdata', False)

    # Cache settings from YAML
    cfg_cache = yaml_config.get('cache', {})
    if cache_path is None:
        cache_path = cfg_cache.get('save', None)
    if not fields_2d:
        fields_2d = cfg_cache.get('fields_2d', [])
    if not fields_3d:
        fields_3d = cfg_cache.get('fields_3d', [])

    plot_specs = yaml_config.get('plots', [])


# ================================================================
#  Build file list
# ================================================================

if args.filename is not None:
    # Single-file CLI mode
    abspath      = os.path.abspath(args.filename)
    root         = os.path.dirname(abspath)
    filelist     = np.array([abspath], dtype='U512')
    short_names  = np.array([os.path.basename(abspath)], dtype=object)
    grav_arr     = np.array([args.grav])
    mwdry_arr    = np.array([args.mwdry])
    num          = 1
    mode_label   = 'file read from --filename'

elif args.config is not None:
    # YAML config batch mode
    root    = yaml_config.get('root', '')
    entries = yaml_config.get('files', [])
    num     = len(entries)
    filelist    = np.empty(num, dtype='U512')
    short_names = np.empty(num, dtype=object)
    grav_arr    = np.full(num, 9.81)
    mwdry_arr   = np.full(num, 28.966)
    for i, entry in enumerate(entries):
        if isinstance(entry, dict):
            name        = entry['name']
            grav_arr[i] = entry.get('grav',  9.81)
            mwdry_arr[i] = entry.get('mwdry', 28.966)
        else:
            name = entry
        short_names[i] = name
        filelist[i]    = os.path.join(root, name) if root else name
    mode_label = f'files read from {args.config}'

else:
    sys.exit('error: either --filename or --config is required.')


# ================================================================
#  Header
# ================================================================

print()
print('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
print('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
print(' Entering run_analysis.py')
print(f' {mode_label}')
if args.vert:
    print(' --vert: computing vertical profiles')
    print('         (ensure gravity and mwdry are set correctly)')
print('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')


# ================================================================
#  Main loop: read → compute → print
# ================================================================

options = {
    'vert':  args.vert,
    'cf':    args.cf,
    'synch': args.synch,
}

all_diagnostics = []

for i in range(num):
    filepath = str(filelist[i])
    label    = str(short_names[i])

    print('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
    print(f'~~~ {filepath}')
    if args.vert:
        print(f'~~~ gravity = {grav_arr[i]}  mwdry = {mwdry_arr[i]}')

    # Read
    raw = reader.read_ncfile(
        filepath,
        grav      = float(grav_arr[i]),
        mwdry     = float(mwdry_arr[i]),
        cf        = args.cf,
        fields_2d = fields_2d,
        fields_3d = fields_3d,
    )

    # Compute
    diag = compute.compute_all(raw, label, options)
    all_diagnostics.append(diag)

    # Print to screen
    if not args.quiet:
        analysis_utils.print_diagnostics(
            diag,
            show_vert  = args.vert,
            show_cf    = args.cf,
            show_synch = args.synch,
        )

    # Verbose vertical profile dump (matches original run_analysis.py behaviour)
    if args.vert and not args.quiet and diag.profile is not None:
        prof = diag.profile
        Pmid_hPa = prof.Pmid / 100.0
        print('-------------- midlayer profile ----------------')
        for z in range(len(prof.Pmid)):
            print(f'{z:3d}  P={Pmid_hPa[z]:.2f} hPa  '
                  f'T={prof.T[z]:.2f} K  '
                  f'LR={prof.lapse_rate[z]:.3f} K/km')


# ================================================================
#  Text file output
# ================================================================

if args.printdata:
    analysis_utils.print_data_to_file(
        all_diagnostics, nostrout=args.nostrout)


# ================================================================
#  Cache
# ================================================================

if cache_path is not None:
    cache.save(all_diagnostics, cache_path)
elif args.vert:
    # Default: save to data/ when --vert is used without --save-cache
    cache.save(all_diagnostics, 'data/diagnostics.pkl')


# ================================================================
#  Inline plots (from YAML config or default vert plot)
# ================================================================

# Default vertical profile plot when --vert is set without a YAML config
if args.vert and not plot_specs:
    plot_specs = [{'type': 'vert_1x3', 'output': 'vert_profiles.png'}]

for spec in plot_specs:
    plot_type = spec.get('type')
    if plot_type is None:
        print(f'warning: plot spec missing "type" key, skipping: {spec}')
        continue
    try:
        plotter = get_plot(plot_type)
        plotter.render(all_diagnostics, spec)
    except Exception as e:
        print(f'warning: plot "{plot_type}" failed: {e}')


# ================================================================
#  Footer
# ================================================================

print('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
print(' Exiting run_analysis.py')
print('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
print()
