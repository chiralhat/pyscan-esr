#!/bin/bash

sudo dpkg --add-architecture armhf
sudo apt update
sudo apt -o Dpkg::Options::="--force-overwrite" install libc6:armhf zlib1g-dev:armhf

sudo mkdir /opt/mokucli
cd /opt/mokucli

sudo wget https://download.liquidinstruments.com/software/mokucli/linux/mokucli-arm32
sudo wget https://download.liquidinstruments.com/software/mokucli/linux/mokucli-linux.tar.gz
sudo tar xvzf mokucli-linux.tar.gz
sudo ln /opt/mokucli/mokucli-arm32 /usr/local/bin/mokucli

