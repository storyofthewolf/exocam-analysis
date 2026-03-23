# plotting.py
#
#
#
# Contains functions for plotting ExoCAM/CESM diagnostic output.
# Designed to be called from analysis.py after data processing is complete.
#
# Functions:
#   plot_vert_profiles  --  global mean vertical profiles (T, Q, lapse rate)
#

import numpy as np
import matplotlib
matplotlib.use('Agg')           # non-interactive backend, safe for HPC/headless
import matplotlib.pyplot as plt


#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# // plot_vert_profiles //
#
# Plot global mean vertical profiles for a batch of simulations.
# Called from analysis.py when args.vert == True.
#
# Arguments:
#   profiles      : list of dicts, one per file, each containing:
#                     'Pmid'       -- pressure at midlayers (Pa), shape (nlev,)
#                     'T'          -- temperature profile (K), shape (nlev,)
#                     'Q'          -- water vapor profile (kg/kg), shape (nlev,)
#                     'lapse_rate' -- lapse rate (K/km), shape (nlev,)
#                     'label'      -- short filename string for legend
#   outfile       : output filename (default: 'vert_profiles.png')
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def plot_vert_profiles(profiles, outfile='vert_profiles.png'):

    if len(profiles) == 0:
        print("plot_vert_profiles: no profile data provided, skipping plot.")
        return

    nfiles = len(profiles)

    # Use a colormap to auto-assign one color per simulation.
    # Analogous to cycling through line colors in a multi-experiment overlay plot.
    cmap   = plt.get_cmap('tab10')
    colors = [cmap(i % 10) for i in range(nfiles)]

    fig, axes = plt.subplots(1, 3, figsize=(14, 6), sharey=True)

    ax_T   = axes[0]   # temperature
    ax_Q   = axes[1]   # water vapor
    ax_LR  = axes[2]   # lapse rate

    xscales = ['linear', 'log', 'linear']
    
    for idx, prof in enumerate(profiles):
        Pmid_hPa = prof['Pmid'] / 100.0   # convert Pa -> hPa for display
        color    = colors[idx]
        label    = prof['label']

        ax_T.plot(prof['T'],          Pmid_hPa, color=color, label=label, linewidth=1.5)
        ax_Q.plot(prof['Q'],          Pmid_hPa, color=color, label=label, linewidth=1.5)
        ax_LR.plot(prof['lapse_rate'], Pmid_hPa, color=color, label=label, linewidth=1.5)

    # --- axes formatting ---
    # Pressure on log-scale y-axis, increasing downward (surface at bottom).
    # This is the standard vertical coordinate display for atmospheric profiles,
    # the same orientation used in CESM/ExoCAM diagnostic plots.
    for ax, xscale in zip(axes, xscales):
        ax.set_yscale('log')
        ax.set_xscale(xscale)
        ax.invert_yaxis()
        ax.set_ylabel('Pressure (hPa)')
        ax.grid(True, which='both', linestyle='--', linewidth=0.4, alpha=0.5)

    ax_T.set_xlabel('Temperature (K)')
    ax_T.set_title('Temperature Profile')

    ax_Q.set_xlabel('Water Vapor (ppmv)')
    ax_Q.set_title('Water Vapor Profile')

    ax_LR.set_xlabel('Lapse Rate (K/km)')
    ax_LR.set_title('Lapse Rate Profile')
    ax_LR.axvline(x=0.0, color='gray', linestyle=':', linewidth=1.0)  # zero lapse rate line

    # Single legend placed outside the rightmost panel
    handles, labels = ax_T.get_legend_handles_labels()
    fig.legend(handles, labels, loc='lower center', ncol=min(nfiles, 4),
               bbox_to_anchor=(0.5, -0.08), fontsize=8, frameon=True)

    fig.suptitle('Global Mean Vertical Profiles', fontsize=12, y=1.01)
    plt.tight_layout()
    plt.savefig(outfile, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print("vertical profile plot written to ", outfile)
