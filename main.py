from file_manager import load_settings
from gui import create_main_window
from communal_calculator import calculate

if __name__ == "__main__":
    # Загружаем настройки при запуске
    is_first_run = not load_settings()
    window = create_main_window(calculate, is_first_run)
    window.mainloop()