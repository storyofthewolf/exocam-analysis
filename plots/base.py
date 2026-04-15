# plots/base.py
#
# Abstract base class for all plot types, plus shared axis helpers.
#

import os
from abc import ABC, abstractmethod
from typing import List
import matplotlib
matplotlib.use('Agg')           # non-interactive backend, safe for HPC/headless
import matplotlib.pyplot as plt

from core.data_model import Diagnostics


class Plot(ABC):
    """Base class for all registered plot types."""

    @abstractmethod
    def render(self, diagnostics: List[Diagnostics], options: dict) -> None:
        """Produce and save a plot.

        Arguments
        ---------
        diagnostics : list of Diagnostics objects (one per simulation)
        options     : dict from the YAML plot spec (type, output, var, ...)
        """


# ================================================================
#  Shared axis helpers
# ================================================================

def setup_pressure_axis(ax):
    """Standard log-pressure y-axis with grid."""
    ax.set_yscale('log')
    ax.set_ylabel('Pressure (hPa)')
    ax.grid(True, which='both', linestyle='--', linewidth=0.4, alpha=0.5)


def get_colors(n: int, colors=None) -> list:
    """Return n colors from tab10 colormap (cycles if n > 10)."""
    if colors is not None:
        return colors
    cmap = plt.get_cmap('tab10')
    return [cmap(i % 10) for i in range(n)]


def get_labels(diagnostics: List[Diagnostics], labels=None) -> list:
    """Return labels list, falling back to simulation labels."""
    if labels is not None:
        return labels
    return [d.label for d in diagnostics]


def save_figure(fig, outfile: str, dpi: int = 150) -> None:
    """Save figure, creating parent directory if needed."""
    parent = os.path.dirname(outfile)
    if parent:
        os.makedirs(parent, exist_ok=True)
    fig.savefig(outfile, dpi=dpi, bbox_inches='tight')
    plt.close(fig)
