#!/bin/bash

librarian_conn_name=nrao

echo Date: $(date)
echo which_day=$which_day

# print out help statement
if [ "$1" = '-h' -o "$1" = '--help' ] ; then
    echo 'Usage:'
    echo 'export which_day=<which_day>'
    echo 'qsub -V -q hera run_notebook_v2.sh'
    exit 0
fi

if [ -z "$which_day" ] ; then
    echo "environ variable 'fileid' is undefined"
    exit 1
fi

# Exit with an error if any sub-command fails.
set -e

# Create a temporary Lustre directory for exporting the data and command the
# Librarian to populate it.

#staging_dir=  #$(mktemp -d --tmpdir=/lustre/aoc/projects/hera/ajosaiti/SDR_RFI_monitoring_staging/)
# fileid$fileid.XXXXXX)
export staging_dir=/lustre/aoc/projects/hera/ajosaiti/SDR_RFI_monitoring_staging/$which_day
rm -rf "$staging_dir"
mkdir "$staging_dir"
chmod ug+rwx "$staging_dir"

remove_staging_notes () {
    stage_files=($(ls $1))
    for f in ${stage_files[@]}
    do
        if [[ $f == *"STAG"* ]]
        then
            rm -f $staging_dir/$f
        fi
    done
    #rm -f $staging_dir/*STAGING*
}

echo "staging_dir is: "
echo "$staging_dir"
remove_staging_notes $staging_dir
search="{\"name-matches\": $which_day, \"name-matches\": \"%.ridz\"}"
librarian_stage_files.py --wait $librarian_conn_name "$staging_dir" "$search"



DATA_PATH=

#for item in "$staging_dir"/2* ; do
#    if [ -n "$DATA_PATH" ] ; then
#        echo >&1 "WARNING: multiple subdirectories staged? $DATA_PATH, $item"
#        exit 1
#    fi
#    if [ "$(basename $item)" == "2*" ] ; then
#        echo >&1 "WARNING: no subdirectory staged: $item"
#        exit 1
#    fi
#    export DATA_PATH="$item"
#done

jd=$(basename $which_day)  #Trying this... #$(basename $DATA_PATH)

# get more env vars
BASENBDIR=/lustre/aoc/projects/hera/ajosaiti/SDR_RFI_monitoring/HERA_daily_RFI
OUTPUT=daily_RFI_report_"$jd".ipynb #NOTE: pdf or ipynb
OUTPUT_SANS_EXTENSION=daily_RFI_report_"$jd"
OUTPUTDIR=/lustre/aoc/projects/hera/ajosaiti/SDR_RFI_monitoring/HERA_daily_RFI

echo "Make sure staging notes are deleted..."
remove_staging_notes $staging_dir
rm -rf $staging_dir/STAGING

# copy and run notebook
echo "starting notebook execution..."

#in line below, if outputting pdf, use --output=$OUTPUTDIR/$OUTPUT_SANS_EXTENSION \
jupyter nbconvert --output=$OUTPUTDIR/$OUTPUT_SANS_EXTENSION \
  --to notebook \
  --ExecutePreprocessor.kernel_name=python \
  --ExecutePreprocessor.allow_errors=True \
  --ExecutePreprocessor.timeout=-1 \
  --execute $BASENBDIR/daily_RFI_report_v2.ipynb

echo "finished notebook execution..."

# cd to git repo
cd $OUTPUTDIR

# add to git repo
echo "adding to GitHub repo"
git add $OUTPUT #pdf: OUTPUT

# add fileid to processed_fileid.txt file
echo $which_day >> $OUTPUTDIR/processed_fileid.txt
git add $OUTPUTDIR/processed_fileid.txt

# commit and push
git commit -m "data inspect notebook for $jd"
git pull
git push origin herapost-master

# mark these files as processed (see cronjob.py). We only need to mark one
# file but we do all of the UV files since that seems like potentially handy
# information to have.
echo "adding Librarian file events"
now_unix=$(date +%s)

for rid in $staging_dir/*/*.ridz ; do
    add_librarian_file_event.py $librarian_conn_name $rid rfi_data.processed when=$now_unix
done

#echo "sending email to heraops"
#sed -e 's/@@JD@@/'$jd'/g' < mail_template.txt > mail.txt
#sendmail -vt < mail.txt

echo "removing staging dir"
rm -rf "$staging_dir"

echo "finished run_notebook.sh"
echo "Date:" $(date)
exit 0