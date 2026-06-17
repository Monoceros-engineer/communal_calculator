import os
import json
import config
from database import load_services, save_service, delete_service, get_service_id_by_key, add_replacement, mark_replacements_paid, clear_paid_replacements


CONFIG_FILE = "calculator_config.json"  # пока оставим, но не будем использовать

def get_old_config_path():
    import os
    # Ищем в папке проекта (где file_manager.py)
    project_path = os.path.dirname(os.path.abspath(__file__))
    local_path = os.path.join(project_path, CONFIG_FILE)
    if os.path.exists(local_path):
        return local_path
    # Ищем в APPDATA
    appdata_path = os.path.join(os.getenv('APPDATA'), 'CommunalCalculator', CONFIG_FILE)
    if os.path.exists(appdata_path):
        return appdata_path
    return None


def load_settings():
    """Загружает услуги из SQLite или мигрирует из JSON, если БД пуста."""
    services = load_services()
    if services:
        config.services = services
        return True  # загружено, не первый запуск
    else:
        # Попытка миграции из старого JSON (ищем в папке проекта или APPDATA)
        old_config_path = get_old_config_path()
        if old_config_path:
            try:
                with open(old_config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                old_services = data.get('services', {})
                if old_services:
                    # Сохраняем в SQLite
                    for key, service in old_services.items():
                        save_service(key, service)
                    # Перезагружаем
                    config.services = load_services()
                    # Можно удалить JSON после успешной миграции, но пока оставим
                    return True
            except Exception as e:
                print(f"Migration error: {e}")
                return False
        return False  # первый запуск

def save_services_to_db(services):
    """Сохраняет все услуги в SQLite."""
    for key, service in services.items():
        save_service(key, service)

def save_settings():
    """Сохраняет текущие услуги из config.services в SQLite."""
    for key, service in config.services.items():
        save_service(key, service)