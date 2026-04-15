#!/usr/bin/env python

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# run_analysis.py                                                                        
#                                                                                    
# Author Eric Wolf                                                                   
# June 2023                                                                          
#                                                                                    
# Purpose:  Analysis of a single file or small batch of files
#                                                                                    
# Notes:  Currently this code only deals with global mean quantities.
#                                                                                    
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


import netCDF4 as nc
import numpy as np
import exocampy_tools as exo
import argparse
import os
import analysis_utils
import plotting
import sys
import pickle


# input arguments and options                                                                                                      
parser = argparse.ArgumentParser()
parser.add_argument('--quiet',         action='store_true', help='do not print to screen')
parser.add_argument('--printdata',     action='store_true', help='print output text files')
parser.add_argument('--vert',          action='store_true', help='calculate vertical profiles')
parser.add_argument('--synch',         action='store_true', help='calculate substellar/antistellar means')
parser.add_argument('--cf',            action='store_true', help='tabulate clear sky fluxes and cloud forcings')
parser.add_argument('--nostrout',      action='store_true', help='remove string type from output text file')
parser.add_argument('--filename',      type=str, default=None,
                                       help='single netcdf file to analyze (overrides files.in)')
parser.add_argument('--grav',          type=float, default=9.81,
                                       help='gravity for --filename mode (default: 9.81)')
parser.add_argument('--mwdry',         type=float, default=28.966,
                                       help='dry air molecular weight for --filename mode (default: 28.966)')

args = parser.parse_args()

# ---------------------------------------------------------------
# build filelist either from command line or files.in
# ---------------------------------------------------------------
if args.filename is not None:
    # command line mode: single file, split into root + short name
    # so the rest of the script sees the same variables as always
    root           = os.path.dirname(os.path.abspath(args.filename))
    filelist_short = np.array([os.path.basename(args.filename)], dtype=object)
    num            = 1
    grav           = np.array([args.grav],  dtype=float)
    mwdry          = np.array([args.mwdry], dtype=float)
    filelist       = np.array([os.path.abspath(args.filename)], dtype='U200')
else:
    # default mode: read batch list from files.in
    root, num, filelist_short, grav, mwdry = analysis_utils.read_file_list()
    filelist = np.empty(num, dtype='U200')
    filelist[:] = root + '/' + filelist_short[:]

# define vector arrays of variables explored
nvars = 50
datacube = np.zeros((nvars, num), dtype=float)
varnames = np.empty(nvars, dtype='U100')

# accumulate vertical profile data across files when --vert is active.
profiles = []

print(' ')
print('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
print('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
print('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
print(' Entering run_analysis.py ')
if args.filename is not None:
    print(' file read from command line argument --filename')
else:
    print(' files read in from files.in ')

if args.vert == True:
    print("If using Z vertical coordinates, make sure to set gravity and mwdry in files.in")


# read in climate data from netcdf
for i in range(num):

    if args.quiet == False: 
        print('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
    print('~~~ ', filelist[i])
    if args.vert == True:
        print('~~~ gravity = ', grav[i])
        print('~~~ mwdry = ', mwdry[i])

    ncid = nc.Dataset(filelist[i], 'r')

    lon  = ncid.variables['lon'][:]
    lat  = ncid.variables['lat'][:]
    lev  = ncid.variables['lev'][:]
    hyai = ncid.variables['hyai'][:]
    hybi = ncid.variables['hybi'][:]
    hyam = ncid.variables['hyam'][:]
    hybm = ncid.variables['hybm'][:]

    nlat = lat.size
    nlon = lon.size
    nlev = lev.size

    # pressures
    PS     = ncid.variables['PS'][:]          ; PS = np.squeeze(PS)    
    P0     = ncid.variables['P0'][:]          ; P0 = np.squeeze(P0)
   

    # temperature variables
    TS     = ncid.variables['TS'][:]          ; TS = np.squeeze(TS)
    T      = ncid.variables['T'][:]           ; T  = np.squeeze(T)

    # ice and snow
    ICEFRAC = ncid.variables['ICEFRAC'][:]    ; ICEFRAC = np.squeeze(ICEFRAC)

    # water variables
    Q      = ncid.variables['Q'][:]           ; Q       = np.squeeze(Q)
    RELHUM = ncid.variables['RELHUM'][:]      ; RELHUM  = np.squeeze(RELHUM)
    TMQ    = ncid.variables['TMQ'][:]         ; TMQ     = np.squeeze(TMQ)

    # cloud water
    CLDLIQ   = ncid.variables['CLDLIQ'][:]    ; CLDLIQ    = np.squeeze(CLDLIQ)
    CLDICE   = ncid.variables['CLDICE'][:]    ; CLDICE    = np.squeeze(CLDICE)
    TGCLDLWP = ncid.variables['TGCLDLWP'][:]  ; TGCLDLWP  = np.squeeze(TGCLDLWP)
    TGCLDIWP = ncid.variables['TGCLDIWP'][:]  ; TGCLDIWP  = np.squeeze(TGCLDIWP)

    # cloud fractions
    CLOUD    = ncid.variables['CLOUD'][:]      ; CLOUD    = np.squeeze(CLOUD)
    CLDTOT   = ncid.variables['CLDTOT'][:]     ; CLDTOT    = np.squeeze(CLDTOT)
    CLDLOW   = ncid.variables['CLDLOW'][:]     ; CLDLOW    = np.squeeze(CLDLOW)
    CLDMED   = ncid.variables['CLDMED'][:]     ; CLDMED    = np.squeeze(CLDMED)
    CLDHGH   = ncid.variables['CLDHGH'][:]     ; CLDHGH    = np.squeeze(CLDHGH)

    # energy
    FLNT   = ncid.variables['FLNT'][:]    ; FLNT      = np.squeeze(FLNT)
    FSNT   = ncid.variables['FSNT'][:]    ; FSNT      = np.squeeze(FSNT)

    if 'FSDTOA' in ncid.variables:
        FSDTOA = ncid.variables['FSDTOA'][:]  ; FSDTOA    = np.squeeze(FSDTOA)

    FLNS    = ncid.variables['FLNS'][:]   ; FLNS      = np.squeeze(FLNS)
    FSNS    = ncid.variables['FSNS'][:]   ; FSNS      = np.squeeze(FSNS)
    LHFLX   = ncid.variables['LHFLX'][:]  ; LHFLX     = np.squeeze(LHFLX)
    SHFLX   = ncid.variables['SHFLX'][:]  ; SHFLX     = np.squeeze(SHFLX)

    # fluxes
    FUL   = ncid.variables['FUL'][:]    ; FUL    = np.squeeze(FUL)
    FDL   = ncid.variables['FDL'][:]    ; FDL    = np.squeeze(FDL)
    FUS   = ncid.variables['FUS'][:]    ; FUS    = np.squeeze(FUS)
    FDS   = ncid.variables['FDS'][:]    ; FDS    = np.squeeze(FDS)

    # heating/cooling rates
    QRS   = ncid.variables['QRS'][:]    ; QRS    = np.squeeze(QRS)
    QRL   = ncid.variables['QRL'][:]    ; QRL    = np.squeeze(QRL)

    if args.cf == True:
        FLNTC  = ncid.variables['FLNTC'][:]   ; FLNTC    = np.squeeze(FLNTC)
        FSNTC  = ncid.variables['FSNTC'][:]   ; FSNTC    = np.squeeze(FSNTC)
        FULC   = ncid.variables['FULC'][:]    ; FULC    = np.squeeze(FULC)
        FDLC   = ncid.variables['FDLC'][:]    ; FDLC    = np.squeeze(FDLC)
        FUSC   = ncid.variables['FUSC'][:]    ; FUSC    = np.squeeze(FUSC)
        FDSC   = ncid.variables['FDSC'][:]    ; FDSC    = np.squeeze(FDSC)

    ncid.close()


    ############################################################################
    ########  compute area weighted averages and derived quantities  ###########
    TS_gmean             = exo.area_weighted_avg(lon, lat, TS)
    ICEFRAC_gmean        = exo.area_weighted_avg(lon, lat, ICEFRAC)
    TMQ_gmean            = exo.area_weighted_avg(lon, lat, TMQ)
    TGCLDLWP_gmean       = exo.area_weighted_avg(lon, lat, TGCLDLWP)
    TGCLDIWP_gmean       = exo.area_weighted_avg(lon, lat, TGCLDIWP)
    CLDTOT_gmean         = exo.area_weighted_avg(lon, lat, CLDTOT)
    FLNT_gmean           = exo.area_weighted_avg(lon, lat, FLNT)
    FSNT_gmean           = exo.area_weighted_avg(lon, lat, FSNT)
    FLNS_gmean           = exo.area_weighted_avg(lon, lat, FLNS)
    FSNS_gmean           = exo.area_weighted_avg(lon, lat, FSNS)
    SHFLX_gmean          = exo.area_weighted_avg(lon, lat, SHFLX)
    LHFLX_gmean          = exo.area_weighted_avg(lon, lat, LHFLX)
    if 'FSDTOA' in ncid.variables:
        FSDTOA_gmean     = exo.area_weighted_avg(lon, lat, FSDTOA)
    temp                 = FUL[0,:,:] ; temp = np.squeeze(temp)
    FULTOA_gmean         = exo.area_weighted_avg(lon, lat, temp)
    temp                 = FDL[0,:,:] ; temp = np.squeeze(temp)
    FDLTOA_gmean         = exo.area_weighted_avg(lon, lat, temp)
    temp                 = FUS[0,:,:] ; temp = np.squeeze(temp)
    FUSTOA_gmean         = exo.area_weighted_avg(lon, lat, temp)
    temp                 = FDS[0,:,:] ; temp = np.squeeze(temp)
    FDSTOA_gmean         = exo.area_weighted_avg(lon, lat, temp)
    temp                 = FUL[nlev,:,:] ; temp = np.squeeze(temp)
    FULSRF_gmean         = exo.area_weighted_avg(lon, lat, temp)
    temp                 = FDL[nlev,:,:] ; temp = np.squeeze(temp)
    FDLSRF_gmean         = exo.area_weighted_avg(lon, lat, temp)
    temp                 = FUS[nlev,:,:] ; temp = np.squeeze(temp)
    FUSSRF_gmean         = exo.area_weighted_avg(lon, lat, temp)
    temp                 = FDS[nlev,:,:] ; temp = np.squeeze(temp)
    FDSSRF_gmean         = exo.area_weighted_avg(lon, lat, temp)

    if args.cf == True:
        FLNTC_gmean           = exo.area_weighted_avg(lon, lat, FLNTC)
        FSNTC_gmean           = exo.area_weighted_avg(lon, lat, FSNTC)
        temp                  = FULC[0,:,:] ; temp = np.squeeze(temp)
        FULCTOA_gmean         = exo.area_weighted_avg(lon, lat, temp)
        temp                  = FDLC[0,:,:] ; temp = np.squeeze(temp)
        FDLCTOA_gmean         = exo.area_weighted_avg(lon, lat, temp)
        temp                  = FUSC[0,:,:] ; temp = np.squeeze(temp)
        FUSCTOA_gmean         = exo.area_weighted_avg(lon, lat, temp)
        temp                  = FDSC[0,:,:] ; temp = np.squeeze(temp)
        FDSCTOA_gmean         = exo.area_weighted_avg(lon, lat, temp)
        temp                  = FULC[nlev,:,:] ; temp = np.squeeze(temp)
        FULCSRF_gmean         = exo.area_weighted_avg(lon, lat, temp)
        temp                  = FDLC[nlev,:,:] ; temp = np.squeeze(temp)
        FDLCSRF_gmean         = exo.area_weighted_avg(lon, lat, temp)
        temp                  = FUSC[nlev,:,:] ; temp = np.squeeze(temp)
        FUSCSRF_gmean         = exo.area_weighted_avg(lon, lat, temp)
        temp                  = FDSC[nlev,:,:] ; temp = np.squeeze(temp)
        FDSCSRF_gmean         = exo.area_weighted_avg(lon, lat, temp)

        # calculate cloud forcings
        lw_cldforc = np.zeros((nlat, nlon), dtype=float)
        sw_cldforc = np.zeros((nlat, nlon), dtype=float)
        for x in range(nlon):
            for y in range(nlat):
                sw_cldforc[y,x] = FSNT[y,x]  - FSNTC[y,x]
                lw_cldforc[y,x] = FLNTC[y,x] - FLNT[y,x]
        temp                  = sw_cldforc[:,:] ; temp = np.squeeze(temp)
        sw_cldforc_gmean         = exo.area_weighted_avg(lon, lat, temp)
        temp                  = lw_cldforc[:,:] ; temp = np.squeeze(temp)
        lw_cldforc_gmean         = exo.area_weighted_avg(lon, lat, temp)


    toa_albedo_gmean     = FUSTOA_gmean/FDSTOA_gmean
    srf_albedo_gmean     = FUSSRF_gmean/FDSSRF_gmean
    toa_balance_gmean    = FSNT_gmean - FLNT_gmean
    srf_balance_gmean    = FSNS_gmean - FLNS_gmean - SHFLX_gmean - LHFLX_gmean
    energy               = FSNT[:,:] - FLNT[:,:] 
    energy_gmean         = exo.area_weighted_avg(lon, lat, energy)

    # define global pressure coordinate arrays
    G = grav[i]
    R = 8.314462/(mwdry[i]/1000.)
    lev_P, ilev_P = exo.hybrid2pressure(nlon, nlat, nlev, PS, P0, hyam, hybm, hyai, hybi)
    lev_Z, ilev_Z = exo.hybrid2height(nlon, nlat, nlev, PS, P0, hyam, hybm, hyai, hybi, T, G, R)
    
    # do vertical profiles
    # this is slow, so only do when requested
    if args.vert == True:
        # define global mean profiles
        Pmid_profile = analysis_utils.calc_gmean_profiles(lon, lat, lev_P)
        Pint_profile = analysis_utils.calc_gmean_profiles(lon, lat, ilev_P)
        Tmid_profile = analysis_utils.calc_gmean_profiles(lon, lat, T)
        Qmid_profile = analysis_utils.calc_gmean_profiles(lon, lat, Q)
        # create Tint_profile
        Tint_profile = np.zeros((nlev+1), dtype=float)
        Tint_profile[nlev] = TS_gmean    
        Tint_profile[0] = Tmid_profile[0]    
        for z in range(nlev-1):
            Tint_profile[z+1] = (Tmid_profile[z] + Tmid_profile[z+1])/2.
        Zmid_profile = analysis_utils.calc_gmean_profiles(lon, lat, lev_Z)
        Zint_profile = analysis_utils.calc_gmean_profiles(lon, lat, ilev_Z)
        # run temperature profile diagnostics for lapse rate, 
        # stratosphere max temperature and tropopause
        lapse_rate, itropo, istrat = analysis_utils.tprofile_diags(Pmid_profile, Tmid_profile, Zint_profile, Tint_profile)
        T_STRAT_gmean = Tmid_profile[istrat]
        T_TROPO_gmean = Tmid_profile[itropo]
        Q_STRAT_gmean = Qmid_profile[itropo]
        if args.quiet == False:
            print("-------------- midlayer profile ----------------")
            for g in range(nlev):
                print(g, Pmid_profile[g], Zmid_profile[g], Tmid_profile[g], lapse_rate[g])
            print("-------------- interface profile ----------------")
            for g in range(nlev+1):
                print(g, Pint_profile[g], Zint_profile[g], Tint_profile[g])

        profiles.append({
            'label'      : filelist_short[i],
            'Pmid'       : Pmid_profile.copy(),
            'T'          : Tmid_profile.copy(),
            'Q'          : Qmid_profile.copy(),
            'lapse_rate' : lapse_rate.copy(),
        })


    # top layer temperature, water vapor and clouds
    PTOP = lev_P[0,:,:] 
    PTOP_gmean =  exo.area_weighted_avg(lon, lat, PTOP)
    TTOP = T[0,:,:] 
    TTOP_gmean =  exo.area_weighted_avg(lon, lat, TTOP)
    QTOP = Q[0,:,:] 
    QTOP_gmean =  exo.area_weighted_avg(lon, lat, QTOP)
    CLDICE_TOP = CLDICE[0,:,:] 
    CLDICE_TOP_gmean =  exo.area_weighted_avg(lon, lat, CLDICE_TOP)
    CLDLIQ_TOP = CLDLIQ[0,:,:] 
    CLDLIQ_TOP_gmean =  exo.area_weighted_avg(lon, lat, CLDLIQ_TOP)

    # compute substellar and antistellar means
    if args.synch == True:
        TS_SS       = np.zeros((nlat, nlon), dtype=float)
        TS_AS       = np.zeros((nlat, nlon), dtype=float)
        CLDTOT_SS   = np.zeros((nlat, nlon), dtype=float)
        CLDTOT_AS   = np.zeros((nlat, nlon), dtype=float)
        TGCLDLWP_SS = np.zeros((nlat, nlon), dtype=float)
        TGCLDLWP_AS = np.zeros((nlat, nlon), dtype=float)
        TGCLDIWP_SS = np.zeros((nlat, nlon), dtype=float)
        TGCLDIWP_AS = np.zeros((nlat, nlon), dtype=float)
        FLNT_SS     = np.zeros((nlat, nlon), dtype=float)
        FLNT_AS     = np.zeros((nlat, nlon), dtype=float)
        if args.cf == True:
            lw_cldforc_AS = np.zeros((nlat, nlon), dtype=float)
            lw_cldforc_SS = np.zeros((nlat, nlon), dtype=float)

        for x in range(nlon):
            for y in range(nlat):
                if (FDS[0,y,x] >  0.0):
                    TS_SS[y,x]         = TS[y,x]          ;  TS_AS[y,x]         = -999.0
                    CLDTOT_SS[y,x]     = CLDTOT[y,x]      ;  CLDTOT_AS[y,x]     = -999.0
                    TGCLDIWP_SS[y,x]   = TGCLDIWP[y,x]    ;  TGCLDIWP_AS[y,x]   = -999.0
                    TGCLDLWP_SS[y,x]   = TGCLDLWP[y,x]    ;  TGCLDLWP_AS[y,x]   = -999.0
                    FLNT_SS[y,x]       = FLNT[y,x]        ;  FLNT_AS[y,x]       = -999.0
                    if args.cf == True:
                        lw_cldforc_SS[y,x] = lw_cldforc[y,x]  ;  lw_cldforc_AS[y,x] = -999.0
                else:
                    TS_SS[y,x]         = -999.0           ;  TS_AS[y,x]         = TS[y,x]
                    CLDTOT_SS[y,x]     = -999.0           ;  CLDTOT_AS[y,x]     = CLDTOT[y,x]
                    TGCLDIWP_SS[y,x]   = -999.0           ;  TGCLDIWP_AS[y,x]   = TGCLDIWP[y,x]
                    TGCLDLWP_SS[y,x]   = -999.0           ;  TGCLDLWP_AS[y,x]   = TGCLDLWP[y,x]
                    FLNT_SS[y,x]       = -999.0           ;  FLNT_AS[y,x]       = FLNT[y,x]
                    if args.cf == True:
                        lw_cldforc_SS[y,x] = -999.0           ;  lw_cldforc_AS[y,x] = lw_cldforc[y,x]

        TS_SS_gmean          = exo.area_weighted_avg(lon, lat, TS_SS)
        TS_AS_gmean          = exo.area_weighted_avg(lon, lat, TS_AS)
        CLDTOT_SS_gmean      = exo.area_weighted_avg(lon, lat, CLDTOT_SS)
        CLDTOT_AS_gmean      = exo.area_weighted_avg(lon, lat, CLDTOT_AS)
        TGCLDLWP_SS_gmean    = exo.area_weighted_avg(lon, lat, TGCLDLWP_SS)
        TGCLDLWP_AS_gmean    = exo.area_weighted_avg(lon, lat, TGCLDLWP_AS)
        TGCLDIWP_SS_gmean    = exo.area_weighted_avg(lon, lat, TGCLDIWP_SS)
        TGCLDIWP_AS_gmean    = exo.area_weighted_avg(lon, lat, TGCLDIWP_AS)
        FLNT_SS_gmean        = exo.area_weighted_avg(lon, lat, FLNT_SS)
        FLNT_AS_gmean        = exo.area_weighted_avg(lon, lat, FLNT_AS)
        lw_cldforc_SS_gmean  = exo.area_weighted_avg(lon, lat, lw_cldforc_SS)
        lw_cldforc_AS_gmean  = exo.area_weighted_avg(lon, lat, lw_cldforc_AS)

    if args.quiet == False:
        ########  print global mean quantities  ###########    
        print("------------------ global mean ------------------")
        print("TS mean ", TS_gmean)
        if args.synch == True:
            print("TS_SS, TS_AS ", TS_SS_gmean, TS_AS_gmean)
        print("TS max, TS min ", np.max(TS[:,:]), np.min(TS[:,:]))
        print("T max, T min ", np.max(T[:,:,:]), np.min(T[:,:,:]))
        print("ICEFRAC", ICEFRAC_gmean)
        print("toa albedo ", toa_albedo_gmean)
        print("srf albedo ", srf_albedo_gmean)
        print("TMQ TGCLDLWP TGCLDIWP ", TMQ_gmean, TGCLDLWP_gmean, TGCLDIWP_gmean)
        print("CLDTOT ", CLDTOT_gmean)
        if args.synch == True:
            print("CLDTOT_SS, CLDTOT_AS ", CLDTOT_SS_gmean, CLDTOT_AS_gmean)
            print("TGCLDLWP_SS, TGCLDLWP_AS ", TGCLDLWP_SS_gmean, TGCLDLWP_AS_gmean)
            print("TGCLDIWP_SS, TGCLDIWP_AS ", TGCLDIWP_SS_gmean, TGCLDIWP_AS_gmean)
        print("TOA ENERGY BALANCE ", toa_balance_gmean, energy_gmean)
        print("SRF ENERGY BALANCE ", srf_balance_gmean)
        print("FLNT FSNT", FLNT_gmean, FSNT_gmean)
        if args.synch == True:
            print("FLNT_SS, FLNT_AS ", FLNT_SS_gmean, FLNT_AS_gmean)
        if 'FSDTOA' in ncid.variables: print("FSDTOA", FSDTOA_gmean)
        print("LW FLUXES ", FULTOA_gmean, FDLTOA_gmean, FULTOA_gmean - FDLTOA_gmean)
        print("SW FLUXES ", FUSTOA_gmean, FDSTOA_gmean, FDSTOA_gmean - FUSTOA_gmean)
        print("TOP ", PTOP_gmean, TTOP_gmean, QTOP_gmean)
        if args.cf == True:
            print("FLNTC FSNTC", FLNTC_gmean, FSNTC_gmean)
            print("CLEAR-SKY LW FLUXES ", FULCTOA_gmean, FDLCTOA_gmean, FULCTOA_gmean - FDLCTOA_gmean)
            print("CLEAR-SKY SW FLUXES ", FUSCTOA_gmean, FDSCTOA_gmean, FDSCTOA_gmean - FUSCTOA_gmean)
            print("SW CLOUD FORCING ", sw_cldforc_gmean)
            print("LW CLOUD FORCING ", lw_cldforc_gmean)
            if args.synch == True:
                print("LW CLOUD FORCING SS ", lw_cldforc_SS_gmean)
                print("LW CLOUD FORCING AS ", lw_cldforc_AS_gmean)

    x=0
    datacube[x,i] = TS_gmean          ; varnames[x] = 'TS'        ; x=x+1
    if (args.vert == True):
        datacube[x,i] = T_STRAT_gmean ; varnames[x] = 'T_STRAT'   ; x=x+1
        datacube[x,i] = T_TROPO_gmean ; varnames[x] = 'T_TROPO'   ; x=x+1
    datacube[x,i] = ICEFRAC_gmean     ; varnames[x] = 'ICEFRAC'   ; x=x+1
    datacube[x,i] = toa_albedo_gmean  ; varnames[x] = 'TOAALB'    ; x=x+1
    datacube[x,i] = FULTOA_gmean      ; varnames[x] = 'OLR'       ; x=x+1
    datacube[x,i] = toa_balance_gmean ; varnames[x] = 'toaEBAL'   ; x=x+1
    datacube[x,i] = srf_balance_gmean ; varnames[x] = 'srfEBAL'   ; x=x+1
    datacube[x,i] = TMQ_gmean         ; varnames[x] = 'TMQ'       ; x=x+1
    datacube[x,i] = TGCLDLWP_gmean    ; varnames[x] = 'TGCLDLWP'  ; x=x+1
    datacube[x,i] = TGCLDIWP_gmean    ; varnames[x] = 'TGCLDIWP'  ; x=x+1
    datacube[x,i] = CLDTOT_gmean      ; varnames[x] = 'CLDTOT'    ; x=x+1
    if (args.cf == True):
        datacube[x,i] = sw_cldforc_gmean      ; varnames[x] = 'CLDFORC_LW'    ; x=x+1
        datacube[x,i] = lw_cldforc_gmean      ; varnames[x] = 'CLDFORC_SW'    ; x=x+1
    if (args.vert == True):
        datacube[x,i] = Q_STRAT_gmean ; varnames[x] = 'Q_STRAT'   ; x=x+1
    
# output global mean quantities to a text file
if args.printdata == True:
    analysis_utils.print_data_to_file(num, filelist_short, datacube, varnames, args.nostrout)

# generate vertical profile plots if requested
if args.vert == True:
    with open('profiles.pkl', 'wb') as f:
        pickle.dump(profiles, f)
    plotting.plot_vert_profiles(profiles)

    
print('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
print(' Exiting run_analysis.py ... ')
print(' ... i hope you found the answers that you seek ')
print('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
print('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
print('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
print(' ')
