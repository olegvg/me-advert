# -*- coding: utf-8 -*-

from __future__ import division

__author__ = 'ogaidukov'

import math
import re

states = {
    'active': u'активная',
    'paused': u'приостановлена',
    'completed': u'закончена',
    'archived': u'архивная'
}

normalized_curve_func = lambda x: 4.0 * math.atan(x) / math.pi  # I prefer using atan rather than atan2


def reach(target_impressions, total_impressions, frequency):
    frequency_to_total_impressions = frequency * normalized_curve_func(total_impressions / target_impressions) + \
                                     normalized_curve_func(target_impressions / total_impressions) - 1
    return total_impressions / frequency_to_total_impressions


def format_decimal(val):
    rev = (str(val))[::-1]
    num_array = []
    for part in re.findall('..?.?', rev):
        num_array.insert(0, part[::-1])
    return ' '.join(num_array)