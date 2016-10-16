from slackclient import SlackClient
from slacker import Slacker
import os
from beepboop import resourcer
from beepboop import bot_manager
import time
from datetime import datetime
import logging
from rota import Person
from rota import Rota

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
        self._slack = Slacker(token)
        self.username = "Rotabot"
        self.icon_emoji = ":robot_face:"
        
    def start(self):
        logging.debug("Starting!")
        if self._client.rtm_connect():
            self._slack.users.set_active()
            while self.keep_running:
                messages = self._client.rtm_read()
                logging.info(messages)
                if len(messages) > 0:
                    for message in messages:
                        if 'type' in message and 'user' in message:
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
                self._slack.chat.post_message(message['channel'],"What kind of rota would you like to make? Please reply with `OOH` or `General Trim`.", username=self.username, as_user=False, icon_emoji=self.icon_emoji)
            elif message['user'] in self._status:
                p = self._status[message['user']]
                if p['status'] == 'awaiting rota type':
                    if message['text'].lower() == "ooh" or message['text'].lower() == "general trim":
                        self.type = message['text'].lower()
                        self._slack.chat.post_message(message['channel'],"Thanks! What day will the rota start on? Please enter it as `YYYY/MM/DD`.", username=self.username, as_user=False, icon_emoji=self.icon_emoji)
                        self._status[message['user']]['status'] = 'awaiting start date'
                    else:
                        self._slack.chat.post_message(message['channel'],"Sorry, that's  not a valid date.  Please try again.", username=self.username, as_user=False, icon_emoji=self.icon_emoji)
                elif p['status'] == 'awaiting start date':
                    try:
                        self.start_date = datetime.strptime(message['text'],"%Y/%m/%d")
                        self._slack.chat.post_message(message['channel'],"OK! Can you please enter the last date for the rota in the same format?", username=self.username, as_user=False, icon_emoji=self.icon_emoji)
                        self._status[message['user']]['status'] = 'awaiting end date'
                    except:
                        self._slack.chat.post_message(message['channel'],"Sorry, that's not a valid date.  Please try again.", username=self.username, as_user=False, icon_emoji=self.icon_emoji)
                elif p['status'] == 'awaiting end date':
                    try:
                        self.end_date = datetime.strptime(message['text'],"%Y/%m/%d")
                        self._slack.chat.post_message(message['channel'],"That's great!", username=self.username, as_user=False, icon_emoji=self.icon_emoji)
                        self._slack.chat.post_message(message['channel'],"Who's on this rota? Please type the names, separated by commas.", username=self.username, as_user=False, icon_emoji=self.icon_emoji)
                        self._status[message['user']]['status'] = 'awaiting names'
                    except:
                        self._slack.chat.post_message(message['channel'],"Sorry, that's not a valid date.  Please try again.", username=self.username, as_user=False, icon_emoji=self.icon_emoji)
                elif p['status'] == 'awaiting names':
                    self.rota_names = [n.strip().title() for n in message['text'].split(',')]
                    self._slack.chat.post_message(message['channel'],"OK! That's *%d people*.  Is that right? `YES` or `NO`" % (len(self.rota_names)), username=self.username, as_user=False, icon_emoji=self.icon_emoji)
                    self._status[message['user']]['status'] = 'awaiting names confirmation'
                elif p['status'] == 'awaiting names confirmation':
                    if message['text'].lower() == "yes":
                        self._slack.chat.post_message(message['channel'],"Great!", username=self.username, as_user=False, icon_emoji=self.icon_emoji)
                        self.rota_patterns = [[1,2,3,4,5]] * len(self.rota_names)
                        self.rota_days_off = [[1,1,1,1,1]] * len(self.rota_names)
                        logging.debug(self.rota_patterns)
                        self._slack.chat.post_message(message['channel'],"What is %s's work pattern? List the 'weekday numbers' of the days worked with no spaces, where Monday is 1, Tuesday is 2, etc.  For example, if %s works every day except Thursday, then write `1235`." % (self.rota_names[0],self.rota_names[0]), username=self.username, as_user=False, icon_emoji=self.icon_emoji)
                        self._status[message['user']]['status'] = "awaiting pattern 0"
                    else:
                        self._slack.chat.post_message(message['channel'],"Oops! Let's try those names again. Please type the names, separated by commas.", username=self.username, as_user=False, icon_emoji=self.icon_emoji)
                        self._status[message['user']]['status'] = 'awaiting names'
                elif p['status'][:len('awaiting pattern')] == 'awaiting pattern':
                     t = p['status'].rsplit(' ',1)
                     if message['text'].isdigit() and len(message['text']) <= 5:
                        success = True
                        pattern = []
                        for char in message['text']:
                            i = int(char)
                            pattern.append(i)
                            if i not in [1,2,3,4,5]:
                                success = False

                        if success:
                            i = int(t[1])
                            self.rota_patterns[i] = pattern
                            i+=1
                            if i < len(self.rota_names):
                                self._status[message['user']]['status'] = "awaiting pattern %d" % i
                                self._slack.chat.post_message(message['channel'],"Thanks.  Now for %s." % (self.rota_names[i]), username=self.username, as_user=False, icon_emoji=self.icon_emoji)
                            else:
                                self._status[message['user']]['status'] = "awaiting leave 0"
                                self._slack.chat.post_message(message['channel'],"Now let's sort out days off.  Can you list the days %s is off? Please list all the days in the format `YYYY/MM/DD`, separated by commas. If %s is not taking any days off, type `-`." % (self.rota_names[0],self.rota_names[0]), username=self.username, as_user=False, icon_emoji=self.icon_emoji)
                        else:
                            self._slack.chat.post_message(message['channel'],"That wasn't quite right.  Can you try again?", username=self.username, as_user=False, icon_emoji=self.icon_emoji)

                        logging.info(self.rota_names)
                        logging.info(self.rota_patterns)
                elif p['status'][:len('awaiting leave')] == 'awaiting leave':
                    t = p['status'].rsplit(' ',1)
                    days_off = []
                    success = False

                    if message['text'] == "-" or message['text'].lower() == "no" or message['text'].lower() == "none":
                        success = True
                    else:
                        try:
                            days_off = [datetime.strptime(d.strip(),"%Y/%m/%d") for d in message['text'].split(',')]
                            success = True
                        except:
                            self._slack.chat.post_message(message['channel'],"That didn't work.  Can you try again?", username=self.username, as_user=False, icon_emoji=self.icon_emoji)

                    if success:
                        i = int(t[1])
                        self.rota_days_off[i] = days_off
                        i+=1
                        if i < len(self.rota_names):
                            self._slack.chat.post_message(message['channel'],"Thanks.  Now for %s." % (self.rota_names[i]), username=self.username, as_user=False, icon_emoji=self.icon_emoji)
                            self._status[message['user']]['status'] = "awaiting leave %d" % i
                        else:
                            self._status[message['user']]['status'] = "awaiting generate"
                            self._slack.chat.post_message(message['channel'],"OK! Are you ready to create this rota?", username=self.username, as_user=False, icon_emoji=self.icon_emoji)
                    logging.info(self.rota_names)
                    logging.info(self.rota_days_off)
                elif p['status'] == 'awaiting generate':
                    if message['text'].lower() == "yes":
                        persons = []
                        logging.info(self.rota_names)
                        logging.info(self.rota_patterns)
                        logging.info(self.rota_days_off)
                        for i in range(0, len(self.rota_names)):
                            persons.append(Person(self.rota_names[i], self.rota_patterns[i], self.rota_days_off[i]))
                        r = Rota(self.start_date, self.end_date, persons, self.type)
                        r.go()
                        rota_md = r.md_rota(True)
                        rota_md_lines = rota_md.split("\n") 
                        n = 21
                        rota_md_group = [rota_md_lines[m:m+n] for m in range(0, len(rota_md_lines), n)]
                        r_title = "Rota for %s to %s" % (self.start_date.strftime("%d/%m/%Y"),self.end_date.strftime("%d/%m/%Y"))
                        self._slack.chat.post_message(message['channel'],"Here's the rota!\n*" + r_title + "*", username=self.username, as_user=False, icon_emoji=self.icon_emoji)
                        for line_md in rota_md_group:
                            if len(line_md) > 0:
                                self._slack.chat.post_message(message['channel'],"```%s```" % ("\n".join(line_md)), username=self.username, as_user=False, icon_emoji=self.icon_emoji)
                        self._slack.chat.post_message(message['channel'],"Does the rota look good?  If you type `YES`, I can upload a file you can import straight into *Google Calendar*.", username=self.username, as_user=False, icon_emoji=self.icon_emoji)
                        self._status[message['user']]['status'] = "awaiting upload confirmation"
                        self._status[message['user']]['last_rota'] = r
                elif p['status'] == 'awaiting upload confirmation':
                    if message['text'].lower() == "yes" and 'last_rota' in self._status[message['user']]:
                        r = self._status[message['user']]['last_rota'] 
                        self._slack.api.post('files.upload',
                             data={
                                 'content': r.rota_csv(),
                                 'filetype': "csv",
                                 'filename': "Rota %s-%s.csv" % (self.start_date.strftime("%b%y"),self.end_date.strftime("%b%y")),
                                 'title': "Rota %s – %s" % (self.start_date.strftime("%b %y"),self.end_date.strftime("%b %y"))
                             })                
                else:
                    self._slack.chat.post_message(message['channel'],"Sorry, I don't understand what you're saying! Type 'create rota' to restart.", username=self.username, as_user=False, icon_emoji=self.icon_emoji)

if __name__ == "__main__":
    log_level = os.getenv("LOG_LEVEL", "INFO")
    logging.basicConfig(format='%(asctime)s - %(levelname)s: %(message)s', level=log_level)
    logging.debug("Init...")
    bot = Bot()
    bot.start()
