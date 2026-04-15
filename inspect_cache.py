#!/usr/bin/env python

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# inspect_cache.py
#
# Standalone utility: print metadata for a Diagnostics cache (.pkl) file.
# No netCDF re-reading required.
#
# Usage:
#   python inspect_cache.py                          # reads data/diagnostics.pkl
#   python inspect_cache.py data/my_study.pkl
#   python inspect_cache.py data/my_study.pkl --sim 2
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

import sys
import os
import argparse
import numpy as np

# Ensure the package root is on sys.path so core.data_model is importable
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from core import cache as cache_io


# ================================================================
#  Helpers
# ================================================================

SEP  = '~' * 68
SEP2 = '-' * 68

def _shape_str(arr):
    return str(arr.shape) if hasattr(arr, 'shape') else repr(arr)


def _coord_summary(coords: dict) -> None:
    lon  = coords.get('lon',  None)
    lat  = coords.get('lat',  None)
    lev  = coords.get('lev',  None)
    Pmid = coords.get('Pmid', None)

    if lon  is not None:
        print(f'    lon   : {len(lon)} points  '
              f'[{lon.min():.2f}° – {lon.max():.2f}°]')
    if lat  is not None:
        print(f'    lat   : {len(lat)} points  '
              f'[{lat.min():.2f}° – {lat.max():.2f}°]')
    if lev  is not None:
        print(f'    lev   : {len(lev)} levels  '
              f'(model hybrid-sigma indices)')
    if Pmid is not None:
        Pmid_hPa = Pmid / 100.0
        print(f'    Pmid  : {len(Pmid_hPa)} levels  '
              f'[{Pmid_hPa.min():.2f} – {Pmid_hPa.max():.2f} hPa]  '
              f'(global mean pressure profile)')


def _profile_summary(prof) -> None:
    nlev = len(prof.Pmid)
    Pmid_hPa = prof.Pmid / 100.0
    print(f'    levels    : {nlev}')
    print(f'    P range   : {Pmid_hPa.min():.2f} – {Pmid_hPa.max():.2f} hPa')
    vars_present = ['Pmid', 'T', 'Q', 'lapse_rate']
    if prof.Z is not None:
        vars_present.append('Z')
    print(f'    variables : {vars_present}')
    print(f'    T range   : {prof.T.min():.2f} – {prof.T.max():.2f} K')
    print(f'    Q range   : {prof.Q.min():.3e} – {prof.Q.max():.3e} kg/kg')


def _print_sim(diag, idx: int, verbose: bool) -> None:
    print(SEP)
    print(f'  Simulation {idx}:  {diag.label}')
    print(SEP2)

    # Coordinates
    print('  Coordinates:')
    _coord_summary(diag.coords)

    # Global means
    gm_keys = sorted(diag.global_means.keys())
    print(f'\n  Global means ({len(gm_keys)} variables):')
    if verbose:
        col = 0
        for k in gm_keys:
            v = diag.global_means[k]
            entry = f'    {k:<22} {v:>12.4g}'
            print(entry)
    else:
        # Print in compact columns
        keys_per_row = 4
        for i in range(0, len(gm_keys), keys_per_row):
            chunk = gm_keys[i:i + keys_per_row]
            print('    ' + '  '.join(f'{k:<18}' for k in chunk))

    # Vertical profile
    print()
    if diag.profile is not None:
        print('  Vertical profile: present')
        _profile_summary(diag.profile)
    else:
        print('  Vertical profile: not computed  (run with --vert)')

    # Synch means
    print()
    if diag.synch_means is not None:
        synch_keys = sorted(diag.synch_means.keys())
        print(f'  Substellar/antistellar means ({len(synch_keys)} variables):')
        print('    ' + '  '.join(f'{k:<18}' for k in synch_keys[:8]))
        if len(synch_keys) > 8:
            print(f'    ... and {len(synch_keys) - 8} more')
    else:
        print('  Substellar/antistellar means: not computed  (run with --synch)')

    # Cached 2D fields
    print()
    if diag.fields_2d:
        print(f'  Cached 2D fields ({len(diag.fields_2d)}):')
        for var, arr in sorted(diag.fields_2d.items()):
            print(f'    {var:<16}  shape {_shape_str(arr)}'
                  f'  range [{arr.min():.4g}, {arr.max():.4g}]')
    else:
        print('  Cached 2D fields: none')

    # Cached 3D fields
    print()
    if diag.fields_3d:
        print(f'  Cached 3D fields ({len(diag.fields_3d)}):')
        for var, arr in sorted(diag.fields_3d.items()):
            print(f'    {var:<16}  shape {_shape_str(arr)}'
                  f'  range [{arr.min():.4g}, {arr.max():.4g}]')
    else:
        print('  Cached 3D fields: none')


# ================================================================
#  Main
# ================================================================

parser = argparse.ArgumentParser(
    description='Print metadata for a Diagnostics cache (.pkl) file.')
parser.add_argument('cache', nargs='?', default='data/diagnostics.pkl',
                    help='path to .pkl file (default: data/diagnostics.pkl)')
parser.add_argument('--sim', type=int, default=None,
                    help='print details for a single simulation index only')
parser.add_argument('--values', action='store_true',
                    help='print actual values of all global means (verbose)')
args = parser.parse_args()

diagnostics = cache_io.load(args.cache)
n = len(diagnostics)

print()
print(SEP)
print(f'  Cache file : {os.path.abspath(args.cache)}')
print(f'  Simulations: {n}')
print(SEP)

# Summary table
print()
print('  Index  Label')
print('  ' + '-' * 50)
for i, d in enumerate(diagnostics):
    profile_tag = '[+vert]'  if d.profile      is not None else '       '
    synch_tag   = '[+synch]' if d.synch_means  is not None else '        '
    f2d_tag     = f'[2D:{len(d.fields_2d)}]'  if d.fields_2d  else ''
    f3d_tag     = f'[3D:{len(d.fields_3d)}]'  if d.fields_3d  else ''
    tags = '  '.join(t for t in [profile_tag, synch_tag, f2d_tag, f3d_tag] if t.strip())
    print(f'  {i:<6} {d.label:<40}  {tags}')

# Per-simulation detail
print()
if args.sim is not None:
    if args.sim < 0 or args.sim >= n:
        sys.exit(f'error: --sim {args.sim} out of range (0–{n-1})')
    _print_sim(diagnostics[args.sim], args.sim, verbose=args.values)
else:
    for i, d in enumerate(diagnostics):
        _print_sim(d, i, verbose=args.values)

print(SEP)
print()
