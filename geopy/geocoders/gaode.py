"""
:class:`.GaoDe` is the GaoDe Maps geocoder.
"""

from geopy.compat import urlencode
from geopy.geocoders.base import Geocoder, DEFAULT_TIMEOUT
from geopy.exc import (
    GeocoderQueryError,
    GeocoderQuotaExceeded,
    GeocoderAuthenticationFailure,
)
from geopy.location import Location
from geopy.util import logger


__all__ = ("GaoDe", )


class GaoDe(Geocoder):
    """
    Geocoder using the GaoDe Maps v3 API. Documentation at:
        http://lbs.amap.com/api/webservice/guide/api/georegeo
    """
    def __init__(
            self,
            api_key,
            scheme='http',
            timeout=DEFAULT_TIMEOUT,
            proxies=None,
            user_agent=None
        ):
        super(GaoDe, self).__init__(
            scheme=scheme, timeout=timeout, proxies=proxies, user_agent=user_agent
        )
        self.api_key = api_key
        self.scheme = scheme
        self.doc = {}
        self.api = 'http://restapi.amap.com/v3/geocode/'
        self.search_api = 'http://restapi.amap.com/v3/place/text'

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
            city=None,
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
        if city:
            params.update({'city': city})
        if not exactly_one:
            params.update({'batch': 'true'})

        url = "?".join((self.api + 'geo', urlencode(params)))
        logger.debug("%s.geocode: %s", self.__class__.__name__, url)
        return self._parse_json(
            self._call_geocoder(url, timeout=timeout), exactly_one=exactly_one
        )

    def search(self, query, city=None, timeout=None, exactly_one=True):
        params = {
            'key': self.api_key,
            'keywords': query,
            'output': 'json',
        }
        if city:
            params.update({'city': city})
        url = '?'.join((self.search_api, urlencode(params)))
        logger.debug("%s.search: %s", self.__class__.__name__, url)
        return self._parse_search_json(
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

        url = "?".join((self.api + 'regeo', urlencode(params)))

        logger.debug("%s.reverse: %s", self.__class__.__name__, url)
        return self._parse_reverse_json(
            self._call_geocoder(url, timeout=timeout),
            params['location'].split(',')
        )


    @staticmethod
    def _parse_reverse_json(page, point):
        """
        Parses a location from a single-result reverse API call.
        """
        place = page.get('regeocode')

        location = place.get('formatted_address').encode('utf-8')
        latitude = point[1]
        longitude = point[0]

        return Location(location, (latitude, longitude), place)

    def _parse_search_json(self, page, exactly_one=True):
        place = page.get('pois')

        if not place:
            self._check_status(page.get('infocode'))
            return None

        def parse_place(place):
            location = place.get('address')
            coordinate = place.get('location').split(',')
            longitude = coordinate[0]
            latitude = coordinate[1]
            return Location(location, (latitude, longitude), place)

        if exactly_one:
            return parse_place(place[0])
        else:
            return [parse_place(item) for item in place]


    def _parse_json(self, page, exactly_one=True):
        """
        Returns location, (latitude, longitude) from JSON feed.
        """

        place = page.get('geocodes', None)

        if not place:
            self._check_status(page.get('infocode'))
            return None

        def parse_place(place):
            """
            Get the location, lat, lng from a single JSON place.
            """
            location = place.get('formatted_address')
            coordinate = place.get('location').split(',')
            longitude = coordinate[0]
            latitude = coordinate[1]
            return Location(location, (latitude, longitude), place)

        if exactly_one:
            return parse_place(place[0])
        else:
            return [parse_place(item) for item in place]

    @staticmethod
    def _check_status(status):
        """
        Validates error statuses.
        """
        if status == '10000':
            # When there are no results, just return.
            return
        if status == '10001':
            raise GeocoderAuthenticationFailure(
                'Invalid user key.'
            )
        elif status == '10002':
            raise GeocoderAuthenticationFailure(
                'Service not available.'
            )
        elif status == '10003':
            raise GeocoderQuotaExceeded(
                'Daily query over limit.'
            )
        elif status == '10004':
            raise GeocoderQuotaExceeded(
                'Access too frequent.'
            )
        elif status == '10005':
            raise GeocoderQueryError(
                'Invalid user IP.'
            )
        elif status == '10006':
            raise GeocoderQueryError(
                'Invalid user domain.'
            )
        elif status == '10007':
            raise GeocoderQueryError(
                'Invalid user signature'
            )
        elif status == '10008':
            raise GeocoderQueryError(
                'Invalid user scode.'
            )
        elif status == '10009':
            raise GeocoderQuotaExceeded(
                'Userkey plat nomatch.'
            )
        elif status == '10010':
            raise GeocoderQuotaExceeded(
                'IP query over limit.'
            )
        elif status == '10011':
            raise GeocoderQuotaExceeded(
                'Not support https.'
            )
        elif status == '10012':
            raise GeocoderQuotaExceeded(
                'Insufficient privileges.'
            )
        elif status == '10013':
            raise GeocoderQuotaExceeded(
                'User key recycled.'
            )
        elif status == '10014':
            raise GeocoderQuotaExceeded(
                'QPS has exceeded the limit.'
            )
        elif status == '10015':
            raise GeocoderQuotaExceeded(
                'Gateway timeout.'
            )
        elif status == '10016':
            raise GeocoderQuotaExceeded(
                'Server is busy.'
            )
        elif status == '10017':
            raise GeocoderQuotaExceeded(
                'Resource unavailable.'
            )
        elif status == '20000':
            raise GeocoderQuotaExceeded(
                'Invalid params.'
            )
        elif status == '20001':
            raise GeocoderQuotaExceeded(
                'Missing required params.'
            )
        elif status == '20002':
            raise GeocoderQuotaExceeded(
                'Illegal request.'
            )
        elif status == '20003':
            raise GeocoderQuotaExceeded(
                'Unknown error.'
            )
        elif status == '20800':
            raise GeocoderQuotaExceeded(
                'Out of service.'
            )
        elif status == '20801':
            raise GeocoderQuotaExceeded(
                'No roads nearby.'
            )
        elif status == '20802':
            raise GeocoderQuotaExceeded(
                'Route fail.'
            )
        elif status == '20803':
            raise GeocoderQuotaExceeded(
                'Over direction range.'
            )
        elif status == '300**':
            raise GeocoderQuotaExceeded(
                'Engine response data error.'
            )
        else:
            raise GeocoderQueryError('Unknown error')
