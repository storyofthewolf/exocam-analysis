#!/usr/bin/env python  

# make_plots.py


import pickle
import plotting

# load profiles saved by run_analysis.py
with open('profiles.pkl', 'rb') as f:
    profiles = pickle.load(f)

plotting.plot_vert_profiles(profiles)
    
plotting.plot_vert_profiles_2x2(profiles,
                                top=[0,1],
                                bottom=[4,5,6,7],
                                top_title='Earth-similar',
                                bottom_title='TRAPPIST-1 e',
                                labels=['modern', 'no O3',
                                        'ben1', 'ben2', 'hab1', 'hab2'])
