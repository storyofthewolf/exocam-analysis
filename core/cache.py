# core/cache.py
#
# Save and load Diagnostics lists to/from disk.
# The cache is the hand-off point between the expensive netCDF processing
# step and fast downstream work (re-plotting, bespoke publication scripts).
#

import os
import sys
import pickle
from typing import List

# Ensure the package root (directory containing core/) is importable,
# even when this module is loaded from a script in a different directory.
_PKG_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PKG_ROOT not in sys.path:
    sys.path.insert(0, _PKG_ROOT)

from core.data_model import Diagnostics


def save(diagnostics: List[Diagnostics], path: str = 'data/diagnostics.pkl') -> None:
    """Pickle a list of Diagnostics objects to disk."""
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, 'wb') as f:
        pickle.dump(diagnostics, f)
    print(f'diagnostics cache written to {path}')


def load(path: str = 'data/diagnostics.pkl') -> List[Diagnostics]:
    """Load a list of Diagnostics objects from a pickle file."""
    with open(path, 'rb') as f:
        diagnostics = pickle.load(f)
    print(f'diagnostics cache loaded from {path}  ({len(diagnostics)} simulation(s))')
    return diagnostics
