# analysis_utils.py
#
# Input/output utilities for ExoCAM analysis.
#
# Functions:
#   print_diagnostics     -- print global means to screen
#   print_data_to_file    -- write global means to analysis_output.txt
#

import numpy as np
from typing import List
from core.data_model import Diagnostics


# ================================================================
#  Ordered list of keys for text output
# (defines column order in the output file)
# ================================================================

_OUTPUT_KEY_ORDER = [
    'TS', 'T_STRAT', 'T_TROPO',
    'ICEFRAC',
    'toa_albedo', 'srf_albedo',
    'OLR',
    'toa_balance', 'srf_balance',
    'TMQ', 'TGCLDLWP', 'TGCLDIWP',
    'CLDTOT',
    'sw_cldforc', 'lw_cldforc',
    'Q_STRAT',
    'FLNT', 'FSNT', 'FLNS', 'FSNS',
    'FULTOA', 'FDLTOA', 'FUSTOA', 'FDSTOA',
    'FULSRF', 'FDLSRF', 'FUSSRF', 'FDSSRF',
    'PTOP', 'TTOP', 'QTOP',
    'TS_SS', 'TS_AS',
    'CLDTOT_SS', 'CLDTOT_AS',
    'TGCLDLWP_SS', 'TGCLDLWP_AS',
    'TGCLDIWP_SS', 'TGCLDIWP_AS',
    'FLNT_SS', 'FLNT_AS',
    'lw_cldforc_SS', 'lw_cldforc_AS',
]

_SCI_NOTATION_KEYS = {'Q_STRAT', 'QTOP'}


# ================================================================
#  Screen output
# ================================================================

def print_diagnostics(diag: Diagnostics,
                      show_vert:  bool = False,
                      show_cf:    bool = False,
                      show_synch: bool = False) -> None:
    """Print global mean diagnostics to the screen for one simulation."""
    gm = diag.global_means

    def g(key, default=None):
        return gm.get(key, default)

    print('------------------ global mean ------------------')
    print(f"TS mean              {g('TS'):.4f}")
    if show_synch and 'TS_SS' in gm:
        print(f"TS_SS, TS_AS         {g('TS_SS'):.4f}  {g('TS_AS'):.4f}")
    print(f"ICEFRAC              {g('ICEFRAC'):.4f}")
    print(f"toa albedo           {g('toa_albedo'):.4f}")
    print(f"srf albedo           {g('srf_albedo'):.4f}")
    print(f"TMQ                  {g('TMQ'):.4f}")
    print(f"TGCLDLWP             {g('TGCLDLWP'):.4f}")
    print(f"TGCLDIWP             {g('TGCLDIWP'):.4f}")
    print(f"CLDTOT               {g('CLDTOT'):.4f}")
    if show_synch and 'CLDTOT_SS' in gm:
        print(f"CLDTOT_SS, CLDTOT_AS {g('CLDTOT_SS'):.4f}  {g('CLDTOT_AS'):.4f}")
        print(f"TGCLDLWP_SS, AS      {g('TGCLDLWP_SS'):.4f}  {g('TGCLDLWP_AS'):.4f}")
        print(f"TGCLDIWP_SS, AS      {g('TGCLDIWP_SS'):.4f}  {g('TGCLDIWP_AS'):.4f}")
    #print(f"TOA ENERGY BALANCE   {g('toa_balance'):.4f}  {g('energy_balance'):.4f}")
    print(f"TOA ENERGY BALANCE   {g('toa_balance'):.4f}")
    print(f"SRF ENERGY BALANCE   {g('srf_balance'):.4f}")
    print(f"FLNT FSNT            {g('FLNT'):.4f}  {g('FSNT'):.4f}")
    if show_synch and 'FLNT_SS' in gm:
        print(f"FLNT_SS, FLNT_AS     {g('FLNT_SS'):.4f}  {g('FLNT_AS'):.4f}")
    if 'FSDTOA' in gm:
        print(f"FSDTOA               {g('FSDTOA'):.4f}")
    print(f"LW FLUXES TOA (DN,UP,NET)      {g('FULTOA'):.4f}  {g('FDLTOA'):.4f}  "
          f"{g('FULTOA') - g('FDLTOA'):.4f}")
    print(f"SW FLUXES TOA (DN,UP,NET)      {g('FUSTOA'):.4f}  {g('FDSTOA'):.4f}  "
          f"{g('FDSTOA') - g('FUSTOA'):.4f}")
    print(f"TOP (P[Pa],T[K],Q[kg/kg] {g('PTOP'):.4f}  {g('TTOP'):.4f}  {g('QTOP'):.4e}")
    if show_vert and 'T_TROPO' in gm:
        print(f"T_TROPO, T_STRAT     {g('T_TROPO'):.4f}  {g('T_STRAT'):.4f}")
        print(f"Q_STRAT              {g('Q_STRAT'):.4e}")
    if show_cf and 'FLNTC' in gm:
        print(f"FLNTC FSNTC          {g('FLNTC'):.4f}  {g('FSNTC'):.4f}")
        print(f"CLEAR-SKY LW (TOA)   {g('FULCTOA'):.4f}  {g('FDLCTOA'):.4f}  "
              f"{g('FULCTOA') - g('FDLCTOA'):.4f}")
        print(f"CLEAR-SKY SW (TOA)   {g('FUSCTOA'):.4f}  {g('FDSCTOA'):.4f}  "
              f"{g('FDSCTOA') - g('FUSCTOA'):.4f}")
        print(f"SW CLOUD FORCING     {g('sw_cldforc'):.4f}")
        print(f"LW CLOUD FORCING     {g('lw_cldforc'):.4f}")
        if show_synch and 'lw_cldforc_SS' in gm:
            print(f"LW CLD FORC SS/AS    {g('lw_cldforc_SS'):.4f}  {g('lw_cldforc_AS'):.4f}")


# ================================================================
#  Text file output
# ================================================================

def print_data_to_file(diagnostics_list: List[Diagnostics],
                       nostrout: bool = False,
                       outfile: str = 'analysis_output.txt') -> None:
    """Write global mean diagnostics to a formatted text file.

    Columns are the variable names present across all simulations (in
    _OUTPUT_KEY_ORDER); rows are simulations.

    Arguments
    ---------
    diagnostics_list : list of Diagnostics objects
    nostrout         : if True, omit simulation name from output rows
    outfile          : output file path
    """
    # Determine which keys are actually populated (union across all simulations)
    all_keys = set()
    for d in diagnostics_list:
        all_keys.update(d.global_means.keys())
    # Filter to ordered list, preserving defined order, appending any extras
    ordered = [k for k in _OUTPUT_KEY_ORDER if k in all_keys]
    extras  = sorted(all_keys - set(ordered))
    ordered += extras

    labels   = [d.label for d in diagnostics_list]
    maxchar  = max(len(s) for s in labels)
    hdr_pad  = maxchar + 4

    fmt_real = '{:10.4f}'
    fmt_exp  = '{:10.4e}'
    fmt_str  = '{:>10}'

    with open(outfile, 'w') as f:
        print('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~', file=f)
        print('CESM ExoCAM diagnostic output using run_analysis.py',     file=f)
        print('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~', file=f)

        # Header row
        hdr = '{:<{}}'.format('i   filenames', hdr_pad)
        f.write(hdr + ' ')
        for j, key in enumerate(ordered):
            end = '\n' if j == len(ordered) - 1 else ' '
            f.write(fmt_str.format(key) + end)

        # Data rows
        for i, diag in enumerate(diagnostics_list):
            ii = i + 1
            if nostrout:
                row_str = f'{ii:<3}'
            else:
                row_str = f'{ii}   {diag.label}'
            row_str = '{:<{}}'.format(row_str, hdr_pad)
            f.write(row_str + ' ')
            for j, key in enumerate(ordered):
                val = diag.global_means.get(key, 0.0)
                fmt = fmt_exp if key in _SCI_NOTATION_KEYS else fmt_real
                end = '\n' if j == len(ordered) - 1 else ' '
                f.write(fmt.format(val) + end)

    print(f'output data written to {outfile}')
