#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Feb 17 12:46:35 2018

@author: simon
"""

## Basic functionality
import swarmtoolkit as st
import numpy as np
import os
from astropy.time import Time
import pandas as pd
# path of data
data_loc = "/home/simon/Desktop/Bachelor_project/data/"

#%%

def load_ap(days = 31):
    # This function loads the ap from a .dat file in data_loc folder
    # It loads for x days in march 2015
    # The output is a list with ap[0]=time, ap[1]=Kp, ap[2]=ap
    
    path_ap = os.path.join(data_loc,'Kp_ap_1998.dat')
    file = open(path_ap,"r") 
    lines = file.readlines() 
    file.close()
    
    
    start = 50145  ## 1. marts 2015 kl 1:30
    slut = start+8*days
    ## time, Kp, ap
    ap = [[0 for x in range(slut-start)],np.zeros(slut-start),np.zeros(slut-start)]
    for i in range(start,slut):
        t = Time(float(lines[i].strip().split()[0])+51544.5, format='mjd', scale='utc')
        t.format = 'datetime'
        ap[0][i-start] = t.value
        ap[1][i-start] = float(lines[i].strip().split()[1])
        ap[2][i-start] = float(lines[i].strip().split()[2])
    
    # Convert to panda data format
    dates = pd.to_datetime(ap[0])
    ap = pd.DataFrame(np.transpose(ap[1:3]), index=dates, columns=['Kp','ap'])
    return ap


#%%

def load_DNS(days=31,output_form='list'):
    # This function loads the DNS zip files from data_loc
    # It loads for x days in march 2015
    # The output is a list with swarmtoolkit.sw_io.Parameter
   
    
    name = 'SW_OPER_DNSCWND_2__20150301T000000_20150301T235950_0101.ZIP'
    path = os.path.join(data_loc,name)
    DNS = st.getCDFparams(path,temp=True)
    
    for i in range(2,days+1):
        ## Gennerate a path name
        if i < 10:
            nr = '0'+str(i)
        else:
            nr = str(i)
        name = name[0:25]+nr + name[27:41]+nr +name[43:]
        path = os.path.join(data_loc,name)
        
        ##Load data
        try:
            temp_DNS = st.getCDFparams(path,temp=True)
        
            ## Append data
            for k in range(len(DNS)):
                DNS[k].values= np.append(DNS[k].values,temp_DNS[k].values)
        except:
            print(name+' Was not found')
    ## Fix unrealistic values / errors in density
    DNS[5].values[DNS[5].values > 1e30] = float('nan')    
    
    # Convert to panda data format
    dates=pd.to_datetime(DNS[0].values)
    data = [DNS[1].values]
    names = ['Altitude','Latitude','Longitude','Local_solar_time','Density']
    for i in range(2,len(DNS)):
        data.append(DNS[i].values)
    DNS = pd.DataFrame(np.transpose(data), index=dates, columns=names)
    
    return DNS

#%%
    
def load_FAC(sat='A',days=31):
    # This function loads the FAC zip files from data_loc
    # It loads for x days in march 2015
    # The output is a list with swarmtoolkit.sw_io.Parameter
    # !!!Note that the 5 march of sat='A' is not in the folder!!!
    
    if sat == 'A':
        name = 'SW_OPER_FACATMS_2F_20150301T000000_20150301T235959_0205.ZIP'
    elif sat =='C':
        name = 'SW_OPER_FACCTMS_2F_20150301T000000_20150301T235959_0205.ZIP' 
    path = os.path.join(data_loc,name)
    FAC = st.getCDFparams(path,temp=True)
    
    for i in range(2,days+1):
        ## Gennerate a path name
        if i < 10:
            nr = '0'+str(i)
        else:
            nr = str(i)
        name = name[0:25]+nr + name[27:41]+nr +name[43:]
        path = os.path.join(data_loc,name)
        
        ##Load data
        try:
            temp_FAC = st.getCDFparams(path,temp=True)
            
            ## Append data
            for k in range(len(FAC)):
                FAC[k].values= np.append(FAC[k].values,temp_FAC[k].values)
        except:
            print(name+' Was not found')
    
    # convert to pandas
    dates=pd.to_datetime(FAC[0].values)
    data = [FAC[1].values]
    names = [FAC[1].name]
    for i in range(2,len(FAC)):
        data.append(FAC[i].values)
        names.append(FAC[i].name)
    FAC = pd.DataFrame(np.transpose(data), index=dates, columns=names)
   
    return FAC

#%%
    
def add_orbit(dataframe):
    """
    Output an np.array with the orbit nr of corrospondig to the latitude.
    The firt mesument is denoted 0 the next 1 and so on.
    Be aware that the latitude should be ordered in time. 
    !!! Orbit nr is sensitive to holds in time series. Orbit nr does not 
    align when there is holds!!!
    
    """
    # initial orbits
    latitude = dataframe['Latitude']
    orbits = np.zeros(len(latitude))
    hemisphere = np.ones(len(latitude))
    current_orbit = 0
    
    # Check if first mesument is on the southen hemisphere
    if latitude[0]<0:
        hemisphere[0]=-1
        
    # go through all latitudes
    for i in range(1,len(latitude)):
        
        if latitude[i]>0:
            hemisphere[i]=1 # set to norhten hemiphere 
            # If the Acending node is crossed. New orbit
            if latitude[i-1]<0:
                current_orbit += 1
        else:
            hemisphere[i]=-1 # set to southen hemiphere 
        # sets orbit
        orbits[i] = current_orbit
        
    dataframe.loc[:,'Orbit_nr'] =  orbits
    dataframe.loc[:,'Hemisphere'] = hemisphere
    return None
            
#%%         

def orbit_means(dataframe,mode='abs'):
    
    if ('FAC' in dataframe.columns):
        pos = 'FAC'
    elif ('Density' in dataframe.columns):
        pos = 'Density'
    else:
        print('Error in data type')
        return 0
    
    if not 'Orbit_nr' in dataframe.columns:
        add_orbit(dataframe)


    #get orbit nr.
    orbit_nr = np.repeat(np.array(range(int(dataframe.Orbit_nr[-1]+1))),2)
    hemisphere = -1*np.ones(len(orbit_nr))
    hemisphere[::2]=-hemisphere[::2]
    #Intialize arrays for result
    values = np.zeros(len(orbit_nr))
    mesuments = np.zeros(len(orbit_nr))
    delta_time = [0 for x in range(len(orbit_nr))]
    dates = [0 for x in range(len(orbit_nr))]
    # sets first orbit
    
    # Go through data
    for i in range(len(orbit_nr)):
        # get the orbit
        df = dataframe[dataframe.Orbit_nr == orbit_nr[i]]
        # Get hemisphere
        df = df[df.Hemisphere == hemisphere[i]]
          
        mesuments[i] = len(df.loc[:,pos])
        if mesuments[i] == 0:
            values[i] = float('nan')
            delta_time[i] = 0
            dates[i] = dataframe.index[0]
        else:
            delta_time[i] = (df.index[-1]-df.index[0]).total_seconds()
            dates[i] = df.index[0] + (df.index[-1]-df.index[0])/2
            if mode == 'simple':
               values[i] = df.loc[:,pos].mean()
            if mode == 'abs':
                values[i] = df.loc[:,pos].apply(abs).mean()
    
            if mode == 'power':
                values[i] = np.sqrt(df.loc[:,pos].apply(lambda x: x**2).mean())
    data = [values,orbit_nr,hemisphere,mesuments,delta_time]
    names = [pos,'Orbit_nr','Hemisphere','Count','Delta_time']
    means = pd.DataFrame(np.transpose(data), index=dates, columns=names)
    return means
    