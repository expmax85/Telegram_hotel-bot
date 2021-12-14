import requests
import speech_recognition as sr
import datetime
import telebot
import os
import re
import subprocess
import logging

from telebot_calendar import Calendar, CallbackData, RUSSIAN_LANGUAGE
from searchrequests import Search, new_logger
from searchresults import city
from dotenv import load_dotenv


load_dotenv('.env')
token = os.getenv("my_token")
bot = telebot.TeleBot(token)
currency = {'USD': 'долларах', 'RUB': 'рублях', 'EUR': 'евро'}
history_dict = dict()
logger = new_logger('main_logger', logging.INFO)
calendar = Calendar(language=RUSSIAN_LANGUAGE)
calendar_1_callback = CallbackData("calendar_1", "action", "year", "month", "day")
calendar_2_callback = CallbackData("calendar_2", "action", "year", "month", "day")


def markup_yes_no() -> 'telebot.types.InlineKeyboardMarkup':
    mrk = telebot.types.InlineKeyboardMarkup(row_width=2)
    button1 = telebot.types.InlineKeyboardButton("да", callback_data='1yes1')
    button2 = telebot.types.InlineKeyboardButton("нет", callback_data='2no2')
    mrk.add(button1, button2)
    return mrk


@bot.message_handler(commands=['start'])
def send_welcome(message: 'telebot.types.Message') -> None:
    print(type(message))
    bot.send_message(message.from_user.id, 'Здравствуйте! Я - бот компании TooEasyTravel. '
                                           'Моя функция - помочь Вам найти подходящий отель. '
                                           'Чтобы просмотреть доступные функции, введите /help.')


@bot.message_handler(commands=['help'])
def send_help(message) -> None:
    bot.send_message(message.from_user.id, 'Вот список доступных команд:\n'
                                           '/lowprice - поиск отелей по низким ценам;\n'
                                           '/highprice - поиск отелей по высоким ценам;\n'
                                           '/bestdeal - поиск отелей, подходящих по цене и расположению от центра;\n'
                                           '/history - вывести историю поиска')


@bot.message_handler(commands=['history'])
def send_history(message) -> None:
    path = os.path.abspath(os.path.join('history', 'User' + str(message.from_user.id) + '.txt'))
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as history:
            count = sum(1 for _ in history)
            history.seek(0)
            for i in range(count):
                text = history.readline()
                if text.strip():
                    if re.match(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}', text):
                        key = str(re.findall(r'\d{2}-\d{2} \d{2}:\d{2}.+', text)[0])
                        history_dict[key] = []
                    else:
                        history_dict[key].append(text)
        keyboard = telebot.types.InlineKeyboardMarkup(row_width=1)
        button_list = list()
        for key in history_dict.keys():
            if history_dict[key]:
                button_list.append(telebot.types.InlineKeyboardButton(text=key, callback_data=key))
        keyboard.add(*button_list)
        bot.send_message(message.from_user.id, "Выберите из списка нужный вам запрос:",
                         reply_markup=keyboard)
    else:
        bot.send_message(message.from_user.id, 'Вы пока еще ничего не искали. '
                                               'Введите команду, или /help для вывода доступных команд')


@bot.message_handler(content_types=['text', 'voice'])
def get_text_messages(message) -> None:
    if message.voice:
        message.text = get_audio_messages(message)
    logger.info(f'User {message.from_user.id} write the message {message.text}')
    if message.text == "Привет":
        bot.send_message(message.from_user.id, "Здравствуй, путешественник! Для просмотра функций введите /help.")
    elif message.text in ('/lowprice', '/highprice', '/bestdeal'):
        city.clear_hotel_list()
        city.mode_search = message.text
        now = datetime.datetime.now()
        Search.history(f'User' + str(message.from_user.id) + '.txt',
                       f'\n{str(now.strftime("%Y-%m-%d %H:%M"))} - {message.text}. ')
        bot.send_message(message.chat.id, 'В каком городе искать?')
        bot.register_next_step_handler(message, choice_town)
    else:
        bot.send_message(message.from_user.id, "Я Вас не понимаю. Повторите или напишите "
                                               "/help для просмотра доступных команд.")


@bot.callback_query_handler(func=lambda call: call.data in history_dict.keys())
def history_show(call) -> None:
    bot.send_message(call.message.chat.id, call.data)
    bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  reply_markup=None)
    if len(history_dict[call.data]) > 0:
        for line in history_dict[call.data]:
            bot.send_message(call.message.chat.id, line)
    bot.send_message(call.message.chat.id, 'Чем я еще могу помочь? (/help для вывода доступных команд)')


def get_audio_messages(message) -> str:
    file_info = bot.get_file(message.voice.file_id)
    file = requests.get(f'https://api.telegram.org/file/bot{token}/{file_info.file_path}')
    src, dst = 'file.oga', 'file.wav'
    with open(src, 'wb') as f:
        f.write(file.content)
    subprocess.run(['ffmpeg', '-loglevel', 'quiet', '-i', src, '-y', '-fs', '700k', dst])
    rec = sr.Recognizer()
    with sr.AudioFile(dst) as source:
        audio = rec.record(source)
    os.remove(dst)
    os.remove(src)
    try:
        msg = rec.recognize_google(audio, language='ru_RU')
        message.text = msg.capitalize()
        logger.info(f"Google Speech Recognition thinks User{message.from_user.id} said: {msg}")
    except sr.UnknownValueError:
        logger.error("error403 - Google Speech Recognition could not understand audio")
        message.text = 'error403'
    except sr.RequestError as e:
        logger.warning(f"error404 - Could not request results from Google Speech Recognition service; {e}")
        message.text = 'error404'
    return message.text


def choice_town(message) -> None:
    if message.voice:
        message.text = get_audio_messages(message)
    try:
        bot.send_message(message.from_user.id, 'Обрабатываю запрос, пожалуйста, подождите...')
        list_town = Search.search_town(message.text)
        if not list_town:
            bot.send_message(message.from_user.id, "Город не найден. Проверьте название или введите другой город:")
            bot.register_next_step_handler(message, choice_town)
        else:
            keyboard = telebot.types.InlineKeyboardMarkup(row_width=1)
            button_list = list()
            for item in list_town:
                button_list.append(telebot.types.InlineKeyboardButton(text=', '.join([item[0][0], item[0][1]]),
                                                            callback_data='<delimiter>'.join([item[0][0], item[1]])))
            keyboard.add(*button_list)
            bot.send_message(message.from_user.id, "Выберите из списка нужный Вам город:",
                             reply_markup=keyboard)
    except Exception as err_town:
        logger.error(err_town)
        bot.send_message(message.from_user.id, 'Произошла непредвиденная ошибка. Возможно, сервис сейчас недоступен. '
                                               'Пожалуйста, повторите запрос немного позже.')
        city.clear_hotel_list()


@bot.callback_query_handler(func=lambda call: call.data.count('<delimiter>') > 0)
def choose_dates(call) -> None:
    city.name_town, city.id_location = call.data.split('<delimiter>')[0], call.data.split('<delimiter>')[1]
    bot.send_message(call.message.chat.id, city.name_town)
    Search.history(f'User' + str(call.message.chat.id) + '.txt', f'{city.name_town}')
    bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  reply_markup=None)
    now = datetime.datetime.now()
    bot.send_message(call.message.chat.id, f"Выберите дату ЗАЕЗДА:",
                     reply_markup=calendar.create_calendar(name=calendar_1_callback.prefix,
                                                           year=now.year, month=now.month))


@bot.callback_query_handler(func=lambda call: call.data.startswith(calendar_1_callback.prefix))
def date_arrived(call: telebot.types.CallbackQuery) -> None:
    name, action, year, month, day = call.data.split(calendar_1_callback.sep)
    date = calendar.calendar_query_handler(bot=bot, call=call, name=name, action=action,
                                           year=year, month=month, day=day)
    if action == "DAY":
        city.date_arrived = date.strftime('%Y-%m-%d')
        now = datetime.datetime.now()
        if city.date_arrived < now.strftime('%Y-%m-%d'):
            bot.send_message(call.message.chat.id, "Ошибка при выборе даты заезда. Следует указывать дату, "
                                                   "не раньше сегодняшней.",
                             reply_markup=calendar.create_calendar(name=calendar_1_callback.prefix,
                                                                   year=now.year, month=now.month))
        else:
            bot.send_message(call.message.chat.id, f'Дата заезда: {city.date_arrived}. Выберите дату ВЫЕЗДА:',
                             reply_markup=calendar.create_calendar(name=calendar_2_callback.prefix,
                                                                   year=now.year, month=now.month))
    elif action == "CANCEL":
        bot.send_message(call.message.chat.id, 'Запрос был отменен. Введите /help для вывода доступных команд')
        city.clear_hotel_list()


@bot.callback_query_handler(func=lambda call: call.data.startswith(calendar_2_callback.prefix))
def date_leave(call: telebot.types.CallbackQuery) -> None:
    name, action, year, month, day = call.data.split(calendar_2_callback.sep)
    date = calendar.calendar_query_handler(bot=bot, call=call, name=name, action=action,
                                           year=year, month=month, day=day)
    if action == "DAY":
        now = datetime.datetime.now()
        city.date_leave = date.strftime('%Y-%m-%d')
        if city.date_leave <= city.date_arrived:
            bot.send_message(call.message.chat.id, f"Ошибка при выборе дат. Дата выезда должна быть позже даты заезда. "
                                                   f"({city.date_arrived})",
                             reply_markup=calendar.create_calendar(name=calendar_2_callback.prefix,
                                                                   year=now.year, month=now.month))
        else:
            bot.send_message(call.message.chat.id,
                             f'Дата заезда: {city.date_arrived}, дата выезда: {city.date_leave}.'
                             f'\nСколько отелей показать? (не более 25)')
            bot.register_next_step_handler(call.message, choice_currency)
    elif action == "CANCEL":
        bot.send_message(call.message.chat.id, 'Запрос был отменен. Введите /help для вывода доступных команд.')
        city.clear_hotel_list()


def choice_currency(message) -> None:
    if message.voice:
        message.text = get_audio_messages(message)
    try:
        if int(message.text):
            city.num_result = message.text
            keyboard = telebot.types.ReplyKeyboardMarkup(row_width=1)
            button_list = list()
            for item in currency.keys():
                button_list.append(telebot.types.KeyboardButton(text=item))
            keyboard.add(*button_list)
            bot.send_message(message.from_user.id, "Выберите валюту:",
                             reply_markup=keyboard)
            if city.mode_search == 'DISTANCE_FROM_LANDMARK':
                bot.register_next_step_handler(message, input_prices)
            else:
                bot.register_next_step_handler(message, show_results)
    except ValueError as error:
        logger.error(f'From User {message.from_user.id}: {message.text} - {error}')
        bot.send_message(message.from_user.id, "Я вас не понимаю. Введите пожалуйста число:")
        bot.register_next_step_handler(message, choice_currency)


def input_prices(message) -> None:
    if message.voice:
        message.text = get_audio_messages(message)
    try:
        if message.text not in currency.keys():
            logger.error(f'From User {message.from_user.id}: {message.text} - {ValueError}')
            bot.send_message(message.from_user.id, "Неверная валюта. Вам необходимо выбрать валюту из списка ниже!")
            bot.register_next_step_handler(message, input_prices)
        else:
            city.currency = message.text
            bot.send_message(message.from_user.id, f'Введите диапазон цен через пробел в {currency[city.currency]}:',
                             reply_markup=telebot.types.ReplyKeyboardRemove())
            bot.register_next_step_handler(message, input_distance)
    except Exception as error:
        logger.critical(f'From User {message.from_user.id}: {message.text} - {error}')
        bot.send_message(message.from_user.id, "Непредвиденная ошибка. Повторите запрос сначала.")
        city.clear_hotel_list()


def input_distance(message) -> None:
    if message.voice:
        message.text = get_audio_messages(message)
    try:
        prices_limit = Search.set_limits(message.text)
        if prices_limit:
            city.range_prices = prices_limit
            bot.send_message(message.from_user.id, 'Введите диапазон расстояния до центра в километрах:')
            bot.register_next_step_handler(message, show_results)
        else:
            bot.send_message(message.from_user.id, f'Я вас не понимаю. '
                                                   f'Необходимо ввести две суммы в {currency[city.currency]}:')
            logger.error(f'From User {message.from_user.id}: {message.text} - {ValueError}')
            bot.register_next_step_handler(message, input_distance)
    except Exception as error:
        logger.critical(f'From User {message.from_user.id}: {message.text} - {error}')
        bot.send_message(message.from_user.id, "Непредвиденная ошибка. Повторите запрос сначала.")


def show_results(message) -> None:
    if message.voice:
        message.text = get_audio_messages(message)
    if city.mode_search == 'DISTANCE_FROM_LANDMARK':
        distance_limit = Search.set_limits(message.text.replace(',', '.'))
        if distance_limit:
            bot.send_message(message.from_user.id, 'Обрабатываю запрос, пожалуйста, подождите...')
            Search.best_deal(city, distance_limit)
        else:
            logger.error(f'From User {message.from_user.id}: {message.text} - {ValueError}')
            bot.send_message(message.from_user.id, f'Я вас не понимаю. '
                                                   f'Необходимо ввести два числа в километрах!')
            bot.register_next_step_handler(message, show_results)
    else:
        if message.text not in currency.keys():
            distance_limit = False
            bot.send_message(message.from_user.id, "Неверная валюта. Вам необходимо выбрать валюту из списка ниже!")
            bot.register_next_step_handler(message, show_results)
        else:
            distance_limit = True
            keyboard = telebot.types.ReplyKeyboardRemove()
            city.currency = message.text
            bot.send_message(message.from_user.id, 'Обрабатываю запрос, пожалуйста, подождите...',
                             reply_markup=keyboard)
            Search.search_hotels(city)
    if distance_limit:
        if len(city.all_hotels) == 0:
            logger.info('Nothing found for request')
            bot.send_message(message.from_user.id, 'Извините, по запрашиваемым параметрам ничего не найдено.'
                                                   'Попробуйте повторить запрос и изменить параметры поиска.')
            Search.history(f'User' + str(message.from_user.id) + '.txt', '\nНичего не найдено.')
        else:
            n = 1
            logger.info('Request was already successful')
            for hotel in city.all_hotels:
                bot.send_message(message.from_user.id, ''.join([str(n), '. ', str(hotel)]))
                Search.history(f'User' + str(message.from_user.id) + '.txt', ''.join(['\n', str(n), '. ', str(hotel)]))
                n += 1
            else:
                bot.send_message(message.from_user.id, 'Хотите посмотреть фотографии отелей?',
                                 reply_markup=markup_yes_no())


@bot.callback_query_handler(func=lambda call: call.data in ('1yes1', '2no2'))
def photo_hotels(call) -> None:
    if call.data == '1yes1':
        bot.send_message(call.message.chat.id, 'Сколько фотографий показать? (не больше 7')
        bot.register_next_step_handler(call.message, number_of_photos)
    elif call.data == '2no2':
        bot.send_message(call.message.chat.id, 'Чем я еще могу Вам помочь? (/help для вывода доступных команд.)')
        city.clear_hotel_list()
    bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  reply_markup=None)


def number_of_photos(message) -> None:
    if message.voice:
        message.text = get_audio_messages(message)
    if message.text.isdigit():
        if int(message.text) not in range(1, 8):
            bot.send_message(message.from_user.id,
                             'Я могу показать Вам не более 7 фотографий. Введите число от 1 до 7.')
            bot.register_next_step_handler(message, number_of_photos)
        else:
            city.num_result = int(message.text)
            keyboard = telebot.types.InlineKeyboardMarkup(row_width=1)
            button_list = list()
            for item in city.all_hotels:
                button_list.append(telebot.types.InlineKeyboardButton(text=str(item.name),
                                                    callback_data='<ph0t0>'.join(str([city.all_hotels.index(item)]))))
            keyboard.add(*button_list)
            bot.send_message(message.from_user.id, "Фотографии какого отеля показать?:",
                             reply_markup=keyboard)
    else:
        bot.send_message(message.from_user.id, 'Я вас не понимаю. Необходимо ввести число от 1 до 7!')
        bot.register_next_step_handler(message, number_of_photos)


@bot.callback_query_handler(func=lambda call: call.data.count('<ph0t0>') > 0)
def show_photo(call) -> None:
    index = int(call.data.split('<ph0t0>')[1])
    bot.send_message(call.message.chat.id, city.all_hotels[index].name)
    bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  reply_markup=None)
    try:
        bot.send_message(call.message.chat.id, 'Загружаю фотографии, пожалуйста, подождите...')
        Search.show_photos(city.all_hotels[index], city.num_result)
        for item in city.all_hotels[index].url_photo:
            file = requests.get(item)
            img = 'img.jpg'
            with open(img, 'wb') as f:
                f.write(file.content)
            with open('img.jpg', 'rb') as img:
                bot.send_photo(call.message.chat.id, img, f'{city.all_hotels[index].name}')
            os.remove('img.jpg')
        else:
            bot.send_message(call.message.chat.id, 'Хотите посмотреть фотографии по другому отелю?',
                             reply_markup=markup_yes_no())
    except Exception as photo_err:
        logger.error(photo_err)
        bot.send_message(call.message.chat.id, "Фотографий по данному отелю не найдено. "
                                               "Хотите посмотреть фотографии по другому отелю?",
                                               reply_markup=markup_yes_no())


if __name__ == "__main__":
    while True:
        try:
            bot.polling(none_stop=True, interval=0)
        except Exception as err:
            logger.fatal(err)
            city.clear_hotel_list()
