import os
import sys

def get_data_dir():
    """Возвращает папку для хранения данных пользователя (создаёт, если не существует)."""
    if sys.platform == 'win32':
        appdata = os.getenv('APPDATA')
        data_dir = os.path.join(appdata, 'CommunalCalculator')
    else:
        data_dir = os.path.join(os.path.expanduser('~'), '.communal_calculator')
    os.makedirs(data_dir, exist_ok=True)
    return data_dir

def get_config_path():
    """Возвращает полный путь к файлу конфигурации calculator_config.json."""
    return os.path.join(get_data_dir(), 'calculator_config.json')

def get_db_path():
    """Возвращает полный путь к файлу базы данных communal.db."""
    return os.path.join(get_data_dir(), 'communal.db')