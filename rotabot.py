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
                        if 'type' in message: 
                            self._process_message(message)
                time.sleep(1)
        else:
            logging.critical("Connection Failed, invalid token?")
    def stop(self):
        self.keep_running = False
    
    def _process_message(self, message):
        if message['type'] == "message" and len(message['text']) > 0:
            if "create rota" in message['text'].lower():
                self._status[message['user']] = {}
                self._status[message['user']] = {'status':'awaiting rota type'} 
                self._client.rtm_send_message(message['channel'],"What kind of rota would you like to make? Please reply with 'OOH' or 'General Trim'.")
            elif message['user'] in self._status:
                p = self._status[message['user']]
                if p['status'] == 'awaiting rota type':
                    if message['text'].lower() == "ooh" or message['text'].lower() == "general trim":
                        self._client.rtm_send_message(message['channel'],"Thanks! What day will the rota start on? Please enter it as YYYY/MM/DD.")
                        self._status[message['user']]['status'] = 'awaiting start date'
                    else:
                        self._client.rtm_send_message(message['channel'],"Sorry, that's  not a valid date.  Please try again.")
                elif p['status'] == 'awaiting start date':
                    try:
                        self.start_date = time.strptime(message['text'],"%Y/%m/%d")
                        self._client.rtm_send_message(message['channel'],"OK! Can you please enter the last date for the rota in the same format?")
                        self._status[message['user']]['status'] = 'awaiting end date'
                    except:
                        self._client.rtm_send_message(message['channel'],"Sorry, that's not a valid date.  Please try again.")
                elif p['status'] == 'awaiting end date':
                    try:
                        self.end_date = time.strptime(message['text'],"%Y/%m/%d")
                        self._client.rtm_send_message(message['channel'],"That's great!")
                        self._client.rtm_send_message(message['channel'],"Who's on this rota? Please type the names, separated by commas.")
                        self._status[message['user']]['status'] = 'awaiting names'
                    except:
                        self._client.rtm_send_message(message['channel'],"Sorry, that's not a valid date.  Please try again.")
                elif p['status'] == 'awaiting names':
                    self.rota_names = [n.strip().title() for n in message['text'].split(',')]
                    self._client.rtm_send_message(message['channel'],"OK! That's %d people.  Is that right? Yes or No" % (len(self.rota_names)))
                    self._status[message['user']]['status'] = 'awaiting names confirmation'
                elif p['status'] == 'awaiting names confirmation':
                    if message['text'].lower() == "yes":
                        self._client.rtm_send_message(message['channel'],"Great!")
                        self.rota_patterns = [[1,1,1,1,1]] * len(self.rota_names)
                        logging.debug(self.rota_patterns)
                        self._client.rtm_send_message(message['channel'],"What is %s's work pattern? For each day of the week, starting with Monday write a 1 or a 0.  For example, if %s works every day except Thursday, then write 11101." % (self.rota_names[0],self.rota_names[0]))
                        self._status[message['user']]['status'] = "awaiting pattern 0"
                    else:
                        self._client.rtm_send_message(message['channel'],"Oops! Let's try those names again. Please type the names, separated by commas.")
                        self._status[message['user']]['status'] = 'awaiting names'
                elif p['status'][:len('awaiting pattern')] == 'awaiting pattern':
                     t = p['status'].rsplit(' ',1)
                     if message['text'].isdigit() and len(message['text']) == 5:
                        success = True
                        pattern = []
                        for char in message['text']:
                            i = int(char)
                            pattern.append(i)
                            if i != 0 and i != 1:
                                success = False
                        
                        if success:
                            i = int(t[1])
                            self.rota_patterns[i] = pattern
                            i+=1
                            self._client.rtm_send_message(message['channel'],"Thanks.  Now for %s." % (self.rota_names[i]))
                            if i < len(self.rota_names):
                                self._status[message['user']]['status'] = "awaiting pattern %d" % i
                            else
                                self._status[message['user']]['status'] = "awaiting leave 0"
                                self._client.rtm_send_message(message['channel'],"Now let's sort out days off.  Can you list the days %s is off? Please list all the days in the format YYYY/MM/DD, separated by commas." % self.rota_names[0])
                        else:
                            self._client.rtm_send_message(message['channel'],"That wasn't quite right.  Can you try again?")
                        
                        logging.info(self.rota_names)
                        logging.info(self.rota_patterns)
                elif p['status'][:len('awaiting leave')] == 'awaiting leave':
                    t = p['status'].rsplit(' ',1)
                    days_off = []
                    success = False
                    try:
                        days_off = [time.strptime(d.strip(),"%Y/%m/%d") for d in message['text'].spit(',')]
                        success = True
                    except:
                        self._client.rtm_send_message(message['channel'],"That didn't work.  Can you try again?")
                        
                    if success:
                        i = int(t[1])
                        self.rota_days_off[i] = days_off
                        i+=1
                        self._client.rtm_send_message(message['channel'],"Thanks.  Now for %s." % (self.rota_names[i]))
                        if i < len(self.rota_names):
                            self._status[message['user']]['status'] = "awaiting leave %d" % i
                        else
                            self._status[message['user']]['status'] = "awaiting generate"
                            self._client.rtm_send_message(message['channel'],"OK! Are you ready to create this rota?")

                    logging.info(self.rota_names)
                    logging.info(self.rota_patterns)
                else:
                    self._client.rtm_send_message(message['channel'],"Sorry, I don't understand what you're saying! Type 'create rota' to restart.")

if __name__ == "__main__":
    log_level = os.getenv("LOG_LEVEL", "DEBUG")
    logging.basicConfig(format='%(asctime)s - %(levelname)s: %(message)s', level=log_level)
    logging.debug("Init...")
    bot = Bot()
    bot.start()