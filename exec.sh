#!/bin/sh
python3 /home/ubuntu/newspaper/newspaper_kindle/fetch_AsiaNikkei.py
python3 /home/ubuntu/newspaper/newspaper_kindle/fetch_JapanTimes.py
python3 /home/ubuntu/newspaper/newspaper_kindle/fetch_Telecom.py
python3 /home/ubuntu/newspaper/newspaper_kindle/notify_finish.py
sudo reboot
