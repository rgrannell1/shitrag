#! /usr/bin/env sh

export $(cat .env | xargs)
node main.js
