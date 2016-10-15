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
        self._status = {}
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
                messages = self._client.rtm_read()
                logging.info(messages)
                if len(messages) > 0:
                    for message in messages:
                        self._process_message(message)
                time.sleep(1)
        else:
            logging.critical("Connection Failed, invalid token?")
    def stop(self):
        self.keep_running = False
    
    def _process_message(self, message):
        if message['type'] == "message":
            if "create rota" in message['text'].lower():
                self._status[message['user']] = {}
                self._status[message['user']] = {'status':'awaiting rota type'} 
                self._client.rtm_send_message(message['channel'],"What kind of rota would you like to make? Please reply with 'OOH' or 'General Trim'.")            
            if message['user'] in self._status:
                p = self._status[message['user']]
                if p['status'] == 'awaiting rota type':
                    if message['text'].lower() == "ooh" or message['text'].lower() == "general trim":
                        self._client.rtm_send_message(message['channel'],"Thanks! What day will the rota start on? Please enter it as YYYY/MM/DD.")
                        self._status[message['user']] = {'status':'awaiting start date'} 
                    else:
                        self._client.rtm_send_message(message['channel'],"Sorry, that's  not a valid date.  Please try again.")
                elif p['status'] == 'awaiting start date':
                    try:
                        self.start_date = time.strptime(message['text'],"%Y/%m%d")
                        self._client.rtm_send_message(message['channel'],"OK! Can you please enter the last date for the rota in the same format?")
                        self._status[message['user']] = {'status':'awaiting end date'} 
                    except:
                        self._client.rtm_send_message(message['channel'],"Sorry, that's not a valid date.  Please try again.")
                elif p['status'] == 'awaiting end date':
                    try:
                        self.end_date = time.strptime(message['text'],"%Y/%m%d")
                        self._client.rtm_send_message(message['channel'],"That's great!")
                        self._client.rtm_send_message(message['channel'],"Who's on this rota? Please type the names, separated by commas.")
                        self._status[message['user']] = {'status':'awaiting names'} 
                    except:
                        self._client.rtm_send_message(message['channel'],"Sorry, that's not a valid date.  Please try again.")
                elif p['status'] == 'awaiting names':
                    self.rota_names = [n.strip().title() for n in message['names'].split(',')]
                    self._client.rtm_send_message(message['channel'],"OK! That's %d people.  Is that right? Yes or No" % (len(self.rota_names))
                    p['status'] == 'awaiting names confirmation':
                elif p['status'] == 'awaiting names confirmation':
                    if message['text'].lower() == "yes":
                        self._client.rtm_send_message(message['channel'],"Great!")
                    else:
                        self._client.rtm_send_message(message['channel'],"Oops! Let's try those names again. Please type the names, separated by commas.")
                        p['status'] == 'awaiting names':
                else:
                    self._client.rtm_send_message("Sorry, I don't understand what you're saying! Type 'create rota' to restart.")

if __name__ == "__main__":
    log_level = os.getenv("LOG_LEVEL", "DEBUG")
    logging.basicConfig(format='%(asctime)s - %(levelname)s: %(message)s', level=log_level)
    logging.debug("Init...")
    bot = Bot()
    bot.start()