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
        root = Tk()
        root.withdraw()
        tutorial = show_tutorial(parent=root)
        root.wait_window(tutorial)

        def on_finish():
            print("on_finish called")
            from file_manager import load_settings
            load_settings()
            services = get_services()
            print("=== FEES after load ===")
            for key, srv in services.items():
                print(f"{key}: fee = {srv.get('fee')}")
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

        win_manage = open_manage_services_window(
            get_services(), save_services, first_run=True, on_finish=on_finish, parent=root
        )
        root.mainloop()
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