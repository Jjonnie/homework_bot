import sys
import os
import logging
import time
import requests
import telegram
from dotenv import load_dotenv
from http import HTTPStatus
from exceptions import (
    NotWrongHttpStatus, NotSendMessage, UnknownStatusHomework
)

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    '%(asctime)s - %(funcName)s - [%(levelname)s] - %(message)s'
)
handler = logging.StreamHandler()
handler.setFormatter(formatter)
logger.addHandler(handler)


def check_tokens():
    """Проверка наличия токенов(PRACTICUM and TELEGRAM) и chat_id."""
    if PRACTICUM_TOKEN is None:
        logging.critical('PRACTICUM_TOKEN не обнаружен!')
        return False
    if TELEGRAM_TOKEN is None:
        logging.critical('TELEGRAM_TOKEN не обнаружен!')
        return False
    if TELEGRAM_CHAT_ID is None:
        logging.critical('TELEGRAM_CHAT_ID не обнаружен!')
        return False
    return True


def send_message(bot: telegram.Bot, message: str) -> None:
    """Отправка сообщения в телеграм."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logger.debug(f'Сообщение {message} отправлено.')
    except telegram.error.TelegramError as error:
        error_message = f'Ошибка при отправке сообщения: {error}'
        logger.error(f'Сообщение {message} не отправлено!')
        raise NotSendMessage(error_message)


def get_api_answer(current_timestamp: int) -> dict:
    """Запрос к эндпоинту API Yandex-Practicum."""
    params = {'from_date': current_timestamp}
    try:
        status_homework = requests.get(
            url=ENDPOINT,
            headers=HEADERS,
            params=params,
        )
    except requests.exceptions.RequestException as error:
        error_message = f'Ошибка при запросе к API Yandex-Practicum: {error}'
        raise NotWrongHttpStatus(error_message)
    status_code = status_homework.status_code
    if status_code != HTTPStatus.OK:
        raise NotWrongHttpStatus(
            f'{ENDPOINT} - недоступен. Код ответа API: {status_code}'
        )
    return status_homework.json()


def check_response(response: dict) -> dict:
    """
    Проверка корректности ответа API.
    Функция возвращает список домашних работ.
    """
    if not isinstance(response, dict):
        raise TypeError('Ответ от сервера API не является словарем.')
    if 'homeworks' not in response:
        raise KeyError('В ответе API отсутствует ключ <homework_name>.')
    homeworks = response['homeworks']
    if not isinstance(homeworks, list):
        raise TypeError('Ответ API не является списком')
    return homeworks


def parse_status(homeworks: dict) -> str:
    """Функция извлекает статус домашней работы."""
    homework_name = homeworks.get('homework_name')
    status_homework = homeworks.get('status')
    if not homework_name:
        raise KeyError(
            'Отсутствуют ключ <homework_name>.'
        )
    if not status_homework:
        raise KeyError(
            'Отсутствуют ключ <homework_status>.'
        )
    if status_homework not in HOMEWORK_VERDICTS:
        raise UnknownStatusHomework('Неизвестный статус домашки.')
    verdict = HOMEWORK_VERDICTS.get(status_homework)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    logger.info('Бот успешно запущен!')
    bot = telegram.Bot(token=TELEGRAM_TOKEN)

    if not check_tokens():
        logger.critical('Отсутствуют токены!')
        sys.exit(0)

    current_timestamp = int(time.time())

    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            logging.info(f'Получили список работ {homeworks}')
            if len(homeworks) > 0:
                send_message(bot, parse_status(homeworks[0]))
            logging.info('Заданий нет')
            current_timestamp = response['current_date']
            time.sleep(RETRY_PERIOD)

        except Exception as error:
            logging.error(f'Сбой в работе программы: {error}')
            send_message(bot, f'Сбой в работе программы: {error}')
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
