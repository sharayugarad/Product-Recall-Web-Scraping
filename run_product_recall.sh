#!/bin/bash

# go to project dir
cd /home/deepak/CodeLab/GitHub/Product-Recall-Web-Scraping || exit 1

# ensure logs folder exists
mkdir -p logs

# activate virtualenv
source venv/bin/activate

# run scraper
python main.py >> logs/cron_run.log 2>&1

