import datetime
from typing import List


class CityResult:

    _mode = {'/bestdeal': 'DISTANCE_FROM_LANDMARK', '/lowprice': 'PRICE', '/highprice': 'PRICE_HIGHEST_FIRST'}

    def __init__(self, town: str = None, id_location: str = None, num_result: str = '25',
                 mode: str = '/lowprice', currency: str = "USD") -> None:
        self._town = town
        self._id_location = id_location
        self._num_result = num_result
        self._mode_search = CityResult._mode[mode]
        self._hotels = []
        self._range_prices = []
        self._currency = currency
        self._date_arrived = None
        self._date_leave = None

    @property
    def id_location(self) -> str:
        return self._id_location

    @id_location.setter
    def id_location(self, id_town: str) -> None:
        self._id_location = id_town

    @property
    def name_town(self) -> str:
        return self._town

    @name_town.setter
    def name_town(self, target_town: str) -> None:
        self._town = target_town

    @property
    def mode_search(self) -> str:
        return self._mode_search

    @mode_search.setter
    def mode_search(self, mode_value: str) -> None:
        self._mode_search = CityResult._mode[mode_value]

    @property
    def num_result(self) -> str:
        return self._num_result

    @num_result.setter
    def num_result(self, value: str) -> None:
        self._num_result = value

    @property
    def all_hotels(self) -> List:
        return self._hotels

    @all_hotels.setter
    def all_hotels(self, hotel: 'Hotel') -> None:
        self._hotels.append(hotel)

    @property
    def range_prices(self) -> List:
        return self._range_prices

    @range_prices.setter
    def range_prices(self, value: List) -> None:
        self._range_prices.extend(value)

    @property
    def currency(self) -> str:
        return self._currency

    @currency.setter
    def currency(self, cur_value: str) -> None:
        self._currency = cur_value

    @property
    def date_arrived(self) -> datetime.datetime:
        return self._date_arrived

    @date_arrived.setter
    def date_arrived(self, value: datetime.datetime) -> None:
        self._date_arrived = value

    @property
    def date_leave(self) -> datetime.datetime:
        return self._date_leave

    @date_leave.setter
    def date_leave(self, value: datetime.datetime) -> None:
        self._date_leave = value

    def clear_hotel_list(self):
        self._town = None
        self._id_location = None
        self._num_result = '25'
        self._mode_search = CityResult._mode['/lowprice']
        self._hotels.clear()
        self._range_prices.clear()
        self._currency = 'USD'
        self._date_arrived = None
        self._date_leave = None


class Hotel:

    def __init__(self, title_hotel: str = None, address_hotel: str = None,
                 price_summary: str = None, distance_from_center: str = None, hotel_id: str = None) -> None:
        self._title_hotel = title_hotel
        self._hotel_id = hotel_id
        self._address_hotel = address_hotel
        self._price_summary = price_summary
        self._distance_from_center = distance_from_center
        self._url_photo = []

    @property
    def name(self) -> str:
        return self._title_hotel

    @name.setter
    def name(self, value: str) -> None:
        self._title_hotel = value

    @property
    def address(self) -> str:
        return self._address_hotel

    @address.setter
    def address(self, value: str) -> None:
        self._address_hotel = value

    @property
    def price(self) -> str:
        return self._price_summary

    @price.setter
    def price(self, value: str) -> None:
        self._price_summary = value

    @property
    def distance(self) -> str:
        return self._distance_from_center

    @distance.setter
    def distance(self, value: str) -> None:
        self._distance_from_center = value

    @property
    def hotel_id(self) -> str:
        return self._hotel_id

    @hotel_id.setter
    def hotel_id(self, value: str) -> None:
        self._hotel_id = value

    @property
    def url_photo(self) -> List:
        return self._url_photo

    @url_photo.setter
    def url_photo(self, value: str) -> None:
        self._url_photo.append(value)

    def __str__(self) -> str:
        return f'{self._title_hotel} находится по адресу: {self._address_hotel}, на расстоянии ' \
               f'от центра {self._distance_from_center}. Общая стоимость: {self._price_summary}'


city = CityResult()
