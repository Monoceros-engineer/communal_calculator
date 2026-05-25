import sys
import traceback

try:
    from PySide6.QtWidgets import (
        QApplication,
        QMainWindow,
        QWidget,
        QVBoxLayout,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QCheckBox,
        QPushButton,
        QTableWidget,
        QTableWidgetItem,
        QMessageBox,
        QSizePolicy,
        QGridLayout,
        QDialog,
    )
    from PySide6.QtCore import Qt, QTimer, QDateTime, QLocale
    import config
    from communal_calculator import process_services_data, normalize_decimal
    from file_manager import save_readings_to_history, load_settings
    from config import services  # или import config, затем использовать config.services
except Exception as e:
    print("Import error:", e)
    sys.exit(1)

# Загружаем настройки из JSON (заполнит config.services)
load_settings()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Калькулятор коммуналки")
        self.move(
            100, 100
        )  # Данное окно появляется на экране с координатами 100 пикселей на 100 пикселей

        # Центральный виджет и основной вертикальный layout
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(
            20, 20, 20, 20
        )  # отступы слева/справа/сверху/снизу
        main_layout.setSpacing(15)
               
        # Виджет для отображаения даты и времени
        # Виджет для отображения даты и времени
        self.datetime_label = QLabel()
        self.datetime_label.setAlignment(Qt.AlignCenter)  # выравнивание по центру
        self.datetime_label.setStyleSheet("font-size: 12px; margin: 5px;")  # небольшой отступ
        
        # Таймер для обновления времени
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_datetime)
        self.timer.start(1000)  # каждую секунду
        self.update_datetime()   # сразу установить текущее значение

        # Задаем шрифт, цвет фона метки через setStyleSheet
        self.datetime_label.setStyleSheet("background-color: #f0f0f0; padding: 5px; font-size: 12px;")
        main_layout.addWidget(self.datetime_label) # Добавляем метку с датой и временем в самый верх главного окна 

        # Контейнер для динамических строк услуг
        self.services_container = (
            QWidget()
        )  # создаем пустой виджет-контейнер self.services_container для строк услуг
        self.grid_layout = QGridLayout(self.services_container)  # создаем сетку
        self.grid_layout.setContentsMargins(
            0, 0, 0, 0
        )  # отступы слева/справа/сверху/снизу
        self.grid_layout.setHorizontalSpacing(10)
        main_layout.addWidget(self.services_container)

        # Кнопка "Рассчитать"
        calc_button = QPushButton("Рассчитать")
        calc_button.setFixedWidth(200)
        calc_button.setFixedHeight(40)
        calc_button.setStyleSheet("""
            QPushButton {
                background-color: lightblue;
                font: bold 12px;
                border: 1px solid #aaa;
                border-radius: 4px;
                padding: 6px;
            }
            QPushButton:hover {
                background-color: #87ceeb;
            }
            QPushButton:pressed {
                background-color: #4682b4;
            }
        """)
        calc_button.clicked.connect(self.calculate)
        main_layout.addWidget(
            calc_button, alignment=Qt.AlignCenter
        )  # Устанавливаем выравнивание по центру
        calc_button.setObjectName("calculateButton")  # даём уникальное имя

        # Словари для хранения виджетов
        self.entries = {}
        self.checkboxes = {}

        # Построение интерфейса услуг
        self.rebuild_services_ui()

    def update_datetime(self):
            now = QDateTime.currentDateTime()
            locale = QLocale(QLocale.Russian)
            # Формат: "Понедельник, 24 мая 2026 г. 15:30:45"
            # Можно изменить под свой вкус
            datetime_str = locale.toString(now, "dddd, d MMMM yyyy г. HH:mm:ss")
            self.datetime_label.setText(datetime_str)

    def rebuild_services_ui(self):
        # Очищаем все строки сетки, кроме первой(с заголовками)
        for i in reversed(range(self.grid_layout.count())):
            self.grid_layout.itemAt(i).widget().deleteLater()
        self.entries.clear()
        self.checkboxes.clear()

        # Заголовки (row 0)
        header_name = QLabel("<b>Ресурс</b>")
        header_name.setAlignment(
            Qt.AlignLeft | Qt.AlignVCenter
        )  # Устанавливаем выравнивание по левому краю горизонтально и по центру вертикально
        self.grid_layout.addWidget(header_name, 0, 0)
        header_value = QLabel("<b>Показания</b>")
        header_value.setAlignment(
            Qt.AlignCenter | Qt.AlignVCenter
        )  # Устанавливаем выравнивание по центру горизонтально и вертикально
        self.grid_layout.addWidget(header_value, 0, 1)
        header_comm = QLabel("<b>Комиссия</b>")
        header_comm.setAlignment(
            Qt.AlignCenter | Qt.AlignVCenter
        )  # Устанавливаем выравнивание по центру горизонтально и вертикально
        self.grid_layout.addWidget(header_comm, 0, 2)

        row = 1
        # Проходим по всем услугам из config
        for key, service in config.services.items():
            if not service.get("enabled", True):
                continue
            # Название услуги с тарифом
            name = service["name"]
            tariff = service.get("tariff", 0.0)
            name_text = f"<b>{name.upper()}</b> (тариф {tariff: .2f})"
            name_label = QLabel(name_text)
            name_label.setWordWrap(True)  # Перенос длинных слов
            self.grid_layout.addWidget(
                name_label, row, 0
            )  # Размещаем название услуги в сетке в первом столбце

            # Поле ввода или метка для фиксированных услуг
            if service["type"] == "metered":
                entry = QLineEdit()
                entry.setFixedWidth(200)  # фиксированная ширина
                self.grid_layout.addWidget(
                    entry, row, 1
                )  # Размещаем окно ввода в сетке во втором столбце
                self.entries[key] = entry
            else:
                label = QLabel("Показания счетчика не требуются")
                label.setFixedWidth(200)
                label.setAlignment(Qt.AlignCenter)  # Выравниваем по центру
                self.grid_layout.addWidget(
                    label, row, 1
                )  # Размещаем виджет в сетке во втором столбце

            # Чекбокс комиссии
            fee_percent = int(service.get("fee", 0.0) * 100)
            cb = QCheckBox(
                f"{fee_percent}%"
            )  # Создаем виджет чекбокса в формате "(размер комиссии)%"
            self.grid_layout.addWidget(
                cb, row, 2, alignment=Qt.AlignCenter
            )  # Размещаем чекбокс в сетке в третьем столбце и выравниваем по центру
            self.checkboxes[key] = (
                cb  # Сохраняем объект чекбокса (cb) в словарь self.checkboxes под ключом, соответствующим идентификатору услуги (например, "gas", "electricity")
            )

            row += 1

            # # Настраиваем растяжение колонок
            self.grid_layout.setColumnStretch(0, 1)  # первая колонка растягивается
            self.grid_layout.setColumnStretch(1, 0)  # вторая – фиксированной ширины
            self.grid_layout.setColumnStretch(2, 0)  # третья – фиксированной ширины

        self.adjustSize()  # Размеры окна автоматически настраиваются под его содержание
        self.setMinimumSize(500, 400)  # Задаем минимальные размеры окна

    def calculate(self):
        readings = {key: entry.text() for key, entry in self.entries.items()}
        commissions = {key: cb.isChecked() for key, cb in self.checkboxes.items()}

        # Функции для показа диалогов (временно через print)
        def show_warning(title, msg):
            from PySide6.QtWidgets import QMessageBox

            QMessageBox.warning(self, title, msg)

        def show_error(title, msg):
            from PySide6.QtWidgets import QMessageBox

            QMessageBox.critical(self, title, msg)

        result = process_services_data(
            readings,
            commissions,
            warning_callback=show_warning,
            error_callback=show_error,
        )
        if result is None:
            return

        (
            results_data,
            current_readings,
            costs,
            total_amount,
            total_fee,
            total_sum_with_fee,
        ) = result
        # Теперь нужно показать окно с результатами. Создадим новый класс ResultWindow.
        self.result_window = ResultWindow(
            results_data,
            current_readings,
            costs,
            total_amount,
            total_fee,
            total_sum_with_fee,
        )
        self.result_window.show()


class ResultWindow(QDialog):  # или QDialog
    def __init__(
        self,
        results_data,
        current_readings,
        costs,
        total_amount,
        total_fee,
        total_sum_with_fee,
    ):
        super().__init__()
        self.setWindowTitle("Результаты расчёта")
        self.setFixedWidth(850)  # фиксируем ширину окна
        self.results_data = results_data
        self.current_readings = current_readings
        self.costs = costs
        self.total_amount = total_amount
        self.total_fee = total_fee
        self.total_sum_with_fee = total_sum_with_fee

        layout = QVBoxLayout(self)

        # Создадим таблицу (QTableWidget) и заполним её данными
        self.table = QTableWidget()  # Создаем виджет таблицы
        self.table.setColumnCount(8)  # Задаем количество столбцов таблицы
        self.table.setHorizontalHeaderLabels(
            [
                "Ресурс",
                "Начало",
                "Конец",
                "Расход",
                "Тариф",
                "Сумма",
                "Комиссия",
                "Итого",
            ]
        )
        self.table.setRowCount(len(results_data))
        for i, data in enumerate(results_data):
            self.table.setItem(i, 0, QTableWidgetItem(data["Name"]))
            self.table.setItem(i, 1, QTableWidgetItem(str(data["Start value"])))
            self.table.setItem(i, 2, QTableWidgetItem(str(data["End value"])))
            self.table.setItem(i, 3, QTableWidgetItem(str(data["Consumption"])))
            self.table.setItem(i, 4, QTableWidgetItem(f"{data['Tariff']:.2f}"))
            self.table.setItem(i, 5, QTableWidgetItem(f"{data['Amount']:.2f}"))
            self.table.setItem(i, 6, QTableWidgetItem(f"{data['Fee']:.2f}"))
            self.table.setItem(i, 7, QTableWidgetItem(f"{data['Total']:.2f}"))
        layout.addWidget(self.table)

        # Задаем общий стиль для таблицы
        self.table.setStyleSheet("""
        QTableWidget::item {
            border: 1px solid #e0e0e0;
        }
        QHeaderView::section {
            background-color: #f0f0f0;
            border: 1px solid #c0c0c0;
            padding: 4px;
            font-weight: bold;                     
        }
    """)

        # Контейнер для итоговой строки
        total_container = (
            QWidget()
        )  # создаем пустой виджет-контейнер для итоговой строки
        self.total_grid_layout = QGridLayout(total_container)  # создаем сетку
        self.total_grid_layout.setContentsMargins(
            0, 0, 0, 0
        )  # отступы слева/справа/сверху/снизу
        self.total_grid_layout.setHorizontalSpacing(10)
        layout.addWidget(total_container)

        total_amount_name = QLabel(f"<b>Итого без комиссии: {total_amount:.2f}</b>")
        total_amount_name.setAlignment(
            Qt.AlignLeft
        )  # Устанавливаем выравнивание по левому краю
        self.total_grid_layout.addWidget(
            total_amount_name, 0, 0
        )  # Разместили header_name в 1 столбце 1 строки сетки

        total_fee_name = QLabel(f"<b>Итого комиссия: {total_fee:.2f}</b>")
        total_fee_name.setAlignment(
            Qt.AlignLeft
        )  # Устанавливаем выравнивание по левому краю
        self.total_grid_layout.addWidget(
            total_fee_name, 0, 1
        )  # Разместили header_name в 2 столбце 1 строки сетки

        total_sum_with_fee_name = QLabel(
            f"<b>Всего с комиссией: {total_sum_with_fee:.2f}</b>"
        )
        total_sum_with_fee_name.setAlignment(
            Qt.AlignLeft
        )  # Устанавливаем выравнивание по левому краю
        self.total_grid_layout.addWidget(
            total_sum_with_fee_name, 0, 2
        )  # Разместили header_name в 3 столбце 1 строки сетки

        # Кнопка закрытия
        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)

        # Установка фиксированной высоты окна по содержимому
        self.setLayout(layout)
        # Вычисляем высоту таблицы
        self.table.updateGeometry()
        header_height = self.table.horizontalHeader().height()
        rows_height = sum(self.table.rowHeight(i) for i in range(self.table.rowCount()))
        total_table_height = header_height + rows_height + 10
        margins = layout.contentsMargins()
        total_height = (
            total_table_height + margins.top() + margins.bottom() + 80
        )  # запас на итоги и кнопку
        self.setFixedHeight(total_height)


if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)
        app.setStyleSheet("""
            QMainWindow { background-color: #f0f0f0; }
            QLabel { font-size: 12px; }
            QLineEdit { padding: 4px; border: 1px solid #ccc; border-radius: 4px; }
            QCheckBox { font-size: 12px; }
            QPushButton {
                padding: 6px;
                border-radius: 4px;
                background-color: #e0e0e0;
                border: 1px solid #aaa;
            }
            QPushButton:hover {
                background-color: #c0c0c0;   /* светлее при наведении */
                border-color: #777;
            }
            QPushButton:pressed {
                background-color: #a0a0a0;   /* темнее при нажатии */
            }
        """)
        window = MainWindow()
        window.show()
        sys.exit(app.exec())
    except Exception as e:
        traceback.print_exc()
        input("Press Enter to exit...")
