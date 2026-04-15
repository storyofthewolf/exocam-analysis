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
from plots.base import Plot, setup_pressure_axis
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
        outfile   = options.get('output', f'map_{var}.png')

        diag = diagnostics[sim_idx]
        lon  = diag.coords['lon']
        lat  = diag.coords['lat']

        # Try 2D first, then slice from 3D
        if var in diag.fields_2d:
            data = diag.fields_2d[var]          # (nlat, nlon)
        elif var in diag.fields_3d:
            data = diag.fields_3d[var][lev_index]  # (nlat, nlon)
            outfile = options.get('output', f'map_{var}_lev{lev_index}.png')
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
        ax.set_title(f'{var}  —  {diag.label}')
        plt.tight_layout()
        plt.savefig(outfile, dpi=150, bbox_inches='tight')
        plt.close(fig)
        print(f'map plot written to {outfile}')


# ================================================================
#  section_latpres
# ================================================================

@register_plot('section_latpres')
class SectionLatPres(Plot):
    """Latitude × pressure zonal mean cross-section.

    YAML options
    ------------
    var        : 3D variable name (must be in fields_3d)
    sim_index  : index into diagnostics list (default: 0)
    zonal_mean : average over longitude before plotting (default: True)
    output     : output filename (default: section_<var>_latpres.png)
    """

    def render(self, diagnostics: List[Diagnostics], options: dict) -> None:
        var        = options['var']
        sim_idx    = options.get('sim_index', 0)
        zonal_mean = options.get('zonal_mean', True)
        outfile    = options.get('output', f'section_{var}_latpres.png')

        diag = diagnostics[sim_idx]
        lat  = diag.coords['lat']
        Pmid_hPa = diag.coords['Pmid'] / 100.0   # Pa → hPa

        data3d = _get_field(diag, var, is_3d=True)   # (nlev, nlat, nlon)

        if zonal_mean:
            data = np.mean(data3d, axis=2)            # (nlev, nlat)
        else:
            data = data3d[:, :, 0]                    # first longitude (fallback)

        LAT, PRES = np.meshgrid(lat, Pmid_hPa)

        fig, ax = plt.subplots(figsize=(8, 6))
        cf = ax.contourf(LAT, PRES, data, levels=20, cmap='viridis')
        ax.contour(LAT, PRES, data, levels=20, colors='k',
                   linewidths=0.3, alpha=0.4)
        _add_colorbar(fig, ax, cf, var)
        _pressure_axis(ax, Pmid_hPa)

        ax.set_xlabel('Latitude (°)')
        title = f'{var} (zonal mean)' if zonal_mean else f'{var}'
        ax.set_title(f'{title}  —  {diag.label}')
        plt.tight_layout()
        plt.savefig(outfile, dpi=150, bbox_inches='tight')
        plt.close(fig)
        print(f'lat-pressure section written to {outfile}')


# ================================================================
#  section_lonpres
# ================================================================

@register_plot('section_lonpres')
class SectionLonPres(Plot):
    """Longitude × pressure cross-section at a specified latitude.

    Particularly useful for tidally locked planets where the equatorial
    substellar-to-antistellar transect is dynamically significant.

    YAML options
    ------------
    var       : 3D variable name (must be in fields_3d)
    sim_index : index into diagnostics list (default: 0)
    lat_deg   : latitude of the cross-section in degrees (default: 0.0 = equator)
    output    : output filename (default: section_<var>_lonpres.png)
    """

    def render(self, diagnostics: List[Diagnostics], options: dict) -> None:
        var     = options['var']
        sim_idx = options.get('sim_index', 0)
        lat_deg = options.get('lat_deg', 0.0)
        outfile = options.get('output', f'section_{var}_lonpres.png')

        diag = diagnostics[sim_idx]
        lon  = diag.coords['lon']
        lat  = diag.coords['lat']
        Pmid_hPa = diag.coords['Pmid'] / 100.0

        data3d = _get_field(diag, var, is_3d=True)   # (nlev, nlat, nlon)

        # Find nearest latitude index
        lat_idx = int(np.argmin(np.abs(lat - lat_deg)))
        lat_actual = float(lat[lat_idx])

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
        plt.savefig(outfile, dpi=150, bbox_inches='tight')
        plt.close(fig)
        print(f'lon-pressure section written to {outfile}')
