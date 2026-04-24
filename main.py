from file_manager import load_settings
from gui import create_main_window
from communal_calculator import (
    calculate_dynamic, save_initial_settings, get_start_values,
    get_tariffs, save_tariffs, get_fees, save_fees, get_services,
    save_services
)

services = get_services()

if __name__ == "__main__":
    is_first_run = not load_settings()
    start_values = get_start_values()
    tariffs = get_tariffs()
    fees = get_fees()
    window = window = create_main_window(
    calculate_dynamic, is_first_run, start_values, save_initial_settings,
    tariffs, save_tariffs, get_fees, save_fees,
    services, save_services)
    window.mainloop()