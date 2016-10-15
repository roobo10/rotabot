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
import pprint

def spawn_bot():
    return SampleBot()

class SampleBot(object):
    def __init__(self):
        self.resource = None

    def start(self, resource):
        self.resource = resource
        print("Started Bot for ResourceID: {}".format(self.resource['resourceID']))
        print("Slack Token {}".format(os.environ['SLACK_TOKEN']))
        # this is where you'd setup your websocket rtm connection to Slack using token
        sc = SlackClient(token)


    def stop(self, resource):
        print("Stopped Bot for ResourceID: {}".format(self.resource['resourceID']))
        self.resource = None
        # this is where you'd close your Slack socket connection, and save any context or data

class Rota:
    _days = [0,1,2,3,4]
    _start = 0
    _end = 0
    _bank_holidays = [arrow.get("2016/12/26"),arrow.get("2016/12/27"),arrow.get("2017/01/02"),arrow.get("2017/01/03"),arrow.get("2017/04/14"),arrow.get("2017/04/17"),arrow.get("2017/05/01"),arrow.get("2017/05/29")]
    _persons = []
    _haystack = []
    _rota = []
    _min_days = 3

    _attempts = 1000

    def __init__(self, start_date, end_date, persons):
        self._start = arrow.get(start_date)
        self._end = arrow.get(end_date)
        self._persons = persons
        logging.debug("Rota for %d days." % self._get_days())

    def _get_workdays(self):
        workdays = 0
        for person in self._persons:
            workdays += len(person._days_worked)
        return workdays

    def _get_days(self):
        days = self._end - self._start
        number_days = 0
        for i in range(days.days + 1):
            d = self._start + td(days=i)
            if d.weekday() in self._days:
                number_days += 1
        return number_days

    def _ooh_coefficient(self):
        total_days = self._get_days()
        days = total_days
        workdays = self._get_workdays()
        logging.debug("Days: %d; Workdays: %d; Persons: %d" % (days, workdays, len(self._persons)))
        ooh_coefficient = ((days / len(self._persons))) / ((workdays / len(self._persons)) /5)
        return ooh_coefficient

    def _build_haystack(self):
        total_days = self._get_days()
        days = total_days
        k = self._ooh_coefficient()
        haystack = []
        for person in self._persons:
            num = int(round(len(person._days_worked)/5 * k))
            for i in range(0,num):
                haystack.append(person._name)

        while len(haystack) > days:
            haystack.pop(random.randint(0,len(haystack)-1))

        while len(haystack) < days:
            person = self._persons[random.randint(0,len(self._persons)-1)]
            haystack.append(person._name)

        logging.debug(haystack)
        logging.debug(len(haystack))

        return haystack

    def _do_rota(self, haystack):
        rota = []
        total_days = self._get_days()
        days = self._end - self._start
        for i in range(0, days.days+1):
            day = self._start + td(days=i)
            if day not in self._bank_holidays and day.weekday() in self._days :
                logging.debug ("Doing day %d of %d..." % (i, days.days))
                selected = False
                attempt = 0
                while not selected and attempt < (len(haystack) * 3):
                    choice = random.randint(0,len(haystack)-1)
                    logging.debug("Trying number %d of %d" % (choice, len(haystack)))
                    for person in self._persons:
                        if selected == False:
                            if person._name == haystack[choice]:
                                logging.debug("Found %s." % (haystack[choice]))
                                if person.can_work(day) and person._name not in rota[-self._min_days:]:
                                    logging.debug("%s is a HIT." % (haystack[choice]))
                                    selected = True
                                    rota.append(haystack.pop(choice))
                                else:
                                    logging.debug("%s is a miss." % (haystack[choice]))

                    attempt += 1
                if not selected:
                    return None
            elif day.weekday() not in self._days:
                rota.append("---------")
            else:
                rota.append("BANK HOLIDAY")
        return rota

    def go(self):
        haystack = self._build_haystack()
        success = False
        attempt = 0
        while not success and attempt <= self._attempts:
            logging.debug("ATTEMPT %s" % attempt)
            copy_haystack = [h for h in haystack]

            rota = self._do_rota(copy_haystack)

            if rota is not None:
                days = self._end - self._start
                fridays =  []
                j = 0
                for i in range(0, days.days + 1):
                    day = self._start + td(days=i)
                    if day.weekday() == 4:
                        fridays.append(rota[i])

                work_fridays = []
                for person in persons:
                    if 4 in person._days_worked:
                        work_fridays.append(person._name)

                fridays_people = {}
                for person in fridays:
                    if person not in fridays_people and person != "BANK HOLIDAY" and person != "---------":
                        fridays_people[person] =  fridays.count(person)

                max_fridays = 0
                logging.debug("Fridays:")
                logging.debug(fridays)
                for person,worked in fridays_people.items():
                    max_fridays = worked if worked > max_fridays else max_fridays

                logging.debug("The most Fridays worked is %d." % max_fridays)

                min_fridays = 1000
                for person in persons:
                    if 4 in person._days_worked:
                        min_fridays = fridays.count(person._name) if fridays.count(person._name) < min_fridays else min_fridays
                logging.debug("The least Fridays worked is %d." % min_fridays)

                if max_fridays <= min_fridays + 1:
                    success = True
            attempt += 1
        logging.debug(rota)
        if success:
            self._rota = rota
            logging.info("SUCCEEDED ON ATTEMPT: %d" % attempt)
        else:
            logging.critical("FAILED TO CREATE ROTA.")
        return success

    def print_rota(self):
        total_days = self._get_days()
        days = self._end - self._start
        fridays = []
        print ("|    Day   | %s | %s |" % ("Weekday".ljust(9), "Name".ljust(13)))
        print ("|:--------:|:----------|:--------------|")
        for i in range(0, days.days + 1):
            day = self._start + td(days=i)
            weekdays = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
            print("| %s | %s | %s |" % (day.strftime("%d/%m/%y"), day.strftime("%A").ljust(9), self._rota[i].ljust(13)))
            if day.weekday() == 4:
                fridays.append(self._rota[i])
        print()
        print()

    def make_csv(self, filename):
        total_days = self._get_days()
        days = self._end - self._start
        ofile  = open(filename, "w",newline="")
        fieldnames=['Subject','Start Date','All Day Event']
        writer = csv.DictWriter(ofile, fieldnames=fieldnames)
        writer.writeheader()

        for i in range(0, days.days + 1):
            day = self._start + td(days=i)
            if self._rota[i] != "---------" and self._rota[i] != "BANK HOLIDAY":
                writer.writerow({'Subject':self._rota[i], 'Start Date':day.strftime("%Y/%m/%d"),'All Day Event':'True'})

        ofile.close()

class Person:
    _name = ""
    _days_worked = []
    _days_off = []

    def __init__(self, name, days_worked, days_off):
        self._name = name
        self._days_worked = days_worked
        self._days_off = days_off

    def can_work(self, day):
        if day not in self._days_off and day.weekday() in self._days_worked:
            return True
        return False

if __name__ == "__main__":

    # Fires when a data-transfer type of message has been sent from the Beep Boop Resourcer server.
    # The following "types" of messages are supported:
    #   add_resource - a request to add a bot instance to a team has been received.
    #   update_resource - a request to update an instance of a bot has been received (config changed)
    #   remove_resource - a request to remove a bot instance from a team has been received.

    # The message has the following (prettyprint) form:
    #   {
    #     u'date': u'2016-03-01T15:06:20.471155964-07:00',
    #     u'msgID': u'00a6d8e1-2f83-439e-9a1c-f9537c8ba0d3',
    #     u'resource': { u'MY_CUSTOM_CONFIG_NAME': u'the peanuts are friendly'},
    #     u'resourceID': u'ec4fba40-1e89-4005-a236-4f6f77ef19ca',
    #     u'type': u'add_resource'
    #   }

    def on_message(ws, message):

        # Access the message type
        print (message['type'])

        # Access the config defined in the bot.yml (commented avoid error)
        # print (message['resource']['MY_CUSTOM_CONFIG'])

        pp = pprint.PrettyPrinter(indent=2)
        pp.pprint(message)


    # Fires when an error occurred in the connection with the Beep Boop Resourcer server.
    def on_error(ws, error):
        print ('Error: ' + str(error))

    # Fires the connection with the Beep Boop resourcer has closed.
    def on_close(ws):
        print ('Closed')

    # Fires when the connection with the Beep Boop resourcer has opened.
    def on_open(ws):
        print('Opened')


    # handler_funcs allows you to declare the events you want to listen for and their handlers
    handler_funcs = dict([
            ('on_open', on_open),
            ('on_message', on_message),
            ('on_error', on_error),
            ('on_close', on_close),
        ])

    # optional to use our bot manager to spawn instances of your bot in daemon threads;
    # bot developer can choose instead to listen to the websockect messages above and
    # write their own bot per resource manager or integrate with a 3rd party library that does
    botManager = bot_manager.BotManager(spawn_bot)

    bp = resourcer.Resourcer(botManager)
    bp.handlers(handler_funcs)
    bp.start()