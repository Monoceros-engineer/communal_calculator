import sys
import os
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
        QTabWidget,
        QHeaderView,
    )
    from PySide6.QtCore import Qt, QTimer, QDateTime, QLocale, QRect
    from PySide6.QtGui import QPixmap, QPainter
    import config
    from communal_calculator import (
        process_services_data,
        normalize_decimal,
        save_tariffs,
        save_fees,
        save_services,
    )
    from file_manager import save_readings_to_history, load_settings
    from config import services  # или import config, затем использовать config.services
    import random
except Exception as e:
    print("Import error:", e)
    sys.exit(1)

# Загружаем настройки из JSON (заполнит config.services)
load_settings()

def resource_path(relative_path):
    """Получить абсолютный путь к ресурсу, работает для разработки и для PyInstaller."""
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


class AnimatedBackground(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.background = QPixmap()
        self.effect = QPixmap()
        self.mode = None
        self.cloud_x = 0
        self.cloud_speed = 0.2
        self.particles = []
        self.init_particles()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_animation)
        self.timer.start(30)  # 30 мс ~33 FPS

    def set_season_effect(self, bg_path, effect_path, mode):
        print(f"DEBUG set_season_effect: mode={mode}, effect_path={effect_path}")
        import os
        if not os.path.exists(effect_path):
            print(f"WARNING: file not found: {effect_path}")
        self.background = QPixmap(bg_path)
        effect_pixmap = QPixmap(effect_path)
        if effect_pixmap.isNull():
            print(f"ERROR: failed to load pixmap: {effect_path}")
        # Уменьшаем эффект в 2 раза (подберите коэффициент)
        scale_factor = 0.5
        new_width = int(effect_pixmap.width() * scale_factor)
        new_height = int(effect_pixmap.height() * scale_factor)
        self.effect = effect_pixmap.scaled(
            new_width, new_height, Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.mode = mode
        self.init_particles()

    def init_particles(self):
        self.particles.clear()
        for _ in range(40):
            self.particles.append(
                {
                    "x": random.randint(0, 800),
                    "y": random.randint(0, 600),
                    "speed": random.uniform(0.5, 2),
                    "drift": random.uniform(-0.5, 0.5),
                    "size": random.uniform(0.3, 1.0),
                }
            )

    def update_animation(self):
        if self.mode in ("clouds", "clouds_summer"):
            self.cloud_x += self.cloud_speed
            if self.cloud_x > self.width():
                self.cloud_x = -self.effect.width()
        else:
            for p in self.particles:
                p["y"] += p["speed"]
                p["x"] += p["drift"]
                if p["y"] > self.height():
                    p["y"] = -20
                    p["x"] = random.randint(0, self.width())
        self.update()

    def paintEvent(self, event):
        if self.background.isNull():
            return
        painter = QPainter(self)
        painter.drawPixmap(self.rect(), self.background)

        if self.mode in ("clouds", "clouds_summer"):
            y = int(
                self.height() * 0.0
            )  # высота положения облаков 0.0 - это самый верх 0.15 - посередине окна
            painter.drawPixmap(int(self.cloud_x), y, self.effect)
            painter.drawPixmap(int(self.cloud_x - self.effect.width()), y, self.effect)
        else:
            for p in self.particles:
                w = int(self.effect.width() * p["size"])
                h = int(self.effect.height() * p["size"])
                painter.drawPixmap(int(p["x"]), int(p["y"]), w, h, self.effect)

def get_season_by_date():
    import datetime

    now = datetime.datetime.now()
    month = now.month
    if 3 <= month <= 5:
        return "spring"
    elif 6 <= month <= 8:
        return "summer"
    elif 9 <= month <= 11:
        return "autumn"
    else:
        return "winter"


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Калькулятор коммуналки")
        self.move(
            100, 100
        )  # Данное окно появляется на экране с координатами 100 пикселей на 100 пикселей

        # Центральный виджет и основной вертикальный layout
        # Создаём фон
        season = get_season_by_date()
        if season == "spring":
            bg_path = "assets/backgrounds/spring.png"
            effect_path = "assets/effects/clouds.png"
            mode = "clouds"
        elif season == "summer":
            bg_path = "assets/backgrounds/summer.png"
            effect_path = "assets/effects/clouds_summer.png"
            mode = "clouds_summer"
        elif season == "autumn":
            bg_path = "assets/backgrounds/autumn.png"
            effect_path = "assets/effects/leaves.png"
            mode = "leaves"
        elif season == "winter":
            bg_path = "assets/backgrounds/winter.png"
            effect_path = "assets/effects/snow.png"
            mode = "snow"
        else:
            bg_path = "assets/backgrounds/spring.png"
            effect_path = "assets/effects/clouds.png"
            mode = "clouds"
        self.animated_bg = AnimatedBackground(self)
        self.setCentralWidget(self.animated_bg)
        self.animated_bg.set_season_effect(bg_path, effect_path, mode)

        print(f"Season detected: {season}")
        print(f"bg_path = {bg_path}")
        print(f"effect_path = {effect_path}")
        print(f"mode = {mode}")

        # Создаём полупрозрачную панель
        self.panel = QWidget(self.animated_bg)
        self.panel.setStyleSheet("""
            background: rgba(255, 255, 255, 220);
            border-radius: 15px;
            border: 1px solid rgba(200, 200, 200, 100);
        """)

        # Layout для панели (вертикальный)
        panel_layout = QVBoxLayout(self.panel)
        panel_layout.setContentsMargins(20, 20, 20, 20)
        panel_layout.setSpacing(15)

        # Центрируем панель на фоне
        bg_layout = QVBoxLayout(self.animated_bg)
        bg_layout.addStretch()
        bg_layout.addWidget(self.panel)
        bg_layout.setContentsMargins(50, 50, 50, 50)   # отступы со всех сторон по 50 пикселей
        bg_layout.addStretch()

        # Кнопки
        self.settings_button = QPushButton("Настройки")
        self.settings_button.clicked.connect(self.open_settings)

        self.help_button = QPushButton("Помощь")
        self.help_button.clicked.connect(self.open_help)

        # Стиль для обеих кнопок
        button_style = """
            QPushButton {
                background-color: #e0e0e0;
                border: 1px solid #aaa;
                border-radius: 4px;
                padding: 6px;
            }
            QPushButton:hover {
                background-color: #c0c0c0;
            }
            QPushButton:pressed {
                background-color: #a0a0a0;
            }
        """
        self.settings_button.setStyleSheet(button_style)
        self.help_button.setStyleSheet(button_style)

        # Горизонтальная упаковка кнопок
        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(self.settings_button)
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.help_button)

        # Добавляем в панель (panel_layout)
        panel_layout.addLayout(buttons_layout)

        # Виджет для отображения даты и времени
        self.datetime_label = QLabel()
        self.datetime_label.setAlignment(Qt.AlignCenter)  # выравнивание по центру
        self.datetime_label.setStyleSheet(
            "font-size: 12px; margin: 5px;"
        )  # небольшой отступ

        # Таймер для обновления времени
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_datetime)
        self.timer.start(1000)  # каждую секунду
        self.update_datetime()  # сразу установить текущее значение

        # Задаем шрифт, цвет фона метки через setStyleSheet
        self.datetime_label.setStyleSheet(
            "background-color: #f0f0f0; padding: 5px; font-size: 12px;"
        )
        panel_layout.addWidget(
            self.datetime_label
        )  # Добавляем метку с датой и временем в самый верх главного окна

        # Контейнер для динамических строк услуг
        self.services_container = (
            QWidget()
        )  # создаем пустой виджет-контейнер self.services_container для строк услуг
        self.grid_layout = QGridLayout(self.services_container)  # создаем сетку
        self.grid_layout.setContentsMargins(
            0, 0, 0, 0
        )  # отступы слева/справа/сверху/снизу
        self.grid_layout.setHorizontalSpacing(10)
        self.grid_layout.setColumnStretch(0, 1)   # первая колонка будет растягиваться
        self.grid_layout.setColumnStretch(1, 0)   # вторая – фиксированной ширины
        self.grid_layout.setColumnStretch(2, 0)   # третья – фиксированной
        panel_layout.addWidget(self.services_container)

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
        panel_layout.addWidget(
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

    def open_settings(self):
        dialog = SettingsWindow(config.services, self)
        if dialog.exec() == QDialog.Accepted:
            # После сохранения обновить интерфейс
            self.rebuild_services_ui()

    def open_help(self):
        import webbrowser
        import tempfile
        import os
        from PySide6.QtWidgets import QMessageBox

        readme_path = resource_path("README.md")
        if not os.path.exists(readme_path):
            QMessageBox.warning(self, "Ошибка", "Файл справки (README.md) не найден.")
            return

        try:
            with open(readme_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось прочитать README.md: {e}")
            return

        html_content = f"""<!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"><title>Справка - Калькулятор коммуналки</title></head>
    <body><pre style="font-family: Arial, sans-serif;">{content}</pre></body>
    </html>"""

        with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as f:
            f.write(html_content)
            temp_html = f.name

        webbrowser.open(temp_html)

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


class SettingsWindow(QDialog):
    def __init__(self, services, parent=None):
        super().__init__(parent)
        self.services = services
        self.setWindowTitle("Настройки")
        #self.setMinimumSize(600, 400)

        # Основной layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Создаём вкладки
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)

        # Вкладка "Тарифы"
        self.tariffs_tab = QWidget()
        self.tab_widget.addTab(self.tariffs_tab, "Тарифы")
        self.setup_tariffs_tab()

        # Вкладка "Комиссии"
        self.commissions_tab = QWidget()
        self.tab_widget.addTab(self.commissions_tab, "Комиссии")
        self.setup_commissions_tab()

        # Вкладка "Управление услугами"
        self.services_tab = QWidget()
        self.tab_widget.addTab(self.services_tab, "Управление услугами")
        self.setup_services_tab()

        # Кнопки "Сохранить" и "Отмена"
        button_box = QHBoxLayout()
        save_btn = QPushButton("Сохранить")
        save_btn.clicked.connect(self.save_all)
        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(self.reject)  # reject закрывает диалог
        button_box.addWidget(save_btn)
        button_box.addWidget(cancel_btn)
        layout.addLayout(button_box)

        # После создания всех виджетов подгоняем размер окна
        self.adjustSize()
        self.setMinimumSize(500, 400)  # чтобы окно не было слишком маленьким
        
    def setup_tariffs_tab(self):
        """Создаёт таблицу для редактирования тарифов."""
        layout = QVBoxLayout(self.tariffs_tab)
        layout.setContentsMargins(10, 10, 10, 10)
        # Таблица
        self.tariffs_table = QTableWidget()
        self.tariffs_table.setColumnCount(2)
        self.tariffs_table.setHorizontalHeaderLabels(["Услуга", "Тариф (руб.)"])
        self.tariffs_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.tariffs_table)
        # Заполняем данными из services
        self.update_tariffs_table()

    def update_tariffs_table(self):
        """Обновляет таблицу тарифов на основе текущих services."""
        services = self.services
        self.tariffs_table.setRowCount(len(services))
        for row, (key, service) in enumerate(services.items()):
            # Название услуги (не редактируется)
            name_item = QTableWidgetItem(service["name"])
            name_item.setFlags(
                name_item.flags() & ~Qt.ItemIsEditable
            )  # запрещаем редактирование
            self.tariffs_table.setItem(row, 0, name_item)
            # Тариф (редактируемое поле)
            tariff_item = QTableWidgetItem(str(service["tariff"]))
            self.tariffs_table.setItem(row, 1, tariff_item)
        #self.tariffs_table.resizeColumnsToContents()
        # Растягиваем колонку с названием (0) на всё доступное пространство
        self.tariffs_table.horizontalHeader().setStretchLastSection(False)
        self.tariffs_table.setColumnWidth(1, 120)  # фиксированная ширина для тарифа
        self.tariffs_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)

    def setup_commissions_tab(self):
        """Создаёт таблицу для редактирования комиссий."""
        layout = QVBoxLayout(self.commissions_tab)
        layout.setContentsMargins(10, 10, 10, 10)
        self.commissions_table = QTableWidget()
        self.commissions_table.setColumnCount(2)
        self.commissions_table.setHorizontalHeaderLabels(["Услуга", "Комиссия (%)"])
        self.commissions_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.commissions_table)
        self.update_commissions_table()

    def update_commissions_table(self):
        services = self.services
        self.commissions_table.setRowCount(len(services))
        for row, (key, service) in enumerate(services.items()):
            name_item = QTableWidgetItem(service["name"])
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            self.commissions_table.setItem(row, 0, name_item)
            fee_percent = int(service.get("fee", 0.0) * 100)
            fee_item = QTableWidgetItem(str(fee_percent))
            self.commissions_table.setItem(row, 1, fee_item)
        #self.commissions_table.resizeColumnsToContents()
        # Растягиваем колонку с названием (0) на всё доступное пространство
        self.commissions_table.horizontalHeader().setStretchLastSection(False)
        self.commissions_table.setColumnWidth(1, 100)
        self.commissions_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)

    def setup_services_tab(self):
        """Вкладка управления услугами (пока заглушка)."""
        layout = QVBoxLayout(self.services_tab)
        label = QLabel(
            "Здесь будет управление услугами (добавление, удаление, включение/отключение)."
        )
        layout.addWidget(label)
        # TODO: реализовать список услуг и кнопки

    def save_all(self):
        """Сохраняет изменения из всех вкладок."""
        # Сохраняем тарифы
        new_tariffs = {}
        for row in range(self.tariffs_table.rowCount()):
            key = list(self.services.keys())[row]
            tariff_str = self.tariffs_table.item(row, 1).text()
            tariff_str = normalize_decimal(tariff_str)  # замена запятой на точку
            try:
                new_tariffs[key] = float(tariff_str)
            except ValueError:
                QMessageBox.warning(
                    self,
                    "Ошибка",
                    f"Некорректный тариф для услуги {self.services[key]['name']}",
                )
                return
        save_tariffs(new_tariffs)

        # Сохраняем комиссии
        new_fees = {}
        for row in range(self.commissions_table.rowCount()):
            key = list(self.services.keys())[row]
            fee_str = self.commissions_table.item(row, 1).text()
            fee_str = normalize_decimal(fee_str)  # замена запятой на точку
            try:
                fee_percent = float(fee_str)
                if fee_percent < 0 or fee_percent > 100:
                    raise ValueError
                new_fees[key] = fee_percent / 100.0
            except ValueError:
                QMessageBox.warning(
                    self,
                    "Ошибка",
                    f"Комиссия должна быть числом от 0 до 100 для услуги {self.services[key]['name']}",
                )
                return
        save_fees(new_fees)

        self.accept()

        # Сохраняем услуги (пока не трогаем)
        # save_services() уже вызывается внутри save_tariffs и save_fees через save_settings()? Нет, они вызывают save_settings() отдельно.
        # Но после сохранения тарифов и комиссий services уже обновились в config.
        # Можно дополнительно вызвать save_services() для сохранения структуры, но она уже вызывается внутри save_tariffs и save_fees.

        self.accept()  # закрываем диалог


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
