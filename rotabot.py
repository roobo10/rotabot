from slackclient import SlackClient
from slacker import Slacker
import os
from beepboop import resourcer
from beepboop import bot_manager
import time
import logging 

class Bot(object):
    def __init__(self):
        logging.debug("Creating BOT!")
        token = None
        self.keep_running = True
        try:
            token = os.environ['SLACK_TOKEN']
        except:
            # Alternatively, place slack token in the source code
            # API_TOKEN = '###token###'
            print('SLACK_TOKEN missing')
        print("Slack Token {}".format(token))
        self._client = SlackClient(token)
    def start(self):
        logging.debug("Starting!")
        if self._client.rtm_connect():
            while self.keep_running:
                logging.info(self._client.rtm_read())
                time.sleep(1)
        else:
            logging.critical("Connection Failed, invalid token?")
        
    def stop(self):
        self.keep_running = False
        
logging.debug("Init...")
bot = Bot()
bot.start()
