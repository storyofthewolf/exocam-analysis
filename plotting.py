# plotting.py
#
#
#
# Contains functions for plotting ExoCAM/CESM diagnostic output.
# Designed to be called from analysis.py or standalone bespoke plot scripts.
#
# Public functions:
#   plot_vert_profiles       --  1x3 panel: T, Q, lapse rate for all profiles
#   plot_vert_profiles_2x2   --  2x2 panel: T and Q with explicit row grouping
#
# Private helpers:
#   _get_colors              --  auto-assign colors from tab10 colormap
#   _get_labels              --  fall back to filenames if no labels provided
#   _setup_pressure_axis     --  standard log-pressure y-axis formatting
#

import numpy as np
import matplotlib
matplotlib.use('Agg')           # non-interactive backend, safe for HPC/headless
import matplotlib.pyplot as plt


# ================================================================
#  Private helpers
# ================================================================

def _get_colors(n, colors=None):
    # If caller supplied colors, use them. Otherwise auto-assign from tab10.
    if colors is not None:
        return colors
    cmap = plt.get_cmap('tab10')
    return [cmap(i % 10) for i in range(n)]


def _get_labels(profiles, labels=None):
    # If caller supplied labels, use them. Otherwise use filenames from profiles.
    if labels is not None:
        return labels
    return [prof['label'] for prof in profiles]


def _setup_pressure_axis(ax):
    # Standard log-pressure y-axis. Inversion is handled once at the
    # figure level (not here) to avoid the sharey double-inversion bug.
    ax.set_yscale('log')
    ax.set_ylabel('Pressure (hPa)')
    ax.grid(True, which='both', linestyle='--', linewidth=0.4, alpha=0.5)


# ================================================================
#  Public plotting functions
# ================================================================

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# // plot_vert_profiles //
#
# 1-row, 3-panel plot: temperature, water vapor, lapse rate.
# Plots all profiles in the list.
#
# Arguments:
#   profiles   : list of dicts, one per file, each containing:
#                  'Pmid'       -- pressure at midlayers (Pa), shape (nlev,)
#                  'T'          -- temperature profile (K), shape (nlev,)
#                  'Q'          -- water vapor mixing ratio (kg/kg), shape (nlev,)
#                  'lapse_rate' -- lapse rate (K/km), shape (nlev,)
#                  'label'      -- filename string (default legend label)
#   labels     : optional list of strings to override legend labels
#   colors     : optional list of colors to override auto-assigned colors
#   outfile    : output filename (default: 'vert_profiles.png')
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def plot_vert_profiles(profiles, labels=None, colors=None, outfile='vert_profiles.png'):

    if len(profiles) == 0:
        print("plot_vert_profiles: no profile data provided, skipping plot.")
        return

    nfiles  = len(profiles)
    colors  = _get_colors(nfiles, colors)
    labels  = _get_labels(profiles, labels)

    fig, axes = plt.subplots(1, 3, figsize=(14, 6), sharey=True)
    ax_T  = axes[0]
    ax_Q  = axes[1]
    ax_LR = axes[2]

    for idx, prof in enumerate(profiles):
        Pmid_hPa = prof['Pmid'] / 100.0
        ax_T.plot(prof['T'],          Pmid_hPa, color=colors[idx], label=labels[idx], linewidth=1.5)
        ax_Q.plot(prof['Q'] * 1.0e6,  Pmid_hPa, color=colors[idx], label=labels[idx], linewidth=1.5)
        ax_LR.plot(prof['lapse_rate'], Pmid_hPa, color=colors[idx], label=labels[idx], linewidth=1.5)

    # invert once on the leftmost axis; sharey propagates to the others
    ax_T.invert_yaxis()

    for ax in axes:
        _setup_pressure_axis(ax)

    ax_T.set_xlabel('Temperature (K)')
    ax_T.set_title('Temperature')
    ax_T.set_xscale('linear')

    ax_Q.set_xlabel('Water Vapor (ppmv)')
    ax_Q.set_title('Water Vapor')
    ax_Q.set_xscale('log')

    ax_LR.set_xlabel('Lapse Rate (K/km)')
    ax_LR.set_title('Lapse Rate')
    ax_LR.set_xscale('linear')
    ax_LR.axvline(x=0.0, color='gray', linestyle=':', linewidth=1.0)

    handles, labels_leg = ax_T.get_legend_handles_labels()
    fig.legend(handles, labels_leg, loc='lower center', ncol=min(nfiles, 4),
               bbox_to_anchor=(0.5, -0.08), fontsize=8, frameon=True)

    fig.suptitle('Global Mean Vertical Profiles', fontsize=12)
    plt.tight_layout()
    plt.savefig(outfile, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print("vertical profile plot written to ", outfile)


#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# // plot_vert_profiles_2x2 //
#
# 2x2 panel plot: temperature (left col) and water vapor (right col),
# top and bottom rows are independently specified groups of profiles.
#
# Arguments:
#   profiles     : full profiles list from analysis.py
#   top          : list of integer indices into profiles for the top row
#   bottom       : list of integer indices into profiles for the bottom row
#   top_title    : optional row label for top row    (default: '')
#   bottom_title : optional row label for bottom row (default: '')
#   labels       : optional list of strings (length = len(profiles)) to
#                  override legend labels for all profiles
#   colors       : optional list of colors (length = len(profiles)) to
#                  override auto-assigned colors for all profiles
#   outfile      : output filename (default: 'vert_profiles_2x2.png')
#
# Example call:
#   plotting.plot_vert_profiles_2x2(
#       profiles, top=[0,1,2], bottom=[3,4,5],
#       top_title='High CO2', bottom_title='Low CO2',
#       labels=['Control','2xCO2','4xCO2','Snowball','Cold trap','Cold dry'],
#       colors=['steelblue','tomato','goldenrod','navy','firebrick','olive'])
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def plot_vert_profiles_2x2(profiles, top, bottom,
                           top_title='', bottom_title='',
                           labels=None, colors=None,
                           outfile='vert_profiles_2x2.png'):

    if len(profiles) == 0:
        print("plot_vert_profiles_2x2: no profile data provided, skipping plot.")
        return

    # colors and labels indexed over the full profiles list so that
    # the same simulation always gets the same color across all plots
    colors = _get_colors(len(profiles), colors)
#    labels = _get_labels(profiles, labels)
    plotted_indices = top + bottom
    if labels is not None:
        # caller supplied labels only for plotted files, in order
        label_map = {idx: lab for idx, lab in zip(plotted_indices, labels)}
    else:
        # fall back to filenames
        label_map = {idx: profiles[idx]['label'] for idx in plotted_indices}

    # sharey='row' shares y-axis within each row but not across rows.
    # This allows top and bottom rows to have independent pressure ranges
    # if needed in the future, while still linking T and Q within a row.
    fig, axes = plt.subplots(2, 2, figsize=(12, 10), sharey='row')

    # axes[row, col]:
    #   [0,0] top-left     T, top group
    #   [0,1] top-right    Q, top group
    #   [1,0] bottom-left  T, bottom group
    #   [1,1] bottom-right Q, bottom group

    for row, indices in enumerate([top, bottom]):
        ax_T = axes[row, 0]
        ax_Q = axes[row, 1]

        for idx in indices:
            prof     = profiles[idx]
            Pmid_hPa = prof['Pmid'] / 100.0
            ax_T.plot(prof['T'],        Pmid_hPa, color=colors[idx], label=label_map[idx], linewidth=1.5)
            ax_Q.plot(prof['Q']*1.0e6,  Pmid_hPa, color=colors[idx], label=label_map[idx], linewidth=1.5)

        # invert once per row on the left axis; sharey='row' propagates to right
        ax_T.invert_yaxis()

        for ax in [ax_T, ax_Q]:
            _setup_pressure_axis(ax)

        ax_T.set_xlabel('Temperature (K)')
        ax_T.set_xscale('linear')

        ax_Q.set_xlabel('Water Vapor (ppmv)')
        ax_Q.set_xscale('log')

        # per-row legend on the right (Q) panel
        ax_Q.legend(loc='best', fontsize=7, frameon=True)

        # row label as rotated annotation to the left of the T panel
        if (row == 0 and top_title) or (row == 1 and bottom_title):
            row_title = top_title if row == 0 else bottom_title
            ax_T.annotate(row_title, xy=(0, 0.5), xytext=(-0.18, 0.5),
                          xycoords='axes fraction', textcoords='axes fraction',
                          fontsize=10, fontweight='bold',
                          va='center', ha='right', rotation=90)

    # column titles on top row only
    axes[0, 0].set_title('Temperature')
    axes[0, 1].set_title('Water Vapor')

    fig.suptitle('Global Mean Vertical Profiles', fontsize=13)
    plt.tight_layout()
    plt.savefig(outfile, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print("vertical profile plot written to ", outfile)
