from tkinter import Tk
from file_manager import load_settings
from gui import open_manage_services_window, create_main_window
from communal_calculator import (
    get_services, save_services, calculate_dynamic,
    save_tariffs, save_fees, save_initial_settings_multi
)

if __name__ == "__main__":
    is_first_run = not load_settings()
    if is_first_run:
        root = Tk()
        root.withdraw()  # скрываем корневое окно

        def on_first_run_finish():
            root.quit()  # завершаем цикл событий, но окно не уничтожаем
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

        open_manage_services_window(get_services(), save_services, first_run=True, on_finish=on_first_run_finish)
        root.mainloop()  # запускаем цикл для окна управления
    else:
        # обычный запуск
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