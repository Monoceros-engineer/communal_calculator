import os
import json
import config
from datetime import datetime
from paths import get_config_path

# Файлы для хранения настроек и истории
CONFIG_FILE = get_config_path()
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
    
def save_readings_to_history(current_readings, costs, total):
    """Сохраняет текущие показания и затраты в историю (JSON)."""
    history = []
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                history = json.load(f)
        except:
            history = []

    record = {
        "date": datetime.now().strftime("%d.%m.%Y %H:%M"),
        "readings": current_readings.copy(),   # словарь всех показаний
        "costs": {k: float(v) for k, v in costs.items()},
        "total": float(total)
    }
    history.append(record)

    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

    return True    
