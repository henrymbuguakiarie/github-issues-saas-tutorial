#!/usr/bin/env bash
####################################
# Generates all GitHub issue reports
####################################

source "$(pwd)/spinner.sh"
SPINNER_TIMER=true

SECONDS=0
REPODIR="/home/$USER/repos"
VENV="/home/$USER/venv/docsreport"
PAT="YOUR_GITHUB_PERSONAL_ACCESS_TOKEN_HERE"

export GH_ACCESS_TOKEN=$PAT
source $VENV/Scripts/activate

echo "-----"

#spinner_start "Generating GitHub issue report: SaaS applications ($(date +%F))"
python docsreport.py --repo "MicrosoftDocs/azure-docs" --label "saas-app-tutorial/subsvc" > $REPODIR/gh-issues-saas-apps/github-issues-saas-apps.md
#spinner_stop $?


DURATION=$SECONDS
echo "-----"
echo "Report generation complete "
echo "-----"
echo ""

# Open files in Visual Studio Code

code $REPODIR/gh-issues-saas-apps/github-issues-saas-apps.md

exit
