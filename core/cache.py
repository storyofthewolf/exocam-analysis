# core/cache.py
#
# Save and load Diagnostics lists to/from disk.
# The cache is the hand-off point between the expensive netCDF processing
# step and fast downstream work (re-plotting, bespoke publication scripts).
#

import pickle
from typing import List
from core.data_model import Diagnostics


def save(diagnostics: List[Diagnostics], path: str = 'diagnostics.pkl') -> None:
    """Pickle a list of Diagnostics objects to disk."""
    with open(path, 'wb') as f:
        pickle.dump(diagnostics, f)
    print(f'diagnostics cache written to {path}')


def load(path: str = 'diagnostics.pkl') -> List[Diagnostics]:
    """Load a list of Diagnostics objects from a pickle file."""
    with open(path, 'rb') as f:
        diagnostics = pickle.load(f)
    print(f'diagnostics cache loaded from {path}  ({len(diagnostics)} simulation(s))')
    return diagnostics
