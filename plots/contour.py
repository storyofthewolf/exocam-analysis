# plots/contour.py
#
# 2D contour plot types for spatial and cross-section views.
#
# Registered plot types:
#   map_latlon      -- longitude × latitude surface map
#   section_latpres -- latitude × pressure zonal mean cross-section
#   section_lonpres -- longitude × pressure cross-section at a given latitude
#

import numpy as np
from typing import List
import matplotlib.pyplot as plt

from core.data_model import Diagnostics
from plots.base import Plot, setup_pressure_axis, save_figure
from plots.registry import register_plot


# ================================================================
#  Shared helper
# ================================================================

def _get_field(diag: Diagnostics, var: str, is_3d: bool):
    """Retrieve a cached field from Diagnostics, with a clear error if missing."""
    store = diag.fields_3d if is_3d else diag.fields_2d
    if var not in store:
        dim = '3D' if is_3d else '2D'
        raise KeyError(
            f"Variable '{var}' not found in {dim} cache for '{diag.label}'.\n"
            f"Add it to cache_fields.{'3d' if is_3d else '2d'} in your config.")
    return store[var]


def _pressure_axis(ax, Pmid_hPa: np.ndarray):
    """Set up a log-pressure y-axis using the provided pressure levels."""
    ax.set_yscale('log')
    ax.set_ylim(Pmid_hPa.max(), Pmid_hPa.min())   # invert: surface at bottom
    ax.set_ylabel('Pressure (hPa)')
    ax.grid(True, which='both', linestyle='--', linewidth=0.4, alpha=0.5)


def _add_colorbar(fig, ax, cf, label: str):
    fig.colorbar(cf, ax=ax, orientation='vertical', pad=0.02, label=label)


# ================================================================
#  map_latlon
# ================================================================

@register_plot('map_latlon')
class MapLatLon(Plot):
    """Longitude × latitude filled contour map.

    Draws one simulation at a time.

    YAML options
    ------------
    var       : variable name (must be in fields_2d, or fields_3d with lev_index)
    sim_index : index into diagnostics list (default: 0)
    lev_index : for 3D variables, which level to plot (default: 0 = model top)
    output    : output filename (default: map_<var>.png)
    """

    def render(self, diagnostics: List[Diagnostics], options: dict) -> None:
        var       = options['var']
        sim_idx   = options.get('sim_index', 0)
        lev_index = options.get('lev_index', 0)

        diag = diagnostics[sim_idx]
        lon  = diag.coords['lon']
        lat  = diag.coords['lat']

        # Try 2D first, then slice from 3D
        if var in diag.fields_2d:
            data    = diag.fields_2d[var]          # (nlat, nlon)
            title   = f'{var}  —  {diag.label}'
            outfile = options.get('output', f'results/{var}_map.png')
        elif var in diag.fields_3d:
            data      = diag.fields_3d[var][lev_index]   # (nlat, nlon)
            pres_hPa  = float(diag.coords['Pmid'][lev_index]) / 100.0
            title     = f'{var}  lev {lev_index} ({pres_hPa:.1f} hPa)  —  {diag.label}'
            outfile   = options.get('output',
                            f'results/{var}_map_lev{lev_index}_{pres_hPa:.1f}hPa.png')
        else:
            raise KeyError(
                f"Variable '{var}' not found in 2D or 3D cache for '{diag.label}'.\n"
                f"Add it to cache_fields in your config.")

        fig, ax = plt.subplots(figsize=(9, 5))
        LON, LAT = np.meshgrid(lon, lat)
        cf = ax.contourf(LON, LAT, data, levels=20, cmap='viridis')
        ax.contour(LON, LAT, data, levels=20, colors='k',
                   linewidths=0.3, alpha=0.4)
        _add_colorbar(fig, ax, cf, var)

        ax.set_xlabel('Longitude (°)')
        ax.set_ylabel('Latitude (°)')
        ax.set_title(title)
        plt.tight_layout()
        save_figure(fig, outfile)
        print(f'map plot written to {outfile}')


# ================================================================
#  section_latpres
# ================================================================

@register_plot('latpres')
class SectionLatPres(Plot):
    """Latitude × pressure cross-section.

    Default: zonal mean (average over all longitudes).
    If lon_deg is provided, slices at the nearest grid longitude instead.

    YAML options
    ------------
    var        : 3D variable name (must be in fields_3d)
    sim_index  : index into diagnostics list (default: 0)
    lon_deg    : longitude of slice in degrees; omit for zonal mean
    output     : output filename (default: <var>_latpres.png)
    """

    def render(self, diagnostics: List[Diagnostics], options: dict) -> None:
        var     = options['var']
        sim_idx = options.get('sim_index', 0)
        lon_deg = options.get('lon_deg', None)   # None → zonal mean

        diag     = diagnostics[sim_idx]
        lat      = diag.coords['lat']
        lon      = diag.coords['lon']
        Pmid_hPa = diag.coords['Pmid'] / 100.0   # Pa → hPa

        data3d = _get_field(diag, var, is_3d=True)   # (nlev, nlat, nlon)

        if lon_deg is None:
            data     = np.mean(data3d, axis=2)        # (nlev, nlat) zonal mean
            title    = f'{var} (zonal mean)  —  {diag.label}'
            outfile  = options.get('output', f'results/{var}_latpres_zonalavg.png')
        else:
            lon_idx    = int(np.argmin(np.abs(lon - lon_deg)))
            lon_actual = float(lon[lon_idx])
            data     = data3d[:, :, lon_idx]          # (nlev, nlat)
            title    = f'{var} at {lon_actual:.1f}°E  —  {diag.label}'
            outfile  = options.get('output', f'results/{var}_latpres_lon{lon_actual:.1f}.png')

        LAT, PRES = np.meshgrid(lat, Pmid_hPa)

        fig, ax = plt.subplots(figsize=(8, 6))
        cf = ax.contourf(LAT, PRES, data, levels=20, cmap='viridis')
        ax.contour(LAT, PRES, data, levels=20, colors='k',
                   linewidths=0.3, alpha=0.4)
        _add_colorbar(fig, ax, cf, var)
        _pressure_axis(ax, Pmid_hPa)

        ax.set_xlabel('Latitude (°)')
        ax.set_title(title)
        plt.tight_layout()
        save_figure(fig, outfile)
        print(f'lat-pressure section written to {outfile}')


# ================================================================
#  section_lonpres
# ================================================================

@register_plot('lonpres')
class SectionLonPres(Plot):
    """Longitude × pressure cross-section at a specified latitude.

    Particularly useful for tidally locked planets where the equatorial
    substellar-to-antistellar transect is dynamically significant.

    YAML options
    ------------
    var       : 3D variable name (must be in fields_3d)
    sim_index : index into diagnostics list (default: 0)
    lat_deg   : latitude of the cross-section in degrees (default: 0.0 = equator)
    output    : output filename (default: <var>_lonpres.png)
    """

    def render(self, diagnostics: List[Diagnostics], options: dict) -> None:
        var     = options['var']
        sim_idx = options.get('sim_index', 0)
        lat_deg = options.get('lat_deg', 0.0)

        diag = diagnostics[sim_idx]
        lon  = diag.coords['lon']
        lat  = diag.coords['lat']
        Pmid_hPa = diag.coords['Pmid'] / 100.0

        data3d = _get_field(diag, var, is_3d=True)   # (nlev, nlat, nlon)

        # Find nearest latitude index
        lat_idx    = int(np.argmin(np.abs(lat - lat_deg)))
        lat_actual = float(lat[lat_idx])
        outfile    = options.get('output', f'results/{var}_lonpres_lat{lat_actual:.1f}.png')

        data = data3d[:, lat_idx, :]                  # (nlev, nlon)

        LON, PRES = np.meshgrid(lon, Pmid_hPa)

        fig, ax = plt.subplots(figsize=(9, 6))
        cf = ax.contourf(LON, PRES, data, levels=20, cmap='viridis')
        ax.contour(LON, PRES, data, levels=20, colors='k',
                   linewidths=0.3, alpha=0.4)
        _add_colorbar(fig, ax, cf, var)
        _pressure_axis(ax, Pmid_hPa)

        ax.set_xlabel('Longitude (°)')
        ax.set_title(f'{var} at {lat_actual:.1f}°  —  {diag.label}')
        plt.tight_layout()
        save_figure(fig, outfile)
        print(f'lon-pressure section written to {outfile}')
