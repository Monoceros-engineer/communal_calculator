import os
import json
import config
from datetime import datetime

# Файлы для хранения настроек и истории
CONFIG_FILE = "calculator_config.json"
HISTORY_FILE = "readings_history.json"


# Функции для работы с настройками
def load_settings():
    """Загружает настройки из файла в config.services"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Ожидаем, что в файле лежит словарь services
            if "services" in data:
                config.services = data["services"]
            else:
                # Если файл старого формата, можно попробовать сконвертировать, но пока просто игнорируем
                pass
            return True
        except:
            return False
    else:
        return False

def save_settings():
    """Сохраняет настройки из config.services в файл"""
    data = {"services": config.services}
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        return True
    except:
        return False
    
def save_readings_to_history(current_readings, costs, total_sum_with_fee):
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
        "total": float(total_sum_with_fee),
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
