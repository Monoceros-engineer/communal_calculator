from decimal import getcontext

# Настройка точности Decimal
getcontext().prec = 28

#Создаем словарь услуг
services = {}

# Язык интерфейса: 'system', 'ru' или 'en'
language = 'system'