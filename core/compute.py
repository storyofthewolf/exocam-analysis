# core/compute.py
#
# All derived quantities for ExoCAM analysis.
# Takes a raw dict from core/reader.py and returns a Diagnostics object.
#
# Public entry point:
#   compute_all(raw, label, options) -> Diagnostics
#
# Internal helpers:
#   _compute_global_means    -- area-weighted averages of standard fields
#   _compute_cloud_forcing   -- clear-sky fluxes and cloud radiative effect
#   _compute_synch_means     -- substellar / antistellar hemisphere means
#   _compute_vertical_profile -- global mean profiles + T diagnostics
#   _tprofile_diags          -- lapse rate, tropopause, stratosphere indices
#

import numpy as np
from core.data_model import Diagnostics, VerticalProfile
from core.coords import (hybrid2pressure, hybrid2height,
                         area_weighted_avg, calc_gmean_profiles)


# ================================================================
#  Temperature profile diagnostics
# ================================================================

def _tprofile_diags(pmid, tmid, zint, tint):
    """Compute lapse rate, tropopause, and stratosphere from mean profiles.

    Arguments
    ---------
    pmid : pressure at midlevels (Pa), shape (nlev,)
    tmid : temperature at midlevels (K), shape (nlev,)
    zint : height at interfaces (m), shape (nlev+1,)
    tint : temperature at interfaces (K), shape (nlev+1,)

    Returns
    -------
    lapse_rate : K/km at each midlevel, shape (nlev,)
    i_tropo    : index of tropopause (minimum T in column)
    i_strat    : index of stratosphere warmest point above tropopause
    """
    nlev = pmid.shape[0]
    lapse_rate = np.zeros(nlev)
    for z in range(nlev):
        deltaT = tint[z - 1] - tint[z]
        deltaZ = zint[z - 1] - zint[z]
        lapse_rate[z] = -deltaT / (deltaZ / 1000.0)

    i_tropo = int(np.argmin(tmid))
    p_tropo = pmid[i_tropo]

    stratcol = np.where(pmid <= p_tropo)[0]
    i_strat  = int(np.argmax(tmid[stratcol]))
    i_strat  = stratcol[i_strat]

    return lapse_rate, i_tropo, i_strat


# ================================================================
#  Global mean scalars
# ================================================================

def _compute_global_means(raw: dict) -> dict:
    """Compute area-weighted global means for all standard fields."""
    lon, lat = raw['lon'], raw['lat']
    nlev     = raw['nlev']
    gm = {}

    # Surface and column quantities
    gm['TS']       = area_weighted_avg(lon, lat, raw['TS'])
    gm['ICEFRAC']  = area_weighted_avg(lon, lat, raw['ICEFRAC'])
    gm['TMQ']      = area_weighted_avg(lon, lat, raw['TMQ'])
    gm['TGCLDLWP'] = area_weighted_avg(lon, lat, raw['TGCLDLWP'])
    gm['TGCLDIWP'] = area_weighted_avg(lon, lat, raw['TGCLDIWP'])
    gm['CLDTOT']   = area_weighted_avg(lon, lat, raw['CLDTOT'])
    gm['FLNT']     = area_weighted_avg(lon, lat, raw['FLNT'])
    gm['FSNT']     = area_weighted_avg(lon, lat, raw['FSNT'])
    gm['FLNS']     = area_weighted_avg(lon, lat, raw['FLNS'])
    gm['FSNS']     = area_weighted_avg(lon, lat, raw['FSNS'])
    gm['SHFLX']    = area_weighted_avg(lon, lat, raw['SHFLX'])
    gm['LHFLX']    = area_weighted_avg(lon, lat, raw['LHFLX'])

    # TOA fluxes (index 0 = top of atmosphere)
    gm['FULTOA'] = area_weighted_avg(lon, lat, raw['FUL'][0])
    gm['FDLTOA'] = area_weighted_avg(lon, lat, raw['FDL'][0])
    gm['FUSTOA'] = area_weighted_avg(lon, lat, raw['FUS'][0])
    gm['FDSTOA'] = area_weighted_avg(lon, lat, raw['FDS'][0])

    # Surface fluxes (index nlev = bottom interface)
    gm['FULSRF'] = area_weighted_avg(lon, lat, raw['FUL'][nlev])
    gm['FDLSRF'] = area_weighted_avg(lon, lat, raw['FDL'][nlev])
    gm['FUSSRF'] = area_weighted_avg(lon, lat, raw['FUS'][nlev])
    gm['FDSSRF'] = area_weighted_avg(lon, lat, raw['FDS'][nlev])

    # Optional FSDTOA
    if raw.get('FSDTOA') is not None:
        gm['FSDTOA'] = area_weighted_avg(lon, lat, raw['FSDTOA'])

    # Derived quantities
    gm['OLR']         = gm['FULTOA']
    gm['toa_albedo']  = gm['FUSTOA'] / gm['FDSTOA']
    gm['srf_albedo']  = gm['FUSSRF'] / gm['FDSSRF']
    gm['toa_balance'] = gm['FSNT'] - gm['FLNT']
    gm['srf_balance'] = gm['FSNS'] - gm['FLNS'] - gm['SHFLX'] - gm['LHFLX']
    energy_2d         = raw['FSNT'] - raw['FLNT']
    gm['energy_balance'] = area_weighted_avg(lon, lat, energy_2d)

    # Top-of-model layer diagnostics
    gm['PTOP']      = area_weighted_avg(lon, lat, raw['PS'] * 0 + 0)  # placeholder, set below
    gm['PTOP']      = area_weighted_avg(lon, lat, raw['T'][0] * 0)    # dummy; overwritten

    return gm


def _compute_top_layer(raw: dict, lev_P: np.ndarray) -> dict:
    """Global means of top-model-layer quantities."""
    lon, lat = raw['lon'], raw['lat']
    gm = {}
    gm['PTOP']       = area_weighted_avg(lon, lat, lev_P[0])
    gm['TTOP']       = area_weighted_avg(lon, lat, raw['T'][0])
    gm['QTOP']       = area_weighted_avg(lon, lat, raw['Q'][0])
    gm['CLDICE_TOP'] = area_weighted_avg(lon, lat, raw['CLDICE'][0])
    gm['CLDLIQ_TOP'] = area_weighted_avg(lon, lat, raw['CLDLIQ'][0])
    return gm


# ================================================================
#  Cloud forcing
# ================================================================

def _compute_cloud_forcing(raw: dict) -> dict:
    """Clear-sky fluxes and cloud radiative effect."""
    lon, lat = raw['lon'], raw['lat']
    nlev     = raw['nlev']
    gm = {}

    gm['FLNTC'] = area_weighted_avg(lon, lat, raw['FLNTC'])
    gm['FSNTC'] = area_weighted_avg(lon, lat, raw['FSNTC'])

    gm['FULCTOA'] = area_weighted_avg(lon, lat, raw['FULC'][0])
    gm['FDLCTOA'] = area_weighted_avg(lon, lat, raw['FDLC'][0])
    gm['FUSCTOA'] = area_weighted_avg(lon, lat, raw['FUSC'][0])
    gm['FDSCTOA'] = area_weighted_avg(lon, lat, raw['FDSC'][0])

    gm['FULCSRF'] = area_weighted_avg(lon, lat, raw['FULC'][nlev])
    gm['FDLCSRF'] = area_weighted_avg(lon, lat, raw['FDLC'][nlev])
    gm['FUSCSRF'] = area_weighted_avg(lon, lat, raw['FUSC'][nlev])
    gm['FDSCSRF'] = area_weighted_avg(lon, lat, raw['FDSC'][nlev])

    # Cloud radiative effect (CRE)
    sw_cldforc = raw['FSNT'] - raw['FSNTC']
    lw_cldforc = raw['FLNTC'] - raw['FLNT']
    gm['sw_cldforc'] = area_weighted_avg(lon, lat, sw_cldforc)
    gm['lw_cldforc'] = area_weighted_avg(lon, lat, lw_cldforc)

    # Return lw_cldforc 2D field too — needed for synch computation
    gm['_lw_cldforc_2d'] = lw_cldforc

    return gm


# ================================================================
#  Substellar / antistellar means
# ================================================================

def _compute_synch_means(raw: dict, cf_means: dict = None) -> dict:
    """Substellar and antistellar hemisphere means for tidally locked planets.

    The day/night mask is based on the top-of-atmosphere downwelling SW flux
    (FDS[0] > 0 → substellar hemisphere).
    """
    lon, lat = raw['lon'], raw['lat']
    FV       = -999.0   # fill value for masked hemisphere

    # Day/night mask: True where substellar (FDS > 0 at TOA)
    ss_mask = raw['FDS'][0] > 0.0     # (nlat, nlon) bool

    def split(field2d):
        """Return (ss_field, as_field) with fill on the non-contributing side."""
        ss = np.where(ss_mask, field2d, FV)
        as_ = np.where(~ss_mask, field2d, FV)
        return ss, as_

    gm = {}

    for var in ('TS', 'CLDTOT', 'TGCLDLWP', 'TGCLDIWP', 'FLNT'):
        ss, as_ = split(raw[var])
        gm[f'{var}_SS'] = area_weighted_avg(lon, lat, ss)
        gm[f'{var}_AS'] = area_weighted_avg(lon, lat, as_)

    if cf_means is not None:
        lw2d = cf_means['_lw_cldforc_2d']
        ss, as_ = split(lw2d)
        gm['lw_cldforc_SS'] = area_weighted_avg(lon, lat, ss)
        gm['lw_cldforc_AS'] = area_weighted_avg(lon, lat, as_)

    return gm


# ================================================================
#  Vertical profiles
# ================================================================

def _compute_vertical_profile(raw: dict, label: str,
                               lev_P: np.ndarray, lev_Z: np.ndarray,
                               ilev_P: np.ndarray, ilev_Z: np.ndarray) -> tuple:
    """Compute global mean vertical profiles and T diagnostics.

    Returns (VerticalProfile, profile_global_means_dict)
    """
    lon, lat = raw['lon'], raw['lat']
    nlev     = raw['nlev']

    Pmid_profile = calc_gmean_profiles(lon, lat, lev_P)
    Pint_profile = calc_gmean_profiles(lon, lat, ilev_P)
    Tmid_profile = calc_gmean_profiles(lon, lat, raw['T'])
    Qmid_profile = calc_gmean_profiles(lon, lat, raw['Q'])
    Zmid_profile = calc_gmean_profiles(lon, lat, lev_Z)
    Zint_profile = calc_gmean_profiles(lon, lat, ilev_Z)

    # Interface temperature: interpolate from midlevel T, with surface = TS_gmean
    TS_gmean     = area_weighted_avg(lon, lat, raw['TS'])
    Tint_profile = np.zeros(nlev + 1)
    Tint_profile[nlev] = TS_gmean
    Tint_profile[0]    = Tmid_profile[0]
    for z in range(nlev - 1):
        Tint_profile[z + 1] = (Tmid_profile[z] + Tmid_profile[z + 1]) / 2.0

    lapse_rate, i_tropo, i_strat = _tprofile_diags(
        Pmid_profile, Tmid_profile, Zint_profile, Tint_profile)

    profile = VerticalProfile(
        label      = label,
        Pmid       = Pmid_profile,
        T          = Tmid_profile,
        Q          = Qmid_profile,
        lapse_rate = lapse_rate,
        Z          = Zmid_profile,
    )

    profile_gm = {
        'T_TROPO': Tmid_profile[i_tropo],
        'T_STRAT': Tmid_profile[i_strat],
        'Q_STRAT': Qmid_profile[i_tropo],
    }

    return profile, profile_gm, Pmid_profile, Pint_profile, Zmid_profile, Zint_profile, Tint_profile


# ================================================================
#  Main entry point
# ================================================================

def compute_all(raw: dict, label: str, options: dict) -> Diagnostics:
    """Compute all requested quantities and return a Diagnostics object.

    Arguments
    ---------
    raw     : dict returned by core.reader.read_ncfile()
    label   : short name for this simulation (filename or config label)
    options : dict of boolean flags:
                vert   -- compute vertical profiles
                cf     -- compute cloud forcing
                synch  -- compute substellar/antistellar means

    Returns
    -------
    Diagnostics object
    """
    do_vert  = options.get('vert',  False)
    do_cf    = options.get('cf',    False)
    do_synch = options.get('synch', False)

    lon, lat = raw['lon'], raw['lat']
    nlev     = raw['nlev']
    nlon     = raw['nlon']
    nlat     = raw['nlat']
    G        = raw['grav']
    R        = 8.314462 / (raw['mwdry'] / 1000.0)

    # Always compute pressure coordinates (needed for top-layer diagnostics)
    lev_P, ilev_P = hybrid2pressure(
        nlon, nlat, nlev,
        raw['PS'], raw['P0'],
        raw['hyam'], raw['hybm'],
        raw['hyai'], raw['hybi'],
    )

    # Global mean pressure profile (cheap; always stored in coords)
    Pmid_mean = np.mean(lev_P, axis=(1, 2))   # (nlev,) hPa after /100

    # --- global means ---
    global_means = _compute_global_means(raw)
    # fix PTOP placeholder with actual lev_P
    global_means.pop('PTOP', None)
    global_means.update(_compute_top_layer(raw, lev_P))

    # --- cloud forcing ---
    cf_means = None
    if do_cf:
        cf_means = _compute_cloud_forcing(raw)
        # store public keys only
        global_means.update({k: v for k, v in cf_means.items()
                              if not k.startswith('_')})

    # --- synch ---
    synch_means = None
    if do_synch:
        synch_means = _compute_synch_means(raw, cf_means if do_cf else None)
        global_means.update(synch_means)

    # --- vertical profile ---
    profile     = None
    lev_Z = ilev_Z = None
    if do_vert:
        lev_Z, ilev_Z = hybrid2height(
            nlon, nlat, nlev,
            raw['PS'], raw['P0'],
            raw['hyam'], raw['hybm'],
            raw['hyai'], raw['hybi'],
            raw['T'], G, R,
        )
        (profile, profile_gm,
         Pmid_prof, Pint_prof,
         Zmid_prof, Zint_prof,
         Tint_prof) = _compute_vertical_profile(
            raw, label, lev_P, lev_Z, ilev_P, ilev_Z)
        global_means.update(profile_gm)

    # --- coordinates ---
    coords = {
        'lon':  lon,
        'lat':  lat,
        'lev':  raw['lev'],
        'Pmid': Pmid_mean,   # (nlev,) Pa — mean pressure profile for plot axes
    }

    return Diagnostics(
        label        = label,
        coords       = coords,
        global_means = global_means,
        profile      = profile,
        synch_means  = synch_means if do_synch else None,
        fields_2d    = raw.get('_cache_2d', {}),
        fields_3d    = raw.get('_cache_3d', {}),
    )
