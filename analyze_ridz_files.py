#import rids
import numpy as np 
import json
import sys
import datetime
import argparse
import os
import matplotlib.pyplot as plt
import matplotlib.dates as pdates
import subprocess

parser = argparse.ArgumentParser(description='Adjust Daily RFI Report Settings.')

parser.add_argument('--which_day', help='YYYYmmdd string of day you would like to analyze, default is yesterday', default = (datetime.date.today()-datetime.timedelta(1)).strftime('%Y%m%d') )
parser.add_argument('--debug', help ='Boolean: Print a bunch of statements to help you diagnose potential problems?', default = 0)
args = parser.parse_args() 

DEBUG = bool(int(args.debug))
STR_DAY = str(args.which_day)

OUT_DAY = 'arr_day.npy' #the output files containing integrated power and metadata for each sweep-spectrum on record
OUT_NIGHT = 'arr_night.npy'
#DATA_PATH = /Users/josaitis/Library/Mobile Documents/com~apple~CloudDocs/Cambridge/HERA/RFI_monitoring/HERA_daily_RFI/ #Temporary, while I work on local computer. For actual github instantion, use: data_path = os.environ['DATA_PATH']
SUNSET_TIMETABLE = np.genfromtxt('HERA_sunrise_sunset_annual.csv', dtype=str,delimiter=',') # Col 0: Month-day (mmdd), Col 1: Sunrise (hhmm), Col 2: Sunset (hhmm)


def file_flush():
	if DEBUG: print('flushing temporary and output files...')
	open(OUT_DAY, 'w').close()
	open(OUT_NIGHT, 'w').close()
	if DEBUG: print('done.')

def delta_hours_minutes(td):
    return td.seconds//3600, (td.seconds//60)%60

def recursive_key_search(dat, key): #https://stackoverflow.com/questions/9807634/find-all-occurrences-of-a-key-in-nested-python-dictionaries-and-lists
#sum_dbm_recursive_key_search(dat, key): #https://stackoverflow.com/questions/9807634/find-all-occurrences-of-a-key-in-nested-python-dictionaries-and-lists
    if key in dat:
        yield dat[key]
    for k in dat:
        if isinstance(dat[k], list):
            for i in dat[k]:
                for j in recursive_key_search(i):
                    yield j

def time_in_rids_fmt(datetime_time): # convert datetime.datetime.now() time into the RIDZ-requested format
	str_iso = datetime_time.isoformat(' ')
	str_time_rids = str( str_iso[0:4] + str_iso[5:7] + str_iso[8:10] + '-' + str_iso[11:13]+str_iso[14:16]+str_iso[17:19])
	return str_time_rids

def sum_array_of_dbm(arr):
	val_sum = 10.*np.log10(np.sum(np.power(10,np.array(arr)/10.)))
	return val_sum

def day_night_initial_calculation(arr_day,arr_night):
	cwd = os.getcwd()
	for filename in os.listdir(cwd):
		if DEBUG: print('considering filename: '+str(filename))
		if filename.endswith('.rids') and (STR_DAY in filename): # NOTE: In final iteration, this should be '.ridz', not '.rids'
			fname_uzip = str(filename.replace('.ridz','.rids'))
			#os.system(str('zipr.py ' +str(filename)))
			dat = json.loads(open(str(fname_uzip)).read())
			for dset in np.array(dat['feature_sets'].keys()):
				t_spectra = datetime.datetime.strptime(str(dset[5:20]), '%Y%m%d-%H%M%S' )
				int_pwr =  sum_array_of_dbm(dat['feature_sets'][str(dset)]['val'])# scalar, the integrated power from one sweep spectrogram measurement
				if DEBUG: 
					print('int_pwr: '+str(int_pwr))
					print('t_spectra: '+str(t_spectra))
					print('sunrise: '+str(sunrise)+', sunset: '+str(sunset))
				if bool( (t_spectra >=sunrise) and (t_spectra<=sunset) ): arr_day.append(np.array([t_spectra,int_pwr]))
				else: arr_night.append(np.array([t_spectra,int_pwr]))
			dat.clear()
			#os.system(str('zipr.py ' +str(fname_uzip))) # re-zip the file
	if DEBUG:
		print('arr_day: '+str(arr_day))
		print('arr_night: '+str(arr_night))

	return arr_day, arr_night

#For the day in question, figure out when sunset and sunrise were. 
col_date,col_key = np.where(SUNSET_TIMETABLE == STR_DAY[4:]) #find mmdd, but it could also be a time
sunrise = datetime.datetime.strptime( str(str(STR_DAY[:4])+str(STR_DAY[4:])+'-'+str(SUNSET_TIMETABLE[int(col_date[col_key==0])][1])) ,'%Y%m%d-%H%M')
sunset = datetime.datetime.strptime( str(str(STR_DAY[:4])+str(STR_DAY[4:])+'-'+str(SUNSET_TIMETABLE[int(col_date[col_key==0])][2])) ,'%Y%m%d-%H%M')
delta_hour, delta_minute = delta_hours_minutes((sunset-sunrise))
#Arrays containing data from each sweep measurement, sorted by whether the data occured in the daytime or nighttime.
arr_day=[] # [datetime.datetime object], [float(integrated power)]
arr_night=[] 


file_flush() # Make sure output files aren't reused with old data in them.
arr_day, arr_night = day_night_initial_calculation(arr_day,arr_night)

#Turn the array of arrays into a 2D array
arr_day=np.array(arr_day)
arr_night = np.array(arr_night)

np.save(OUT_DAY,arr_day)
np.save(OUT_NIGHT,arr_night)

## Prepare environment for ipynb notebook executable
env = dict(os.environ)
env['sessid'] = str(STR_DAY)
plots_dir = os.getcwd()
plot_script = os.path.join(plots_dir, 'run_notebook.sh')
subprocess.check_call(['/opt/services/torque/bin/qsub', '-z', '-j', 'oe', '-o', '/lustre/aoc/projects/hera/ajosaiti/qsub.log', '-V', '-q', 'hera', plot_script],
	shell = False,
	env = env
	)

if DEBUG: 
	print('arr_day: '+str(arr_day))
	print('arr_day[0,0]: '+str(arr_day[0,0]))
	print('arr_day[:,0]: '+str(arr_day[:,0]))

arr_full_day = np.concatenate((np.array(arr_day), np.array(arr_night)),axis=0)

#plt.figure(1)
#plt.subplot(211)
#plt.plot(arr_day[:,0], arr_day[:,1],'bo')
#plt.plot(arr_night[:,0], arr_night[:,1],'go')
#plt.subplot(211).set_title(str('Daytime ('+str(delta_hour)+' Hours, '+str(delta_minute)+' Minutes) Integrated Power: '+str(  np.round(sum_array_of_dbm(arr_day[:,1]),decimals=1) )+ 'dBm, Nighttime Integrated Power: '+str(  np.round(sum_array_of_dbm(arr_night[:,1]),decimals=1)  )+' dBm'))
#plt.subplot(212)
#plt.plot(arr_full_day[:,0], arr_full_day[:,1],'ro')
#plt.subplot(212).set_title(str('Full 24 Hours, Average Integrated Power: ' + str(  np.round(sum_array_of_dbm(arr_full_day[:,1]),decimals=1)  )+' dBm'))

#plt.show()




