##!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Sep 15 14:32:59 2020

@author: jolenebritton
@ Assumption: (Kevin) A segment that undergoes fusion cannot create any new branches. A segment that gets fused to, 
@                        cannot create any new branches if it has not already done so.
"""

import csv
import numpy as np
# import pandas as pd
import os
import time
import pickle
from joblib import Parallel, delayed
import multiprocessing
import matplotlib.pyplot as plt
import seaborn as sns
import argparse

num_cores = multiprocessing.cpu_count()

cwd_path='D:/Fungi_new_v4'
# cwd_path ='/Users/libra/Desktop/FBI_FungalGrowth-Bill1'
#cwd_path ='/Users/d3k137/docs/projects/boltzmann/code/06212017/run/fungal_growth/FBI_FungalGrowth2'
#cwd_path = '/scratch/d3k137'
#os.chdir(cwd_path)

import helper_functions as hf
import growth_functions as gf
import nutrient_functions2 as nf
import setup_functions as sf
# Load in parameters as a dictionary
global params

msg = "Adding description"
# Initialize parser
parser = argparse.ArgumentParser(description = msg)
parser.add_argument("-i", "--Input", help = "Show Input")
# Read arguments from command line
args = parser.parse_args()
print(args.Input)
try:
    # Load in parameters as a dictionary
    params, config = hf.get_configs(args.Input)
except:
    print('failed to load parameters from command line')
    params, config = hf.get_configs('parameters.ini')
    #params, config = hf.get_configs('parameters_env3_anastomosis0.25.ini')
# Define string constants
left ='LEFT'
right = 'RIGHT'
left_compartment = 'LEFT_COMPARTMENT'
right_compartment = 'RIGHT_COMPARTMENT'
enzyme_level = 'ENZYME_LEVEL'
deltag0 = 'DGZERO'
deltag0_sigma = 'DGZERO StdDev'
same_compartment = 'Same Compartment?'
full_rxn = 'Full Rxn'
    

def driver_singleNutrient(run):
    t_0 = time.time()
    reached_max_branches = False
    
    # ----------------------------------------------------------------------------
    # SET UP
    # ----------------------------------------------------------------------------
    
    # Load in parameters as a dictionary
    #params, config = hf.get_configs('parameters.ini')
    
    # Extract some commonly used parameters
    sl = params['sl']
    dt_i = params['dt_i']
    branch_rate = params['branch_rate']
    
    ###########################################################################
    ###########################################################################
    ###########################################################################
    ## Describe the type of simulation we will be running!
    # Are we doing calibration? 1 = YES, 0 = NO
    isCalibration = 0
    print('isCalibration : ', isCalibration)
    
    # Are we using the newer version of the distance to tip calculation (with
    # bias given to tips of the same branch)? 1 = YES, 0 = NO
    dist2Tip_new = 0
    print('dist2Tip_new : ', dist2Tip_new)
    
    # Is the background environment diffusion-capable? 1 = YES, 0 = NO
    try: 
        backDiff = params['diffusion_on']
    except: backDiff = 1
    print('backDiff : ', backDiff)

    # Is the nutrient background variable or fixed? If fixed, then the butrient concentration in the environment
    # is fixed at the initial value. If variable, then the nutrient concentration in the environment is updated
    # variable = 1; fixed = 0 #need to added to parameters.ini
    var_nutrient_backgrnd = params['var_nutrient_backgrnd']
    # We may/may not still want excreted compounds to diffuse, though
    if backDiff == 0:
        glucDiff = 0
        trehaDiff = 0
    

    # Is fungal fusion (anastomosis) active? 1 = YES, 0 = NO
    try: #(params['fungal_fusion'])
        fungal_fusion = params['fungal_fusion']
    except NameError: fungal_fusion = 0
    print('fungal_fusion : ', fungal_fusion)
    
    # Is chemoattractant released at the tip only? 1 = YES, 0 = NO
    try: #(params['isTipRelease'])
        isTipRelease = params['isTipRelease']
    except NameError: isTipRelease = 0
    print('isTipRelease : ', isTipRelease)
    
    # Is the initial condition a line or a cross? 1 = Line, 0 = Cross
    whichInitialCondition = 0
    print('whichInitialCondition : ', whichInitialCondition)
    
    # Is active transport (translocation) active for both gluc and trehalose in the
    # fungal colony? 1 = YES, 0 = NO
    isActiveTrans = 1
    print('isActiveTrans : ', isActiveTrans)
    
    # Is the branching restricted to N segment away from the tip?
    # 0 = Unbiased branching
    # 1 = No branching
    # N = 2,3,... branching only occur N segment away from the tip.
    # Why N = 2 would be the minimum? Because in the current setup, a segment
    # directly behind the tip is not enclosed by two septa hence not eligible
    # for branching.
    try:
        restrictBranching = params['restrictBranching']
    except NameError: restrictBranching = 3
    print('restrictBranching : ', restrictBranching)
    
    # Is the initial background environment with 'patchy' nutrient distribution?
    # 1 = YES, 0 = NO
    try: 
        isPatchyExtEnvironment = params['is_pathchyEnv']
    except NameError: isPatchyExtEnvironment = 0
    print('isPatchyExtEnvironment : ', isPatchyExtEnvironment)
    
    if (isPatchyExtEnvironment == 1):
        ## There are currently 5 presets of the non-homogeneous randomized
        ## nutrient distribution. setBackground = 1,2,3,4,or 5 will determine 
        ## the set to use.
        ## setBackground = 1,2,3 have 50 nutrient foci
        ## setBackground = 4,5 have 100 nutrient foci
        try: 
            setBackground = params['setPatchyEnv']
        except NameError: setBackground = 3
        print('Patchy Background : ', setBackground)
    
    # Is the cell wall convection (active transport) scaled by local metabolism 
    # activity? 1 = YES, 0 = NO
    isConvectDependOnMetabo_cw = 1
    print('isConvectDependOnMetabo_cw : ', isConvectDependOnMetabo_cw)
    
    # Is the glucose convection (active transport) scaled by local metabolism 
    # activity? 1 = YES, 0 = NO
    isConvectDependOnMetabo_gluc = 1
    print('isConvectDependOnMetabo_gluc : ', isConvectDependOnMetabo_gluc)
    
    # Is the trehalose convection (active transport) scaled by local metabolism 
    # activity? 1 = YES, 0 = NO
    isConvectDependOnMetabo_treha = 1
    print('isConvectDependOnMetabo_treha : ', isConvectDependOnMetabo_treha)
    
    # What is the probability for fusion to be established?
    try: 
        chance_to_fuse = params['chance_to_fuse']
    except NameError: chance_to_fuse = 0.5
    print('The probability for fungal fusion is set to : ', chance_to_fuse)
    
    ###########################################################################
    ###########################################################################
    ###########################################################################
    
    
    
    # breakpoint()
    # Set up external grid and glucose amounts in each cell
    if (isPatchyExtEnvironment == 0):
        x_vals, y_vals, sub_e_gluc, sub_e_treha = sf.external_grid(params)
    else:
        x_vals, y_vals, sub_e_gluc, sub_e_treha = sf.external_grid_patchy(setBackground, params, run+1)
    
    folder_string, param_string = hf.get_filepath(params)
    # Create appropriate folder
    if not os.path.exists('Results/{}/Run{}'.format(param_string, run)):
        try:
            os.makedirs('Results/{}/Run{}'.format(param_string, run))
        except FileExistsError:
            print('File exists error:', 'Results/{}/Run{}'.format(param_string, run))
        except:
            print('Failed to create folder:', 'Results/{}/Run{}'.format(param_string, run))
   
    grid_file = "Results/{}/Run{}/grid_coordinates_temp.txt".format(param_string, run)
    thisfile = open(grid_file,'w')
    for i in range(np.shape(x_vals)[0]): 
        print(x_vals[i],y_vals[i],file=thisfile)
    thisfile.close()
    
    # Plotting label scaling parameters for external domain
    num_ticks = 11 # number of tick labels to appear
    yticks = np.linspace(0, len(x_vals)-1, num_ticks, dtype=np.int64)
    yticklabels = np.around(np.linspace(-sl*params['grid_scale_val'], sl*params['grid_scale_val'], num_ticks),3) 

    # File path for saving results
    folder_string, param_string = hf.get_filepath(params)
    if not os.path.exists('Results/{}/Run{}'.format(param_string, run)):
        os.makedirs('Results/{}/Run{}'.format(param_string, run))
    
    # Save copy of the parameters used
    params_file = 'Results/{}/Run{}/{}_params.ini'.format(param_string,
                                                          run,
                                                          param_string)
    with open(params_file, 'w') as configfile:    # save
        config.write(configfile)
    
    # Initialize lists for saving stats
    count_branches = []
    count_tips = []
    count_radii = []
    count_max_radii = []
    count_avg_radii = []
    count_rms_radii = []
    count_rms_tip_radii = []
    count_times = []
    count_biomass = []
    total_length_progression = []
    
    
    # ----------------------------------------------------------------------------
    # INITIAL CONDITIONS
    # ----------------------------------------------------------------------------
    
    # Initialize mycelia dictionary
    # environ_type = 'control' or 'gm41'
    mycelia = sf.mycelia_dict(params)
    
    # Initialize time
    current_time = 0
    
    # Initial mycelia centered at origin
    num_segs = params['init_segs_count']
    if (whichInitialCondition == 1):
        mycelia, num_branches, num_total_segs, dtt = sf.initial_conditions_line(mycelia, num_segs, x_vals, y_vals,params)
    elif (whichInitialCondition == 0):
        mycelia, num_branches, num_total_segs, dtt = sf.initial_conditions_cross(mycelia, num_segs, x_vals, y_vals, params)
    
    # ----------------------------------------------------------------------------
    # GROW THAT FUNGUS!
    # ----------------------------------------------------------------------------
    current_step = 2
    
    # Initialize values for storing computational times
    time_extend = 0
    time_branch = 0
    time_external = 0
    time_translocation = 0
    time_uptake = 0
    
    step_size_extern = 1
    
    #hf.plot_fungus(mycelia, num_total_segs, current_time, folder_string, param_string, params, run)
    #hf.plot_fungus_gluc(mycelia, num_total_segs, current_time, folder_string, param_string, params, run)
    #hf.plot_fungus_generic(mycelia, num_total_segs, current_time, folder_string, param_string, params, run)
    try: 
        restart = params['restart']
    except NameError: restart = 0
    if (restart == 1):
            try:
                restart_file = "Results/{}/Run{}/restart.pkl".format(param_string, run)
            except:
                print('No restart file found:', restart_file)
    elif (restart == 2):
            try:
                restart_file = params['restart_file']
            except NameError: restart_file = "restart_test.pkl"
    if (restart > 0):
            try:
                file = open(restart_file,'rb')
            except: 
                print('No restart file found:', restart_file)   
            
            mycelia = pickle.load(file)
            num_total_segs = pickle.load(file)
            dtt = pickle.load(file)
            sub_e_gluc = pickle.load(file)
            sub_e_treha = pickle.load(file)
            current_time = pickle.load(file)
            file.close()
            N = round(len(x_vals)/2)-2
    
    if (restart == 0):
        # Plot the initial nutrient background:
        glucose_ext = sub_e_gluc/params['vol_grid']*1e12 # Convert to molar quantities for display
        max_e_gluc = np.max(glucose_ext)
        hf.plot_externalsub(sub_e_gluc, yticks, yticklabels, 0.0, max_e_gluc, 'Se', folder_string, param_string, params, run)


    print_increment = 1
    print('Start: Current time: ', current_time, 'Final time: ', params['final_time'])
    while current_time < params['final_time']: 
        # Convert units
        if params['plot_units_time'] == 'days':
            plot_time = current_time / (60*60*24)
        elif params['plot_units_time'] == 'hours':
            plot_time = current_time / (60*60)
        elif params['plot_units_time'] == 'minutes':
            plot_time = current_time / 60
        elif params['plot_units_time'] == 'seconds':
            plot_time = current_time
        print('Time: ', plot_time, params['plot_units_time'])
        
        #Loop over updates for external diffusion and uptake by fungi    
        ntimes = np.floor(params['dt_i']/ params['dt_e'])
        if (ntimes < 1):
            print('Internal time step is less than external time step:')
            print('Assumption in simulation is that internal time step is greater than external time step.')
            breakpoint()
        if ((glucDiff ==0) and (trehaDiff == 0)):
            ntimes = 1
            params['dt_e'] = params['dt_i']
        this_time = 0
        while(this_time < ntimes):
            this_time = this_time + 1
            if current_step % step_size_extern == 0:  
                # EXTERNAL NUTRIENT
                tE_0 = time.time()
                # sub_e_gluc = nf.rk_update(sub_e_gluc, 'glucose', step_size_extern)
                ##################################################################
                ######################## Background Diffusion ####################
                ##################################################################            
            
                if (glucDiff != 0):
                    sub_e_gluc = nf.diffusion_ADI(sub_e_gluc, params['dt_e'],params)
                if (trehaDiff != 0):
                    sub_e_treha = nf.diffusion_ADI_treha(sub_e_treha, params['dt_e'],params)
                    # if np.min(sub_e_gluc)<1e-17:
                    #     breakpoint()
                    if np.min(sub_e_treha)<0:
                        # if np.min(sub_e_treha)<-1e12:
                            # breakpoint()    
                        negativeTreha = np.where(sub_e_treha<0.0)[:]
                        sub_e_treha[negativeTreha] = 0.0
            
                ##################################################################
                ######################## Background Diffusion ####################
                ##################################################################
                # breakpoint()
                tE_1 = time.time()
                time_external = (tE_1 - tE_0)
        
            # UPTAKE
            tU_0 = time.time()
            mycelia = nf.uptake(sub_e_gluc, mycelia, num_total_segs, var_nutrient_backgrnd, params['dt_e'],params)
            # mycelia = nf.uptake(sub_e_gluc, sub_e_treha, mycelia, num_total_segs, var_nutrient_backgrnd)
            tU_1 = time.time()
            time_uptake = (tU_1 - tU_0)
        # end while
        
        # RELEASE
        mycelia = nf.release(sub_e_treha, mycelia, num_total_segs, isTipRelease, params)
        if (np.isnan(np.sum(mycelia['cw_i'][:num_total_segs]))):
            breakpoint()
               
        # TRANSLOCATION
        tT_0 = time.time()
        
        mycelia = nf.transloc(mycelia, params, num_total_segs, dtt, isActiveTrans,
                              whichInitialCondition,
                              isConvectDependOnMetabo_cw,
                              isConvectDependOnMetabo_gluc,
                              isConvectDependOnMetabo_treha)
        if (np.isnan(np.sum(mycelia['cw_i'][:num_total_segs]))):
                breakpoint()
        
        tT_1 = time.time()
        time_translocation = (tT_1 - tT_0)
        

        
        # EXTENSION (GROWTH)
        tG_0 = time.time()
        
        old_num_total_segs = num_total_segs
        # breakpoint()
        mycelia, num_total_segs, dtt = gf.extension(mycelia, params, num_total_segs, 
                                        dtt, x_vals, y_vals,isCalibration, 
                                        dist2Tip_new, fungal_fusion,
                                        chance_to_fuse, branch_rate, sub_e_gluc)
        #if(np.any(np.isnan(mycelia['cw_i'][:num_total_segs]))):
        #    breakpoint()
        
        #if (old_num_total_segs > num_total_segs):
        #   breakpoint()
       
        tG_1 = time.time()
        time_extend = (tG_1 - tG_0)
        
        # BRANCHING
        #if(num_total_segs > 9):
        #    breakpoint()

        tB_0 = time.time()

        old_num_total_segs = num_total_segs 
        #adj_branch_rate = branch_rate/ntimes
        #adj_branch_rate = branch_rate*(params['kg1_wall']/params['sl'])*ntimes#*params['dt_i']
        n = (params['sl']/params['kg1_wall'])/params['dt_i']
        adj_branch_rate = 1 - (branch_rate**(1/n))
        adj_branch_rate = branch_rate
        if any(np.where(mycelia['can_branch'])[0]):
            reached_max_branches, mycelia, num_total_segs, dtt = gf.branching(mycelia, sub_e_gluc, params, 
                                        num_total_segs, dtt, x_vals, y_vals, 
                                        isCalibration, dist2Tip_new, 
                                        fungal_fusion, restrictBranching,
                                        chance_to_fuse, adj_branch_rate)
        if reached_max_branches == True:
            print ('Reached maximum number of branches:', np.max(mycelia['cw_i'])[0])
            breakpoint()
            break
        if (old_num_total_segs > num_total_segs):
           breakpoint()
        tB_1 = time.time()
        if (np.isnan(np.sum(mycelia['cw_i'][:num_total_segs]))):
                breakpoint()
        time_branch = (tB_1 - tB_0)
            
        if current_step % (4*160) == 0: 
            if (np.isnan(np.sum(mycelia['cw_i'][:num_total_segs]))):
                breakpoint()
            num_seg = np.where(mycelia['branch_id'][:num_total_segs] > -1)[0]
            num_branch = np.max(mycelia['branch_id'][:num_total_segs])
            print('Current number of active segments : ', len(num_seg))
            print('Current number of active branch : ', (num_branch))

        #if(current_time > 24*3600*10):
        #    grd_density = sf.grid_density(mycelia, sub_e_gluc, num_total_segs) 
        #    print('Max grid density = ', np.max(grd_density))

        print('time_expternal: ',time_external)
        print('time_uptake: ',time_uptake)
        print('time_translocation: ',time_translocation)
        print('time_extend: ',time_extend)
        print('time_branch: ',time_branch)
        #print('time_total: ',time_total)

        print_time = 2*3600*print_increment # print every 4 hours
        # PLOT & SAVE DATA
        if (current_time > print_time):
            print_increment = print_increment+1        
            if(current_time > 24*3600*10):
                grd_density = sf.grid_density(mycelia, sub_e_gluc, num_total_segs) 
                print('Max grid density = ', np.max(grd_density))
            
        #if (current_time > 0.25* print_time):
            file_name = "Results/{}/Run{}/restart_t={}.pkl".format(param_string, run, current_time)
            file = open(file_name,'wb')
            pickle.dump(mycelia,file)
            pickle.dump(num_total_segs,file)
            pickle.dump(dtt,file)
            pickle.dump(sub_e_gluc,file)
            pickle.dump(sub_e_treha,file)
            pickle.dump(current_time,file)
            file.flush()
            os.fsync(file.fileno()) 
            file.close()

        # if current_step % (4*160) == 0: 
        # if current_step % (1*160) == 0:
            # breakpoint()
            hf.plot_fungus(mycelia, num_total_segs, current_time, folder_string, param_string, params, run)
            hf.plot_fungus_gluc(mycelia, num_total_segs, current_time, folder_string, param_string, params, run)
            # hf.plot_fungus_generic(mycelia, num_total_segs, current_time, folder_string, param_string, params, run)
            hf.plot_fungus_treha(mycelia, num_total_segs, current_time, folder_string, param_string, params, run)
            if 1>0:#params['init_sub_e_gluc'] > 1e-15:
                # hf.plot_externalsub(sub_e_gluc, yticks, yticklabels, current_time, params['init_sub_e_gluc'], 'Se', folder_string, param_string, params, run)
                glucose_ext = sub_e_gluc/params['vol_grid']*1e12 # Convert to molar quantities for display
                max_e_gluc = np.max(glucose_ext)
                print('max_e_gluc : ', max_e_gluc)
                hf.plot_externalsub(sub_e_gluc, yticks, yticklabels, current_time, max_e_gluc, 'Se', folder_string, param_string, params, run)
                hf.plot_externalsub_hyphae(sub_e_gluc, mycelia, num_total_segs, yticks, yticklabels, current_time, params['init_sub_e_gluc'], 'Se', folder_string, param_string, params, run)
                treha_ext = sub_e_treha/params['vol_grid']*1e12 # Convert to molar quantities for display
                max_e_treha = np.max(treha_ext)
                # max_e_treha_fixed = 1e-11
                if trehaDiff == 1:
                    hf.plot_externalsub_treha(sub_e_treha, yticks, yticklabels, current_time, max_e_treha, 'Se', folder_string, param_string, params, run)
                    hf.plot_externalsub_treha_hyphae(sub_e_treha, mycelia, num_total_segs, yticks, yticklabels, current_time, max_e_treha, 'Se', folder_string, param_string, params, run)
            
            # dist_from_center = []
            # for i in range(num_total_segs):
            #     if mycelia['branch_id'][i]==-1:
            #         mycelia['dist_from_center'][i] = 0.0
            #         continue
            #     mycelia['dist_from_center'][i] = (np.sqrt(mycelia['xy2'][i][0]**2 + mycelia['xy2'][i][1]**2))
            DONT_INCLUDE = np.where(mycelia['branch_id'][:num_total_segs] == -1)[0]
            DO_INCLUDE = np.where(mycelia['branch_id'][:num_total_segs]>-1)[0]
            total_length = 0.0
            for i in range(len(DO_INCLUDE)):
                mycelia['dist_from_center'][DO_INCLUDE[i]] = (np.sqrt(mycelia['xy2'][DO_INCLUDE[i]][0]**2 + mycelia['xy2'][DO_INCLUDE[i]][1]**2))
                total_length += (np.sqrt((mycelia['xy2'][DO_INCLUDE[i]][0] - mycelia['xy1'][DO_INCLUDE[i]][0])**2 + (mycelia['xy2'][DO_INCLUDE[i]][1] - mycelia['xy1'][DO_INCLUDE[i]][1])**2))
            total_length_progression.append(total_length)
            mycelia['dist_from_center'][DONT_INCLUDE] = 0.0;
            hf.plot_hist(mycelia, current_time, num_total_segs, param_string, params, run)
            
            count_branches.append(max(mycelia['branch_id'])[0]+1)
            count_tips.append(np.count_nonzero(mycelia['is_tip']))
            count_max_radii.append(max(np.sqrt(mycelia['xy2'][:,0]**2 + mycelia['xy2'][:,1]**2)))
            count_avg_radii.append(np.mean(np.sqrt(mycelia['xy2'][:,0]**2 + mycelia['xy2'][:,1]**2)))
            
            tip_idx = np.where(mycelia['is_tip'])[0]
            count_rms_tip_radii.append(np.sqrt(np.mean(mycelia['xy2'][tip_idx,0]**2 + mycelia['xy2'][tip_idx,1]**2)))
            count_rms_radii.append(np.sqrt(np.mean(mycelia['xy2'][:,0]**2 + mycelia['xy2'][:,1]**2)))
            
            count_times.append(current_time)
            total_biomass = np.sum(mycelia['seg_length'])*params['cross_area']*params['hy_density']
            count_biomass.append(total_biomass)
            
            N = round(len(x_vals)/2)-2
        
            avg_treha_annulus = np.zeros(N)
            max_treha_annulus = np.zeros(N)
            min_treha_annulus = np.zeros(N)
            # breakpoint()
            center_x = round(len(x_vals)/2)#np.where(x_vals == 0)[0]
            print('center_x : ', center_x)
            center_y = round(len(y_vals)/2)#np.where(y_vals == 0)[0]
            print('center_y : ', center_y)
            
            ## For "pseudo-radial" annulus on center of each cell (with 4 grid points)
            for i in range(N):
                count = 0
                min_treha = 1e5
                max_treha = -1e5
                if i == 0:
                    j = 1
                    block1 = (1/4)*(sub_e_treha[center_x, center_y] +
                                            sub_e_treha[center_x+j, center_y] +
                                            sub_e_treha[center_x, center_y+j] +
                                            sub_e_treha[center_x+j, center_y+j] )
                    if (block1 >= max_treha):
                        max_treha = block1
                    if (block1 <= min_treha):
                        min_treha = block1
                    avg_treha_annulus[i] += block1
                    
                    block2 = (1/4)*(sub_e_treha[center_x, center_y] +
                                            sub_e_treha[center_x+j, center_y] +
                                            sub_e_treha[center_x, center_y-j] +
                                            sub_e_treha[center_x+j, center_y-j] )
                    if (block2 >= max_treha):
                        max_treha = block2
                    if (block2 <= min_treha):
                        min_treha = block2
                    avg_treha_annulus[i] += block2
                    
                    block3 = (1/4)*(sub_e_treha[center_x, center_y] +
                                            sub_e_treha[center_x-j, center_y] +
                                            sub_e_treha[center_x, center_y+j] +
                                            sub_e_treha[center_x-j, center_y+j] )
                    if (block3 >= max_treha):
                        max_treha = block3
                    if (block3 <= min_treha):
                        min_treha = block3
                    avg_treha_annulus[i] += block3
                    
                    block4 = (1/4)*(sub_e_treha[center_x, center_y] +
                                            sub_e_treha[center_x-j, center_y] +
                                            sub_e_treha[center_x, center_y-j] +
                                            sub_e_treha[center_x-j, center_y-j] )
                    if (block4 >= max_treha):
                        max_treha = block4
                    if (block4 <= min_treha):
                        min_treha = block4
                    avg_treha_annulus[i] += block4
                    
                    count = 4
                
                else:
                    for j in range(0,i+1):
                        if (j < i):
                            block = (1/4)*(sub_e_treha[center_x+j, center_y+i] +
                                            sub_e_treha[center_x+j, center_y+i+1] +
                                            sub_e_treha[center_x+j+1, center_y+i] +
                                            sub_e_treha[center_x+j+1, center_y+i+1] )
                            if (block >= max_treha):
                                max_treha = block
                            if (block <= min_treha):
                                min_treha = block
                            count +=1
                            avg_treha_annulus[i] += block
                            
                            block = (1/4)*(sub_e_treha[center_x+j, center_y-i] +
                                            sub_e_treha[center_x+j, center_y-i-1] +
                                            sub_e_treha[center_x+j+1, center_y-i] +
                                            sub_e_treha[center_x+j+1, center_y-i-1] )
                            if (block >= max_treha):
                                max_treha = block
                            if (block <= min_treha):
                                min_treha = block
                            count +=1
                            avg_treha_annulus[i] += block
                            
                            block = (1/4)*(sub_e_treha[center_x-j, center_y+i] +
                                            sub_e_treha[center_x-j, center_y+i+1] +
                                            sub_e_treha[center_x-j-1, center_y+i] +
                                            sub_e_treha[center_x-j-1, center_y+i+1] )
                            if (block >= max_treha):
                                max_treha = block
                            if (block <= min_treha):
                                min_treha = block
                            count +=1
                            avg_treha_annulus[i] += block
                            
                            block = (1/4)*(sub_e_treha[center_x-j, center_y-i] +
                                            sub_e_treha[center_x-j, center_y-i-1] +
                                            sub_e_treha[center_x-j-1, center_y-i] +
                                            sub_e_treha[center_x-j-1, center_y-i-1] )
                            if (block >= max_treha):
                                max_treha = block
                            if (block <= min_treha):
                                min_treha = block
                            count +=1
                            avg_treha_annulus[i] += block
                        
                        if (j == i):
                            for k in range(0, i+1): # Say, i = 1, k varies between 0 ~ 1
                                block = (1/4)*(sub_e_treha[center_x+j, center_y+k] +
                                                sub_e_treha[center_x+j, center_y+k+1] +
                                                sub_e_treha[center_x+j+1, center_y+k] +
                                                sub_e_treha[center_x+j+1, center_y+k+1] )
                                if (block >= max_treha):
                                    max_treha = block
                                if (block <= min_treha):
                                    min_treha = block
                                count +=1
                                avg_treha_annulus[i] += block
                                
                                block = (1/4)*(sub_e_treha[center_x+j, center_y-k] +
                                                sub_e_treha[center_x+j, center_y-k-1] +
                                                sub_e_treha[center_x+j+1, center_y-k] +
                                                sub_e_treha[center_x+j+1, center_y-k-1] )
                                if (block >= max_treha):
                                    max_treha = block
                                if (block <= min_treha):
                                    min_treha = block
                                count +=1
                                avg_treha_annulus[i] += block
                                
                                block = (1/4)*(sub_e_treha[center_x-j, center_y+k] +
                                                sub_e_treha[center_x-j, center_y+k+1] +
                                                sub_e_treha[center_x-j-1, center_y+k] +
                                                sub_e_treha[center_x-j-1, center_y+k+1] )
                                if (block >= max_treha):
                                    max_treha = block
                                if (block <= min_treha):
                                    min_treha = block
                                count +=1
                                avg_treha_annulus[i] += block
                                
                                block = (1/4)*(sub_e_treha[center_x-j, center_y-k] +
                                                sub_e_treha[center_x-j, center_y-k-1] +
                                                sub_e_treha[center_x-j-1, center_y-k] +
                                                sub_e_treha[center_x-j-1, center_y-k-1] )
                                if (block >= max_treha):
                                    max_treha = block
                                if (block <= min_treha):
                                    min_treha = block
                                count +=1
                                avg_treha_annulus[i] += block
                    
                avg_treha_annulus[i] = avg_treha_annulus[i]/count
                max_treha_annulus[i] = max_treha
                min_treha_annulus[i] = min_treha
            
            ## For "pseudo-raidal" annulus on grid points only
            # for i in range(N):
            #     count = 0
            #     min_treha = 1e5
            #     max_treha = -1e5
            #     if i == 0:
            #         # continue
            #         avg_treha_annulus[i] = sub_e_treha[center_x,center_y]
            #         count+=1
            #     # elif i == 1:
            #     elif i == 1:
            #         avg_treha_annulus[i] += sub_e_treha[center_x+1, center_y+0]
            #         if (sub_e_treha[center_x+1, center_y+0] >= max_treha):
            #             max_treha = sub_e_treha[center_x+1, center_y+0]
            #         if (sub_e_treha[center_x+1, center_y+0] <= min_treha):
            #             min_treha = sub_e_treha[center_x+1, center_y+0]
            #         avg_treha_annulus[i] += sub_e_treha[center_x+1, center_y+1]
            #         if (sub_e_treha[center_x+1, center_y+1] >= max_treha):
            #             max_treha = sub_e_treha[center_x+1, center_y+1]
            #         if (sub_e_treha[center_x+1, center_y+1] <= min_treha):
            #             min_treha = sub_e_treha[center_x+1, center_y+1]
            #         avg_treha_annulus[i] += sub_e_treha[center_x+1, center_y-1]
            #         if (sub_e_treha[center_x+1, center_y-1] >= max_treha):
            #             max_treha = sub_e_treha[center_x+1, center_y-1]
            #         if (sub_e_treha[center_x+1, center_y-1] <= min_treha):
            #             min_treha = sub_e_treha[center_x+1, center_y-1]
            #         avg_treha_annulus[i] += sub_e_treha[center_x, center_y+1]
            #         if (sub_e_treha[center_x, center_y+1] >= max_treha):
            #             max_treha = sub_e_treha[center_x, center_y+1]
            #         if (sub_e_treha[center_x, center_y+1] <= min_treha):
            #             min_treha = sub_e_treha[center_x, center_y+1]
            #         avg_treha_annulus[i] += sub_e_treha[center_x, center_y-1]
            #         if (sub_e_treha[center_x, center_y-1] >= max_treha):
            #             max_treha = sub_e_treha[center_x, center_y-1]
            #         if (sub_e_treha[center_x, center_y-1] <= min_treha):
            #             min_treha = sub_e_treha[center_x, center_y-1]
            #         avg_treha_annulus[i] += sub_e_treha[center_x-1, center_y+0]
            #         if (sub_e_treha[center_x-1, center_y+0] >= max_treha):
            #             max_treha = sub_e_treha[center_x-1, center_y+0]
            #         if (sub_e_treha[center_x-1, center_y+0] <= min_treha):
            #             min_treha = sub_e_treha[center_x-1, center_y+0]
            #         avg_treha_annulus[i] += sub_e_treha[center_x-1, center_y+1]
            #         if (sub_e_treha[center_x-1, center_y+1] >= max_treha):
            #             max_treha = sub_e_treha[center_x-1, center_y+1]
            #         if (sub_e_treha[center_x-1, center_y+1] <= min_treha):
            #             min_treha = sub_e_treha[center_x-1, center_y+1]
            #         avg_treha_annulus[i] += sub_e_treha[center_x-1, center_y-1]
            #         if (sub_e_treha[center_x-1, center_y-1] >= max_treha):
            #             max_treha = sub_e_treha[center_x-1, center_y-1]
            #         if (sub_e_treha[center_x-1, center_y-1] <= min_treha):
            #             min_treha = sub_e_treha[center_x-1, center_y-1]
            #         avg_treha_annulus[i] = avg_treha_annulus[i]/8.0
            #         max_treha_annulus[i] = max_treha
            #         min_treha_annulus[i] = min_treha
            #     else:
            #         for j in range(0,i):
            #             if j <= (i-1):
            #                     avg_treha_annulus[i] += sub_e_treha[center_x+j, center_y+i]
            #                     if (sub_e_treha[center_x+j, center_y+i] >= max_treha):
            #                         max_treha = sub_e_treha[center_x+j, center_y+i]
            #                     if (sub_e_treha[center_x+j, center_y+i] <= min_treha):
            #                         min_treha = sub_e_treha[center_x+j, center_y+i]
                                
            #                     avg_treha_annulus[i] += sub_e_treha[center_x+j, center_y-i]
            #                     if (sub_e_treha[center_x+j, center_y-i] >= max_treha):
            #                         max_treha = sub_e_treha[center_x+j, center_y-i]
            #                     if (sub_e_treha[center_x+j, center_y-i] <= min_treha):
            #                         min_treha = sub_e_treha[center_x+j, center_y-i]
                                
            #                     avg_treha_annulus[i] += sub_e_treha[center_x-j, center_y+i]
            #                     if (sub_e_treha[center_x-j, center_y+i] >= max_treha):
            #                         max_treha = sub_e_treha[center_x-j, center_y+i]
            #                     if (sub_e_treha[center_x-j, center_y+i] <= min_treha):
            #                         min_treha = sub_e_treha[center_x-j, center_y+i]
                                    
            #                     avg_treha_annulus[i] += sub_e_treha[center_x-j, center_y-i]
            #                     if (sub_e_treha[center_x-j, center_y-i] >= max_treha):
            #                         max_treha = sub_e_treha[center_x-j, center_y-i]
            #                     if (sub_e_treha[center_x-j, center_y-i] <= min_treha):
            #                         min_treha = sub_e_treha[center_x-j, center_y-i]
                                    
            #                     count += 4
            #             else:
            #                 for k in range(0,i-1):
            #                     if k == 0:
            #                         avg_treha_annulus[i] += sub_e_treha[center_x+j, center_y+k]
            #                         if (sub_e_treha[center_x+j, center_y+k] >= max_treha):
            #                             max_treha = sub_e_treha[center_x+j, center_y+k]
            #                         if (sub_e_treha[center_x+j, center_y+k] <= min_treha):
            #                             min_treha = sub_e_treha[center_x+j, center_y+k]
                                    
            #                         avg_treha_annulus[i] += sub_e_treha[center_x-j, center_y+k]
            #                         if (sub_e_treha[center_x-j, center_y+k] >= max_treha):
            #                             max_treha = sub_e_treha[center_x-j, center_y+k]
            #                         if (sub_e_treha[center_x-j, center_y+k] <= min_treha):
            #                             min_treha = sub_e_treha[center_x-j, center_y+k]
                                    
            #                         count += 2
            #                     else:
            #                         avg_treha_annulus[i] += sub_e_treha[center_x+j, center_y+k]
            #                         if (sub_e_treha[center_x+j, center_y+k] >= max_treha):
            #                             max_treha = sub_e_treha[center_x+j, center_y+k]
            #                         if (sub_e_treha[center_x+j, center_y+k] <= min_treha):
            #                             min_treha = sub_e_treha[center_x+j, center_y+k]
                                    
            #                         avg_treha_annulus[i] += sub_e_treha[center_x+j, center_y-k]
            #                         if (sub_e_treha[center_x+j, center_y-i] >= max_treha):
            #                             max_treha = sub_e_treha[center_x+j, center_y-k]
            #                         if (sub_e_treha[center_x+j, center_y-i] <= min_treha):
            #                             min_treha = sub_e_treha[center_x+j, center_y-k]
                                    
            #                         avg_treha_annulus[i] += sub_e_treha[center_x-j, center_y+k]
            #                         if (sub_e_treha[center_x-j, center_y+k] >= max_treha):
            #                             max_treha = sub_e_treha[center_x-j, center_y+k]
            #                         if (sub_e_treha[center_x-j, center_y+k] <= min_treha):
            #                             min_treha = sub_e_treha[center_x-j, center_y+k]
                        
            #                         avg_treha_annulus[i] += sub_e_treha[center_x-j, center_y-k]
            #                         if (sub_e_treha[center_x-j, center_y-i] >= max_treha):
            #                             max_treha = sub_e_treha[center_x-j, center_y-k]
            #                         if (sub_e_treha[center_x-j, center_y-i] <= min_treha):
            #                             min_treha = sub_e_treha[center_x+j, center_y-k]
                                    
            #                         count += 4
                    
            #         avg_treha_annulus[i] = avg_treha_annulus[i]/count
            #         max_treha_annulus[i] = max_treha
            #         min_treha_annulus[i] = min_treha
            # breakpoint() 
                # ----------------------------------------------------------------------------
            
            # Write Current RESULTS to CSV
            # ----------------------------------------------------------------------------
            t_1 = time.time()
            num_branches = max(mycelia['branch_id'])[0]+1
            num_segs = num_total_segs
            num_tips = np.count_nonzero(mycelia['is_tip'])
            max_radii = max(np.sqrt(mycelia['xy2'][:,0]**2 + mycelia['xy2'][:,1]**2))
            avg_radii = np.mean(np.sqrt(mycelia['xy2'][:,0]**2 + mycelia['xy2'][:,1]**2))
            time_total = t_1 - t_0
            time_mins, time_secs = divmod(time_total, 60)
            min_seg_length_nonTipIdx = (np.where(mycelia['is_tip'][:num_total_segs] == False))[0]
            min_seg_length_nonTipIdx2 = (np.where(mycelia['branch_id'][min_seg_length_nonTipIdx] != -1))[0]
            max_seg_length = max(mycelia['seg_length'])[0]
            min_seg_length = 0.0
            if np.any(mycelia['seg_length'][min_seg_length_nonTipIdx[min_seg_length_nonTipIdx2]]):
                min_seg_length = min(mycelia['seg_length'][min_seg_length_nonTipIdx[min_seg_length_nonTipIdx2]])
            # breakpoint()
            potential_CFL_fail_segment = np.where(mycelia['seg_length'][:num_total_segs] < params['dt_i']*params['kg1_wall'])[0]
            CFL_fail_segment = len(np.where(mycelia['is_tip'][potential_CFL_fail_segment] == False)[0])
            #total_biomass = np.sum(mycelia['seg_length'])*params['cross_area']*params['hy_density']
    
            #count_branches.append(num_branches)
            #count_tips.append(num_tips)
            #count_radii.append(max_radii)
            #count_times.append(current_time)
            #count_biomass.append(total_biomass)
    
            #count_branches = np.array(count_branches)
            #count_tips = np.array(count_tips)
            #count_radii = np.array(count_radii)
            #count_times = np.array(count_times)
            #count_biomass = np.array(count_biomass)
            #avg_treha_annulus = np.array(avg_treha_annulus)
            #max_treha_annulus = np.array(max_treha_annulus)
            #min_treha_annulus = np.array(min_treha_annulus)
    
            output_dict = {
                'run_num' : run,
                'total_run_time': t_1-t_0,
                'array_times' : count_times,
                'total_biomass' : count_biomass,
                'max_radii' : count_max_radii,
                'avg_radii' : count_avg_radii,
                'rms_radii' : count_rms_radii,
                'rms_tip_radii' : count_rms_tip_radii,
                'array_num_branches' : count_branches,
                'array_num_tips' : count_tips,
                'array_branching_density' : np.array(count_branches)/count_tips,
                'array_radii' : count_radii,
                'array_avg_radii' : count_avg_radii,
                'num_segments_at_end' : num_segs,
                'max_seg_length' : max_seg_length,
                'min_seg_length_nonTip' : min_seg_length,
                'CFL_fail_segment ' : CFL_fail_segment,
                'isCalibration ': isCalibration,
                'dist2Tip_new ': dist2Tip_new,
                'backDiff ': backDiff,
                'fungal_fusion' : fungal_fusion,
                'isTipRelease' : isTipRelease,
                'isActiveTrans' : isActiveTrans,
                'whichInitialCondition' : whichInitialCondition,
                'restrictBranching' : restrictBranching,
                'isPatchyExtEnvironment' : isPatchyExtEnvironment,
                'isConvectDependOnMetabo_cw' : isConvectDependOnMetabo_cw,
                'isConvectDependOnMetabo_gluc' : isConvectDependOnMetabo_gluc,
                'isConvectDependOnMetabo_treha' : isConvectDependOnMetabo_treha,
                'chance_to_fuse' : chance_to_fuse,
                'total_length_progression' : np.array(total_length_progression),
                'avg_treha_annulus' : avg_treha_annulus,
                'max_treha_annulus' : max_treha_annulus,
                'min_treha_annulus' : min_treha_annulus}
            output_file_csv = "Results/{}/Run{}/{}_outputdata_{}_t={:0.2f}.csv".format(param_string, 
                                                                      run, 
                                                                      param_string, 
                                                                      run,
                                                                      current_time)
            #with open(output_file_csv, 'w') as csv_file:  
            #    writer = csv.writer(csv_file)
            #    for key, value in output_dict.items():
            #        writer.writerow([key, value])
            # Write to output csv file
            csv_file = open(output_file_csv, 'w')
            writer = csv.writer(csv_file)
            for key, value in output_dict.items():
                writer.writerow([key, value])
            csv_file.flush()
            os.fsync(csv_file.fileno())
            csv_file.close()
            # end xxx           
            
            WWWW = np.where(avg_treha_annulus == np.max(avg_treha_annulus))[0]
            print('Max avg treha at contour : ', WWWW)
            #hf.plot_avg_treha_annulus(avg_treha_annulus,np.max(avg_treha_annulus), np.min(avg_treha_annulus), 'Avgerage Trehalose Per Annulus', folder_string, param_string, current_time, params, run)
            hf.plot_max_treha_annulus(max_treha_annulus,1.0, 'Max Trehalose Per Annulus', folder_string, param_string, current_time, params, run)
            hf.plot_min_treha_annulus(min_treha_annulus,1.0, 'Min Trehalose Per Annulus', folder_string, param_string, current_time, params, run)
        # Update time
            # breakpoint()
        current_time += dt_i
        current_step += 1
        # end

    # end
    print('End: Current time: ', current_time, 'Final time: ', params['final_time'])
    
    # Write out a restart file
    file_name = "Results/{}/Run{}/restart_t={}.pkl".format(param_string, run, current_time)
    file = open(file_name,'wb')
    pickle.dump(mycelia,file)
    pickle.dump(num_total_segs,file)
    pickle.dump(dtt,file)
    pickle.dump(sub_e_gluc,file)
    pickle.dump(sub_e_treha,file)
    pickle.dump(current_time,file)
    file.flush()
    os.fsync(file.fileno()) 
    file.close()
    
    # Plot results at final time
    hf.plot_fungus(mycelia, num_total_segs, current_time, folder_string, param_string, params, run)
    hf.plot_fungus_gluc(mycelia, num_total_segs, current_time, folder_string, param_string, params, run)
    hf.plot_fungus_treha(mycelia, num_total_segs, current_time, folder_string, param_string, params, run)
    if params['init_sub_e_gluc'] > 1e-15:
        hf.plot_externalsub(sub_e_gluc, yticks, yticklabels, current_time, params['init_sub_e_gluc'], 'Se', folder_string, param_string, params, run)
        hf.plot_externalsub_hyphae(sub_e_gluc, mycelia, num_total_segs, yticks, yticklabels, current_time, params['init_sub_e_gluc'], 'Se', folder_string, param_string, params, run)
        
        if trehaDiff == 1:
            max_e_treha = np.max(sub_e_treha)
            hf.plot_externalsub_treha(sub_e_treha, yticks, yticklabels, current_time, max_e_treha, 'Se', folder_string, param_string, params, run)
            hf.plot_externalsub_treha_hyphae(sub_e_treha, mycelia, num_total_segs, yticks, yticklabels, current_time, max_e_treha, 'Se', folder_string, param_string, params, run)
            
    
    for i in range(num_total_segs):
        if mycelia['branch_id'][i]==-1:
            continue
        mycelia['dist_from_center'][i] = (np.sqrt(mycelia['xy2'][i][0]**2 + mycelia['xy2'][i][1]**2))
        # mycelia['true_seg_length'][i] = (np.sqrt((mycelia['xy2'][i][0]-mycelia['xy1'][i][0])**2 + (mycelia['xy2'][i][1]-mycelia['xy1'][i][1])**2))
    # hf.plot_hist(mycelia, num_total_segs, param_string, params, run)
    
    # np.ceil(mycelia['dist_from_center'][:num_total_segs])
    # density_per_unit_radius = np.zeros(2000)
    # density_per_unit_annulus = np.zeros(2000)
    # breakpoint()
    center_x = np.where(x_vals == 0)[0]
    # print('center_x : ', center_x)
    center_y = np.where(y_vals == 0)[0]
    # print('center_y : ', center_y)
        
    avg_treha_annulus = np.zeros(N)
    max_treha_annulus = np.zeros(N)
    min_treha_annulus = np.zeros(N)
    # breakpoint()
    center_x = round(len(x_vals)/2)#np.where(x_vals == 0)[0]
    print('center_x : ', center_x)
    center_y = round(len(y_vals)/2)#np.where(y_vals == 0)[0]
    print('center_y : ', center_y)
    
    ## For "pseudo-raidal" annulus
    for i in range(N):
        count = 0
        min_treha = 1e5
        max_treha = -1e5
        if i == 0:
            # continue
            avg_treha_annulus[i] = sub_e_treha[center_x,center_y]
            count+=1
        # elif i == 1:
        elif i == 1:
            avg_treha_annulus[i] += sub_e_treha[center_x+1, center_y+0]
            if (sub_e_treha[center_x+1, center_y+0] >= max_treha):
                max_treha = sub_e_treha[center_x+1, center_y+0]
            if (sub_e_treha[center_x+1, center_y+0] <= min_treha):
                min_treha = sub_e_treha[center_x+1, center_y+0]
            avg_treha_annulus[i] += sub_e_treha[center_x+1, center_y+1]
            if (sub_e_treha[center_x+1, center_y+1] >= max_treha):
                max_treha = sub_e_treha[center_x+1, center_y+1]
            if (sub_e_treha[center_x+1, center_y+1] <= min_treha):
                min_treha = sub_e_treha[center_x+1, center_y+1]
            avg_treha_annulus[i] += sub_e_treha[center_x+1, center_y-1]
            if (sub_e_treha[center_x+1, center_y-1] >= max_treha):
                max_treha = sub_e_treha[center_x+1, center_y-1]
            if (sub_e_treha[center_x+1, center_y-1] <= min_treha):
                min_treha = sub_e_treha[center_x+1, center_y-1]
            avg_treha_annulus[i] += sub_e_treha[center_x, center_y+1]
            if (sub_e_treha[center_x, center_y+1] >= max_treha):
                max_treha = sub_e_treha[center_x, center_y+1]
            if (sub_e_treha[center_x, center_y+1] <= min_treha):
                min_treha = sub_e_treha[center_x, center_y+1]
            avg_treha_annulus[i] += sub_e_treha[center_x, center_y-1]
            if (sub_e_treha[center_x, center_y-1] >= max_treha):
                max_treha = sub_e_treha[center_x, center_y-1]
            if (sub_e_treha[center_x, center_y-1] <= min_treha):
                min_treha = sub_e_treha[center_x, center_y-1]
            avg_treha_annulus[i] += sub_e_treha[center_x-1, center_y+0]
            if (sub_e_treha[center_x-1, center_y+0] >= max_treha):
                max_treha = sub_e_treha[center_x-1, center_y+0]
            if (sub_e_treha[center_x-1, center_y+0] <= min_treha):
                min_treha = sub_e_treha[center_x-1, center_y+0]
            avg_treha_annulus[i] += sub_e_treha[center_x-1, center_y+1]
            if (sub_e_treha[center_x-1, center_y+1] >= max_treha):
                max_treha = sub_e_treha[center_x-1, center_y+1]
            if (sub_e_treha[center_x-1, center_y+1] <= min_treha):
                min_treha = sub_e_treha[center_x-1, center_y+1]
            avg_treha_annulus[i] += sub_e_treha[center_x-1, center_y-1]
            if (sub_e_treha[center_x-1, center_y-1] >= max_treha):
                max_treha = sub_e_treha[center_x-1, center_y-1]
            if (sub_e_treha[center_x-1, center_y-1] <= min_treha):
                min_treha = sub_e_treha[center_x-1, center_y-1]
            avg_treha_annulus[i] = avg_treha_annulus[i]/8.0
            max_treha_annulus[i] = max_treha
            min_treha_annulus[i] = min_treha
        else:
            for j in range(0,i):
                if j <= (i-1):
                        avg_treha_annulus[i] += sub_e_treha[center_x+j, center_y+i]
                        if (sub_e_treha[center_x+j, center_y+i] >= max_treha):
                            max_treha = sub_e_treha[center_x+j, center_y+i]
                        if (sub_e_treha[center_x+j, center_y+i] <= min_treha):
                            min_treha = sub_e_treha[center_x+j, center_y+i]
                        
                        avg_treha_annulus[i] += sub_e_treha[center_x+j, center_y-i]
                        if (sub_e_treha[center_x+j, center_y-i] >= max_treha):
                            max_treha = sub_e_treha[center_x+j, center_y-i]
                        if (sub_e_treha[center_x+j, center_y-i] <= min_treha):
                            min_treha = sub_e_treha[center_x+j, center_y-i]
                        
                        avg_treha_annulus[i] += sub_e_treha[center_x-j, center_y+i]
                        if (sub_e_treha[center_x-j, center_y+i] >= max_treha):
                            max_treha = sub_e_treha[center_x-j, center_y+i]
                        if (sub_e_treha[center_x-j, center_y+i] <= min_treha):
                            min_treha = sub_e_treha[center_x-j, center_y+i]
                            
                        avg_treha_annulus[i] += sub_e_treha[center_x-j, center_y-i]
                        if (sub_e_treha[center_x-j, center_y-i] >= max_treha):
                            max_treha = sub_e_treha[center_x-j, center_y-i]
                        if (sub_e_treha[center_x-j, center_y-i] <= min_treha):
                            min_treha = sub_e_treha[center_x-j, center_y-i]
                            
                        count += 4
                else:
                    for k in range(0,i-1):
                        if k == 0:
                            avg_treha_annulus[i] += sub_e_treha[center_x+j, center_y+k]
                            if (sub_e_treha[center_x+j, center_y+k] >= max_treha):
                                max_treha = sub_e_treha[center_x+j, center_y+k]
                            if (sub_e_treha[center_x+j, center_y+k] <= min_treha):
                                min_treha = sub_e_treha[center_x+j, center_y+k]
                            
                            avg_treha_annulus[i] += sub_e_treha[center_x-j, center_y+k]
                            if (sub_e_treha[center_x-j, center_y+k] >= max_treha):
                                max_treha = sub_e_treha[center_x-j, center_y+k]
                            if (sub_e_treha[center_x-j, center_y+k] <= min_treha):
                                min_treha = sub_e_treha[center_x-j, center_y+k]
                            
                            count += 2
                        else:
                            avg_treha_annulus[i] += sub_e_treha[center_x+j, center_y+k]
                            if (sub_e_treha[center_x+j, center_y+k] >= max_treha):
                                max_treha = sub_e_treha[center_x+j, center_y+k]
                            if (sub_e_treha[center_x+j, center_y+k] <= min_treha):
                                min_treha = sub_e_treha[center_x+j, center_y+k]
                            
                            avg_treha_annulus[i] += sub_e_treha[center_x+j, center_y-k]
                            if (sub_e_treha[center_x+j, center_y-i] >= max_treha):
                                max_treha = sub_e_treha[center_x+j, center_y-k]
                            if (sub_e_treha[center_x+j, center_y-i] <= min_treha):
                                min_treha = sub_e_treha[center_x+j, center_y-k]
                            
                            avg_treha_annulus[i] += sub_e_treha[center_x-j, center_y+k]
                            if (sub_e_treha[center_x-j, center_y+k] >= max_treha):
                                max_treha = sub_e_treha[center_x-j, center_y+k]
                            if (sub_e_treha[center_x-j, center_y+k] <= min_treha):
                                min_treha = sub_e_treha[center_x-j, center_y+k]
                
                            avg_treha_annulus[i] += sub_e_treha[center_x-j, center_y-k]
                            if (sub_e_treha[center_x-j, center_y-i] >= max_treha):
                                max_treha = sub_e_treha[center_x-j, center_y-k]
                            if (sub_e_treha[center_x-j, center_y-i] <= min_treha):
                                min_treha = sub_e_treha[center_x+j, center_y-k]
                            
                            count += 4
            
            avg_treha_annulus[i] = avg_treha_annulus[i]/count
            max_treha_annulus[i] = max_treha
            min_treha_annulus[i] = min_treha
                        
    # breakpoint()
    # plt.figure()
    # plt.hist(mycelia['dist_from_center'][:num_total_segs], bins='auto')
    hf.plot_hist(mycelia,current_time, num_total_segs, param_string, params, run)
    # plt.figure()
    # plt.plot(range(2000), density_per_unit_radius)
    # plt.plot(range(2000), density_per_unit_annulus)
    # hf.plot_density_annulus(density_per_unit_annulus, num_total_segs, param_string, params, run)
    
    # ----------------------------------------------------------------------------
    # RESULTS
    # ----------------------------------------------------------------------------
    t_1 = time.time()
    num_branches = max(mycelia['branch_id'])[0]+1
    num_segs = num_total_segs
    num_tips = np.count_nonzero(mycelia['is_tip'])
    max_radii = max(np.sqrt(mycelia['xy2'][:,0]**2 + mycelia['xy2'][:,1]**2))
    avg_radii = np.mean(np.sqrt(mycelia['xy2'][:,0]**2 + mycelia['xy2'][:,1]**2))
    rms_radii = np.sqrt(np.mean(np.sqrt(mycelia['xy2'][:,0]**2 + mycelia['xy2'][:,1]**2)**2))
    
    tip_idx = np.where(mycelia['is_tip'])[0]
    rms_tip_radii = np.sqrt(np.mean(mycelia['xy2'][tip_idx,0]**2 + mycelia['xy2'][tip_idx,1]**2))
    
    time_total = t_1 - t_0
    time_mins, time_secs = divmod(time_total, 60)
    min_seg_length_nonTipIdx = (np.where(mycelia['is_tip'][:num_total_segs] == False))[0]
    min_seg_length_nonTipIdx2 = (np.where(mycelia['branch_id'][min_seg_length_nonTipIdx] != -1))[0]
    max_seg_length = max(mycelia['seg_length'])[0]
    min_seg_length = min(mycelia['seg_length'][min_seg_length_nonTipIdx[min_seg_length_nonTipIdx2]])[0]
    # breakpoint()
    potential_CFL_fail_segment = np.where(mycelia['seg_length'][:num_total_segs] < params['dt_i']*params['kg1_wall'])[0]
    CFL_fail_segment = len(np.where(mycelia['is_tip'][potential_CFL_fail_segment] == False)[0])
    total_biomass = np.sum(mycelia['seg_length'])*params['cross_area']*params['hy_density']
    
    count_branches.append(num_branches)
    count_tips.append(num_tips)
    count_max_radii.append(max_radii)
    count_avg_radii.append(avg_radii)
    count_rms_radii.append(rms_radii)
    count_rms_tip_radii.append(rms_tip_radii)

    count_times.append(current_time)
    count_biomass.append(total_biomass)
    
    count_branches = np.array(count_branches)
    count_tips = np.array(count_tips)
    count_radii = np.array(count_radii)
    count_times = np.array(count_times)
    count_biomass = np.array(count_biomass)
    avg_treha_annulus = np.array(avg_treha_annulus)
    max_treha_annulus = np.array(max_treha_annulus)
    min_treha_annulus = np.array(min_treha_annulus)
    
   # Print out results:
    print('')
    print('-----------------------------------------------------------')
    print('PARAMETERS:')
    for i in params:
        print('  {}: {}'.format(i, params[i]))
    print('-----------------------------------------------------------')
    print('isCalibration : ', format(isCalibration))
    print('dist2Tip_new : ', format(dist2Tip_new))
    print('backDiff : ',format(backDiff))
    print('fungal_fusion : ', format(fungal_fusion))
    print('isTipRelease : ', format(isTipRelease))
    print('isActiveTrans : ', format(isActiveTrans))
    print('whichInitialCondition : ', format(whichInitialCondition)) 
    print('restrictBranching : ', format(restrictBranching))
    print('isPatchyExtEnvironment :', format(isPatchyExtEnvironment))
    print('isConvectDependOnMetabo_cw : ', format(isConvectDependOnMetabo_cw))
    print('isConvectDependOnMetabo_gluc : ', format(isConvectDependOnMetabo_gluc))
    print('isConvectDependOnMetabo_treha : ', format(isConvectDependOnMetabo_treha))
    print('chance_to_fuse : ', format(chance_to_fuse))
    print('RESULTS:')
    print('Max segment length: {}',format(max_seg_length))
    print('Min segment length: {}',format(min_seg_length))
    print('Number of CFL-fail segment : {}',format(CFL_fail_segment))
    print('  Number of Branches at End of Simulation: {}'.format(num_branches))
    print('  Number of Tips at End of Simulation:     {}'.format(num_tips))
    print('  Num. Branches / Num. Tips:               {:.3f}'.format(num_branches/num_tips))
    print('  Number of Segments at End of Simulation: {}'.format(num_segs))
    print('  Radius at End of Simulation:        {:.4f}'.format(max_radii))
    print('  Average Radius at End of Simulation:        {:.4f}'.format(avg_radii))
    print('-----------------------------------------------------------')
    print('TIME:')
    print('  External Update:      {:.4f}'.format(time_external))
    print('  Extension:            {:.4f}'.format(time_extend))
    print('  Branching:            {:.4f}'.format(time_branch))
    print('  Translocation Update: {:.4f}'.format(time_translocation))
    print('  Uptake Update:        {:.4f}'.format(time_uptake))
    print('  Total Run Time:       {:.4f} ({} mins, {:.2f} secs)'.format(time_total, time_mins, time_secs))
    print('-----------------------------------------------------------')
    
    
    # # Save hy & output info
    # hy_file_pkl = "Results/{}/{}/{}_hy_{}.pkl".format(folder_string, param_string, param_string, run)
    # with open(hy_file_pkl, 'wb') as f:
    #     pickle.dump(hy, f)
        
    
    output_dict = {
        'run_num' : run,
        'total_run_time': t_1-t_0,
        'array_times' : count_times,
        'total_biomass' : count_biomass,
        'max_radii' : count_max_radii,
        'avg_radii' : count_avg_radii,
        'rms_radii' : count_rms_radii,
        'rms_tip_radii' : count_rms_tip_radii,
        'array_num_branches' : count_branches,
        'array_num_tips' : count_tips,
        'array_branching_density' : count_branches/count_tips,
        'array_radii' : count_radii,
        'num_segments_at_end' : num_segs,
        'max_seg_length' : max_seg_length,
        'min_seg_length_nonTip' : min_seg_length,
        'CFL_fail_segment ' : CFL_fail_segment,
        'isCalibration ': isCalibration,
        'dist2Tip_new ': dist2Tip_new,
        'backDiff ': backDiff,
        'fungal_fusion' : fungal_fusion,
        'isTipRelease' : isTipRelease,
        'isActiveTrans' : isActiveTrans,
        'whichInitialCondition' : whichInitialCondition,
        'restrictBranching' : restrictBranching,
        'isPatchyExtEnvironment' : isPatchyExtEnvironment,
        'isConvectDependOnMetabo_cw' : isConvectDependOnMetabo_cw,
        'isConvectDependOnMetabo_gluc' : isConvectDependOnMetabo_gluc,
        'isConvectDependOnMetabo_treha' : isConvectDependOnMetabo_treha,
        'chance_to_fuse' : chance_to_fuse,
        'total_length_progression' : np.array(total_length_progression),
        'avg_treha_annulus' : avg_treha_annulus,
        'max_treha_annulus' : max_treha_annulus,
        'min_treha_annulus' : min_treha_annulus}
    output_file_csv = "Results/{}/Run{}/{}_outputdata_{}_t={:0.2f}.csv".format(param_string, 
                                                                      run, 
                                                                      param_string, 
                                                                      run,
                                                                      current_time)
    # write to csv_file:  
    csv_file = open(output_file_csv, 'w')
    writer = csv.writer(csv_file)
    for key, value in output_dict.items():
        writer.writerow([key, value])
    csv_file.flush()
    os.fsync(csv_file.fileno())
    csv_file.close()

    # Plot some stats       
    hf.plot_stat(count_times, count_branches, 'Num. of Branches', folder_string, param_string, params, run)
    hf.plot_stat(count_times, count_tips, 'Num. of Tips', folder_string, param_string, params, run)
    hf.plot_stat(count_times, count_branches/count_tips, 'Branching Density', folder_string, param_string, params, run)
    hf.plot_stat(count_times, count_rms_tip_radii, 'RMS Radii of Mycelia Tips ({})'.format(params['plot_units_space']), folder_string, param_string, params, run)
    #hf.plot_avg_treha_annulus(avg_treha_annulus,np.max(avg_treha_annulus), np.min(avg_treha_annulus), 'Average Trehalose Per Annulus', folder_string, param_string, current_time, params, run)
    # hf.plot_avg_treha_annulus(avg_treha_annulus,np.max(avg_treha_annulus), 'Avgerage Trehalose Per Annulus', folder_string, param_string, current_time, params, run)
    hf.plot_max_treha_annulus(max_treha_annulus,1.0, 'Max Trehalose Per Annulus', folder_string, param_string, current_time, params, run)
    hf.plot_min_treha_annulus(min_treha_annulus,1.0, 'Min Trehalose Per Annulus', folder_string, param_string, current_time, params, run)
        
    return output_dict

    
## Run Multiple iterations
try:
    num_runs = params['num_parallel_runs']
except: 
    num_runs = 1
folder_string, param_string = hf.get_filepath(params)

# Create appropriate folder
if not os.path.exists('Results/{}/Avg{}'.format(param_string, num_runs)):
    try:
        os.makedirs('Results/{}/Avg{}'.format(param_string, num_runs))
    except: 
        pass

# Initialize arrays for storing results
all_branches = np.array([])
all_tips = np.array([])
all_density = np.array([])
all_radii = np.array([])

# Run the same simulation in parallel
output_dict = Parallel(n_jobs=min(num_runs,num_cores))(delayed(driver_singleNutrient)(run) for run in range(num_runs))

  
if num_runs > 1:
    # Convert data to matrix
    for run in range(num_runs):
        if run == 0:
            all_branches = np.hstack((all_branches, output_dict[run]['array_num_branches'].flatten()))
            all_tips = np.hstack((all_tips, output_dict[run]['array_num_tips'].flatten()))
            all_density = np.hstack((all_density, output_dict[run]['array_branching_density'].flatten()))
            all_radii = np.hstack((all_radii, output_dict[run]['array_radii'].flatten()))
        else:
            all_branches = np.vstack((all_branches, output_dict[run]['array_num_branches'].flatten()))
            all_tips = np.vstack((all_tips, output_dict[run]['array_num_tips'].flatten()))
            all_density = np.vstack((all_density, output_dict[run]['array_branching_density'].flatten()))
            all_radii = np.vstack((all_radii, output_dict[run]['array_radii'].flatten()))
          
    # Find avg. values for each time        
    avg_branches = np.average(all_branches, axis=0)
    avg_tips = np.average(all_tips, axis=0)
    avg_density = np.average(all_density, axis=0)
    #avg_radii = np.average(all_radii, axis=0)
        
    # Find std. dev. values for each time
    std_branches = np.std(all_branches, axis=0)
    std_tips = np.std(all_tips, axis=0)
    std_density = np.std(all_density, axis=0)
    #std_radii = np.std(all_radii, axis=0)
    
    # Plot avgs with error bars
    hf.plot_errorbar_stat(output_dict[0]['array_times'].flatten(), 
                          avg_branches, std_branches, 
                          'Avg. Num. of Branches ({} Iterations)'.format(
                              num_runs), 
                          folder_string, param_string, params, num_runs)
    hf.plot_errorbar_stat(output_dict[0]['array_times'].flatten(), 
                          avg_tips, std_tips, 
                          'Avg. Num. of Tips ({} Iterations)'.format(
                              num_runs), 
                          folder_string, param_string, params, num_runs)
    hf.plot_errorbar_stat(output_dict[0]['array_times'].flatten(), 
                          avg_density, std_density, 
                          'Avg. Branching Density ({} Iterations)'.format(
                              num_runs), 
                          folder_string, param_string, params, num_runs)
    #hf.plot_errorbar_stat(output_dict[0]['array_times'].flatten(), 
    #                      avg_radii, std_radii, 
    #                      'Avg. Radii in {} ({} Iterations)'.format(
    #                          params['plot_units_space'], num_runs), 
    #                      folder_string, param_string, params, num_runs)



    
    

    
    
    
        
