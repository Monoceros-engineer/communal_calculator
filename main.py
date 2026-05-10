from tkinter import Tk
from file_manager import load_settings
from gui import open_manage_services_window, create_main_window, show_tutorial
from communal_calculator import (
    get_services, save_services, calculate_dynamic,
    save_tariffs, save_fees, save_initial_settings_multi
)

if __name__ == "__main__":
    root = Tk()
    root.withdraw()  # скрываем корневое окно

    is_first_run = not load_settings()

    if is_first_run:
        # Показываем туториал (без корневого окна)
        tutorial = show_tutorial()
        tutorial.wait_window()
        # Открываем окно управления услугами (без корневого окна)
        win_manage = open_manage_services_window(get_services(), save_services, first_run=True, on_finish=None)
        win_manage.wait_window()
        # Перезагружаем настройки
        from file_manager import load_settings
        load_settings()
        services = get_services()
        tariffs = {key: srv["tariff"] for key, srv in services.items()}
        fees = {key: srv["fee"] for key, srv in services.items()}
        start_values = {key: srv.get("start_value", 0) for key, srv in services.items() if srv["type"] == "metered"}
        window = create_main_window(
            calculate_dynamic, start_values, save_initial_settings_multi,
            tariffs, save_tariffs, fees, save_fees,
            services, save_services
        )
        window.mainloop()
    else:
        # Обычный запуск (не первый)
        services = get_services()
        tariffs = {key: srv["tariff"] for key, srv in services.items()}
        fees = {key: srv["fee"] for key, srv in services.items()}
        start_values = {key: srv.get("start_value", 0) for key, srv in services.items() if srv["type"] == "metered"}
        window = create_main_window(
            calculate_dynamic, start_values, save_initial_settings_multi,
            tariffs, save_tariffs, fees, save_fees,
            services, save_services,
            parent=root
        )
        window.protocol("WM_DELETE_WINDOW", lambda: (window.destroy(), root.destroy()))
        window.mainloop()