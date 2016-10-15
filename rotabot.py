import math
import random
import functools
from collections import Counter
import logging
import arrow
from datetime import date, timedelta as td
import csv
from slackclient import SlackClient
from slacker import Slacker
import os
from beepboop import resourcer
from beepboop import bot_manager
import time

class Bot(object):
    def __init__(self):
        print("Creating BOT!")
        token = None
        self.keep_running = True
        try:
            # Raises a KeyError if SLACK_TOKEN environment variable is missing
            token = os.environ['SLACK_TOKEN']
        except:
            # Alternatively, place slack token in the source code
            # API_TOKEN = '###token###'
            print('SLACK_TOKEN missing')
        print("Slack Token {}".format(token))
        self._client = SlackClient(token)

    def start(self):
        print("Starting!")
        if self._client.rtm_connect():
            while self.keep_running:
                print(self._client.rtm_read())
                time.sleep(1)
        else:
            print("Connection Failed, invalid token?")
        
    def stop(self):
        self.keep_running = False

print("Main!")
bot = Bot()
bot.start()
