# -*- coding: utf-8 -*-
"""
Defines views.
"""
import calendar
import logging

from flask import abort, make_response, redirect
from flask.ext.mako import render_template
from mako.exceptions import TopLevelLookupException

from presence_analyzer.main import app
from presence_analyzer.utils import (
    jsonify, get_data, mean, group_by_weekday, mean_time_of_presence, get_xml
)


log = logging.getLogger(__name__)  # pylint: disable=invalid-name


@app.route('/<string:template_file>', methods=['GET'])
def template_for_url(template_file):
    """
    Render templates for url.
    """
    get_xml()
    if not template_file.endswith('.html'):
        template_file = '{}.html'.format(template_file)

    try:
        return render_template(template_file, template_file=template_file)
    except TopLevelLookupException:
        return make_response('page not found', 404)


@app.route('/')
def mainpage():
    """
    Redirects to front page.
    """
    return redirect('presence_weekday.html')


@app.route('/api/v1/users', methods=['GET'])
@jsonify
def users_view():
    """
    Users listing for dropdown.
    """
    data = get_data()
    return [
        {'user_id': i, 'name': 'User {0}'.format(str(i))}
        for i in data.keys()
    ]


@app.route('/api/v1/mean_time_weekday/<int:user_id>', methods=['GET'])
@jsonify
def mean_time_weekday_view(user_id):
    """
    Returns mean presence time of given user grouped by weekday.
    """
    data = get_data()
    if user_id not in data:
        log.debug('User %s not found!', user_id)
        abort(404)

    weekdays = group_by_weekday(data[user_id])
    result = [
        (calendar.day_abbr[weekday], mean(intervals))
        for weekday, intervals in enumerate(weekdays)
    ]
    return result


@app.route('/api/v1/presence_weekday/<int:user_id>', methods=['GET'])
@jsonify
def presence_weekday_view(user_id):
    """
    Returns total presence time of given user grouped by weekday.
    """
    data = get_data()
    if user_id not in data:
        log.debug('User %s not found!', user_id)
        abort(404)

    weekdays = group_by_weekday(data[user_id])
    result = [
        (calendar.day_abbr[weekday], sum(intervals))
        for weekday, intervals in enumerate(weekdays)
    ]

    result.insert(0, ('Weekday', 'Presence (s)'))
    return result


@app.route('/api/v1/presence_start_end/<int:user_id>', methods=['GET'])
@jsonify
def presence_start_end_view(user_id):
    """
    Returns mean time of presence.
    """
    data = get_data()
    if user_id not in data:
        log.debug('User %s not found!', user_id)
        abort(404)

    mean_times = mean_time_of_presence(data[user_id])
    result = [
        (calendar.day_abbr[weekday], mean_times[value])
        for weekday, value in enumerate(mean_times)
    ]
    return result
