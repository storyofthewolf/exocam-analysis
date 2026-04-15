# core/coords.py
#
# Coordinate utilities for ExoCAM/CESM hybrid sigma-pressure grids.
#
# Originally from exocampy_tools.py (Author: Wolf E.T., translated to Python
# by R. Deitrick October 2022). Incorporated locally and vectorized.
#
# Functions:
#   hybrid2pressure     -- hybrid sigma-pressure → pressure at mid/interface levels
#   hybrid2height       -- hybrid sigma-pressure → geometric height (vectorized)
#   area_weighted_avg   -- area-weighted global mean of a 2D field (vectorized)
#   calc_gmean_profiles -- level-by-level global mean of a 3D field
#

import numpy as np


# ================================================================
#  Pressure coordinate conversion
# ================================================================

def hybrid2pressure(nlon, nlat, nlev, PS, P0, hyam, hybm, hyai, hybi):
    """Convert hybrid sigma-pressure coordinates to pressure.

    Arguments
    ---------
    nlon, nlat, nlev : grid dimensions
    PS   : surface pressure (nlat, nlon) Pa
    P0   : reference pressure (scalar) Pa
    hyam, hybm : hybrid A/B coefficients at layer midpoints, shape (nlev,)
    hyai, hybi : hybrid A/B coefficients at layer interfaces, shape (nlev+1,)

    Returns
    -------
    lev_P  : pressure at midlevels  (nlev,  nlat, nlon) Pa
    ilev_P : pressure at interfaces (nlev+1, nlat, nlon) Pa
    """
    lev_P  = hyam[:, None, None] * P0 + hybm[:, None, None] * PS[None, :, :]
    ilev_P = hyai[:, None, None] * P0 + hybi[:, None, None] * PS[None, :, :]
    return lev_P, ilev_P


# ================================================================
#  Height coordinate conversion  (vectorized)
# ================================================================

def hybrid2height(nlon, nlat, nlev, PS, P0, hyam, hybm, hyai, hybi, T, G, R):
    """Convert hybrid sigma-pressure coordinates to geometric height.

    Uses the hypsometric equation: dZ = (R*T/g) * ln(p_bot / p_top)

    The original implementation used a triple Python loop over
    (nlev, nlat, nlon).  This version computes all layer thicknesses
    simultaneously and accumulates height via np.cumsum, eliminating all
    Python loops.

    Arguments
    ---------
    nlon, nlat, nlev : grid dimensions
    PS   : surface pressure (nlat, nlon) Pa
    P0   : reference pressure (scalar) Pa
    hyam, hybm : hybrid A/B coefficients at layer midpoints
    hyai, hybi : hybrid A/B coefficients at layer interfaces
    T    : temperature (nlev, nlat, nlon) K
    G    : gravitational acceleration (m s-2)
    R    : specific gas constant for dry air (J kg-1 K-1)

    Returns
    -------
    lev_Z  : height at midlevels   (nlev,   nlat, nlon) m
    ilev_Z : height at interfaces  (nlev+1, nlat, nlon) m
             ilev_Z[nlev] = 0  (surface, topography not yet included)

    Notes
    -----
    Surface geopotential (topography) is currently set to zero.
    """
    lev_P, ilev_P = hybrid2pressure(nlon, nlat, nlev, PS, P0, hyam, hybm, hyai, hybi)

    nlev, nlat, nlon = T.shape
    nilev = nlev + 1

    # Layer thickness at each level: dZ = (R*T/g) * ln(p_bot / p_top)
    # ilev_P[1:]  = lower interface pressure (p_bot) for each midlevel
    # ilev_P[:-1] = upper interface pressure (p_top) for each midlevel
    delta_Z = R * T / G * np.log(ilev_P[1:] / ilev_P[:-1])  # (nlev, nlat, nlon)

    # Interface heights counted upward from the surface (surface = index nlev = 0 m).
    # ilev_Z[zi] = sum(delta_Z[zi : nlev]) = reverse cumulative sum.
    ilev_Z = np.zeros((nilev, nlat, nlon))
    ilev_Z[:nlev] = np.cumsum(delta_Z[::-1], axis=0)[::-1]

    # Midlevel height = height of lower interface + scale-height offset to midpoint
    # Z_SCALE = (R*T/g) * ln(p_bot / p_mid)  [positive: midpoint is above lower interface]
    lev_Z = ilev_Z[1:] + R * T / G * np.log(ilev_P[1:] / lev_P)

    return lev_Z, ilev_Z


# ================================================================
#  Area-weighted global mean  (vectorized)
# ================================================================

def area_weighted_avg(lon, lat, var):
    """Area-weighted global mean of a 2D lon-lat field.

    Accepts arrays in either (nlat, nlon) or (nlon, nlat) order.
    Grid cells with value == -999.0 (fill_value) are excluded.

    Arguments
    ---------
    lon : longitude array (nlon,) degrees
    lat : latitude array  (nlat,) degrees
    var : 2D field, shape (nlat, nlon) or (nlon, nlat)

    Returns
    -------
    weighted_avg : scalar float
    """
    fill_value = -999.0
    nlon = len(lon)
    nlat = len(lat)

    # Staggered latitude grid (vectorized)
    slat = np.empty(nlat + 1)
    slat[0]  = -90.0
    slat[-1] =  90.0
    slat[1:-1] = (lat[:-1] + lat[1:]) / 2.0

    # Staggered longitude grid
    slon = np.empty(nlon + 1)
    slon[:nlon] = lon
    slon[nlon]  = 360.0

    # Cell areas: longitude width (radians) × sin-latitude band (dimensionless)
    # Area is separable, so build as outer product.
    dlon     = np.diff(slon) * (np.pi / 180.0)                              # (nlon,)
    dlat_sin = np.sin(slat[1:] * (np.pi / 180.0)) - \
               np.sin(slat[:-1] * (np.pi / 180.0))                          # (nlat,)

    if var.shape[0] == nlon:          # (nlon, nlat) orientation
        area = dlon[:, None] * dlat_sin[None, :]
    else:                             # (nlat, nlon) orientation
        area = dlat_sin[:, None] * dlon[None, :]

    mask = (var != fill_value)
    return float(np.sum(area * var * mask) / np.sum(area * mask))


# ================================================================
#  Level-by-level global mean profile
# ================================================================

def calc_gmean_profiles(lon, lat, var):
    """Global mean vertical profile of a 3D field.

    Arguments
    ---------
    lon : longitude array (nlon,)
    lat : latitude array  (nlat,)
    var : 3D field (nlev, nlat, nlon)

    Returns
    -------
    var_gmean : 1D array (nlev,) of global mean values at each level
    """
    nlev = var.shape[0]
    var_gmean = np.zeros(nlev)
    for z in range(nlev):
        var_gmean[z] = area_weighted_avg(lon, lat, var[z])
    return var_gmean
