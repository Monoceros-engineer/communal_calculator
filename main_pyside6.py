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
        QComboBox,
        QDialogButtonBox,
        QListWidget,
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
        self.background = QPixmap(bg_path)
        effect_pixmap = QPixmap(effect_path)
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

class WelcomeWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Добро пожаловать!")
        self.setFixedSize(500, 400)
        self.setWindowFlags(Qt.FramelessWindowHint)  # убираем рамку (опционально)
        self.setModal(True)

        # Определяем сезон для фона
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
        else:  # winter
            bg_path = "assets/backgrounds/winter.png"
            effect_path = "assets/effects/snow.png"
            mode = "snow"

        # Создаём анимированный фон
        self.animated_bg = AnimatedBackground(self)
        self.animated_bg.set_season_effect(bg_path, effect_path, mode)
        self.animated_bg.setGeometry(0, 0, 600, 400)

        # Заголовок (надпись)
        self.title_label = QLabel("<h1>Добро пожаловать в Калькулятор коммуналки!</h1>", self)
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet("""
            QLabel {
                color: white;
                background: rgba(0, 0, 0, 150);
                border-radius: 10px;
                padding: 10px; 
                font-weight: bold;
                font-size: 10px;
            }
        """)
        self.title_label.adjustSize()
        self.title_label.move((self.width() - self.title_label.width()) // 2, 50)

        # Кнопка "Начать"
        self.start_button = QPushButton("Начать", self)
        self.start_button.setFixedSize(200, 50)
        self.start_button.setStyleSheet("""
            QPushButton {
                font-size: 16px;
                font-weight: bold;
                background-color: #4CAF50;
                color: white;
                border-radius: 10px;
                border: none;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        # Размещаем кнопку по центру
        self.start_button.move((self.width() - self.start_button.width()) // 2,
                               (self.height() - self.start_button.height()) // 2)
        self.start_button.clicked.connect(self.on_start)

    def on_start(self):
        self.accept()  # закрываем окно с кодом Accepted

    def resizeEvent(self, event):
        # При изменении размера (хотя у нас фиксированный размер) перецентрируем кнопку
        self.start_button.move((self.width() - self.start_button.width()) // 2,
                               (self.height() - self.start_button.height()) // 2)
        super().resizeEvent(event)

class FirstRunWizard(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Настройка услуг")
        self.setModal(True)
        self.setMinimumSize(600, 500)

        # Определяем сезон для фона
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
        else:  # winter
            bg_path = "assets/backgrounds/winter.png"
            effect_path = "assets/effects/snow.png"
            mode = "snow"

        # Создаём анимированный фон
        self.animated_bg = AnimatedBackground(self)
        self.animated_bg.set_season_effect(bg_path, effect_path, mode)

        # Основной layout диалога (только для фона)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.animated_bg)   # фон занимает всю область
        
        # Полупрозрачная панель для контента
        self.panel = QWidget(self.animated_bg)
        self.panel.setStyleSheet("""
            background: rgba(255, 255, 255, 220);
            border-radius: 15px;
            border: 1px solid rgba(200, 200, 200, 100);
        """)
        self.panel.setMinimumWidth(400)

        # Layout панели
        panel_layout = QVBoxLayout(self.panel)
        panel_layout.setContentsMargins(20, 20, 20, 20)
        panel_layout.setSpacing(15)

        # Приветственный текст
        label = QLabel(
            "<h2>Добро пожаловать в Калькулятор коммуналки!</h2>"
            "<p>Давайте начнем с настройки программы. Для того, чтобы все работало,</p>"
            "<p>необходимо сделать несколько простых шагов:</p>"
            "<p>1. Нажмите кнопку 'Добавить', чтобы создать услугу, расход по которой вы будете считать\n"
    " (газ, свет, вода и т.д.).</p>"
    "<p>2. Выберите тип услуги: 'По счётчику' или 'Фиксированная'.</p>"
    "<p>3. Заполните название, тариф, комиссию (если есть). Для услуг по счётчику также укажите начальные показания (то есть те показания счетчика, которые вы передавали при прошлой оплате услуги).</p>"
    "<p>4. После добавления всех услуг закройте окно управления.</p>"
    "<p>5. В главном окне вводите текущие показания и нажимайте 'Рассчитать'.</p>"
    "<p>Совет: Наводите курсор на кнопки — появятся подсказки.</p>"
        )
        label.setWordWrap(True)
        panel_layout.addWidget(label)

        # Список добавленных услуг
        panel_layout.addWidget(QLabel("Добавленные услуги:"))
        self.services_list = QListWidget()
        panel_layout.addWidget(self.services_list)

        # Кнопки
        btn_layout = QHBoxLayout()
        self.btn_add = QPushButton("Добавить услугу")
        self.btn_finish = QPushButton("✅ Готово")
        self.btn_finish.setEnabled(False)
        btn_layout.addWidget(self.btn_add)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_finish)
        panel_layout.addLayout(btn_layout)

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

        self.btn_add.setStyleSheet(button_style)
        self.btn_finish.setStyleSheet(button_style)
        
        self.btn_add.setToolTip("Нажмите, чтобы добавить новую услугу (газ, свет, вода, интернет и т.д.).")
        self.btn_finish.setToolTip("Завершить настройку и перейти к главному окну (можно добавить услуги позже через меню 'Настройки').")

        self.btn_add.clicked.connect(self.add_service)
        self.btn_finish.clicked.connect(self.accept)

        # Обновляем список
        self.update_services_list()

        # Размещаем панель по центру фона
        bg_layout = QVBoxLayout(self.animated_bg)
        bg_layout.addStretch()
        bg_layout.addWidget(self.panel, alignment=Qt.AlignCenter)
        bg_layout.addStretch()
        bg_layout.setContentsMargins(50, 50, 50, 50)


    def update_services_list(self):
        self.services_list.clear()
        for key, service in config.services.items():
            self.services_list.addItem(f"{service['name']} ({service['type']})")
        self.btn_finish.setEnabled(len(config.services) > 0)

    def add_service(self):
        dialog = AddServiceDialog(config.services, self)
        if dialog.exec():
            self.update_services_list()
            save_services()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Калькулятор коммуналки")
        self.move(
            100, 100
        )  # Данное окно появляется на экране с координатами 100 пикселей на 100 пикселей
        self.setWindowIcon(QIcon(resource_path("icon.ico")))

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
        dialog = SettingsWindow(config.services, refresh_callback=self.rebuild_services_ui, parent=self)
        if dialog.exec() == QDialog.Accepted:
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

        # Показать подсказку с начальными показаниями (если есть услуги)
        if config.services:
            msg_lines = ["В прошлом месяце показания ваших счётчиков были:"]
            for key, service in config.services.items():
                if service.get("type") == "metered" and service.get("enabled"):
                    start_val = service.get("start_value", 0)
                    msg_lines.append(f"{service['name']}: {start_val}")
            if len(msg_lines) > 1:  # есть хотя бы одна услуга по счётчику
                msg = "\n".join(msg_lines) + "\n\nВведите новые показания и нажмите 'Рассчитать'"
                QMessageBox.information(self, "Информация", msg)
        
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
    results_data, current_readings, costs, total_amount, total_fee, total_sum_with_fee,
    config.services, save_services
)
        self.result_window.show()


class ResultWindow(QDialog):  # или QDialog
    def __init__(self, results_data, current_readings, costs, 
                 total_amount, total_fee, 
                 total_sum_with_fee, services, 
                 save_services_callback):
        super().__init__()
        self.setWindowTitle("Результаты расчёта")
        self.setFixedWidth(850)  # фиксируем ширину окна
        self.results_data = results_data
        self.current_readings = current_readings
        self.costs = costs
        self.total_amount = total_amount
        self.total_fee = total_fee
        self.total_sum_with_fee = total_sum_with_fee
        self.services = services
        self.save_services_callback = save_services_callback
        self.setWindowIcon(QIcon(resource_path("icon.ico")))

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

        # Кнопки
        button_layout = QHBoxLayout()
        self.save_btn = QPushButton("✅ Сохранить и закрыть")
        self.close_btn = QPushButton("❌ Закрыть без сохранения")
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.close_btn)
        # Добавляем button_layout в основной layout (в конец)

        self.save_btn.clicked.connect(self.save_and_close)
        self.close_btn.clicked.connect(self.reject)  # reject закрывает диалог
        
        layout.addLayout(button_layout)

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

    def save_and_close(self):
        from file_manager import save_readings_to_history
        from PySide6.QtWidgets import QMessageBox

        # Сохраняем историю
        save_readings_to_history(self.current_readings, self.costs, self.total_sum_with_fee)

        # Обновляем начальные значения для meter-услуг
        for key, reading in self.current_readings.items():
            if key in self.services and self.services[key]["type"] == "metered":
                self.services[key]["start_value"] = reading

        # Сохраняем услуги
        self.save_services_callback()

        # Сообщение пользователю
        msg = "Показания сохранены!\n\nНовые начальные значения для следующего месяца:\n"
        for key, reading in self.current_readings.items():
            service_name = self.services[key].get("name", key)
            msg += f"{service_name}: {reading}\n"
        QMessageBox.information(self, "Готово", msg)

        self.accept()  # закрываем окно

class AddServiceDialog(QDialog):
    def __init__(self, services, parent=None):
        super().__init__(parent)
        self.services = services
        self.setWindowTitle("Добавление услуги")
        self.setMinimumWidth(400)
        layout = QVBoxLayout(self)

        # Название услуги
        layout.addWidget(QLabel("Название услуги:"))
        self.name_edit = QLineEdit()
        self.name_edit.setToolTip("Введите название услуги, которую вы хотите добавить (например, 'Газ', 'Электричество').")
        layout.addWidget(self.name_edit)

        # Тип услуги
        layout.addWidget(QLabel("Тип:"))
        self.type_combo = QComboBox()
        self.type_combo.addItems(["По счётчику", "Фиксированная"])
        self.type_combo.setToolTip(
            "Выберите тип услуги:\n"
            "- По счётчику: если вы снимаете показания счётчика для расчёта (газ, свет, вода).\n"
            "- Фиксированная: если платёж не зависит от потребления (интернет, мусор, капремонт)."
        )
        layout.addWidget(self.type_combo)

        # Начальное значение (для по счётчику)
        self.start_label = QLabel("Начальное значение:")
        self.start_edit = QLineEdit()
        self.start_edit.setToolTip(
            "Введите показания счётчика, которые были у вас в прошлом месяце.\n"
            "Для новой услуги – начальное значение обычно равно 0."
        )
        layout.addWidget(self.start_label)
        layout.addWidget(self.start_edit)

        # Тариф
        layout.addWidget(QLabel("Тариф (руб.):"))
        self.tariff_edit = QLineEdit()
        self.tariff_edit.setToolTip(
            "Введите стоимость за единицу потребления услуги (например, за 1 кВт·ч электроэнергии)."
        )
        layout.addWidget(self.tariff_edit)

        # Комиссия (%)
        layout.addWidget(QLabel("Комиссия (%):"))
        self.fee_edit = QLineEdit()
        self.fee_edit.setToolTip(
            "Укажите комиссию банка в процентах (0 – если комиссия не взимается)."
        )
        layout.addWidget(self.fee_edit)

        # Включена ли
        self.enabled_check = QCheckBox("Включена")
        self.enabled_check.setChecked(True)
        self.enabled_check.setToolTip("Если галочка снята, услуга не будет отображаться в главном окне и не будет учитываться в расчётах.")
        layout.addWidget(self.enabled_check)

        # Кнопки
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        # Логика: при изменении типа скрывать/показывать поле начального значения
        self.type_combo.currentIndexChanged.connect(self.update_visibility)
        self.update_visibility()

    def update_visibility(self):
        is_metered = self.type_combo.currentText() == "По счётчику"
        self.start_label.setVisible(is_metered)
        self.start_edit.setVisible(is_metered)

    def accept(self):
        # Валидация и добавление услуги
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Ошибка", "Введите название услуги")
            return
        key = name.lower().replace(' ', '_')
        if key in self.services:
            QMessageBox.warning(self, "Ошибка", "Услуга с таким названием уже существует")
            return

        service_type = "metered" if self.type_combo.currentText() == "По счётчику" else "fixed"
        try:
            tariff = float(self.tariff_edit.text().strip())
            if tariff <= 0:
                raise ValueError
        except:
            QMessageBox.warning(self, "Ошибка", "Тариф должен быть положительным числом")
            return

        try:
            fee_percent = float(self.fee_edit.text().strip())
            if fee_percent < 0 or fee_percent > 100:
                raise ValueError
            fee = fee_percent / 100.0
        except:
            QMessageBox.warning(self, "Ошибка", "Комиссия должна быть числом от 0 до 100")
            return

        new_service = {
            "name": name,
            "type": service_type,
            "enabled": self.enabled_check.isChecked(),
            "tariff": tariff,
            "fee": fee
        }
        if service_type == "metered":
            try:
                start_val = float(self.start_edit.text().strip())
                if start_val < 0:
                    raise ValueError
                new_service["start_value"] = start_val
            except:
                QMessageBox.warning(self, "Ошибка", "Начальное значение должно быть неотрицательным числом")
                return

        self.services[key] = new_service
        save_services()
        super().accept()

class EditServiceDialog(QDialog):
    def __init__(self, services, key, parent=None):
        super().__init__(parent)
        self.services = services
        self.key = key
        self.service = services[key]
        self.setWindowTitle(f"Редактирование услуги: {self.service['name']}")
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)

        # Название
        layout.addWidget(QLabel("Название услуги:"))
        self.name_edit = QLineEdit(self.service["name"])
        layout.addWidget(self.name_edit)

        # Тип (нельзя изменить, только показать)
        layout.addWidget(QLabel("Тип:"))
        type_text = "По счётчику" if self.service["type"] == "metered" else "Фиксированная"
        type_label = QLabel(type_text)
        layout.addWidget(type_label)

        # Начальное значение (только для metered)
        if self.service["type"] == "metered":
            layout.addWidget(QLabel("Начальное значение:"))
            self.start_edit = QLineEdit(str(self.service.get("start_value", 0)))
            layout.addWidget(self.start_edit)
        else:
            self.start_edit = None

        # Тариф
        layout.addWidget(QLabel("Тариф (руб.):"))
        self.tariff_edit = QLineEdit(str(self.service["tariff"]))
        layout.addWidget(self.tariff_edit)

        # Комиссия (%)
        layout.addWidget(QLabel("Комиссия (%):"))
        fee_percent = int(self.service.get("fee", 0.0) * 100)
        self.fee_edit = QLineEdit(str(fee_percent))
        layout.addWidget(self.fee_edit)

        # Включена
        self.enabled_check = QCheckBox("Включена")
        self.enabled_check.setChecked(self.service.get("enabled", True))
        layout.addWidget(self.enabled_check)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def accept(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Ошибка", "Название услуги не может быть пустым")
            return
        # Если имя изменилось, обновим ключ
        new_key = name.lower().replace(' ', '_')
        if new_key != self.key and new_key in self.services:
            QMessageBox.warning(self, "Ошибка", "Услуга с таким названием уже существует")
            return

        try:
            tariff = float(self.tariff_edit.text().strip())
            if tariff <= 0:
                raise ValueError
        except:
            QMessageBox.warning(self, "Ошибка", "Тариф должен быть положительным числом")
            return

        try:
            fee_percent = float(self.fee_edit.text().strip())
            if fee_percent < 0 or fee_percent > 100:
                raise ValueError
            fee = fee_percent / 100.0
        except:
            QMessageBox.warning(self, "Ошибка", "Комиссия должна быть числом от 0 до 100")
            return

        updated = {
            "name": name,
            "type": self.service["type"],
            "enabled": self.enabled_check.isChecked(),
            "tariff": tariff,
            "fee": fee
        }
        if self.service["type"] == "metered" and self.start_edit:
            try:
                start_val = float(self.start_edit.text().strip())
                if start_val < 0:
                    raise ValueError
                updated["start_value"] = start_val
            except:
                QMessageBox.warning(self, "Ошибка", "Начальное значение должно быть неотрицательным числом")
                return

        # Удаляем старый ключ, если изменился
        if new_key != self.key:
            del self.services[self.key]
        self.services[new_key] = updated
        save_services()
        super().accept()

class SettingsWindow(QDialog):
    def __init__(self, services, refresh_callback=None, parent=None):
        super().__init__(parent)
        self.services = services
        self.refresh_callback = refresh_callback  # для обновления главного окна
        self.setWindowTitle("Настройки")
        self.setWindowIcon(QIcon(resource_path("icon.ico")))
        
        # Основной layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Создаём вкладки
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)

        # Вкладка "Управление услугами"
        self.services_tab = QWidget()
        self.tab_widget.addTab(self.services_tab, "Управление услугами")
        self.setup_services_tab()

        # Вкладка "Тарифы"
        self.tariffs_tab = QWidget()
        self.tab_widget.addTab(self.tariffs_tab, "Изменить тариф")
        self.setup_tariffs_tab()

        # Вкладка "Комиссии"
        self.commissions_tab = QWidget()
        self.tab_widget.addTab(self.commissions_tab, "Изменить комиссию")
        self.setup_commissions_tab()

        # Кнопки диалога
        button_box = QDialogButtonBox()
        save_btn = button_box.addButton("Сохранить", QDialogButtonBox.AcceptRole)
        cancel_btn = button_box.addButton("Отмена", QDialogButtonBox.RejectRole)
        save_btn.clicked.connect(self.save_all)
        cancel_btn.clicked.connect(self.reject)
        save_btn.setToolTip("Сохранить все изменения и закрыть окно настроек.")
        cancel_btn.setToolTip("Отменить изменения и закрыть окно.")
        layout.addWidget(button_box)

        # Заполнение таблиц (они будут обновляться в setup_*)
        self.update_tariffs_table()
        self.update_commissions_table()
        self.update_services_table()

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
        layout = QVBoxLayout(self.services_tab)
        layout.setContentsMargins(10, 10, 10, 10)

        # Таблица услуг
        self.services_table = QTableWidget()
        self.services_table.setColumnCount(5)
        self.services_table.setHorizontalHeaderLabels(
            ["Название", "Тип", "Включена", "Тариф (руб.)", "Комиссия (%)"]
        )
        self.services_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.services_table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.services_table)

        # Кнопки управления
        btn_layout = QHBoxLayout()
        self.btn_add = QPushButton("Добавить")
        self.btn_edit = QPushButton("Редактировать")
        self.btn_delete = QPushButton("Удалить")
        self.btn_toggle = QPushButton("Вкл/Выкл")
        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_edit)
        btn_layout.addWidget(self.btn_delete)
        btn_layout.addWidget(self.btn_toggle)
        layout.addLayout(btn_layout)

        # Подключение сигналов
        self.btn_add.clicked.connect(self.add_service)
        self.btn_edit.clicked.connect(self.edit_service)
        self.btn_delete.clicked.connect(self.delete_service)
        self.btn_toggle.clicked.connect(self.toggle_service)

        self.services_table.itemSelectionChanged.connect(self.update_buttons_state)
        self.update_buttons_state()

    def update_services_table(self):
        """Обновляет таблицу услуг на основе self.services"""
        services = self.services
        self.services_table.setRowCount(len(services))
        for row, (key, service) in enumerate(services.items()):
            name_item = QTableWidgetItem(service.get("name", key))
            name_item.setData(Qt.UserRole, key)  # сохраняем ключ
            self.services_table.setItem(row, 0, name_item)

            type_item = QTableWidgetItem("По счётчику" if service.get("type") == "metered" else "Фиксированная")
            self.services_table.setItem(row, 1, type_item)

            enabled = service.get("enabled", True)
            enabled_item = QTableWidgetItem("Да" if enabled else "Нет")
            self.services_table.setItem(row, 2, enabled_item)

            tariff_item = QTableWidgetItem(f"{service.get('tariff', 0.0):.2f}")
            self.services_table.setItem(row, 3, tariff_item)

            fee_percent = int(service.get("fee", 0.0) * 100)
            fee_item = QTableWidgetItem(f"{fee_percent}")
            self.services_table.setItem(row, 4, fee_item)

        self.services_table.resizeColumnsToContents()
        self.services_table.horizontalHeader().setStretchLastSection(True)

    def update_buttons_state(self):
        """Активирует/деактивирует кнопки редактирования/удаления/переключения при выделении строки"""
        has_selection = len(self.services_table.selectedItems()) > 0
        self.btn_edit.setEnabled(has_selection)
        self.btn_delete.setEnabled(has_selection)
        self.btn_toggle.setEnabled(has_selection)

    def add_service(self):
        dialog = AddServiceDialog(self.services, self)
        if dialog.exec():
            # Сохраняем изменения и обновляем таблицу
            self.update_services_table()
            self.update_tariffs_table()   # обновить тарифы (если появилась новая услуга)
            self.update_commissions_table()
            if self.refresh_callback:
                self.refresh_callback()

    def edit_service(self):
        selected = self.services_table.selectedItems()
        if not selected:
            return
        row = selected[0].row()
        key = self.services_table.item(row, 0).data(Qt.UserRole)
        if not key:
            return
        dialog = EditServiceDialog(self.services, key, self)
        if dialog.exec():
            self.update_services_table()
            self.update_tariffs_table()
            self.update_commissions_table()
            if self.refresh_callback:
                self.refresh_callback()

    def delete_service(self):
        selected = self.services_table.selectedItems()
        if not selected:
            return
        row = selected[0].row()
        key = self.services_table.item(row, 0).data(Qt.UserRole)
        if not key:
            return
        confirm = QMessageBox.question(
            self, "Удаление услуги",
            f"Удалить услугу '{self.services[key].get('name', key)}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            del self.services[key]
            save_services()  # сохраняем в файл
            self.update_services_table()
            self.update_tariffs_table()
            self.update_commissions_table()
            if self.refresh_callback:
                self.refresh_callback()

    def toggle_service(self):
        selected = self.services_table.selectedItems()
        if not selected:
            return
        row = selected[0].row()
        key = self.services_table.item(row, 0).data(Qt.UserRole)
        if not key:
            return
        current = self.services[key].get("enabled", True)
        self.services[key]["enabled"] = not current
        save_services()
        self.update_services_table()
        if self.refresh_callback:
            self.refresh_callback()

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

        self.accept()  # закрываем диалог


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Устанавливаем иконку приложения (глобально)
    from PySide6.QtGui import QIcon
    app.setWindowIcon(QIcon(resource_path("icon.ico")))

    # Загружаем стили (как у вас было)
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
            background-color: #c0c0c0;
        }
        QPushButton:pressed {
            background-color: #a0a0a0;
        }
    """)

    # Проверяем, есть ли услуги
    load_settings()
    if not config.services:
        # Показываем приветственное окно с анимированным фоном
        welcome = WelcomeWindow()
        if welcome.exec() != QDialog.Accepted:
            sys.exit(0)  # пользователь закрыл окно, выходим
        # Теперь показываем мастер добавления услуг
        wizard = FirstRunWizard()
        if wizard.exec() != QDialog.Accepted:
            sys.exit(0)
        # после мастера услуги добавлены

    # Запускаем главное окно
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
