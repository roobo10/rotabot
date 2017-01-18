import math
import random
import functools
from collections import Counter
import logging
from datetime import datetime, date, timedelta as td
import csv
import io

class Rota:
    _days = [1,2,3,4,5]
    _start = 0
    _end = 0
    _bank_holidays = [datetime.strptime("2016/12/26","%Y/%m/%d"),
                        datetime.strptime("2016/12/27","%Y/%m/%d"),
                        datetime.strptime("2017/01/02","%Y/%m/%d"),
                        datetime.strptime("2017/01/03","%Y/%m/%d"),
                        datetime.strptime("2017/04/14","%Y/%m/%d"),
                        datetime.strptime("2017/04/17","%Y/%m/%d"),
                        datetime.strptime("2017/05/01","%Y/%m/%d"),
                        datetime.strptime("2017/05/29","%Y/%m/%d"),
                        datetime.strptime("2017/07/17","%Y/%m/%d"),
                        datetime.strptime("2017/09/25","%Y/%m/%d"),
                        datetime.strptime("2017/12/25","%Y/%m/%d"),
                        datetime.strptime("2017/12/26","%Y/%m/%d"),
                        datetime.strptime("2018/01/01","%Y/%m/%d"),
                        datetime.strptime("2017/01/02","%Y/%m/%d")]
    _persons = []
    _haystack = []
    _rota = []
    _min_days = 3
    _type = "ooh"

    _attempts = 1000

    def __init__(self, start_date, end_date, persons, type="ooh"):
        self._start = start_date
        self._end = end_date
        self._persons = persons
        if type == "gentrim" or type == "general trim" :
            self._days = [1,2,4,5]
            self._type = "gentrim"
            self._min_days = 10
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
            if d.isoweekday() in self._days:
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
            if day not in self._bank_holidays and day.isoweekday() in self._days :
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
            elif day.isoweekday() not in self._days:
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
            
            if self._type != "ooh":
                success = True
            else:
                if rota is not None:
                    days = self._end - self._start
                    fridays =  []
                    j = 0
                    for i in range(0, days.days + 1):
                        day = self._start + td(days=i)
                        if day.isoweekday() == 5:
                            fridays.append(rota[i])

                    work_fridays = []
                    for person in self._persons:
                        if 5 in person._days_worked:
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
                    for person in self._persons:
                        if 5 in person._days_worked:
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
            print("| %s | %s | %s |" % (day.strftime("%d/%m/%y"), day.strftime("%A").ljust(9), self._rota[i].ljust(13)))
            if day.isoweekday() == 5:
                fridays.append(self._rota[i])
        print()
        print()

    def md_rota(self, show_fridays=False):
        total_days = self._get_days()
        days = self._end - self._start
        fridays = []
        md = "|    Day   | %s | %s |\n" % ("Weekday".ljust(9), "Name".ljust(13))
        md += "|:--------:|:----------|:--------------|\n"
        for i in range(0, days.days + 1):
            day = self._start + td(days=i)
            md += "| %s | %s | %s |\n" % (day.strftime("%d/%m/%y"), day.strftime("%A").ljust(9), self._rota[i].ljust(13))
            if day.isoweekday() == 5:
                fridays.append(self._rota[i])
                
        if show_fridays:
            md += "\n| Name          | Fridays |\n"
            md +=   "|:--------------|:--------|\n"
            
            for p in self._persons:
                md += "| %s | %s |\n" %(p._name.ljust(13), str(fridays.count(p._name)).ljust(7))
        return md

    def rota_csv(self):
        total_days = self._get_days()
        days = self._end - self._start
        csv_output  = io.StringIO()
        fieldnames=['Subject','Start Date','All Day Event']
        if self._type == "gentrim":
            fieldnames = ['Subject','Start Date','Start Time', 'End Time']
        writer = csv.DictWriter(csv_output, fieldnames=fieldnames)
        writer.writeheader()

        for i in range(0, days.days + 1):
            day = self._start + td(days=i)
            if self._rota[i] != "---------" and self._rota[i] != "BANK HOLIDAY":
                if self._type == "gentrim":
                    writer.writerow({'Subject':self._rota[i], 'Start Date':day.strftime("%Y/%m/%d"),'Start Time':'1:00 PM','End Time':'2:00 PM'})
                else:    
                    writer.writerow({'Subject':self._rota[i], 'Start Date':day.strftime("%Y/%m/%d"),'All Day Event':'True'})

        return csv_output.getvalue()

class Person:
    _name = ""
    _days_worked = []
    _days_off = []

    def __init__(self, name, days_worked, days_off):
        self._name = name
        self._days_worked = days_worked
        self._days_off = days_off

    def can_work(self, day):
        if day not in self._days_off and day.isoweekday() in self._days_worked:
            return True
        return False

