import os
import json
from datetime import datetime

# Файлы для хранения настроек и истории
CONFIG_FILE = "calculator_config.json"
HISTORY_FILE = "readings_history.json"


# Функции для работы с настройками
def load_settings():
    """Загружает настройки из файла"""
    global start_value_gas, start_value_electricity, start_value_water
    global tarif_gas, tarif_electricity, tarif_water
    global fee_gas, fee_electricity, fee_water

    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                settings = json.load(f)

            start_value_gas = settings.get("start_value_gas", 25745)
            start_value_electricity = settings.get("start_value_electricity", 9838)
            start_value_water = settings.get("start_value_water", 502)

            tarif_gas = settings.get("tarif_gas", 8.7)
            tarif_electricity = settings.get("tarif_electricity", 7.1)
            tarif_water = settings.get("tarif_water", 84.44)

            fee_gas = settings.get("fee_gas", 0.01)
            fee_electricity = settings.get("fee_electricity", 0.01)
            fee_water = settings.get("fee_water", 0.01)

            return True  # Настройки загружены
        except:
            return False  # Ошибка загрузки
    else:
        return False  # Файл не найден - первый запуск


def save_settings():
    """Сохраняет настройки в файл"""
    settings = {
        "start_value_gas": start_value_gas,
        "start_value_electricity": start_value_electricity,
        "start_value_water": start_value_water,
        "tarif_gas": tarif_gas,
        "tarif_electricity": tarif_electricity,
        "tarif_water": tarif_water,
        "fee_gas": fee_gas,
        "fee_electricity": fee_electricity,
        "fee_water": fee_water,
    }

    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=4)
        return True
    except:
        return False
    
def save_readings_to_history(current_readings, costs, total):
    """Сохраняет текущие показания в историю и обновляет начальные значения"""
    global start_value_gas, start_value_electricity, start_value_water

    # Загружаем существующую историю
    history = []
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                history = json.load(f)
        except:
            history = []

    # Создаем запись о текущем расчете
    record = {
        "date": datetime.now().strftime("%d.%m.%Y %H:%M"),
        "readings": {
            "gas": current_readings["gas"],
            "electricity": current_readings["electricity"],
            "water": current_readings["water"],
        },
        "costs": {
            "gas": float(costs["gas"]),
            "electricity": float(costs["electricity"]),
            "water": float(costs["water"]),
        },
        "total": float(total),
    }

    history.append(record)

    # Сохраняем историю
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

    # ОБНОВЛЯЕМ НАЧАЛЬНЫЕ ЗНАЧЕНИЯ текущими показаниями
    start_value_gas = current_readings["gas"]
    start_value_electricity = current_readings["electricity"]
    start_value_water = current_readings["water"]

    # Сохраняем обновленные начальные значения
    save_settings()

    return True    
