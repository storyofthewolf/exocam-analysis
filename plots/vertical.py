# plots/vertical.py
#
# Vertical profile plot types (refactored from plotting.py).
#
# Registered plot types:
#   vert_1x3  -- 1×3 panel: Temperature | Water Vapor | Lapse Rate
#   vert_2x2  -- 2×2 panel: two groups, each with T and Q columns
#

from typing import List
import matplotlib.pyplot as plt

from core.data_model import Diagnostics
from plots.base import Plot, setup_pressure_axis, get_colors, get_labels, save_figure
from plots.registry import register_plot


# ================================================================
#  vert_1x3
# ================================================================

@register_plot('vert_1x3')
class VertProfiles1x3(Plot):
    """1×3 panel: Temperature, Water Vapor, Lapse Rate for all profiles.

    YAML options
    ------------
    output      : output filename (default: vert_profiles.png)
    labels      : list of strings to override legend labels
    colors      : list of color strings to override auto-assigned colors
    """

    def render(self, diagnostics: List[Diagnostics], options: dict) -> None:
        outfile = options.get('output', 'results/vert_profiles.png')
        labels  = options.get('labels', None)
        colors  = options.get('colors', None)

        profiles = [d.profile for d in diagnostics if d.profile is not None]
        if not profiles:
            print('vert_1x3: no vertical profile data found, skipping.')
            return

        nfiles = len(profiles)
        colors = get_colors(nfiles, colors)
        if labels is None:
            labels = [p.label for p in profiles]

        fig, axes = plt.subplots(1, 3, figsize=(14, 6), sharey=True)
        ax_T, ax_Q, ax_LR = axes

        for idx, prof in enumerate(profiles):
            Pmid_hPa = prof.Pmid / 100.0
            ax_T.plot(prof.T,          Pmid_hPa, color=colors[idx],
                      label=labels[idx], linewidth=1.5)
            ax_Q.plot(prof.Q * 1.0e6,  Pmid_hPa, color=colors[idx],
                      label=labels[idx], linewidth=1.5)
            ax_LR.plot(prof.lapse_rate, Pmid_hPa, color=colors[idx],
                       label=labels[idx], linewidth=1.5)

        ax_T.invert_yaxis()   # invert once; sharey propagates

        for ax in axes:
            setup_pressure_axis(ax)

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

        handles, leg_labels = ax_T.get_legend_handles_labels()
        fig.legend(handles, leg_labels, loc='lower center',
                   ncol=min(nfiles, 4), bbox_to_anchor=(0.5, -0.08),
                   fontsize=8, frameon=True)

        fig.suptitle('Global Mean Vertical Profiles', fontsize=12)
        plt.tight_layout()
        save_figure(fig, outfile)
        print(f'vertical profile plot written to {outfile}')


# ================================================================
#  vert_2x2
# ================================================================

@register_plot('vert_2x2')
class VertProfiles2x2(Plot):
    """2×2 panel: two groups of profiles, each with T and Q columns.

    YAML options
    ------------
    top          : list of integer indices into diagnostics for the top row
    bottom       : list of integer indices into diagnostics for the bottom row
    top_title    : row label for top row    (default: '')
    bottom_title : row label for bottom row (default: '')
    labels       : list of strings (one per plotted profile, in top+bottom order)
    colors       : list of colors (one per all diagnostics, for consistent mapping)
    output       : output filename (default: vert_profiles_2x2.png)
    """

    def render(self, diagnostics: List[Diagnostics], options: dict) -> None:
        top          = options.get('top',          [])
        bottom       = options.get('bottom',       [])
        top_title    = options.get('top_title',    '')
        bottom_title = options.get('bottom_title', '')
        labels       = options.get('labels',       None)
        colors       = options.get('colors',       None)
        outfile      = options.get('output', 'results/vert_profiles_2x2.png')

        if not top and not bottom:
            print('vert_2x2: no top/bottom indices specified, skipping.')
            return

        # Colors indexed over the full diagnostics list for consistent mapping
        colors = get_colors(len(diagnostics), colors)

        plotted_indices = top + bottom
        if labels is not None:
            label_map = {idx: lab for idx, lab in zip(plotted_indices, labels)}
        else:
            label_map = {idx: diagnostics[idx].label for idx in plotted_indices}

        fig, axes = plt.subplots(2, 2, figsize=(12, 10), sharey='row')

        for row, indices in enumerate([top, bottom]):
            ax_T = axes[row, 0]
            ax_Q = axes[row, 1]

            for idx in indices:
                prof = diagnostics[idx].profile
                if prof is None:
                    print(f'vert_2x2: no profile for simulation {idx}, skipping.')
                    continue
                Pmid_hPa = prof.Pmid / 100.0
                ax_T.plot(prof.T,       Pmid_hPa, color=colors[idx],
                          label=label_map[idx], linewidth=1.5)
                ax_Q.plot(prof.Q * 1e6, Pmid_hPa, color=colors[idx],
                          label=label_map[idx], linewidth=1.5)

            ax_T.invert_yaxis()   # invert once per row; sharey='row' propagates

            for ax in [ax_T, ax_Q]:
                setup_pressure_axis(ax)

            ax_T.set_xlabel('Temperature (K)')
            ax_T.set_xscale('linear')
            ax_Q.set_xlabel('Water Vapor (ppmv)')
            ax_Q.set_xscale('log')
            ax_Q.legend(loc='best', fontsize=7, frameon=True)

            row_title = top_title if row == 0 else bottom_title
            if row_title:
                ax_T.annotate(row_title, xy=(0, 0.5), xytext=(-0.18, 0.5),
                              xycoords='axes fraction', textcoords='axes fraction',
                              fontsize=10, fontweight='bold',
                              va='center', ha='right', rotation=90)

        axes[0, 0].set_title('Temperature')
        axes[0, 1].set_title('Water Vapor')
        fig.suptitle('Global Mean Vertical Profiles', fontsize=13)
        plt.tight_layout()
        save_figure(fig, outfile)
        print(f'vertical profile plot written to {outfile}')
