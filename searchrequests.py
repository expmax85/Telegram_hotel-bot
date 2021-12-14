import logging
import os
import re
import requests
from langdetect import detect
from typing import Union, List
from searchresults import Hotel, CityResult
from dotenv import load_dotenv
from os import getenv


def new_logger(name: str, level=logging.ERROR, file: str = 'logs.log') -> logging:
    log = logging.getLogger(name)
    if log.hasHandlers():
        log.handlers = []
    log.setLevel(level)
    handler = logging.FileHandler(file, encoding='utf8')
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    log.addHandler(handler)
    return log


load_dotenv('.env')
api = getenv("hotelAPIkey")
logger = new_logger('search_logger')
headers = {
    'x-rapidapi-key': api,
    'x-rapidapi-host': "hotels4.p.rapidapi.com"}


class Search:

    @classmethod
    def search_town(cls, town: str) -> Union[List, str]:
        cls.url = "https://hotels4.p.rapidapi.com/locations/search"
        cls.querystring = {"query": town,
                           "locale": '_'.join([detect(town).lower(), detect(town).upper()])
                           }
        try:
            cls.response = requests.request("GET", cls.url, headers=headers, params=cls.querystring)
            results = cls.response.json()['suggestions'][0]['entities']
            town_list = []
            for item in results:
                if item['type'] == 'CITY' and item['name'].lower() == town.lower():
                    result = re.findall(r'<span.+>(.+)<.span>, (.+)"', str(item))
                    result.append(item['destinationId'])
                    town_list.append(result)
            return town_list
        except BaseException as err:
            logger.critical(f'Searchrequests.search_town: - {err}')
            return 'error'

    @classmethod
    def search_hotels(cls, temp: 'CityResult') -> Union['CityResult', str]:
        cls.url = "https://hotels4.p.rapidapi.com/properties/list"
        cls.querystring = {"adults1": "1", "pageNumber": "1", "destinationId": temp.id_location,
                           "pageSize": temp.num_result, "checkOut": temp.date_leave,
                           "checkIn": temp.date_arrived, "sortOrder": temp.mode_search,
                           "locale": "ru_RU", "currency": temp.currency}
        try:
            cls.response = requests.request("GET", cls.url, headers=headers, params=cls.querystring)
            results = cls.response.json()["data"]["body"]["searchResults"]["results"]
            for item in results:
                if item['address'].get('streetAddress') is None:
                    address = 'Не указан'
                else:
                    address = item['address']['streetAddress'] + item['address']['extendedAddress']
                temp.all_hotels = Hotel(item['name'], address,
                                        item["ratePlan"]["price"]["current"],
                                        item['landmarks'][0]['distance'],
                                        item['id'])
        except BaseException as err:
            logger.critical(f'Searchrequests.search_hotels: - {err}')
        return temp

    @classmethod
    def best_deal(cls, temp: 'CityResult', distance_range: List) -> Union['CityResult', str]:
        cls.url = "https://hotels4.p.rapidapi.com/properties/list"
        cls.querystring = {"adults1": "1", "pageNumber": "1", "destinationId": temp.id_location,
                           "pageSize": temp.num_result, "checkOut": temp.date_leave,
                           "checkIn": temp.date_arrived, "sortOrder": "PRICE",
                           "locale": "ru_RU", "currency": temp.currency, "priceMin": temp.range_prices[0],
                           "priceMax": temp.range_prices[1]}
        try:
            cls.response = requests.request("GET", cls.url, headers=headers, params=cls.querystring)
            results = cls.response.json()["data"]["body"]["searchResults"]["results"]
            for item in results:
                if int(float(item['landmarks'][0]['distance'][:-3].replace(',', '.')) * 10) in range(
                        int(float(distance_range[0]) * 10), int(float(distance_range[1]) * 10)):
                    if item['address'].get('streetAddress') is None:
                        address = 'Не указан'
                    else:
                        address = item['address']['streetAddress'] + item['address']['extendedAddress']
                    temp.all_hotels = Hotel(item['name'], address,
                                            item["ratePlan"]["price"]["current"],
                                            item['landmarks'][0]['distance'],
                                            item['id'])
        except BaseException as err:
            logger.critical(f'Searchrequests.best_deal: - {err}')
        return temp

    @classmethod
    def show_photos(cls, hotel: 'Hotel', number: int) -> 'Hotel':
        cls.url = "https://hotels4.p.rapidapi.com/properties/get-hotel-photos"
        cls.querystring = {"id": hotel.hotel_id}
        try:
            cls.response = requests.request("GET", cls.url, headers=headers, params=cls.querystring)
            results = cls.response.json()["hotelImages"]
            for i in range(number):
                hotel.url_photo.append(results[i]['baseUrl'].replace('{size}', results[i]['sizes'][0]['suffix']))
        except BaseException as err:
            logger.critical(f'Searchrequests.show_photo: - {err}')
        return hotel

    @classmethod
    def set_limits(cls, string: str) -> List:
        temp = []
        string = tuple(string.split())
        for item in string:
            if item.isdigit():
                temp.append(item)
        if len(temp) != 2:
            temp = []
        else:
            if int(temp[0]) > int(temp[1]):
                temp[0], temp[1] = temp[1], temp[0]
        return temp

    @classmethod
    def history(cls, filename: str, text: str) -> None:
        if not os.path.exists('history'):
            os.mkdir("history")
        path = os.path.abspath(os.path.join('history', filename))
        mode = 'a' if os.path.exists(path) else 'w'
        with open(path, mode, encoding='utf-8') as history:
            history.write(text)
