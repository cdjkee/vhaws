#!/usr/bin/env bash
echo "------------START------------"
NEEDRESTART_MODE=a
apt update
apt install -y pip awscli
mkdir ~/.aws
cd ~/.aws
echo "[default]" > config
echo "region = eu-north-1" >> config
echo "output = json" >> config
echo "------------END------------"