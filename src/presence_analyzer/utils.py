# -*- coding: utf-8 -*-
"""
Helper functions used in views.
"""

import csv
import logging

from json import dumps
from functools import wraps
from datetime import datetime
from threading import Lock
from time import time

from flask import Response
from lxml import etree

from presence_analyzer.main import app


log = logging.getLogger(__name__)  # pylint: disable=invalid-name


CACHE = {}


def memoize(duration):
    """
    Decorator to caching data. Set duration in seconds.
    Return data from cache if exist and not expired.
    """
    lock = Lock()

    def _memoize(function):  # pylint: disable=missing-docstring
        def __memoize(*args, **kwargs):  # pylint: disable=missing-docstring
            key = function.__name__
            now = time()

            with lock:
                if key in CACHE and CACHE[key]['time'] > now:
                    return CACHE[key]['value']

                result = function(*args, **kwargs)
                CACHE[key] = {
                    'time': now + duration,
                    'value': result
                }

            return result
        return __memoize
    return _memoize


def jsonify(function):
    """
    Creates a response with the JSON representation of wrapped function result.
    """
    @wraps(function)
    def inner(*args, **kwargs):
        """
        This docstring will be overridden by @wraps decorator.
        """
        return Response(
            dumps(function(*args, **kwargs)),
            mimetype='application/json'
        )
    return inner


@memoize(600)
def get_data():
    """
    Extracts presence data from CSV file and groups it by user_id.

    It creates structure like this:
    data = {
        'user_id': {
            datetime.date(2013, 10, 1): {
                'start': datetime.time(9, 0, 0),
                'end': datetime.time(17, 30, 0),
            },
            datetime.date(2013, 10, 2): {
                'start': datetime.time(8, 30, 0),
                'end': datetime.time(16, 45, 0),
            },
        }
    }
    """
    data = {}
    with open(app.config['DATA_CSV'], 'r') as csvfile:
        presence_reader = csv.reader(csvfile, delimiter=',')
        for i, row in enumerate(presence_reader):
            if len(row) != 4:
                # ignore header and footer lines
                continue

            try:
                user_id = int(row[0])
                date = datetime.strptime(row[1], '%Y-%m-%d').date()
                start = datetime.strptime(row[2], '%H:%M:%S').time()
                end = datetime.strptime(row[3], '%H:%M:%S').time()
            except (ValueError, TypeError):
                log.debug('Problem with line %d: ', i, exc_info=True)

            data.setdefault(user_id, {})[date] = {'start': start, 'end': end}

    return data


@memoize(600)
def get_data_xml():
    """
    Get data from xml.

    It creates structure like this:
    data = {
        'user_id': {
                'avatar': 'scheme://server:port/api/images/users/user_id',
                'name': 'Jan K.',
                }
            }
    """
    tree = etree.parse(app.config['DATA_XML'])  # pylint: disable=no-member
    root = tree.getroot()
    server = root.find('server')
    users = root.find('users')
    result = {}

    for user in users:
        result[int(user.attrib['id'])] = {
            'avatar': '{protocol}://{serv}:{port}{url}'.format(
                protocol=server.find('protocol').text,
                serv=server.find('host').text,
                port=server.find('port').text,
                url=user.find('avatar').text
            ),
            'name': user.find('name').text
        }

    return result


def group_by_weekday(items):
    """
    Groups presence entries by weekday.
    """
    result = [[], [], [], [], [], [], []]  # one list for every day in week
    for date in items:
        start = items[date]['start']
        end = items[date]['end']
        result[date.weekday()].append(interval(start, end))
    return result


def mean_by_month(items):
    """
    Groups mean presence by month.
    """
    result = [[] for _ in range(12)]
    for date in items:
        start = items[date]['start']
        end = items[date]['end']
        result[date.month-1].append(interval(start, end))
    return [mean(intervals) for intervals in result]


def seconds_since_midnight(time_to_calc):
    """
    Calculates amount of seconds since midnight.
    """
    return (
        time_to_calc.hour * 3600 + time_to_calc.minute * 60 +
        time_to_calc.second
    )


def interval(start, end):
    """
    Calculates inverval in seconds between two datetime.time objects.
    """
    return seconds_since_midnight(end) - seconds_since_midnight(start)


def mean(items):
    """
    Calculates arithmetic mean. Returns zero for empty lists.
    """
    return float(sum(items)) / len(items) if len(items) > 0 else 0


def mean_time_of_presence(items):
    """
    Calculates mean time of presence.
    """
    result = {i: {'start': [], 'end': []} for i in range(7)}

    for date in items:
        start = items[date]['start']
        end = items[date]['end']
        result[date.weekday()]['start'].append(seconds_since_midnight(start))
        result[date.weekday()]['end'].append(seconds_since_midnight(end))

    for day in result:
        result[day]['start'] = mean(result[day]['start'])
        result[day]['end'] = mean(result[day]['end'])
    return result
