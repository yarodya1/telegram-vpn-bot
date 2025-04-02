#!/bin/bash

docker build -t free_vpn_bot .

docker compose up -d --build --force-recreate
