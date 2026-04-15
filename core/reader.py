# core/reader.py
#
# Pure netCDF extraction for ExoCAM/CESM output files.
# No computation — just reads variables and returns a raw dict of arrays.
# All arrays are squeezed to remove singleton time dimensions.
#

import numpy as np
import netCDF4 as nc


# Variables always read from every file
_VARS_2D = [
    'PS', 'TS', 'ICEFRAC', 'TMQ', 'TGCLDLWP', 'TGCLDIWP',
    'CLDTOT', 'CLDLOW', 'CLDMED', 'CLDHGH',
    'FLNT', 'FSNT', 'FLNS', 'FSNS', 'LHFLX', 'SHFLX',
]
_VARS_3D = ['T', 'Q', 'RELHUM', 'CLDLIQ', 'CLDICE', 'CLOUD', 'QRS', 'QRL']
_VARS_FLUX = ['FUL', 'FDL', 'FUS', 'FDS']   # shape (nlev+1, nlat, nlon)

# Clear-sky variables (only read when cf=True)
_VARS_CF_2D = ['FLNTC', 'FSNTC']
_VARS_CF_FLUX = ['FULC', 'FDLC', 'FUSC', 'FDSC']

# Optional variables (read if present)
_VARS_OPTIONAL_2D = ['FSDTOA']


def read_ncfile(filepath: str,
                grav: float = 9.81,
                mwdry: float = 28.966,
                cf: bool = False,
                fields_2d: list = None,
                fields_3d: list = None) -> dict:
    """Read one ExoCAM netCDF file and return a raw dict of arrays.

    Arguments
    ---------
    filepath  : absolute path to the netCDF file
    grav      : gravitational acceleration (m s-2), used later in compute.py
    mwdry     : dry air molecular weight (g/mol), used later in compute.py
    cf        : if True, also read clear-sky flux variables
    fields_2d : additional 2D variable names to read and store for caching
    fields_3d : additional 3D variable names to read and store for caching

    Returns
    -------
    raw : dict of numpy arrays plus scalar metadata
    """
    fields_2d = fields_2d or []
    fields_3d = fields_3d or []

    raw = {'filepath': filepath, 'grav': grav, 'mwdry': mwdry}

    with nc.Dataset(filepath, 'r') as ncid:

        # --- coordinate dimensions ---
        raw['lon']  = ncid.variables['lon'][:]
        raw['lat']  = ncid.variables['lat'][:]
        raw['lev']  = ncid.variables['lev'][:]
        raw['hyai'] = ncid.variables['hyai'][:]
        raw['hybi'] = ncid.variables['hybi'][:]
        raw['hyam'] = ncid.variables['hyam'][:]
        raw['hybm'] = ncid.variables['hybm'][:]

        raw['nlat'] = int(raw['lat'].size)
        raw['nlon'] = int(raw['lon'].size)
        raw['nlev'] = int(raw['lev'].size)

        raw['P0'] = float(np.squeeze(ncid.variables['P0'][:]))

        # --- standard 2D and 3D variables ---
        for vname in _VARS_2D:
            raw[vname] = np.squeeze(ncid.variables[vname][:])

        for vname in _VARS_3D:
            raw[vname] = np.squeeze(ncid.variables[vname][:])

        for vname in _VARS_FLUX:
            raw[vname] = np.squeeze(ncid.variables[vname][:])

        # --- optional variables (read if present) ---
        for vname in _VARS_OPTIONAL_2D:
            if vname in ncid.variables:
                raw[vname] = np.squeeze(ncid.variables[vname][:])
            else:
                raw[vname] = None

        # --- clear-sky variables ---
        if cf:
            for vname in _VARS_CF_2D:
                raw[vname] = np.squeeze(ncid.variables[vname][:])
            for vname in _VARS_CF_FLUX:
                raw[vname] = np.squeeze(ncid.variables[vname][:])

        # --- on-demand fields for contour plot caching ---
        raw['_cache_2d'] = {}
        for vname in fields_2d:
            if vname in ncid.variables:
                raw['_cache_2d'][vname] = np.squeeze(ncid.variables[vname][:])
            else:
                print(f'  warning: requested cache field {vname} not found in {filepath}')

        raw['_cache_3d'] = {}
        for vname in fields_3d:
            if vname in ncid.variables:
                raw['_cache_3d'][vname] = np.squeeze(ncid.variables[vname][:])
            else:
                print(f'  warning: requested cache field {vname} not found in {filepath}')

    return raw
