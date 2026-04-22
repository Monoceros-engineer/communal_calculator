from decimal import getcontext

# Настройка точности Decimal
getcontext().prec = 28

#Создаем словарь услуг
services = {
    "gas": {
        "name": "Газ",
        "type": "metered",       # "metered" - по счётчику, "fixed" - фиксированный
        "enabled": True,
        "start_value": 25745,
        "tariff": 8.7,
        "fee": 0.01
    },
    "electricity": {
        "name": "Электричество",
        "type": "metered",
        "enabled": True,
        "start_value": 9838,
        "tariff": 7.1,
        "fee": 0.01
    },
    "water": {
        "name": "Вода",
        "type": "metered",
        "enabled": True,
        "start_value": 502,
        "tariff": 84.44,
        "fee": 0.01
    }
}