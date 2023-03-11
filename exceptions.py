class NotSendMessage(Exception):
    "Исключение - сообщение не отправлено."
    pass


class NotWrongHttpStatus(Exception):
    "Исключение - эндпоинт с API недоступен."
    pass



class UnknownStatusHomework(Exception):
    "Исключение - неизвестный статус домашки."
    pass
