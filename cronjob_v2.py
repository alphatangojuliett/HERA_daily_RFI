#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2018 

import os
import subprocess
import sys
from hera_librarian import LibrarianClient
import numpy as np
import json
import argparse
import datetime


connection_name = 'nrao'

# Search for files that were:
#
# 1. recorded on a specfic day, as evident in the naming scheme of the file. Typically this day will be yesterday.

#
connection_name = 'nrao'

parser = argparse.ArgumentParser(description='Adjust Daily RFI Report Settings.')

parser.add_argument('--which_day', help='YYYYmmdd string of day you would like to analyze, default is yesterday', default = (datetime.date.today()-datetime.timedelta(1)).strftime('%Y%m%d') )
parser.add_argument('--debug', help ='Boolean: Print a bunch of statements to help you diagnose potential problems?', default = 0)
args = parser.parse_args()

DEBUG = bool(int(args.debug))
STR_DAY = str(args.which_day)

proto_search = {}
proto_search["name-matches"] =str("SDR_SpectrumPeak."+str(STR_DAY)+".%")
search = str(json.dumps(proto_search))

def main():

    plots_dir = os.path.dirname('/lustre/aoc/projects/hera/ajosaiti/SDR_RFI_monitoring/HERA_daily_RFI/')
    plot_script = os.path.join(plots_dir, 'run_notebook_v2.sh')

    env = dict(os.environ)
    env['which_day'] = STR_DAY
    #env['STAGING_DIR'] =os.path.dirname('lustre/aoc/projects/hera/ajosaiti/SDR_RFI_monitoring_staging/') #to be used in the .ipynb

    subprocess.check_call(
        ['/opt/services/torque/bin/qsub', '-z', '-j', 'oe', '-o', '/lustre/aoc/projects/hera/ajosaiti/qsub.log', '-V', '-q', 'hera', plot_script],
        shell = False,
        env = env
    )


if __name__ == '__main__':
    main()