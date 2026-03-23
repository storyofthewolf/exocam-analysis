# analysis_utils.py
#
#
#
#  Contains functions for inputs, outputs, and basic plotting
#

import sys
import numpy as np
import exocampy_tools as exo

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# // read_file_list //
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def read_file_list():

    with open('files.in', 'r') as file:
        root = file.readline()
        root = root.rstrip("\n")
        num = file.readline()
        num = int(num)
        filelist = np.array([None] * num, dtype=object)
        grav     = np.array([None] * num, dtype=float)
        mwdry    = np.array([None] * num, dtype=float)
        for i in range(num):
            j=i+1
            line_in = file.readline()             
            line_in = line_in.split()
            filelist[i] = line_in[0]
            if len(line_in) > 2:
                grav[i]  = line_in[1]
                mwdry[i] = line_in[2]
            else:
                grav[i]  = 9.81
                mwdry[i] = 28.966

    return root, num, filelist, grav, mwdry

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# // print global mean data to file //
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def print_data_to_file(num, filelist_short, datacube, varnames, nostrout):

    outfile = "analysis_output.txt"

    char_count_array = np.array([len(s) for s in filelist_short])                      
    maxchar = np.amax(char_count_array)
    istr = "i   filenames"
    istr = "{:<{}}".format(istr, maxchar+4) 
    format_real = "{:10.4f}"
    format_exp  = "{:10.4e}"
    format_string = "{:>10}"
    index = np.where(np.array(datacube[:,0]) != 0.0)[0]

    with open(outfile,"w") as f:
        for i in range(num):

            endstr = ' '
            ii=i+1
            if ii==1:
                # This prints the header information
                print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~", file=f)
                print("CESM ExoCAM diagnostic output using analysis.py", file=f)
                print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~", file=f)
                print(istr, end=endstr,flush=True, file=f)
                for j in index:
                    if (j == np.amax(index)): endstr=('\n')
                    print(format_string.format(varnames[j]), flush=True,  end=endstr, file=f)
                endstr =' '
            # This prints file index and name
            if (nostrout == False):
                if ii < 10:   istr2 = str(ii) + '   ' + filelist_short[i]
                if ii >= 10:  istr2 = str(ii) + '  '  + filelist_short[i]
                if ii >= 100: istr2 = str(ii) + ' '   + filelist_short[i]
            if (nostrout == True):
                if ii < 10:   istr2 = str(ii) + '   '
                if ii >= 10:  istr2 = str(ii) + '  '
                if ii >= 100: istr2 = str(ii) + ' '
            istr2 = "{:<{}}".format(istr2, maxchar+4)
            print(istr2, end=endstr, flush=True, file=f)
            for j in index:                
                # This prints the output data
                if (varnames[j] == "Q_STRAT"): 
                    format_number = format_exp
                else:
                    format_number = format_real
                if (j == np.amax(index)): endstr=('\n')
                print(format_number.format(datacube[j,i]), end=endstr, flush=True,  file=f)
    print("output data written to ", outfile)

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# // calculate global mean profiles //
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def calc_gmean_profiles(lon, lat, var):
    nlev = var.shape[0]   
    var_gmean = np.zeros((nlev), dtype=float)

    for z in range(nlev):    
        temp_in      = var[z,:,:] ; temp_in = np.squeeze(temp_in)
        temp_out     =  exo.area_weighted_avg(lon, lat, temp_in)
        var_gmean[z] = temp_out
        
    return var_gmean


#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# // calculate lapse rate, tropopause, and stratosphere 
# // temperature and pressure levels 
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def tprofile_diags(pmid, tmid, zint, tint):
    # pressure input on the midlayers
    # temperatures and height input on interfaces
    nlev = pmid.shape[0]   
    lapse_rate = np.zeros((nlev), dtype=float)
    for z in range(nlev):
        deltaT      = (tint[z-1]   - tint[z])
        deltaZ      = (zint[z-1] - zint[z])
        lapse_rate[z] = (-1)*deltaT/(deltaZ/1000.0) 

    # define tropopause as the minimum temperature
    t_tropo = np.min(tmid)
    i_tropo = np.where(tmid[:] == np.min(tmid[:]))
    p_tropo = pmid[i_tropo]
    #print("itropo ", i_tropo, t_tropo, p_tropo)
    
    # define stratosphere temperature as maximum temperature
    # at or above the already defined tropopause
    stratcol = np.where(pmid[:] <= p_tropo)
    t_strat  = np.max(tmid[stratcol])
    i_strat  = np.where(tmid[:] == max(tmid[stratcol]))
    p_strat  = pmid[i_strat] 
    #print("strat ", i_strat, t_strat, p_strat)
   
    return lapse_rate, i_tropo, i_strat

