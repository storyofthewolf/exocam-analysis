# core/data_model.py
#
# Data containers for ExoCAM analysis.
#
# VerticalProfile  -- global mean vertical profile for one simulation
# Diagnostics      -- all computed quantities for one simulation
#

from dataclasses import dataclass, field
from typing import Optional
import numpy as np


@dataclass
class VerticalProfile:
    """Global mean vertical profile for one simulation."""
    label: str
    Pmid: np.ndarray        # pressure at midlevels (Pa), shape (nlev,)
    T:    np.ndarray        # temperature (K), shape (nlev,)
    Q:    np.ndarray        # water vapor mixing ratio (kg/kg), shape (nlev,)
    lapse_rate: np.ndarray  # lapse rate (K/km), shape (nlev,)
    Z:    Optional[np.ndarray] = None  # geometric height at midlevels (m), shape (nlev,)


@dataclass
class Diagnostics:
    """All computed quantities for one simulation.

    global_means  -- dict of scalar diagnostics (replaces the old datacube array)
    coords        -- coordinate arrays needed for plotting
    profile       -- vertical profile (populated when --vert is used)
    synch_means   -- substellar/antistellar means (populated when --synch is used)
    fields_2d     -- on-demand 2D fields (nlat, nlon) for contour plots
    fields_3d     -- on-demand 3D fields (nlev, nlat, nlon) for contour plots
    """
    label:       str
    coords:      dict                           # lon, lat, lev, Pmid (mean pressure profile)
    global_means: dict                          # str -> float
    profile:     Optional[VerticalProfile] = None
    synch_means: Optional[dict]           = None
    fields_2d:   dict = field(default_factory=dict)  # varname -> (nlat, nlon) array
    fields_3d:   dict = field(default_factory=dict)  # varname -> (nlev, nlat, nlon) array
