#! -*- coding: utf-8 -*-
import re
import datetime
import calendar
from django.utils.regex_helper import normalize
from django.db.models.query import QuerySet
from django.core.urlresolvers import reverse

class PageSelector(object):
    def __init__(self, selector, default=None):
        self.patterns = [
            re.compile(r'^(?P<objects_per_page>\d+)-(?P<page>\d+)$'),
            re.compile(r'^(?P<objects_per_page>\d+)-(?P<page>\d+)-(?P<year>\d{4})$'),
            re.compile(r'^(?P<objects_per_page>\d+)-(?P<page>\d+)-(?P<year>\d{4})-(?P<week_or_month_selector>[wm])(?P<week_or_month>\d{1,2})$'),
            re.compile(r'^(?P<objects_per_page>\d+)-(?P<page>\d+)-(?P<year>\d{4})-(?P<week_or_month_selector>[m])(?P<week_or_month>\d{1,2})-(?P<day>\d{1,2})$'),
        ]
        self.selector = selector
        self.default = default
        self.populate()

    def populate(self):
        try:
            for pattern in self.patterns:
                match = pattern.search(self.selector)
                if match is not None:
                    break
        except TypeError:
            today = self.default or datetime.date.today()

            self.objects_per_page = 60
            self.page = 0
            self.year = today.year
            self.week_or_month_selector = 'm'
            self.month = today.month
            #self.day = today.day
            #return
        else:
            if match is not None:
                for k, v in match.groupdict().items():
                    setattr(self, k, v)

            self.objects_per_page = int(self.objects_per_page)
            self.page = int(self.page)
            if hasattr(self, "week_or_month_selector"):
                if self.week_or_month_selector == 'm':
                    self.month = self.week_or_month
                if self.week_or_month_selector == 'w':
                    self.week = self.week_or_month

    def __repr__(self):
        #return self.generate(**dict(self.__dict__))
        if hasattr(self, "day"):
            return "%d-%d-%d-%s%d-%d" % (
                self.objects_per_page,
                self.page,
                self.year,
                self.week_or_month_selector,
                self.month,
                self.day
            )
        if hasattr(self, "month"):
            return "%d-%d-%d-%s%d" % (
                self.objects_per_page,
                self.page,
                self.year,
                self.week_or_month_selector,
                self.month,
            )
        if hasattr(self, "month"):
            return "%d-%d-%d" % (
                self.objects_per_page,
                self.page,
                self.year,
            )
        return "%d-%d" % (
            self.objects_per_page,
            self.page,
        )


    def is_valid(self):
        try:
            for pattern in self.patterns:
                match = pattern.search(self.selector)
                if match is not None:
                    break
        except TypeError:
            return False

        if match is None:
            return False

        elements = match.groupdict()
        # Ne sert à rien car compris dans les regexp
        #if elements.has_key('week_or_month_selector') and elements['week_or_month_selector'] is not None and elements['week_or_month_selector'] != 'm' and elements['week_or_month_selector'] != 'w':
        #    return False
        if elements.has_key('week_or_month_selector') and elements['week_or_month_selector'] == 'm':
            if elements.has_key('week_or_month') and int(elements['week_or_month']) < 1:
                return False
            if elements.has_key('week_or_month') and int(elements['week_or_month']) > 12:
                return False
        if elements.has_key('week_or_month_selector') and elements['week_or_month_selector'] == 'w':
            # Ne sert à rien car ne passe pas les regexp
            #if elements.has_key('day') and elements['day'] is not None:
            #    return False
            if elements.has_key('week_or_month') and int(elements['week_or_month']) < 1:
                return False
            if elements.has_key('week_or_month') and int(elements['week_or_month']) > 53:
                return False

        if elements.has_key('day') and elements['day'] is not None:
            try:
                date = datetime.date(int(elements['year']), int(elements['week_or_month']), int(elements['day']))
            except ValueError:
                return False

        return True

    def generate(self, **kwargs):
        for pattern in self.patterns:
            normalized_patterns = normalize(pattern.pattern)
            for normalized_pattern in normalized_patterns:
                args = kwargs.copy()
                if args.has_key('month'):
                    args['week_or_month_selector'] = 'm'
                    args['week_or_month'] = args['month']
                    del args['month']
                if args.has_key('week'):
                    if args.has_key('day'):
                        raise TypeError
                    args['week_or_month_selector'] = 'w'
                    args['week_or_month'] = args['week']
                    del args['week']

                keys = args.keys()
                keys.sort()

                allowed_keys = normalized_pattern[1]
                allowed_keys.sort()

                if keys == allowed_keys:
                    self.selector = normalized_pattern[0] % args
                    if self.is_valid():
                        self.populate()
                        return self.selector

        raise TypeError

class DateComponent(object):
    page = None

    def selector(self):
        raise NotImplemented

    def get_absolute_url(self):
        return reverse(self.page.paginator.url_name, kwargs={ "selector": self.selector() })

class Day(DateComponent):
    def __init__(self, year, month, day, page):
        self.year = int(year)
        self.month = int(month)
        self.day = int(day)
        self.page = page

    def __repr__(self):
        return str(self.day)

    def repr(self):
        return repr(self)

    def date(self):
        return datetime.date(self.year, self.month, self.day)

    def selector(self):
        return u"%d-%d-%d-m%d-%d" % (
            self.page.selector.objects_per_page,
            self.page.selector.page,
            self.year,
            self.month,
            self.day
        )

class Month(DateComponent):
    def __init__(self, year, month, page):
        self.year = int(year)
        self.month = int(month)
        self.page = page

    def __repr__(self):
        return str(self.month)

    def repr(self):
        return repr(self)

    def days(self):
        return self.page.paginator.get_days_range(self.page, self.year, self.month)

    def date(self):
        return datetime.date(self.year, self.month, 1)

    def selector(self):
        return u"%d-%d-%d-m%d" % (
            self.page.selector.objects_per_page,
            self.page.selector.page,
            self.year,
            self.month
        )

class Year(DateComponent):
    def __init__(self, year, page):
        self.year = int(year)
        self.page = page

    def __repr__(self):
        return str(self.year)

    def repr(self):
        return repr(self)

    def months(self):
        return self.page.paginator.get_months_range(self.page, self.year)

    def date(self):
        return datetime.date(self.year, 1, 1)

    def selector(self):
        return u"%d-%d-%d" % (
            self.page.selector.objects_per_page,
            self.page.selector.page,
            self.year
        )

class DatePaginator(object):
    def __init__(self, object_list, attr, url_name):
        if not isinstance(object_list, QuerySet):
            raise Exception
        self.all_object_list = self.object_list = object_list
        self.attr = attr
        self._count = None
        self._years = []
        self._months = []
        self.url_name = url_name
        self.is_date_paginator = True

    def page(self, selector_str):
        object_list = self.object_list
        selector = PageSelector(selector_str, default=getattr(self.object_list[0], self.attr))

        filters = None

        year = None
        month = None
        day = None
        if selector and hasattr(selector, 'year'):
            year = int(selector.year)
        if selector and hasattr(selector, 'month'):
            month = int(selector.month)
        if selector and hasattr(selector, 'day'):
            day = int(selector.day)

        if day:
            filters = { '%s__range' % self.attr: (datetime.date(year,month,day),datetime.date(year,month,day) + datetime.timedelta(days=1)) }
        elif month:
            month_start, month_end = calendar.monthrange(year, month)
            filters = { '%s__range' % self.attr: (datetime.date(year,month,1), datetime.date(year,month,month_end) + datetime.timedelta(days=1)) }
        elif year:
            filters = { '%s__range' % self.attr: (datetime.date(year,1,1), datetime.date(year,12,31) + datetime.timedelta(days=1)) }

        if filters:
            sub_object_list = object_list.filter(**filters)
        else:
            sub_object_list = object_list

        self._page = Page(sub_object_list, selector, self)
        return self._page

    def _get_count(self):
        "Returns the total number of objects, across all pages."
        if hasattr(self, "_page"):
            return self._page.count
        if self._count is None:
            try:
                self._count = self.object_list.count()
            except (AttributeError, TypeError):
                # AttributeError if object_list has no count() method.
                # TypeError if object_list.count() requires arguments
                # (i.e. is of type list).
                self._count = len(self.object_list)
        return self._count
    count = property(_get_count)

    def get_total_count(self):
        return self.all_object_list.count()

    def get_years_range(self, page):
        if not self._years:
            self._years = [
                Year(year, page)
                for year in sorted(
                    [
                        d.year for d in self.object_list.only(self.attr).dates(
                            self.attr,
                            'year',
                            order='DESC'
                        )
                    ]
                )
            ]

        return self._years


    def get_months_range(self, page, year):
        if not self._months:
            self._months = [
                Month(year, month, page)
                for month in sorted(
                    [
                        d.month
                        for d in self.object_list.only(self.attr).filter(
                            **{
                                '%s__range' % self.attr: (datetime.date(year,1,1), datetime.date(year, 12, 31) + datetime.timedelta(days=1))
                            }
                        ).dates(self.attr,
                                'month',
                                order='ASC'
                               )
                    ]
                )
            ]

        return self._months

    def get_days_range(self, page, year, month):
        month_start, month_end = calendar.monthrange(year, month)

        return [
            Day(year, month, day, page)
            for day in sorted(
                [
                    d.day
                    for d in self.object_list.filter(
                        **{
                            '%s__range' % self.attr: (datetime.date(year,month,1), datetime.date(year, month, month_end) + datetime.timedelta(days=1))
                        }
                    ).dates(self.attr,
                            'day',
                            order='ASC'
                           )
                ]
            )
        ]

    def get_weeks_range(self, page, year):
        raise NotImplemented

class Page(object):
    def __init__(self, object_list, selector, paginator):
        self.objects = object_list
        self.selector = selector
        self.paginator = paginator
        self._count = None

    def __repr__(self):
        try:
            return '<Page %s>' % str(self.selector)
        except:
            return '<Unknown page>'

    def _years(self):
        return self.paginator.get_years_range(self)
    years = property(_years)

    def year(self):
        if hasattr(self.selector, "year"):
            return Year(self.selector.year, self)
        return None

    def _object_list(self):
        selector = self.selector

        bottom = selector.page * selector.objects_per_page
        top = (selector.page + 1) * selector.objects_per_page
        return self.objects[bottom:top]
    object_list = property(_object_list)

    def month(self):
        try:
            return Month(self.selector.year, self.selector.month, self)
        except:
            return None

    def day(self):
        try:
            return Day(self.selector.year, self.selector.month, self.selector.day, self)
        except:
            return None

    def _get_count(self):
        if not self._count:
            self._count = self.objects.count()
        return self._count
    count = property(_get_count)

    def has_more(self):
        return (self.selector.page + 1) * self.selector.objects_per_page < self.count

    def remaining_objects(self):
        return self.count - self.selector.page * self.selector.objects_per_page

    def get_selector(self):
        return "%d-%d" % (
            self.selector.objects_per_page,
            self.selector.page,
        )

    def get_absolute_url_for_all(self):
        return reverse(self.paginator.url_name, kwargs={ "selector": self.get_selector() })

    def get_absolute_url(self):
        if hasattr(self.selector, "day"):
            return self.day().get_absolute_url()
        if hasattr(self.selector, "month"):
            return self.month().get_absolute_url()
        if hasattr(self.selector, "year"):
            return self.year().get_absolute_url()
        return self.get_absolute_url_for_all()

    def next_page(self):
        new_selector = self.selector
        new_selector.page = new_selector.page + 1
        return Page(self.objects, new_selector, self.paginator)

