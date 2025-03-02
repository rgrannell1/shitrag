#! /usr/bin/env sh


#export PUPPETEER_PRODUCT=$(chrome deno run -A --unstable https://deno.land/x/puppeteer@16.2.0/install.ts)
export PUPPETEER_PRODUCT=chrome

export SHITRAG_ENDPOINT="https://www.dailymail.co.uk/home/sitemaparchive/day_"
export SHITRAG_DB="./shitrag.db"

python3 scrape.py
