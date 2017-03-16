#!/usr/bin/env python
# -*- coding: utf-8 -*-

from geopy.compat import urlencode
from geopy.geocoders.base import Geocoder, DEFAULT_TIMEOUT
from geopy.exc import (
    GeocoderQueryError,
    GeocoderQuotaExceeded,
    GeocoderAuthenticationFailure,
)
from geopy.location import Location
from geopy.util import logger


__all__ = ("Tencent", )

class Tencent(Geocoder):
    """
    Geocoder using the Tencent Maps v1 API. Documentation at:
        http://lbs.qq.com/webservice_v1/guide-geocoder.html
    """

    def __init__(
            self,
            api_key,
            scheme='http',
            timeout=DEFAULT_TIMEOUT,
            proxies=None,
            user_agent=None
        ):
        """
        Initialize a customized Tencent geocoder using the v1 API.

        .. versionadded:: 1.0.0

        :param string api_key: The API key required by Tencent Map to perform
            geocoding requests. API keys are managed through the Tencent APIs
            console (http://lbs.qq.com/mykey.html).

        :param string scheme: Use 'https' or 'http' as the API URL's scheme.
            Default is http and only http support.

        :param dict proxies: If specified, routes this geocoder's requests
            through the specified proxy. E.g., {"https": "192.0.2.0"}. For
            more information, see documentation on
            :class:`urllib2.ProxyHandler`.
        """
        super(Tencent, self).__init__(
            scheme=scheme, timeout=timeout, proxies=proxies, user_agent=user_agent
        )
        self.api_key = api_key
        self.scheme = scheme
        self.doc = {}
        self.api = 'http://apis.map.qq.com/ws/geocoder/v1/'


    @staticmethod
    def _format_components_param(components):
        """
        Format the components dict to something Baidu understands.
        """
        return "|".join(
            (":".join(item)
             for item in components.items()
            )
        )

    def geocode(
            self,
            query,
            exactly_one=True,
            timeout=None,
        ):
        """
        Geocode a location query.

        :param string query: The address or query you wish to geocode.

        :param bool exactly_one: Return one result or a list of results, if
            available.

        :param int timeout: Time, in seconds, to wait for the geocoding service
            to respond before raising a :class:`geopy.exc.GeocoderTimedOut`
            exception. Set this only if you wish to override, on this call
            only, the value set during the geocoder's initialization.

        """
        params = {
            'key': self.api_key,
            'output': 'json',
            'address': self.format_string % query,
        }

        url = "?".join((self.api, urlencode(params)))
        logger.debug("%s.geocode: %s", self.__class__.__name__, url)
        return self._parse_json(
            self._call_geocoder(url, timeout=timeout), exactly_one=exactly_one
        )

    def reverse(self, query, timeout=None):  # pylint: disable=W0221
        """
        Given a point, find an address.

        :param query: The coordinates for which you wish to obtain the
            closest human-readable addresses.
        :type query: :class:`geopy.point.Point`, list or tuple of (latitude,
            longitude), or string as "%(latitude)s, %(longitude)s"

        :param int timeout: Time, in seconds, to wait for the geocoding service
            to respond before raising a :class:`geopy.exc.GeocoderTimedOut`
            exception. Set this only if you wish to override, on this call
            only, the value set during the geocoder's initialization.

        """
        params = {
            'key': self.api_key,
            'output': 'json',
            'location': self._coerce_point_to_string(query),
        }

        url = "?".join((self.api, urlencode(params)))

        logger.debug("%s.reverse: %s", self.__class__.__name__, url)
        return self._parse_reverse_json(
            self._call_geocoder(url, timeout=timeout)
        )


    @staticmethod
    def _parse_reverse_json(page):
        """
        Parses a location from a single-result reverse API call.
        """
        place = page.get('result')

        location = place['formatted_address']['recommend'].encode('utf-8')
        latitude = place['location']['lat']
        longitude = place['location']['lng']

        return Location(location, (latitude, longitude), place)


    def _parse_json(self, page, exactly_one=True):
        """
        Returns location, (latitude, longitude) from JSON feed.
        """

        place = page.get('result', None)

        if not place:
            self._check_status(page.get('status'))
            return None

        def parse_place(place):
            """
            Get the location, lat, lng from a single JSON place.
            """
            location = place.get('title')
            latitude = place['location']['lat']
            longitude = place['location']['lng']
            return Location(location, (latitude, longitude), place)

        if exactly_one:
            return parse_place(place)
        else:
            return [parse_place(item) for item in place]

    @staticmethod
    def _check_status(status):
        """
        Validates error statuses.
        """
        if status == 0:
            # When there are no results, just return.
            return
        if status == 110:
            raise GeocoderQueryError(
                u'请求来源未被授权.'
            )
        elif status == 306:
            raise GeocoderQueryError(
                u'请求有护持信息请检查字符串.'
            )
        elif status == 310:
            raise GeocoderAuthenticationFailure(
                u'请求参数信息有误.'
            )
        elif status == 311:
            raise GeocoderQuotaExceeded(
                u'key格式错误.'
            )
        else:
            raise GeocoderQueryError('Unknown error')


