import sys
import os
import traceback
from database import init_db, save_bill
from paths import get_db_path
from stats_window import StatisticsWindow

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
        QStackedWidget,
        QDateEdit,
    )
    from PySide6.QtCore import Qt, QTimer, QDateTime, QLocale, QRect, Signal, QDate, QTranslator, QLibraryInfo
    from PySide6.QtGui import QPixmap, QPainter
    import config
    from communal_calculator import (
        process_services_data,
        normalize_decimal,
        save_tariffs,
        save_fees,
        save_services,
    )
    from file_manager import load_settings
    from config import services  # или import config, затем использовать config.services
    from services import BaseService, MeteredService, FixedService
    import random
except Exception as e:
    print("Import error:", e)
    sys.exit(1)


# Загружаем настройки из JSON (заполнит config.services)
load_settings()

def resource_path(relative_path):
    """Получить абсолютный путь к ресурсу, работает для разработки, PyInstaller и cx_Freeze."""
    if getattr(sys, 'frozen', False):
        # cx_Freeze и PyInstaller: исполняемый файл
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


def install_translators(app):
    """Загружает .qm по настройке config.language.

    'system' → по локали системы; 'ru' → ru_RU; 'en' → en_US.
    Файлы лежат в translations/app_<lang>.qm.
    Отсутствующий файл — это не ошибка: молча оставляем русский.
    """
    translator = QTranslator(app)
    lang = getattr(config, 'language', 'system')
    if lang == 'system':
        sys_lang = QLocale.system().name()  # e.g. 'ru_RU', 'en_US'
        target = 'ru' if sys_lang.startswith('ru') else 'en' if sys_lang.startswith('en') else 'ru'
    else:
        target = lang
    qm_path = resource_path(f"translations/app_{target}.qm")
    if os.path.exists(qm_path):
        translator.load(qm_path)
        app.installTranslator(translator)
    # Хранить ссылку, чтобы не собрал GC:
    app._translator = translator


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
        self.setWindowTitle(self.tr("Добро пожаловать!"))
        self.setFixedSize(500, 400)
        self.setWindowFlags(Qt.FramelessWindowHint)  # убираем рамку (опционально)
        self.setModal(True)
        self.setWindowIcon(QIcon(resource_path("icon.ico")))

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
        self.title_label = QLabel(self.tr("<h1>Добро пожаловать в Калькулятор коммуналки!</h1>"), self)
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
        self.start_button = QPushButton(self.tr("Начать"), self)
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

        # Кнопка помощи
        self.help_button = QPushButton(self.tr("Помощь"), self)
        self.help_button.setFixedSize(200, 40)
        self.help_button.setStyleSheet("""
            QPushButton {
                font-size: 14px;
                background-color: #3498db;
                color: white;
                border-radius: 10px;
                border: none;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #1c6ea4;
            }
        """)
        self.help_button.move((self.width() - self.help_button.width()) // 2,
                            (self.height() - self.start_button.height()) // 2 + 70)
        self.help_button.clicked.connect(self.open_help)

    def on_start(self):
        self.accept()  # закрываем окно с кодом Accepted

    def resizeEvent(self, event):
        # При изменении размера (хотя у нас фиксированный размер) перецентрируем кнопку
        self.start_button.move((self.width() - self.start_button.width()) // 2,
                               (self.height() - self.start_button.height()) // 2)
        super().resizeEvent(event)

    def open_help(self):
        import webbrowser
        import os
        from PySide6.QtWidgets import QMessageBox
        help_path = resource_path("help.html")
        if os.path.exists(help_path):
            webbrowser.open(help_path)
        else:
            QMessageBox.warning(self, self.tr("Ошибка"), self.tr("Файл справки не найден."))

class FirstRunWizard(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Настройка услуг"))
        self.setModal(True)
        self.setMinimumSize(600, 500)
        self.setWindowIcon(QIcon(resource_path("icon.ico")))

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
        label = QLabel(self.tr(
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
        ))
        label.setWordWrap(True)
        panel_layout.addWidget(label)

        # Список добавленных услуг
        panel_layout.addWidget(QLabel(self.tr("Добавленные услуги:")))
        self.services_list = QListWidget()
        panel_layout.addWidget(self.services_list)

        # Кнопки
        btn_layout = QHBoxLayout()
        self.btn_add = QPushButton(self.tr("Добавить услугу"))
        self.btn_help = QPushButton(self.tr("Помощь"))
        self.btn_finish = QPushButton(self.tr("✅ Готово"))
        self.btn_finish.setEnabled(False)

        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_help)
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
        self.btn_help.setStyleSheet(button_style)
        self.btn_finish.setStyleSheet(button_style)
        
        self.btn_add.setToolTip(self.tr("Нажмите, чтобы добавить новую услугу (газ, свет, вода, интернет и т.д.)."))
        self.btn_finish.setToolTip(self.tr("Завершить настройку и перейти к главному окну (можно добавить услуги позже через меню 'Настройки')."))
        self.btn_help.setToolTip(self.tr("Нажмите, чтобы получить подробную справку и ознакомиться с руководством пользователя"))

        self.btn_add.clicked.connect(self.add_service)
        self.btn_help.clicked.connect(self.open_help)
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

    def open_help(self):
        import webbrowser
        import os
        from PySide6.QtWidgets import QMessageBox
        help_path = resource_path("help.html")
        if os.path.exists(help_path):
            webbrowser.open(help_path)
        else:
            QMessageBox.warning(self, self.tr("Ошибка"), self.tr("Файл справки не найден."))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(self.tr("Калькулятор коммуналки"))
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
                
        # Кнопки
        self.settings_button = QPushButton(self.tr("Настройки"))
        self.settings_button.clicked.connect(self.open_settings)

        self.help_button = QPushButton(self.tr("Помощь"))
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

        # Создаём QStackedWidget, то есть нижняя часть панели с дашбордом
        self.stacked = QStackedWidget()
        self.stacked.setStyleSheet("background: transparent;")

        # Дашборд
        self.dashboard = DashboardWidget()
        self.stacked.addWidget(self.dashboard)

        # Переключение: кнопка на дашборде переводит на ввод
        self.dashboard.go_to_input.connect(lambda: self.stacked.setCurrentIndex(1))

        # Проверяем приближающиеся поверки
        self.check_verifications()

        # По умолчанию показываем дашборд
        self.stacked.setCurrentIndex(0)
        
        # Форма ввода (старый MainWindow, но теперь как виджет)
        self.input_panel = InputPanel()
        #Добавляем виджет ввода показаний (self.input_panel) в стек, то есть контейнер (self.stacked) (вторая страница, индекс 1)
        self.stacked.addWidget(self.input_panel)
        self.input_panel.go_back.connect(
            lambda: (
                self.dashboard.update_data(),   # обновляем данные дашборда
                self.stacked.setCurrentIndex(0) # переключаемся на дашборд (первая траница, индекс 0)
            )
        )

        self.dashboard.open_stats.connect(self.open_statistics)

        # Добавляем стек в панель
        panel_layout.addWidget(self.stacked)

        # Размещаем панель на фоне
        bg_layout = QVBoxLayout(self.animated_bg)
        bg_layout.setContentsMargins(50, 50, 50, 50)   # отступы со всех сторон по 50 пикселей
        bg_layout.addWidget(self.panel)

        # Указываем, что panel не растягивается, а stacked занимает всё свободное место
        bg_layout.setStretchFactor(self.panel, 0)
        bg_layout.setStretchFactor(self.stacked, 1)

        self.adjustSize()  # Размеры окна автоматически настраиваются под его содержание
        self.setMinimumSize(500, 400)  # Задаем минимальные размеры окна

    def replace_meter(self, key):
        dialog = MeterReplacementDialog(key, self)
        dialog.exec()

    def update_datetime(self):
        now = QDateTime.currentDateTime()
        locale = QLocale(QLocale.Russian)
        # Формат: "Понедельник, 24 мая 2026 г. 15:30:45"
        # Можно изменить под свой вкус
        datetime_str = locale.toString(now, self.tr("dddd, d MMMM yyyy г. HH:mm:ss"))
        self.datetime_label.setText(datetime_str)

    def open_settings(self):
        dialog = SettingsWindow(config.services, refresh_callback=None, parent=self)
        if dialog.exec() == QDialog.Accepted:
            load_settings() # ← перезагружаем объекты из БД
            self.dashboard.update_data()#Обновление дашборда
            if hasattr(self, 'input_panel'):
                self.input_panel.rebuild_services_ui() # обновляем форму ввода

    def open_help(self):
        import webbrowser
        import os
        from PySide6.QtWidgets import QMessageBox

        # Путь к файлу help.html (рядом с программой или в ресурсах)
        help_path = resource_path("help.html")
        if os.path.exists(help_path):
            webbrowser.open(help_path)
        else:
            QMessageBox.warning(self, self.tr("Ошибка"), self.tr("Файл справки (help.html) не найден."))

    def check_verifications(self):
        from datetime import datetime, timedelta

        notifications = []
        today = datetime.now().date()

        for key, service in config.services.items():
            # Проверяем только услуги по счётчику
            if not isinstance(service, MeteredService):
                continue

            next_date_str = service.get('next_verification_date')
            if not next_date_str:
                continue

            try:
                next_date = datetime.strptime(next_date_str, "%Y-%m-%d").date()
                days_left = (next_date - today).days
                if 0 <= days_left <= 30:
                    notifications.append(self.tr("• {name} — {days} дн.").format(name=service['name'], days=days_left))
            except:
                continue

        if notifications:
            msg = self.tr("⚠️ Внимание! Приближается поверка счётчиков:\n\n") + "\n".join(notifications)
            QMessageBox.information(self, self.tr("Напоминание о поверке"), msg)

    def open_statistics(self):
        dialog = StatisticsWindow(self)
        dialog.exec()
    
    

class DashboardWidget(QWidget):
    go_to_input = Signal()
    open_stats = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(self)

        # Карточки с услугами
        self.cards_layout = QGridLayout()
        layout.addLayout(self.cards_layout)

        # График (matplotlib)
        try:
            from matplotlib.figure import Figure
            from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
            self.figure = Figure(figsize=(7, 4), dpi=100)
            self.canvas = FigureCanvas(self.figure)
            self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            layout.addWidget(self.canvas)
        except ImportError:
            self.canvas = None
            layout.addWidget(QLabel(self.tr("Для графиков установите matplotlib")))

        # Кнопка перехода к вводу
        enter_btn = QPushButton(self.tr("📝 Ввести показания"))

        # Кнопка статистики
        stat_btn = QPushButton(self.tr("Статистика"))

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
        #Применяем стили для кнопок
        enter_btn.setStyleSheet(button_style)
        stat_btn.setStyleSheet(button_style)
        enter_btn.clicked.connect(self.go_to_input.emit)
        stat_btn.clicked.connect(self.open_stats.emit)
        
        # Горизонтальный layout для кнопок
        button_layout = QHBoxLayout()

        # Кнопка "Ввести показания" (слева)
        button_layout.addWidget(enter_btn)

        # Растяжка, которая раздвигает кнопки
        button_layout.addStretch()

        # Кнопка "Статистика" (справа)
        button_layout.addWidget(stat_btn)

        # Добавляем этот layout в основной layout
        layout.addLayout(button_layout)

        self.update_data()

    def update_data(self):
        self.update_cards()
        self.update_chart()

    def update_cards(self):
        # Очищаем старые карточки
        for i in reversed(range(self.cards_layout.count())):
            widget = self.cards_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()

        # Заголовки
        self.cards_layout.addWidget(QLabel(self.tr("<b>Услуга</b>")), 0, 0)
        self.cards_layout.addWidget(QLabel(self.tr("<b>Показания</b>")), 0, 1)
        self.cards_layout.addWidget(QLabel(self.tr("<b>Тариф</b>")), 0, 2)

        row = 1
        for key, service in config.services.items():
            if not service.get("enabled", True):
                continue
            card = service.render_dashboard_card()
            self.cards_layout.addWidget(card["name_label"], row, 0)
            self.cards_layout.addWidget(card["reading_label"], row, 1)
            self.cards_layout.addWidget(card["tariff_label"], row, 2)
            row += 1

    def update_chart(self):
        if self.canvas is None:
            return
        import sqlite3
        import pandas as pd
        conn = sqlite3.connect(get_db_path())
        query = """
            SELECT strftime('%m', date) as month, total_with_fee
            FROM bills
            WHERE strftime('%Y', date) = strftime('%Y', 'now')
            ORDER BY date
        """
        df = pd.read_sql_query(query, conn)
        conn.close()

        self.figure.clear()
        ax = self.figure.add_subplot(111)
        if not df.empty:
            ax.plot(df['month'], df['total_with_fee'], marker='o', linestyle='-', color='#2E86C1')
            ax.set_title(self.tr("Расходы по месяцам (текущий год)"))
            ax.set_xlabel(self.tr("Месяц"))
            ax.set_ylabel(self.tr("Сумма, руб."))
            ax.grid(True, linestyle='--', alpha=0.6)
        else:
            ax.text(0.5, 0.5, self.tr("Нет данных за текущий год"), ha='center', va='center')
        self.canvas.draw()


class InputPanel(QWidget):
    go_back = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")
        #self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout = QVBoxLayout(self)

        # Кнопки
        self.settings_button = QPushButton(self.tr("Настройки"))
        self.settings_button.clicked.connect(self.open_settings)

        self.help_button = QPushButton(self.tr("Помощь"))
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
        self.grid_layout.setColumnStretch(3, 0)   # для кнопки действия
        self.grid_layout.setColumnStretch(4, 0)   # для кнопки реквизитов
        layout.addWidget(self.services_container)

        # Кнопка "Рассчитать"
        calc_button = QPushButton(self.tr("Рассчитать"))
        calc_button.clicked.connect(self.calculate)

        #Кнопка "Назад"
        back_button = QPushButton(self.tr("Назад"))
        back_button.clicked.connect(self.go_back.emit)
        
        #Стили для кнопок "Рассчитать" и "Назад"
        Calc_and_back_button_style = """
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
        """
        #Задаем стили кнопкам "Рассчитать" и "Назад"
        calc_button.setStyleSheet(Calc_and_back_button_style)
        back_button.setStyleSheet(Calc_and_back_button_style)

        # Горизонтальная упаковка кнопок "Рассчитать" и "Назад"
        Calc_and_back_button_layout = QHBoxLayout()
        Calc_and_back_button_layout.addWidget(calc_button)
        Calc_and_back_button_layout.addStretch()
        Calc_and_back_button_layout.addWidget(back_button)

        # Добавляем этот layout в основной layout вместо отдельной кнопки
        layout.addLayout(Calc_and_back_button_layout)
        
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
        datetime_str = locale.toString(now, self.tr("dddd, d MMMM yyyy г. HH:mm:ss"))
        self.datetime_label.setText(datetime_str)

    def open_settings(self):
        dialog = SettingsWindow(config.services, refresh_callback=self.rebuild_services_ui, parent=self)
        if dialog.exec() == QDialog.Accepted:
            self.rebuild_services_ui()

    def open_help(self):
        import webbrowser
        import os
        from PySide6.QtWidgets import QMessageBox

        # Путь к файлу help.html (рядом с программой или в ресурсах)
        help_path = resource_path("help.html")
        if os.path.exists(help_path):
            webbrowser.open(help_path)
        else:
            QMessageBox.warning(self, self.tr("Ошибка"), self.tr("Файл справки (help.html) не найден."))

    def rebuild_services_ui(self):
        # Очищаем все строки сетки, кроме первой(с заголовками)
        for i in reversed(range(self.grid_layout.count())):
            self.grid_layout.itemAt(i).widget().deleteLater()
        self.entries.clear()
        self.checkboxes.clear()

        # Заголовки (row 0)
        header_name = QLabel(self.tr("<b>Ресурс</b>"))
        header_name.setAlignment(
            Qt.AlignLeft | Qt.AlignVCenter
        )  # Устанавливаем выравнивание по левому краю горизонтально и по центру вертикально
        self.grid_layout.addWidget(header_name, 0, 0)
        header_value = QLabel(self.tr("<b>Показания</b>"))
        header_value.setAlignment(
            Qt.AlignCenter | Qt.AlignVCenter
        )  # Устанавливаем выравнивание по центру горизонтально и вертикально
        self.grid_layout.addWidget(header_value, 0, 1)
        header_comm = QLabel(self.tr("<b>Комиссия</b>"))
        header_comm.setAlignment(
            Qt.AlignCenter | Qt.AlignVCenter
        )  # Устанавливаем выравнивание по центру горизонтально и вертикально
        self.grid_layout.addWidget(header_comm, 0, 2)
        header_actions = QLabel(self.tr("<b>Действия</b>"))
        self.grid_layout.addWidget(header_actions, 0, 3)
        # Устанавливаем выравнивание по центру горизонтально и вертикально
        header_info = QLabel(self.tr("<b>Информация</b>"))
        self.grid_layout.addWidget(header_info, 0, 4)

        # Настройка растяжения колонок
        self.grid_layout.setColumnStretch(0, 1)  # первая колонка растягивается
        self.grid_layout.setColumnStretch(1, 0)  # вторая – фиксированной ширины
        self.grid_layout.setColumnStretch(2, 0)  # третья – фиксированной ширины
        self.grid_layout.setColumnStretch(3, 0)  # для кнопки действия
        self.grid_layout.setColumnStretch(4, 0)  # для кнопки реквизитов

        row = 1
        # Проходим по всем услугам из config
        for key, service in config.services.items():
            if not service.get("enabled", True):
                continue
            widgets = service.render_input_row(self)

            self.grid_layout.addWidget(widgets["name_label"], row, 0)
            self.grid_layout.addWidget(widgets["value_widget"], row, 1)
            self.grid_layout.addWidget(
                widgets["commission_cb"], row, 2, alignment=Qt.AlignCenter)
            self.grid_layout.addWidget(
                widgets["action_widget"], row, 3, alignment=Qt.AlignCenter)
            self.grid_layout.addWidget(
                widgets["provider_btn"], row, 4, alignment=Qt.AlignCenter)

            if widgets["entry"] is not None:
                self.entries[key] = widgets["entry"]
            self.checkboxes[key] = widgets["checkbox"]

            row += 1

        # Добавляем растягивающуюся пустую строку
        self.grid_layout.setRowStretch(row, 1)
        # Для всех предыдущих строк (с услугами) устанавливаем растяжение 0
        for r in range(1, row):
            self.grid_layout.setRowStretch(r, 0)
        self.adjustSize()  # Размеры окна автоматически настраиваются под его содержание
        #self.setFixedHeight(self.sizeHint().height())
        self.setMinimumSize(500, 400)  # Задаем минимальные размеры окна

    def replace_meter(self, key):
        dialog = MeterReplacementDialog(key, self)
        dialog.exec()

    def show_provider_info(self, service_key):
        from database import get_provider, set_service_provider
        from config import services
        from file_manager import load_settings

        # --- ПРИНУДИТЕЛЬНАЯ ПЕРЕЗАГРУЗКА ---
        load_settings()   # всегда загружаем свежие данные из БД

        service = services.get(service_key)

        if not service:
            QMessageBox.warning(self, self.tr("Ошибка"), self.tr("Услуга не найдена"))
            return

        provider_id = service.get('provider_id')
        if provider_id:
            provider = get_provider(provider_id)
            if provider:
                dialog = ProviderInfoDialog(provider, self)
                dialog.exec()
                return
            else:
                # Если provider_id есть, но данных нет – сбрасываем
                set_service_provider(service_key, None)
                service['provider_id'] = None

        # Если реквизитов нет – открываем диалог создания
        dialog = EditProviderDialog(service_key, None, self)
        if dialog.exec():
            # После сохранения обновляем интерфейс (чтобы отобразилась кнопка или изменилось состояние)
            load_settings()   # <-- перезагружаем услуги из БД
            self.rebuild_services_ui()
            # Также обновим дашборд, если он открыт
            if self.parent() and hasattr(self.parent(), 'dashboard'):
                self.parent().dashboard.update_data()
    
    def _counter_menu(self, service_key):
        """Возвращает список действий (текст, обработчик) для текущего meter_state."""
        import config

        def placeholder(message=None):
            if message is None:
                message = self.tr("Будет доступно в следующей версии")
            def _show():
                QMessageBox.information(self, self.tr("Информация"), message)
            return _show

        def continue_work():
            service = config.services.get(service_key)
            if service is not None:
                service.meter_state = 'active'
                save_services()
            self.rebuild_services_ui()
            if self.parent() and hasattr(self.parent(), 'dashboard'):
                self.parent().dashboard.update_data()

        service = config.services.get(service_key)
        state = (service.meter_state if service is not None and service.type == 'metered' else None) or 'active'

        if state == 'active':
            return [
                (self.tr("🔁 Замена счётчика"), lambda: self.replace_meter(service_key)),
                (self.tr("🔍 Поверка счётчика"), lambda: self.show_verification_dialog(service_key)),
                (self.tr("🔧 Ремонт счётчика"), lambda: self.show_verification_dialog(service_key, default_event_type='on_repair')),
                (self.tr("⛔ Снять счётчик"), lambda: self.remove_meter(service_key)),
                (self.tr("❌ Отмена"), None),
            ]
        if state == 'on_verification':
            return [
                (self.tr("✅ Завершить поверку"), lambda: self.show_verification_dialog(service_key)),
                (self.tr("↩️ Отменить поверку"), placeholder()),
                (self.tr("❌ Отмена"), None),
            ]
        if state == 'on_repair':
            return [
                (self.tr("✅ Завершить ремонт"), lambda: self.show_verification_dialog(service_key, default_event_type='on_repair')),
                (self.tr("↩️ Отменить ремонт"), placeholder()),
                (self.tr("❌ Отмена"), None),
            ]
        if state == 'removed':
            return [
                (self.tr("🆕 Установить новый счётчик"), lambda: self.install_meter(service_key)),
                (self.tr("❌ Отмена"), None),
            ]
        if state == 'replaced':
            return [
                (self.tr("✅ Продолжить работу"), continue_work),
                (self.tr("❌ Отмена"), None),
            ]
        return [
            (self.tr("🔁 Замена счётчика"), lambda: self.replace_meter(service_key)),
            (self.tr("🔍 Поверка счётчика"), lambda: self.show_verification_dialog(service_key)),
            (self.tr("❌ Отмена"), None),
        ]

    def show_counter_actions(self, service_key):
        """Открывает диалог выбора действия со счётчиком (зависит от meter_state)."""
        dialog = QDialog(self)
        dialog.setWindowTitle(self.tr("Действия со счётчиком"))
        dialog.setMinimumWidth(300)
        dialog.setStyleSheet("background-color: white;")
        layout = QVBoxLayout(dialog)

        label = QLabel(self.tr("Выберите действие для счётчика:"))
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)

        BUTTON_STYLE = ("""
                    QPushButton {
                        background-color: #e0e0e0;
                        border: 1px solid #aaa;
                        border-radius: 4px;
                        padding: 4px;
                    }
                    QPushButton:hover {
                        background-color: #c0c0c0;
                    }
                    QPushButton:pressed {
                        background-color: #a0a0a0;
                    }
                """)

        for text, handler in self._counter_menu(service_key):
            btn = QPushButton(text)
            btn.setStyleSheet(BUTTON_STYLE)
            if handler is None:
                btn.clicked.connect(dialog.reject)
            else:
                btn.clicked.connect(lambda checked=False, h=handler: (dialog.accept(), h()))
            layout.addWidget(btn)

        dialog.exec()

    def show_verification_dialog(self, service_key, default_event_type=None):
        from database import get_active_verification, get_service_id_by_key
        from file_manager import load_settings

        service_id = get_service_id_by_key(service_key)
        if service_id is None:
            QMessageBox.warning(self, self.tr("Ошибка"), self.tr("Услуга не найдена"))
            return

        active = get_active_verification(service_id)
        if active:
            # Если есть активная поверка – открываем редактирование
            dialog = VerificationDialog(service_key, active['id'], self, default_event_type=default_event_type)
        else:
            dialog = VerificationDialog(service_key, None, self, default_event_type=default_event_type)

        if dialog.exec():
            load_settings()
            self.rebuild_services_ui()
            if self.parent() and hasattr(self.parent(), 'dashboard'):
                self.parent().dashboard.update_data()

    def remove_meter(self, service_key):
        """Снять счётчик: официально демонтируем (расчёт по тарифу)."""
        dialog = RemoveMeterDialog(service_key, self)
        if dialog.exec() == QDialog.Accepted:
            self.rebuild_services_ui()
            if self.parent() and hasattr(self.parent(), 'dashboard'):
                self.parent().dashboard.update_data()

    def install_meter(self, service_key):
        """Установить новый счётчик: возвращаем услугу в активное состояние."""
        dialog = InstallMeterDialog(service_key, self)
        if dialog.exec() == QDialog.Accepted:
            self.rebuild_services_ui()
            if self.parent() and hasattr(self.parent(), 'dashboard'):
                self.parent().dashboard.update_data()


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
            used_replacement_ids,
            verification_ids_used,
            norm_verification_ids,
        ) = result
        # Теперь нужно показать окно с результатами. Создадим новый класс ResultWindow.
        self.result_window = ResultWindow(
            results_data, current_readings, costs, total_amount, total_fee, total_sum_with_fee,
            config.services, save_services, used_replacement_ids,
            verification_ids_used, norm_verification_ids
        )
        self.result_window.show()

class ResultWindow(QDialog):
    def __init__(self, results_data, current_readings, costs, 
                 total_amount, total_fee, total_sum_with_fee, 
                 services, save_services_callback, used_replacement_ids,
                  verification_ids_used, norm_verification_ids
                 ):
        super().__init__()
        self.setWindowTitle(self.tr("Результаты расчёта"))
        self.setFixedWidth(850)  # фиксируем ширину окна
        self.results_data = results_data
        self.current_readings = current_readings
        self.costs = costs
        self.total_amount = total_amount
        self.total_fee = total_fee
        self.total_sum_with_fee = total_sum_with_fee
        self.services = services
        self.save_services_callback = save_services_callback
        self.used_replacement_ids = used_replacement_ids
        self.verification_ids_used = verification_ids_used
        self.norm_verification_ids = norm_verification_ids
        self.setWindowIcon(QIcon(resource_path("icon.ico")))

        layout = QVBoxLayout(self)

        # Создадим таблицу (QTableWidget) и заполним её данными
        self.table = QTableWidget()  # Создаем виджет таблицы
        self.table.setColumnCount(8)  # Задаем количество столбцов таблицы
        self.table.setHorizontalHeaderLabels(
            [
                self.tr("Ресурс"),
                self.tr("Начало"),
                self.tr("Конец"),
                self.tr("Расход"),
                self.tr("Тариф"),
                self.tr("Сумма"),
                self.tr("Комиссия"),
                self.tr("Итого"),
            ]
        )
        self.table.setRowCount(len(results_data))
        for i, data in enumerate(results_data):
            self.table.setItem(i, 0, QTableWidgetItem(data["Name"]))
            self.table.setItem(i, 1, QTableWidgetItem(str(data["Start value"])))
            self.table.setItem(i, 2, QTableWidgetItem(str(data["End value"])))
            self.table.setItem(i, 3, QTableWidgetItem(str(data["Consumption"])))
            self.table.setItem(i, 4, QTableWidgetItem(f"{data['Tariff']:.2f}" if data['Tariff'] is not None else ""))
            self.table.setItem(i, 5, QTableWidgetItem(f"{data['Amount']:.2f}" if data['Amount'] is not None else ""))
            self.table.setItem(i, 6, QTableWidgetItem(f"{data['Fee']:.2f}" if data['Fee'] is not None else ""))
            self.table.setItem(i, 7, QTableWidgetItem(f"{data['Total']:.2f}" if data['Total'] is not None else ""))
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

        total_amount_name = QLabel(self.tr("<b>Итого без комиссии: {t}</b>").format(t=f"{total_amount:.2f}"))
        total_amount_name.setAlignment(
            Qt.AlignLeft
        )  # Устанавливаем выравнивание по левому краю
        self.total_grid_layout.addWidget(
            total_amount_name, 0, 0
        )  # Разместили header_name в 1 столбце 1 строки сетки

        total_fee_name = QLabel(self.tr("<b>Итого комиссия: {t}</b>").format(t=f"{total_fee:.2f}"))
        total_fee_name.setAlignment(
            Qt.AlignLeft
        )  # Устанавливаем выравнивание по левому краю
        self.total_grid_layout.addWidget(
            total_fee_name, 0, 1
        )  # Разместили header_name в 2 столбце 1 строки сетки

        total_sum_with_fee_name = QLabel(
            self.tr("<b>Всего с комиссией: {t}</b>").format(t=f"{total_sum_with_fee:.2f}")
        )
        total_sum_with_fee_name.setAlignment(
            Qt.AlignLeft
        )  # Устанавливаем выравнивание по левому краю
        self.total_grid_layout.addWidget(
            total_sum_with_fee_name, 0, 2
        )  # Разместили header_name в 3 столбце 1 строки сетки

        # Кнопки
        button_layout = QHBoxLayout()
        self.save_btn = QPushButton(self.tr("✅ Сохранить и закрыть"))
        self.close_btn = QPushButton(self.tr("❌ Закрыть без сохранения"))
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
        from database import save_bill, mark_replacements_paid, get_verification_by_id, update_verification
        from file_manager import save_settings
        from datetime import datetime
        import math
        from decimal import Decimal

        # Фильтруем результаты: исключаем записи по счётчику без Start value
        filtered_results = []
        for data in self.results_data:
            service_key = data.get("Key")
            service = self.services.get(service_key)
            if not service:
                # Если услуга не найдена — пропускаем
                continue
            # Если услуга фиксированная — всегда добавляем
            if isinstance(service, FixedService):
                filtered_results.append(data)
                continue
            # Для услуг по счётчику проверяем Start value
            start_val = data.get('Start value')
            if start_val is not None and isinstance(start_val, (int, float, Decimal)):
                filtered_results.append(data)

        # Подготовка данных для БД
        def to_float(value):
            if value is None or value == "—" or value == "-":
                return None
            return float(value)

        # Формируем детали только для отфильтрованных записей
        details = []
        for data in filtered_results:
            details.append({
                'service_key': data.get("Key"),
                'service_name': data["Name"],
                'start_reading': to_float(data.get("Start value")),
                'end_reading': to_float(data.get("End value")),
                'consumption': to_float(data.get("Consumption")),
                'tariff': float(data["Tariff"]) if data["Tariff"] is not None else 0,
                'amount': round(float(data["Amount"]), 2),
                'fee': round(float(data["Fee"]), 2),
                'total': round(float(data["Total"]), 2)
            })

        bill_data = {
            'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'total_amount': float(self.total_amount),
            'total_fee': float(self.total_fee),
            'total_with_fee': float(self.total_sum_with_fee),
            'details': details,
            'used_replacements': self.used_replacement_ids   # <-- исправлено
        }
        bill_id = save_bill(bill_data)

        if self.used_replacement_ids:
            mark_replacements_paid(self.used_replacement_ids, bill_id)

        # Обновляем is_consumption_paid для использованных поверок
        for vid in self.verification_ids_used:
            verif = get_verification_by_id(vid)
            if verif:
                verif['is_consumption_paid'] = 1
                update_verification(vid, verif)

        # Обновляем is_norm_paid для нормативов
        for vid in self.norm_verification_ids:
            verif = get_verification_by_id(vid)
            if verif:
                verif['is_norm_paid'] = 1
                update_verification(vid, verif)

        # Обновляем начальные значения
        for key, reading in self.current_readings.items():
            if key in self.services and isinstance(self.services[key], MeteredService):
                self.services[key]["start_value"] = reading

        # Очищаем использованные замены из self.services
        for key, service in self.services.items():
            if "replacements" in service:
                service["replacements"] = [
                    rep for rep in service["replacements"]
                    if rep.get('id') not in self.used_replacement_ids
                ]
        # Сохраняем услуги в SQLite
        save_settings()

        # Показываем сообщение
        msg = self.tr("Показания сохранены!\n\nНовые начальные значения для следующего месяца:\n")
        for key, reading in self.current_readings.items():
            service_name = self.services[key].get("name", key)
            msg += f"{service_name}: {reading}\n"
        QMessageBox.information(self, self.tr("Готово"), msg)

        self.accept()

    def _prepare_bill_data(self):
        """Подготавливает словарь для сохранения в БД."""
        from datetime import datetime
        details = []
        used_replacements = []
        for i, data in enumerate(self.results_data):
            service_key = list(self.services.keys())[i]  # нужно сопоставить по порядку; лучше передавать key
            # Но в results_data нет ключа, поэтому лучше модифицировать calculate, чтобы results_data содержал ключ.
            # Пока сделаем костыль: сопоставляем по имени (не надёжно).
            # Чтобы избежать этого, нужно в results_data добавить поле "key". Это потребует изменений в process_services_data.
            # Для начала создадим словарь service_keys по имени.
        return {
            'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'total_amount': self.total_amount,
            'total_fee': self.total_fee,
            'total_sum_with_fee': self.total_sum_with_fee,  # в save_and_close используется total_sum_with_fee
            'details': details,
            'used_replacements': used_replacements
        }

class AddServiceDialog(QDialog):
    def __init__(self, services, parent=None):
        super().__init__(parent)
        self.services = services
        self.setWindowTitle(self.tr("Добавление услуги"))
        self.setMinimumWidth(400)
        layout = QVBoxLayout(self)

        # Название услуги
        layout.addWidget(QLabel(self.tr("Название услуги:")))
        self.name_edit = QLineEdit()
        self.name_edit.setToolTip(self.tr("Введите название услуги, которую вы хотите добавить (например, 'Газ', 'Электричество')."))
        layout.addWidget(self.name_edit)

        # Тип услуги
        layout.addWidget(QLabel(self.tr("Тип:")))
        self.type_combo = QComboBox()
        self.type_combo.addItems([self.tr("По счётчику"), self.tr("Фиксированная")])
        self.type_combo.setToolTip(self.tr(
            "Выберите тип услуги:\n"
            "- По счётчику: если вы снимаете показания счётчика для расчёта (газ, свет, вода).\n"
            "- Фиксированная: если платёж не зависит от потребления (интернет, мусор, капремонт)."
        ))
        layout.addWidget(self.type_combo)

        # Начальное значение (для по счётчику)
        self.start_label = QLabel(self.tr("Начальное значение:"))
        self.start_edit = QLineEdit()
        self.start_edit.setToolTip(self.tr(
            "Введите показания счётчика, которые были у вас в прошлом месяце.\n"
            "Для новой услуги – начальное значение обычно равно 0."
        ))
        layout.addWidget(self.start_label)
        layout.addWidget(self.start_edit)

        # Тариф
        layout.addWidget(QLabel(self.tr("Тариф (руб.):")))
        self.tariff_edit = QLineEdit()
        self.tariff_edit.setToolTip(self.tr(
            "Введите стоимость за единицу потребления услуги (например, за 1 кВт·ч электроэнергии)."
        ))
        layout.addWidget(self.tariff_edit)

        # Включена ли услуга
        self.enabled_check = QCheckBox(self.tr("Включена"))
        self.enabled_check.setChecked(True)
        self.enabled_check.setToolTip(self.tr("Если галочка снята, услуга не будет отображаться в главном окне и не будет учитываться в расчётах."))
        layout.addWidget(self.enabled_check)

        # Кнопки
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        buttons.setStyleSheet("""
                    QPushButton {
                        background-color: #e0e0e0;
                        border: 1px solid #aaa;
                        border-radius: 4px;
                        padding: 4px;
                    }
                    QPushButton:hover {
                        background-color: #c0c0c0;
                    }
                    QPushButton:pressed {
                        background-color: #a0a0a0;
                    }
                """)
        #Меняем название кнопки Cancel
        cancel_btn = buttons.button(QDialogButtonBox.Cancel)
        if cancel_btn:
            cancel_btn.setText(self.tr("Отмена"))
        layout.addWidget(buttons)

        # Логика: при изменении типа скрывать/показывать поле начального значения
        self.type_combo.currentIndexChanged.connect(self.update_visibility)
        self.update_visibility()

    def update_visibility(self):
        is_metered = self.type_combo.currentText() == self.tr("По счётчику")
        self.start_label.setVisible(is_metered)
        self.start_edit.setVisible(is_metered)

    def accept(self):
        # Валидация и добавление услуги
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, self.tr("Ошибка"), self.tr("Введите название услуги"))
            return
        key = name.lower().replace(' ', '_')
        if key in self.services:
            QMessageBox.warning(self, self.tr("Ошибка"), self.tr("Услуга с таким названием уже существует"))
            return

        service_type = "metered" if self.type_combo.currentText() == self.tr("По счётчику") else "fixed"
        try:
            tariff = float(normalize_decimal(self.tariff_edit.text().strip()))
            if tariff <= 0:
                raise ValueError
        except:
            QMessageBox.warning(self, self.tr("Ошибка"), self.tr("Тариф должен быть положительным числом"))
            return

        new_service = {
            "name": name,
            "type": service_type,
            "enabled": self.enabled_check.isChecked(),
            "tariff": tariff,
            # "fee" отсутствует – будет добавлен позже при настройке комиссии через чекбокс
        }
        if service_type == "metered":
            try:
                start_val = float(normalize_decimal(self.start_edit.text().strip()))
                if start_val < 0:
                    raise ValueError
                new_service["start_value"] = start_val
            except:
                QMessageBox.warning(self, self.tr("Ошибка"), self.tr("Начальное значение должно быть неотрицательным числом"))
                return

        self.services[key] = BaseService.from_dict(new_service, key=key)
        save_services()
        super().accept()

class EditServiceDialog(QDialog):
    def __init__(self, services, key, parent=None):
        super().__init__(parent)
        self.services = services
        self.key = key
        self.service = services[key]
        self.setWindowTitle(self.tr("Редактирование услуги: {name}").format(name=self.service['name']))
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)

        # Название
        layout.addWidget(QLabel(self.tr("Название услуги:")))
        self.name_edit = QLineEdit(self.service["name"])
        layout.addWidget(self.name_edit)

        # Тип (нельзя изменить, только показать)
        layout.addWidget(QLabel(self.tr("Тип:")))
        type_text = self.tr("По счётчику") if isinstance(self.service, MeteredService) else self.tr("Фиксированная")
        type_label = QLabel(type_text)
        layout.addWidget(type_label)

        # Начальное значение (только для metered)
        if isinstance(self.service, MeteredService):
            layout.addWidget(QLabel(self.tr("Начальное значение:")))
            self.start_edit = QLineEdit(str(self.service.get("start_value", 0)))
            layout.addWidget(self.start_edit)
        else:
            self.start_edit = None

        # Тариф
        layout.addWidget(QLabel(self.tr("Тариф (руб.):")))
        self.tariff_edit = QLineEdit(str(self.service["tariff"]))
        layout.addWidget(self.tariff_edit)

        # Комиссия (%)
        layout.addWidget(QLabel(self.tr("Комиссия (%):")))
        fee_percent = int((self.service.get("fee") or 0.0) * 100)
        self.fee_edit = QLineEdit(str(fee_percent))
        layout.addWidget(self.fee_edit)

        # Включена
        self.enabled_check = QCheckBox(self.tr("Включена"))
        self.enabled_check.setChecked(self.service.get("enabled", True))
        layout.addWidget(self.enabled_check)

        #Кнопки
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        buttons.setStyleSheet("""
                    QPushButton {
                        background-color: #e0e0e0;
                        border: 1px solid #aaa;
                        border-radius: 4px;
                        padding: 4px;
                    }
                    QPushButton:hover {
                        background-color: #c0c0c0;
                    }
                    QPushButton:pressed {
                        background-color: #a0a0a0;
                    }
                """)
        #Меняем название кнопки Cancel
        cancel_btn = buttons.button(QDialogButtonBox.Cancel)
        if cancel_btn:
            cancel_btn.setText(self.tr("Отмена"))
        layout.addWidget(buttons)

        self.replace_button = QPushButton(self.tr("Замена счётчика"))
        self.replace_button.clicked.connect(self.replace_meter)
        layout.addWidget(self.replace_button)

    def replace_meter(self):
        dialog = MeterReplacementDialog(self.service, self)
        if dialog.exec():
            # Возможно, потребуется обновить отображение, но пока ничего не делаем
            pass
    
    def accept(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, self.tr("Ошибка"), self.tr("Название услуги не может быть пустым"))
            return
        # Если имя изменилось, обновим ключ
        new_key = name.lower().replace(' ', '_')
        if new_key != self.key and new_key in self.services:
            QMessageBox.warning(self, self.tr("Ошибка"), self.tr("Услуга с таким названием уже существует"))
            return

        try:
            tariff = float(normalize_decimal(self.tariff_edit.text().strip()))
            if tariff <= 0:
                raise ValueError
        except:
            QMessageBox.warning(self, self.tr("Ошибка"), self.tr("Тариф должен быть положительным числом"))
            return

        try:
            fee_percent = float(self.fee_edit.text().strip())
            if fee_percent < 0 or fee_percent > 100:
                raise ValueError
            fee = fee_percent / 100.0
        except:
            QMessageBox.warning(self, self.tr("Ошибка"), self.tr("Комиссия должна быть числом от 0 до 100"))
            return

        updated = {
            "id": self.service.id,
            "name": name,
            "type": self.service["type"],
            "enabled": self.enabled_check.isChecked(),
            "tariff": tariff,
            "fee": fee,
            "provider_id": self.service.provider_id,
        }
        if isinstance(self.service, MeteredService) and self.start_edit:
            try:
                start_val = float(normalize_decimal(self.start_edit.text().strip()))
                if start_val < 0:
                    raise ValueError
                updated["start_value"] = start_val
            except:
                QMessageBox.warning(self, self.tr("Ошибка"), self.tr("Начальное значение должно быть неотрицательным числом"))
                return

        # Сохраняем состояние объекта, которое диалог не редактирует
        # (замены, поверки), чтобы не потерять его при пересоздании объекта.
        if isinstance(self.service, BaseService):
            updated["replacements"] = self.service.replacements
            updated["active_verification"] = self.service.active_verification
            updated["last_completed_verification"] = self.service.last_completed_verification
            updated["next_verification_date"] = self.service.next_verification_date

        # Удаляем старый ключ, если изменился
        if new_key != self.key:
            del self.services[self.key]
        self.services[new_key] = BaseService.from_dict(updated, key=new_key)
        save_services()
        super().accept()

class MeterReplacementDialog(QDialog):
    def __init__(self, service_key, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: white;")#Прописываем белый фон окна (так как по умолчанию он черный)
        self.service_key = service_key
        self.setWindowTitle(self.tr("Замена счётчика"))
        self.setMinimumWidth(300)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(self.tr("Показания старого счётчика на момент замены:")))
        self.old_edit = QLineEdit()
        layout.addWidget(self.old_edit)
        layout.addWidget(QLabel(self.tr("Показания нового счётчика на момент установки:")))
        self.new_edit = QLineEdit()
        layout.addWidget(self.new_edit)
        layout.addWidget(QLabel(self.tr("Дата (необязательно, в формате ГГГГ-ММ-ДД):")))
        self.date_edit = QLineEdit()
        layout.addWidget(self.date_edit)
        self.pay_consumption_check = QCheckBox(self.tr("Оплатить расход по старому счётчику"))
        layout.addWidget(self.pay_consumption_check)


        #Кнопки
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        buttons.setStyleSheet("""
                    QPushButton {
                        background-color: #e0e0e0;
                        border: 1px solid #aaa;
                        border-radius: 4px;
                        padding: 4px;
                    }
                    QPushButton:hover {
                        background-color: #c0c0c0;
                    }
                    QPushButton:pressed {
                        background-color: #a0a0a0;
                    }
                """)
        #Меняем название кнопки Cancel
        cancel_btn = buttons.button(QDialogButtonBox.Cancel)
        if cancel_btn:
            cancel_btn.setText(self.tr("Отмена"))
        layout.addWidget(buttons)

    def ask_fee_percent(self):
        dialog = QDialog(self)
        dialog.setWindowTitle(self.tr("Настройка комиссии банка"))
        dialog.setMinimumWidth(300)
        dialog.setStyleSheet("background-color: white;")
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel(self.tr("Укажите размер комиссии (в процентах), которую берёт банк:")))
        percent_edit = QLineEdit()
        layout.addWidget(percent_edit)

        #Кнопки
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        buttons.setStyleSheet("""
                    QPushButton {
                        background-color: #e0e0e0;
                        border: 1px solid #aaa;
                        border-radius: 4px;
                        padding: 4px;
                    }
                    QPushButton:hover {
                        background-color: #c0c0c0;
                    }
                    QPushButton:pressed {
                        background-color: #a0a0a0;
                    }
                """)
        #Меняем название кнопки Cancel
        cancel_btn = buttons.button(QDialogButtonBox.Cancel)
        if cancel_btn:
            cancel_btn.setText(self.tr("Отмена"))
        layout.addWidget(buttons)

        if dialog.exec() == QDialog.Accepted:
            try:
                percent = float(percent_edit.text().strip())
                if percent < 0 or percent > 100:
                    raise ValueError
                return percent
            except:
                QMessageBox.warning(self, self.tr("Ошибка"), self.tr("Введите число от 0 до 100"))
                return None
        return None

    def accept(self):
        from communal_calculator import normalize_decimal
        from database import get_service_id_by_key, add_replacement, save_bill
        from config import services
        from file_manager import save_settings
        from datetime import datetime
        from decimal import Decimal

        try:
            old_final = float(normalize_decimal(self.old_edit.text()))
            new_start = float(normalize_decimal(self.new_edit.text()))
        except:
            QMessageBox.warning(self, self.tr("Ошибка"), self.tr("Введите корректные числа"))
            return

        #Получаем числовой идентификатор (ID) услуги из таблицы services по её строковому ключу (self.service_key)
        service_id = get_service_id_by_key(self.service_key)
        if service_id is None:
            QMessageBox.warning(self, self.tr("Ошибка"), self.tr("Услуга не найдена в базе данных"))
            return

        date_str = self.date_edit.text().strip()
        if not date_str:
            date_str = datetime.now().strftime("%Y-%m-%d")

        # 1. Создаём запись о замене (как обычно)
        replacement_id = add_replacement(service_id, old_final, new_start, date_str)

        # 2. --- Проверяем, нужно ли оплатить расход сразу ---
        pay_consumption = self.pay_consumption_check.isChecked()
        if pay_consumption:
            # Получаем данные услуги
            service = services.get(self.service_key)
            if not service:
                QMessageBox.warning(self, self.tr("Ошибка"), self.tr("Услуга не найдена в config"))
                return

            start_value = Decimal(service.get('start_value', 0))
            old_final_dec = Decimal(old_final)
            tariff = Decimal(service.get('tariff', 0))
            fee = Decimal(service.get('fee') or 0.0)

            # Расход до замены
            consumption = max(old_final_dec - start_value, Decimal('0'))
            amount = consumption * tariff

            # Открываем диалог подтверждения
            items = [(self.tr("Расход до замены"), float(amount))]
            confirm = PaymentConfirmationDialog(items, service['name'], self)
            if confirm.exec() != QDialog.Accepted:
                return  # пользователь отменил

            result = confirm.get_result()
            apply_fee = result['apply_fee']

            # Определяем процент комиссии
            fee_percent = Decimal('0')
            if apply_fee:
                if fee == 0:
                    percent = self.ask_fee_percent()
                    if percent is None:
                        return
                    service['fee'] = percent / 100.0
                    save_settings()
                    fee_percent = Decimal(service['fee'])
                else:
                    fee_percent = fee

            # Рассчитываем комиссию
            fee_amount = amount * fee_percent if apply_fee else Decimal('0')
            total = amount + fee_amount

            # Формируем детали для save_bill
            details = [{
                'service_key': self.service_key,
                'service_name': service['name'],
                'start_reading': float(start_value),
                'end_reading': float(old_final),
                'consumption': float(consumption),
                'tariff': float(tariff),
                'amount': round(float(amount), 2),
                'fee': round(float(fee_amount), 2),
                'total': round(float(total), 2)
            }]

            # Сохраняем в bills
            bill_data = {
                'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'total_amount': float(amount),
                'total_fee': float(fee_amount),
                'total_with_fee': float(total),
                'details': details,
                'used_replacements': [replacement_id]
            }
            bill_id = save_bill(bill_data)

            # Обновляем start_value услуги на new_start
            services[self.service_key]['start_value'] = new_start
            save_settings()

            # Помечаем замену как оплаченную (is_paid=1)
            from database import mark_replacements_paid
            mark_replacements_paid([replacement_id], bill_id)

            QMessageBox.information(self, self.tr("Успешно"), self.tr("Замена сохранена и оплачена"))
        else:
            # Если оплата не требуется — просто обновляем интерфейс
            from file_manager import load_settings
            load_settings()
            if self.parent():
                self.parent().rebuild_services_ui()

        super().accept()


class ClickToSelectLineEdit(QLineEdit):
    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self.selectAll()

class VerificationDialog(QDialog):
    def __init__(self, service_key, verification_id=None, parent=None, default_event_type=None):
        super().__init__(parent)
        self.service_key = service_key
        self.verification_id = verification_id
        self.default_event_type = default_event_type
        self.setWindowTitle(self.tr("Поверка счётчика") if not verification_id else self.tr("Редактирование поверки"))
        self.setMinimumWidth(450)
        self.setStyleSheet("background-color: white;")
        layout = QVBoxLayout(self)

        # --- Поля (как в MeterReplacementDialog + дополнительные) ---
        self.old_edit = ClickToSelectLineEdit()
        self.new_edit = ClickToSelectLineEdit()
        self.date_start_edit = QDateEdit()
        self.date_start_edit.setCalendarPopup(True)
        self.date_start_edit.setDisplayFormat("dd.MM.yyyy")
        self.date_start_edit.setDate(QDate.currentDate())

        self.date_end_edit = QDateEdit()
        self.date_end_edit.setCalendarPopup(True)
        self.date_end_edit.setDisplayFormat("dd.MM.yyyy")
        self.date_end_edit.setDate(QDate.currentDate())
        self.date_end_edit.setSpecialValueText(self.tr("Не завершена"))
        self.date_end_edit.setEnabled(False)

        self.amount_norm_edit = ClickToSelectLineEdit()
        self.next_verification_date_edit = QDateEdit()
        self.next_verification_date_edit.setCalendarPopup(True)
        self.next_verification_date_edit.setDisplayFormat("dd.MM.yyyy")
        self.next_verification_date_edit.setDate(QDate.currentDate().addYears(3))

        self.completed_check = QCheckBox(self.tr("Счётчик установлен обратно"))
        self.completed_check.toggled.connect(self.on_completed_toggled)

        # --- Новые чекбоксы для оплаты ---
        self.pay_consumption_check = QCheckBox(self.tr("Оплатить расход на момент снятия"))
        self.pay_norm_check = QCheckBox(self.tr("Оплатить сумму по нормативу"))        

        # Форма
        fields = [
            (self.tr("Показания на момент снятия:"), self.old_edit),
            (self.tr("Показания на момент установки:"), self.new_edit),
            (self.tr("Дата снятия счётчика:"), self.date_start_edit),
            (self.tr("Дата установки обратно:"), self.date_end_edit),
            (self.tr("Сумма по нормативу (руб.):"), self.amount_norm_edit),
            (self.tr("Дата следующей поверки:"), self.next_verification_date_edit),
        ]
        for label, widget in fields:
            row = QHBoxLayout()
            row.addWidget(QLabel(label))
            row.addWidget(widget)
            layout.addLayout(row)

        layout.addWidget(self.completed_check)
        layout.addWidget(self.pay_consumption_check)
        layout.addWidget(self.pay_norm_check)

        # --- Если редактируем – загружаем данные ---
        if verification_id:
            from database import get_verification_by_id
            data = get_verification_by_id(verification_id)
            if data:
                self.old_edit.setText(str(data['old_final']) if data.get('old_final') is not None else '')
                self.new_edit.setText(str(data['new_start']) if data.get('new_start') is not None else '')
                self.date_start_edit.setDate(QDate.fromString(data['date_start'], "yyyy-MM-dd"))
                self.pay_consumption_check.setChecked(data.get('is_consumption_paid', False))
                self.pay_norm_check.setChecked(data.get('is_norm_paid', False))
                if data['date_end']:
                    self.date_end_edit.setDate(QDate.fromString(data['date_end'], "yyyy-MM-dd"))
                    self.completed_check.setChecked(True)
                else:
                    self.completed_check.setChecked(False)
                self.amount_norm_edit.setText(str(data['amount_norm']) if data.get('amount_norm') is not None else '')
                if data.get('next_verification_date'):
                    self.next_verification_date_edit.setDate(QDate.fromString(data['next_verification_date'], "yyyy-MM-dd"))

        # --- Кнопки ---
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        button_box.setStyleSheet("""
                    QPushButton {
                        background-color: #e0e0e0;
                        border: 1px solid #aaa;
                        border-radius: 4px;
                        padding: 4px;
                    }
                    QPushButton:hover {
                        background-color: #c0c0c0;
                    }
                    QPushButton:pressed {
                        background-color: #a0a0a0;
                    }
                """)
        # --- Меняем названия кнопки Cancel ---
        cancel_btn = button_box.button(QDialogButtonBox.Cancel)
        if cancel_btn:
            cancel_btn.setText(self.tr("Отмена"))
        layout.addWidget(button_box)
 
    def on_completed_toggled(self, checked):
        self.date_end_edit.setEnabled(checked)
        self.new_edit.setEnabled(checked)  # новые показания нужны только при завершении
        if not checked:
            self.date_end_edit.setDate(QDate())
            self.date_end_edit.setSpecialValueText(self.tr("Не завершена"))
            self.new_edit.clear()

    def get_data(self):
        def to_float(value):
            if value is None:
                return None
            s = str(value).strip()
            if s == '' or s.lower() == 'none':
                return None
            try:
                return float(s.replace(',', '.'))
            except ValueError:
                return None

        old_final = self.old_edit.text()
        new_start = self.new_edit.text() if self.completed_check.isChecked() else None
        date_start = self.date_start_edit.date().toString("yyyy-MM-dd")
        if self.completed_check.isChecked():
            date_end = self.date_end_edit.date().toString("yyyy-MM-dd")
        else:
            date_end = None
        amount_norm = self.amount_norm_edit.text()
        next_verification_date = (
            self.next_verification_date_edit.date().toString("yyyy-MM-dd")
            if not self.next_verification_date_edit.date().isNull() else None
        )

        return {
            'old_final': to_float(old_final),
            'new_start': to_float(new_start),
            'date_start': date_start,
            'date_end': date_end,
            'amount_norm': to_float(amount_norm),
            'next_verification_date': next_verification_date,
        }

    def ask_fee_percent(self):
        dialog = QDialog(self)
        dialog.setWindowTitle(self.tr("Настройка комиссии банка"))
        dialog.setMinimumWidth(300)
        dialog.setStyleSheet("background-color: white;")
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel(self.tr("Укажите размер комиссии (в процентах), которую берёт банк:")))
        percent_edit = QLineEdit()
        layout.addWidget(percent_edit)

        #Кнопки
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        buttons.setStyleSheet("""
                    QPushButton {
                        background-color: #e0e0e0;
                        border: 1px solid #aaa;
                        border-radius: 4px;
                        padding: 4px;
                    }
                    QPushButton:hover {
                        background-color: #c0c0c0;
                    }
                    QPushButton:pressed {
                        background-color: #a0a0a0;
                    }
                """)
        #Меняем название кнопки Cancel
        cancel_btn = buttons.button(QDialogButtonBox.Cancel)
        if cancel_btn:
            cancel_btn.setText(self.tr("Отмена"))
        layout.addWidget(buttons)

        if dialog.exec() == QDialog.Accepted:
            try:
                percent = float(percent_edit.text().strip())
                if percent < 0 or percent > 100:
                    raise ValueError
                return percent
            except:
                QMessageBox.warning(self, self.tr("Ошибка"), self.tr("Введите число от 0 до 100"))
                return None
        return None

    def accept(self):
        from database import add_verification, update_verification, get_service_id_by_key, save_bill
        from config import services
        from file_manager import save_settings
        from decimal import Decimal
        from datetime import datetime

        data = self.get_data()
        # Валидация полей при завершении поверки
        if self.completed_check.isChecked():
            if data.get('date_end') is None:
                QMessageBox.warning(self, self.tr("Ошибка"), self.tr("Укажите дату установки счётчика обратно"))
                return
            if data.get('new_start') is None:
                QMessageBox.warning(self, self.tr("Ошибка"), self.tr("Укажите показания счётчика на момент установки"))
                return
        # Валидация
        if not data['date_start']:
            QMessageBox.warning(self, self.tr("Ошибка"), self.tr("Дата снятия счётчика обязательна"))
            return
        if data['old_final'] is None:
            QMessageBox.warning(self, self.tr("Ошибка"), self.tr("Введите показания на момент снятия"))
            return

        service_id = get_service_id_by_key(self.service_key)
        if service_id is None:
            QMessageBox.warning(self, self.tr("Ошибка"), self.tr("Услуга не найдена"))
            return

        # Сохраняем поверку (создаём или обновляем)
        if self.verification_id:
            update_verification(self.verification_id, data, default_event_type=self.default_event_type)
        else:
            self.verification_id = add_verification(service_id, data, default_event_type=self.default_event_type)

        # --- Немедленная оплата, если чекбоксы активны ---
        pay_consumption = self.pay_consumption_check.isChecked()
        pay_norm = self.pay_norm_check.isChecked()

        if pay_consumption or pay_norm:
            # Получаем текущие данные услуги
            service = services.get(self.service_key)
            if not service:
                QMessageBox.warning(self, self.tr("Ошибка"), self.tr("Услуга не найдена в config"))
                return

            start_value = Decimal(service.get('start_value', 0))
            old_final = Decimal(data['old_final'])
            tariff = Decimal(service.get('tariff', 0))

            items = []
            total_without_fee = Decimal('0')

            # 1. Расход до снятия
            if pay_consumption:
                consumption = max(old_final - start_value, Decimal('0'))
                amount = consumption * tariff
                items.append((self.tr("Расход до снятия"), float(amount)))
                total_without_fee += amount

            # 2. Норматив
            if pay_norm:
                amount_norm = Decimal(data['amount_norm'] or 0)
                if amount_norm > 0:
                    items.append((self.tr("Сумма по нормативу"), float(amount_norm)))
                    total_without_fee += amount_norm

            if not items:
                QMessageBox.warning(self, self.tr("Ошибка"), self.tr("Нет позиций для оплаты"))
                return

            # Открываем диалог подтверждения
            confirm = PaymentConfirmationDialog(items, service['name'], self)
            if confirm.exec() != QDialog.Accepted:
                return  # пользователь отменил

            # Получаем результат из PaymentConfirmationDialog
            result = confirm.get_result()
            apply_fee = result['apply_fee']

            # Определяем процент комиссии
            fee_percent = Decimal('0')
            if apply_fee:
                service_fee = Decimal(service.get('fee') or 0.0)
                if service_fee == 0:
                    # Комиссия не задана — запрашиваем у пользователя
                    percent = self.ask_fee_percent()
                    if percent is None:
                        return  # пользователь отменил
                    # Сохраняем комиссию в настройках услуги
                    service['fee'] = percent / 100.0
                    save_settings()
                    fee_percent = Decimal(service['fee'])
                else:
                    fee_percent = service_fee

            # Формируем детали для save_bill с учётом комиссии
            details = []
            total_amount = Decimal('0')
            total_fee = Decimal('0')
            total_with_fee = Decimal('0')

            for desc, amount in items:
                amount_d = Decimal(str(amount))
                fee_amount = amount_d * fee_percent if apply_fee else Decimal('0')
                total_item = amount_d + fee_amount
                details.append({
                    'service_key': self.service_key,
                    'service_name': service['name'],
                    'start_reading': float(start_value) if desc == self.tr("Расход до снятия") else None,
                    'end_reading': float(old_final) if desc == self.tr("Расход до снятия") else None,
                    'consumption': float(amount_d / tariff) if desc == self.tr("Расход до снятия") else 0,
                    'tariff': float(tariff) if desc == self.tr("Расход до снятия") else 0,
                    'amount': round(float(amount_d), 2),
                    'fee': round(float(fee_amount), 2),
                    'total': round(float(total_item), 2)
                })
                total_amount += amount_d
                total_fee += fee_amount
                total_with_fee += total_item

            # Сохраняем в bills
            bill_data = {
                'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'total_amount': float(total_amount),
                'total_fee': float(total_fee),
                'total_with_fee': float(total_with_fee),
                'details': details,
                'used_replacements': []
            }
            bill_id = save_bill(bill_data)

            # Обновляем start_value если оплачен расход
            if pay_consumption and data['date_end'] and data['new_start'] is not None:
                services[self.service_key]['start_value'] = data['new_start']
                save_settings()

            # Обновляем флаги оплаты
            if pay_consumption:
                data['is_consumption_paid'] = 1
            if pay_norm:
                data['is_norm_paid'] = 1
            if self.verification_id:
                update_verification(self.verification_id, data, default_event_type=self.default_event_type)

            from file_manager import load_settings
            load_settings()

            msg = QMessageBox(self)
            msg.setWindowTitle(self.tr("Успешно"))
            msg.setText(self.tr("Поверка сохранена и оплачена"))
            msg.setIcon(QMessageBox.Information)

            # Применяем стиль ко всему диалогу, чтобы все кнопки внутри унаследовали
            msg.setStyleSheet("""
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
            """)

            msg.exec()

        super().accept()

class SettingsWindow(QDialog):
    def __init__(self, services, refresh_callback=None, parent=None):
        super().__init__(parent)
        self.services = services
        self.refresh_callback = refresh_callback  # для обновления главного окна
        self.setWindowTitle(self.tr("Настройки"))
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
        self.tab_widget.addTab(self.services_tab, self.tr("Управление услугами"))
        self.setup_services_tab()

        # Вкладка "Тарифы"
        self.tariffs_tab = QWidget()
        self.tab_widget.addTab(self.tariffs_tab, self.tr("Изменить тариф"))
        self.setup_tariffs_tab()

        # Вкладка "Комиссии"
        self.commissions_tab = QWidget()
        self.tab_widget.addTab(self.commissions_tab, self.tr("Изменить комиссию"))
        self.setup_commissions_tab()

        #Вкладка "Реквизиты"
        self.providers_tab = QWidget()
        self.tab_widget.addTab(self.providers_tab, self.tr("Реквизиты"))
        self.setup_providers_tab()

        # Вкладка "История счётчиков"
        self.history_tab = QWidget()
        self.tab_widget.addTab(self.history_tab, self.tr("История"))
        self.setup_history_tab()

        # Вкладка "Язык"
        self.language_tab = QWidget()
        self.tab_widget.addTab(self.language_tab, self.tr("Язык"))
        self.setup_language_tab()

        # Кнопки диалога
        button_box = QDialogButtonBox()
        save_btn = button_box.addButton(self.tr("Сохранить"), QDialogButtonBox.AcceptRole)
        cancel_btn = button_box.addButton(self.tr("Отмена"), QDialogButtonBox.RejectRole)
        save_btn.clicked.connect(self.save_all)
        cancel_btn.clicked.connect(self.reject)
        save_btn.setToolTip(self.tr("Сохранить все изменения и закрыть окно настроек."))
        cancel_btn.setToolTip(self.tr("Отменить изменения и закрыть окно."))
        layout.addWidget(button_box)

        # Заполнение таблиц (они будут обновляться в setup_*)
        self.update_tariffs_table()
        self.update_commissions_table()
        self.update_services_table()

        # После создания всех виджетов подгоняем размер окна
        self.adjustSize()
        self.setMinimumSize(530, 400)  # чтобы окно не было слишком маленьким
        
    def setup_tariffs_tab(self):
        """Создаёт таблицу для редактирования тарифов."""
        layout = QVBoxLayout(self.tariffs_tab)
        layout.setContentsMargins(10, 10, 10, 10)
        # Таблица
        self.tariffs_table = QTableWidget()
        self.tariffs_table.setColumnCount(2)
        self.tariffs_table.setHorizontalHeaderLabels([self.tr("Услуга"), self.tr("Тариф (руб.)")])
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
        self.commissions_table.setHorizontalHeaderLabels([self.tr("Услуга"), self.tr("Комиссия (%)")])
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
            fee_percent = int((service.get("fee") or 0.0) * 100)
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
            [self.tr("Название"), self.tr("Тип"), self.tr("Включена"), self.tr("Тариф (руб.)"), self.tr("Комиссия (%)")]
        )
        self.services_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.services_table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.services_table)

        # Кнопки управления
        btn_layout = QHBoxLayout()
        self.btn_add = QPushButton(self.tr("Добавить"))
        self.btn_edit = QPushButton(self.tr("Редактировать"))
        self.btn_delete = QPushButton(self.tr("Удалить"))
        self.btn_toggle = QPushButton(self.tr("Вкл/Выкл"))
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

            type_item = QTableWidgetItem(self.tr("По счётчику") if isinstance(service, MeteredService) else self.tr("Фиксированная"))
            self.services_table.setItem(row, 1, type_item)

            enabled = service.get("enabled", True)
            enabled_item = QTableWidgetItem(self.tr("Да") if enabled else self.tr("Нет"))
            self.services_table.setItem(row, 2, enabled_item)

            tariff_item = QTableWidgetItem(f"{service.get('tariff', 0.0):.2f}")
            self.services_table.setItem(row, 3, tariff_item)

            fee_percent = int((service.get("fee") or 0.0) * 100)
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

    def setup_providers_tab(self):
        """Создаёт интерфейс вкладки Реквизиты"""
        layout = QVBoxLayout(self.providers_tab)
        layout.setContentsMargins(10, 10, 10, 10)

        # Таблица провайдеров
        self.providers_table = QTableWidget()
        self.providers_table.setColumnCount(5)
        self.providers_table.setHorizontalHeaderLabels(["ID", self.tr("Название"), self.tr("ИНН"), self.tr("Банк"), self.tr("Привязанная услуга")])
        self.providers_table.hideColumn(0)  # скрываем ID
        self.providers_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.providers_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.providers_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.providers_table)

        # Кнопки управления
        btn_layout = QHBoxLayout()
        self.btn_add_provider = QPushButton(self.tr("Добавить"))
        self.btn_edit_provider = QPushButton(self.tr("Редактировать"))
        self.btn_delete_provider = QPushButton(self.tr("Удалить"))
        self.btn_attach_provider = QPushButton(self.tr("Привязать к услуге"))

        for btn in (self.btn_add_provider, self.btn_edit_provider, self.btn_delete_provider, self.btn_attach_provider):
            btn.setStyleSheet("""
                    QPushButton {
                        background-color: #e0e0e0;
                        border: 1px solid #aaa;
                        border-radius: 4px;
                        padding: 4px;
                    }
                    QPushButton:hover {
                        background-color: #c0c0c0;
                    }
                    QPushButton:pressed {
                        background-color: #a0a0a0;
                    }
                """)

        btn_layout.addWidget(self.btn_add_provider)
        btn_layout.addWidget(self.btn_edit_provider)
        btn_layout.addWidget(self.btn_delete_provider)
        btn_layout.addWidget(self.btn_attach_provider)
        layout.addLayout(btn_layout)

        # Подключение сигналов
        self.btn_add_provider.clicked.connect(self.add_provider)
        self.btn_edit_provider.clicked.connect(self.edit_provider)
        self.btn_delete_provider.clicked.connect(self.delete_provider)
        self.btn_attach_provider.clicked.connect(self.attach_provider)

        # Заполнение таблицы
        self.refresh_providers_table()

    def refresh_providers_table(self):
        """Загружает данные по реквизитам из БД"""
        from database import get_all_providers, get_provider
        from config import services

        providers = get_all_providers()
        self.providers_table.setRowCount(len(providers))

        # Сопоставляем provider_id с названиями услуг
        service_by_provider = {}
        for key, service in services.items():
            if service.get('provider_id'):
                service_by_provider[service['provider_id']] = service['name']

        for i, p in enumerate(providers):
            provider = get_provider(p['id'])
            if not provider:
                continue
            self.providers_table.setItem(i, 0, QTableWidgetItem(str(provider['id'])))
            self.providers_table.setItem(i, 1, QTableWidgetItem(provider.get('name', '')))
            self.providers_table.setItem(i, 2, QTableWidgetItem(provider.get('inn', '')))
            self.providers_table.setItem(i, 3, QTableWidgetItem(provider.get('bank', '')))
            attached = service_by_provider.get(provider['id'], self.tr('Не привязана'))
            self.providers_table.setItem(i, 4, QTableWidgetItem(attached))

        self.providers_table.resizeColumnsToContents()

    def add_provider(self):
        """Добавить – открывает EditProviderDialog без service_key (только создание провайдера)"""
        dialog = EditProviderDialog(None, None, self)  # service_key=None, provider_data=None
        if dialog.exec():
            self.refresh_providers_table()
            if self.refresh_callback:
                self.refresh_callback()  # обновить главное окно

    def edit_provider(self):
        """Редактировать – берёт выбранную строку, загружает данные провайдера и открывает EditProviderDialog с provider_data"""
        selected = self.providers_table.selectedItems()
        if not selected:
            QMessageBox.warning(self, self.tr("Ошибка"), self.tr("Выберите организацию"))
            return
        row = selected[0].row()
        provider_id = int(self.providers_table.item(row, 0).text())
        from database import get_provider
        provider = get_provider(provider_id)
        if not provider:
            QMessageBox.warning(self, self.tr("Ошибка"), self.tr("Данные не найдены"))
            return
        dialog = EditProviderDialog(None, provider, self)  # service_key=None, provider_data=provider
        if dialog.exec():
            self.refresh_providers_table()
            if self.refresh_callback:
                self.refresh_callback()

    def delete_provider(self):
        """Удалить – подтверждение и удаление провайдера"""
        selected = self.providers_table.selectedItems()
        if not selected:
            QMessageBox.warning(self, self.tr("Ошибка"), self.tr("Выберите организацию"))
            return
        row = selected[0].row()
        provider_id = int(self.providers_table.item(row, 0).text())
        confirm = QMessageBox.question(self, self.tr("Удаление"), self.tr("Удалить организацию?"), QMessageBox.Yes | QMessageBox.No)
        if confirm == QMessageBox.Yes:
            from database import delete_provider
            delete_provider(provider_id)
            self.refresh_providers_table()
            if self.refresh_callback:
                self.refresh_callback()

    def attach_provider(self):
        """Привязать к услуге – выбор услуги из списка и привязка к ней провайдера"""
        selected = self.providers_table.selectedItems()
        if not selected:
            QMessageBox.warning(self, self.tr("Ошибка"), self.tr("Выберите организацию"))
            return
        row = selected[0].row()
        provider_id = int(self.providers_table.item(row, 0).text())
        from config import services

        # Список услуг без привязки
        available = [key for key, s in services.items() if s.get('enabled', True) and not s.get('provider_id')]
        if not available:
            QMessageBox.information(self, self.tr("Информация"), self.tr("Нет свободных услуг для привязки"))
            return

        # Диалог выбора
        dialog = QDialog(self)
        dialog.setWindowTitle(self.tr("Привязка к услуге"))
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel(self.tr("Выберите услугу:")))
        combo = QComboBox()
        for key in available:
            combo.addItem(services[key]['name'], key)
        layout.addWidget(combo)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(dialog.accept)
        btn_box.rejected.connect(dialog.reject)
        btn_box.setStyleSheet("""
                    QPushButton {
                        background-color: #e0e0e0;
                        border: 1px solid #aaa;
                        border-radius: 4px;
                        padding: 4px;
                    }
                    QPushButton:hover {
                        background-color: #c0c0c0;
                    }
                    QPushButton:pressed {
                        background-color: #a0a0a0;
                    }
                """)
        #Меняем название кнопки Cancel
        cancel_btn = btn_box.button(QDialogButtonBox.Cancel)
        if cancel_btn:
            cancel_btn.setText(self.tr("Отмена"))
        layout.addWidget(btn_box)

        if dialog.exec():
            service_key = combo.currentData()
            from database import set_service_provider
            set_service_provider(service_key, provider_id)
            self.refresh_providers_table()
            if self.refresh_callback:
                self.refresh_callback()

    # ---------- Вкладка "История" ----------

    @staticmethod
    def _display_date(iso_date):
        """Преобразует ISO-дату (YYYY-MM-DD) в DD.MM.YYYY."""
        if not iso_date:
            return "-"
        parts = str(iso_date).split('-')
        if len(parts) == 3:
            return f"{parts[2]}.{parts[1]}.{parts[0]}"
        return str(iso_date)

    @staticmethod
    def _display_number(value):
        if value is None or value == '':
            return "-"
        try:
            f = float(value)
            if f.is_integer():
                return str(int(f))
            return str(f)
        except (TypeError, ValueError):
            return str(value)

    def _event_label(self, event):
        event_type = event.get('event_type')
        meter_state = event.get('meter_state')
        if event_type == 'replacement':
            return self.tr("Замена счётчика")
        if event_type == 'verification_start':
            return self.tr("Ремонт начат") if meter_state == 'on_repair' else self.tr("Поверка начата")
        if event_type == 'verification_end':
            return self.tr("Ремонт завершён") if meter_state == 'on_repair' else self.tr("Поверка завершена")
        if event_type == 'removal':
            return self.tr("Демонтаж")
        if event_type == 'installation':
            return self.tr("Установка нового счётчика")
        return "—"

    def setup_history_tab(self):
        layout = QVBoxLayout(self.history_tab)
        layout.setContentsMargins(10, 10, 10, 10)

        self.history_table = QTableWidget()
        self.history_table.setColumnCount(9)
        self.history_table.setHorizontalHeaderLabels([
            "ID", self.tr("Услуга"), self.tr("Дата"), self.tr("Событие"),
            self.tr("Начало"), self.tr("Конец"), self.tr("Сумма норматива"), self.tr("Оплачено"), self.tr("Комментарий"),
        ])
        self.history_table.hideColumn(0)
        self.history_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.history_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.history_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.history_table)

        btn_layout = QHBoxLayout()
        self.btn_add_history = QPushButton(self.tr("Добавить"))
        self.btn_edit_history = QPushButton(self.tr("Редактировать"))
        self.btn_delete_history = QPushButton(self.tr("Удалить"))
        for btn in (self.btn_add_history, self.btn_edit_history, self.btn_delete_history):
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #e0e0e0;
                    border: 1px solid #aaa;
                    border-radius: 4px;
                    padding: 4px;
                }
                QPushButton:hover {
                    background-color: #c0c0c0;
                }
                QPushButton:pressed {
                    background-color: #a0a0a0;
                }
            """)
        btn_layout.addWidget(self.btn_add_history)
        btn_layout.addWidget(self.btn_edit_history)
        btn_layout.addWidget(self.btn_delete_history)
        layout.addLayout(btn_layout)

        self.btn_add_history.clicked.connect(self.add_history_event)
        self.btn_edit_history.clicked.connect(self.edit_history_event)
        self.btn_delete_history.clicked.connect(self.delete_history_event)

        self.refresh_history_table()

    def refresh_history_table(self):
        from database import load_all_meter_events

        events = load_all_meter_events()
        self.history_table.setRowCount(len(events))
        for row, event in enumerate(events):
            id_item = QTableWidgetItem(str(event.get('id')))
            id_item.setData(Qt.UserRole, event.get('service_key'))
            self.history_table.setItem(row, 0, id_item)
            self.history_table.setItem(row, 1, QTableWidgetItem(event.get('service_name') or ''))
            self.history_table.setItem(row, 2, QTableWidgetItem(self._display_date(event.get('date'))))
            self.history_table.setItem(row, 3, QTableWidgetItem(self._event_label(event)))
            self.history_table.setItem(row, 4, QTableWidgetItem(self._display_number(event.get('old_final'))))
            self.history_table.setItem(row, 5, QTableWidgetItem(self._display_number(event.get('new_start'))))
            self.history_table.setItem(row, 6, QTableWidgetItem(self._display_number(event.get('amount_norm'))))
            self.history_table.setItem(row, 7, QTableWidgetItem(self.tr("Да") if event.get('is_paid') else self.tr("Нет")))
            self.history_table.setItem(row, 8, QTableWidgetItem(event.get('comment') or "-"))

        self.history_table.resizeColumnsToContents()
        self.history_table.horizontalHeader().setStretchLastSection(False)
        self.history_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)

    def _after_history_change(self):
        """Перезагружает услуги, обновляет таблицу и главное окно."""
        from file_manager import load_settings
        load_settings()
        self.services = config.services
        self.refresh_history_table()
        parent = self.parent()
        if parent is not None:
            if hasattr(parent, 'dashboard'):
                parent.dashboard.update_data()
            if hasattr(parent, 'input_panel'):
                parent.input_panel.rebuild_services_ui()

    def add_history_event(self):
        dialog = EventEditDialog(None, self)
        if dialog.exec() == QDialog.Accepted:
            self._after_history_change()

    def edit_history_event(self):
        selected = self.history_table.selectedItems()
        if not selected:
            QMessageBox.warning(self, self.tr("Ошибка"), self.tr("Выберите событие"))
            return
        row = selected[0].row()
        event_id = int(self.history_table.item(row, 0).text())
        dialog = EventEditDialog(event_id, self)
        if dialog.exec() == QDialog.Accepted:
            self._after_history_change()

    def delete_history_event(self):
        selected = self.history_table.selectedItems()
        if not selected:
            QMessageBox.warning(self, self.tr("Ошибка"), self.tr("Выберите событие"))
            return
        row = selected[0].row()
        id_item = self.history_table.item(row, 0)
        event_id = int(id_item.text())
        service_key = id_item.data(Qt.UserRole)
        confirm = QMessageBox.question(
            self, self.tr("Удаление события"),
            self.tr("Удалить выбранное событие?"),
            QMessageBox.Yes | QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return
        from database import delete_meter_event, recalculate_service_meter_state
        delete_meter_event(event_id)
        recalculate_service_meter_state(service_key)
        self._after_history_change()

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
            self, self.tr("Удаление услуги"),
            self.tr("Удалить услугу '{name}'?").format(name=self.services[key].get('name', key)),
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            from database import delete_service
            delete_service(key)
            del self.services[key]
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

    def setup_language_tab(self):
        """Создаёт интерфейс вкладки выбора языка."""
        layout = QVBoxLayout(self.language_tab)
        layout.setContentsMargins(10, 10, 10, 10)

        self.language_combo = QComboBox()
        self.language_combo.addItem(self.tr("Системный (по умолчанию)"), 'system')
        self.language_combo.addItem(self.tr("Русский"), 'ru')
        self.language_combo.addItem(self.tr("English"), 'en')
        layout.addWidget(self.language_combo)

        current = getattr(config, 'language', 'system') or 'system'
        idx = self.language_combo.findData(current)
        if idx >= 0:
            self.language_combo.setCurrentIndex(idx)

        hint = QLabel(self.tr("Изменения вступят в силу после перезапуска программы."))
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.restart_btn = QPushButton(self.tr("Перезапустить сейчас"))
        self.restart_btn.clicked.connect(self.on_language_restart)
        layout.addWidget(self.restart_btn)
        layout.addStretch()

    def on_language_restart(self):
        """Сохраняет выбранный язык и сообщает о необходимости перезапуска."""
        from file_manager import save_language
        lang = self.language_combo.currentData()
        if lang:
            config.language = lang
            save_language()
        QMessageBox.information(
            self,
            self.tr("Информация"),
            self.tr("Изменения вступят в силу после перезапуска. "
                    "Пожалуйста, закройте и запустите программу заново.")
        )

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
                    self.tr("Ошибка"),
                    self.tr("Некорректный тариф для услуги {name}").format(name=self.services[key]['name']),
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
                    self.tr("Ошибка"),
                    self.tr("Комиссия должна быть числом от 0 до 100 для услуги {name}").format(name=self.services[key]['name']),
                )
                return
        save_fees(new_fees)

        self.accept()

        self.accept()  # закрываем диалог

class EventEditDialog(QDialog):
    """Диалог добавления/редактирования события счётчика в Истории."""

    def __init__(self, event_id=None, parent=None):
        super().__init__(parent)
        self.event_id = event_id
        self.setWindowTitle(self.tr("Добавить событие") if event_id is None else self.tr("Редактировать событие"))
        self.setMinimumWidth(430)
        self.setStyleSheet("background-color: white;")
        layout = QVBoxLayout(self)

        # Услуга
        row = QHBoxLayout()
        row.addWidget(QLabel(self.tr("Услуга:")))
        self.service_combo = QComboBox()
        from config import services
        from services import MeteredService
        for key, service in services.items():
            if isinstance(service, MeteredService):
                self.service_combo.addItem(service.get('name', key), key)
        row.addWidget(self.service_combo)
        layout.addLayout(row)

        # Тип события
        row = QHBoxLayout()
        row.addWidget(QLabel(self.tr("Тип события:")))
        self.type_combo = QComboBox()
        self.type_combo.addItem(self.tr("Замена счётчика"), 'replacement')
        self.type_combo.addItem(self.tr("Поверка"), 'verification')
        self.type_combo.addItem(self.tr("Ремонт"), 'repair')
        self.type_combo.addItem(self.tr("Демонтаж навсегда"), 'removal')
        self.type_combo.addItem(self.tr("Установка нового счётчика"), 'installation')
        row.addWidget(self.type_combo)
        layout.addLayout(row)

        # Дата события
        row = QHBoxLayout()
        row.addWidget(QLabel(self.tr("Дата события:")))
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("dd.MM.yyyy")
        self.date_edit.setDate(QDate.currentDate())
        row.addWidget(self.date_edit)
        layout.addLayout(row)

        # Показания до
        row = QHBoxLayout()
        row.addWidget(QLabel(self.tr("Показания до:")))
        self.old_edit = ClickToSelectLineEdit()
        row.addWidget(self.old_edit)
        layout.addLayout(row)

        # Показания после
        row = QHBoxLayout()
        row.addWidget(QLabel(self.tr("Показания после:")))
        self.new_edit = ClickToSelectLineEdit()
        row.addWidget(self.new_edit)
        layout.addLayout(row)

        # Дата завершения (опционально)
        self.completed_check = QCheckBox(self.tr("Событие завершено (указать дату завершения)"))
        layout.addWidget(self.completed_check)
        row = QHBoxLayout()
        row.addWidget(QLabel(self.tr("Дата завершения:")))
        self.date_end_edit = QDateEdit()
        self.date_end_edit.setCalendarPopup(True)
        self.date_end_edit.setDisplayFormat("dd.MM.yyyy")
        self.date_end_edit.setDate(QDate.currentDate())
        self.date_end_edit.setEnabled(False)
        row.addWidget(self.date_end_edit)
        layout.addLayout(row)
        self.completed_check.toggled.connect(lambda checked: self.date_end_edit.setEnabled(checked))

        # Сумма по нормативу
        row = QHBoxLayout()
        row.addWidget(QLabel(self.tr("Сумма по нормативу (руб.):")))
        self.amount_norm_edit = ClickToSelectLineEdit()
        row.addWidget(self.amount_norm_edit)
        layout.addLayout(row)

        # Оплачено
        self.paid_check = QCheckBox(self.tr("Оплачено"))
        layout.addWidget(self.paid_check)

        # Комментарий
        row = QHBoxLayout()
        row.addWidget(QLabel(self.tr("Комментарий:")))
        self.comment_edit = QLineEdit()
        row.addWidget(self.comment_edit)
        layout.addLayout(row)

        # Кнопки
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        button_box.setStyleSheet("""
            QPushButton {
                background-color: #e0e0e0;
                border: 1px solid #aaa;
                border-radius: 4px;
                padding: 4px;
            }
            QPushButton:hover {
                background-color: #c0c0c0;
            }
            QPushButton:pressed {
                background-color: #a0a0a0;
            }
        """)
        cancel_btn = button_box.button(QDialogButtonBox.Cancel)
        if cancel_btn:
            cancel_btn.setText(self.tr("Отмена"))
        layout.addWidget(button_box)

        if event_id is not None:
            self._load_event(event_id)

    def _load_event(self, event_id):
        from database import load_all_meter_events

        event = next((e for e in load_all_meter_events() if e['id'] == event_id), None)
        if event is None:
            return

        service_key = event.get('service_key')
        idx = self.service_combo.findData(service_key)
        if idx >= 0:
            self.service_combo.setCurrentIndex(idx)
        self.service_combo.setEnabled(False)

        event_type = event.get('event_type')
        meter_state = event.get('meter_state')
        if event_type == 'replacement':
            kind = 'replacement'
        elif event_type == 'removal':
            kind = 'removal'
        elif event_type == 'installation':
            kind = 'installation'
        elif meter_state == 'on_repair':
            kind = 'repair'
        else:
            kind = 'verification'
        idx = self.type_combo.findData(kind)
        if idx >= 0:
            self.type_combo.setCurrentIndex(idx)

        if event.get('date'):
            d = QDate.fromString(event['date'], "yyyy-MM-dd")
            if d.isValid():
                self.date_edit.setDate(d)

        self.completed_check.setChecked(bool(event.get('date_end')))
        if event.get('date_end'):
            d = QDate.fromString(event['date_end'], "yyyy-MM-dd")
            if d.isValid():
                self.date_end_edit.setDate(d)

        if event.get('old_final') is not None:
            self.old_edit.setText(str(event['old_final']))
        if event.get('new_start') is not None:
            self.new_edit.setText(str(event['new_start']))
        if event.get('amount_norm') is not None:
            self.amount_norm_edit.setText(str(event['amount_norm']))
        self.paid_check.setChecked(bool(event.get('is_paid')))
        comment = event.get('comment')
        self.comment_edit.setText(comment if comment else '')

    @staticmethod
    def _to_float(value):
        s = (value or '').strip()
        if s == '':
            return None
        try:
            return float(s.replace(',', '.'))
        except ValueError:
            return None

    def accept(self):
        from database import add_meter_event, update_meter_event, recalculate_service_meter_state

        service_key = self.service_combo.currentData()
        if not service_key:
            QMessageBox.warning(self, self.tr("Ошибка"), self.tr("Выберите услугу"))
            return

        kind = self.type_combo.currentData()
        date_val = self.date_edit.date().toString("yyyy-MM-dd")
        date_end = self.date_end_edit.date().toString("yyyy-MM-dd") if self.completed_check.isChecked() else None

        if kind == 'replacement':
            event_type = 'replacement'
            meter_state = 'active'
        elif kind == 'removal':
            event_type = 'removal'
            meter_state = 'removed'
        elif kind == 'installation':
            event_type = 'installation'
            meter_state = 'active'
        elif kind == 'repair':
            if date_end:
                event_type = 'verification_end'
                meter_state = 'active'
            else:
                event_type = 'verification_start'
                meter_state = 'on_repair'
        else:  # verification
            if date_end:
                event_type = 'verification_end'
                meter_state = 'active'
            else:
                event_type = 'verification_start'
                meter_state = 'on_verification'

        old_final = self._to_float(self.old_edit.text())
        new_start = self._to_float(self.new_edit.text())
        amount_norm = self._to_float(self.amount_norm_edit.text())

        # Валидация
        if kind == 'replacement':
            if old_final is None or new_start is None:
                QMessageBox.warning(self, self.tr("Ошибка"), self.tr("Для замены укажите показания до и после"))
                return
        if kind in ('verification', 'repair') and date_end and new_start is None:
            QMessageBox.warning(self, self.tr("Ошибка"), self.tr("Укажите показания после"))
            return

        if kind in ('verification', 'repair'):
            date_column = None
            date_start = date_val
        else:
            date_column = date_val
            date_start = None

        comment = self.comment_edit.text().strip()
        if not comment:
            comment = None

        event_data = {
            'service_key': service_key,
            'event_type': event_type,
            'meter_state': meter_state,
            'date': date_column,
            'date_start': date_start,
            'date_end': date_end,
            'old_final': old_final,
            'new_start': new_start,
            'amount_norm': amount_norm,
            'is_paid': 1 if self.paid_check.isChecked() else 0,
            'comment': comment,
        }

        if self.event_id is not None:
            update_meter_event(self.event_id, event_data)
        else:
            add_meter_event(event_data)

        recalculate_service_meter_state(service_key)
        super().accept()


class RemoveMeterDialog(QDialog):
    """Диалог снятия счётчика (демонтаж навсегда)."""

    def __init__(self, service_key, parent=None):
        super().__init__(parent)
        self.service_key = service_key
        from config import services
        self.service = services.get(service_key)
        self.setWindowTitle(self.tr("Снять счётчик"))
        self.setMinimumWidth(400)
        self.setStyleSheet("background-color: white;")
        layout = QVBoxLayout(self)

        # Услуга (read-only)
        row = QHBoxLayout()
        row.addWidget(QLabel(self.tr("Услуга:")))
        name = self.service.get('name', service_key) if self.service else service_key
        row.addWidget(QLabel(name))
        layout.addLayout(row)

        # Дата снятия
        row = QHBoxLayout()
        row.addWidget(QLabel(self.tr("Дата снятия:")))
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("dd.MM.yyyy")
        self.date_edit.setDate(QDate.currentDate())
        row.addWidget(self.date_edit)
        layout.addLayout(row)

        # Показания на момент снятия
        row = QHBoxLayout()
        row.addWidget(QLabel(self.tr("Показания на момент снятия:")))
        self.reading_edit = QLineEdit()
        row.addWidget(self.reading_edit)
        layout.addLayout(row)

        # Комментарий
        row = QHBoxLayout()
        row.addWidget(QLabel(self.tr("Комментарий:")))
        self.comment_edit = QLineEdit()
        row.addWidget(self.comment_edit)
        layout.addLayout(row)

        # Кнопки
        button_box = QDialogButtonBox()
        remove_btn = button_box.addButton(self.tr("Снять"), QDialogButtonBox.AcceptRole)
        cancel_btn = button_box.addButton(self.tr("Отмена"), QDialogButtonBox.RejectRole)
        remove_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        button_box.setStyleSheet("""
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
                                """)
        layout.addWidget(button_box)

    @staticmethod
    def _to_float(value):
        s = (value or '').strip()
        if s == '':
            return None
        try:
            return float(s.replace(',', '.'))
        except ValueError:
            return None

    def accept(self):
        from database import add_meter_event, recalculate_service_meter_state
        from config import services
        from file_manager import save_settings

        reading = self._to_float(self.reading_edit.text())
        old_final = reading if reading is not None else 0.0
        date_iso = self.date_edit.date().toString("yyyy-MM-dd")
        comment = self.comment_edit.text().strip()
        if not comment:
            comment = None

        add_meter_event({
            'service_key': self.service_key,
            'event_type': 'removal',
            'meter_state': 'removed',
            'date': date_iso,
            'date_start': None,
            'date_end': None,
            'old_final': old_final,
            'new_start': None,
            'amount_norm': None,
            'is_paid': 0,
            'comment': comment,
        })

        service = services.get(self.service_key)
        if service is not None:
            service.meter_state = 'removed'

        save_settings()
        recalculate_service_meter_state(self.service_key)
        super().accept()


class InstallMeterDialog(QDialog):
    """Диалог установки нового счётчика."""

    def __init__(self, service_key, parent=None):
        super().__init__(parent)
        self.service_key = service_key
        from config import services
        self.service = services.get(service_key)
        self.setWindowTitle(self.tr("Установить новый счётчик"))
        self.setMinimumWidth(400)
        self.setStyleSheet("background-color: white;")
        layout = QVBoxLayout(self)

        # Услуга (read-only)
        row = QHBoxLayout()
        row.addWidget(QLabel(self.tr("Услуга:")))
        name = self.service.get('name', service_key) if self.service else service_key
        row.addWidget(QLabel(name))
        layout.addLayout(row)

        # Дата установки
        row = QHBoxLayout()
        row.addWidget(QLabel(self.tr("Дата установки:")))
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("dd.MM.yyyy")
        self.date_edit.setDate(QDate.currentDate())
        row.addWidget(self.date_edit)
        layout.addLayout(row)

        # Начальные показания нового счётчика
        row = QHBoxLayout()
        row.addWidget(QLabel(self.tr("Начальные показания:")))
        self.start_edit = QLineEdit("0")
        row.addWidget(self.start_edit)
        layout.addLayout(row)

        # Тариф (предзаполнен текущим)
        row = QHBoxLayout()
        row.addWidget(QLabel(self.tr("Тариф:")))
        current_tariff = self.service.get('tariff', 0.0) if self.service else 0.0
        self.tariff_edit = QLineEdit(str(current_tariff))
        row.addWidget(self.tariff_edit)
        layout.addLayout(row)

        # Комментарий
        row = QHBoxLayout()
        row.addWidget(QLabel(self.tr("Комментарий:")))
        self.comment_edit = QLineEdit()
        row.addWidget(self.comment_edit)
        layout.addLayout(row)

        # Кнопки
        button_box = QDialogButtonBox()
        install_btn = button_box.addButton(self.tr("Установить"), QDialogButtonBox.AcceptRole)
        cancel_btn = button_box.addButton(self.tr("Отмена"), QDialogButtonBox.RejectRole)
        install_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        button_box.setStyleSheet("""
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
                            """)
        layout.addWidget(button_box)

    @staticmethod
    def _to_float(value):
        s = (value or '').strip()
        if s == '':
            return None
        try:
            return float(s.replace(',', '.'))
        except ValueError:
            return None

    def accept(self):
        from database import add_meter_event, recalculate_service_meter_state
        from config import services
        from file_manager import save_settings

        start_value = self._to_float(self.start_edit.text())
        if start_value is None:
            start_value = 0.0
        tariff_value = self._to_float(self.tariff_edit.text())
        if tariff_value is None:
            QMessageBox.warning(self, self.tr("Ошибка"), self.tr("Некорректный тариф"))
            return
        date_iso = self.date_edit.date().toString("yyyy-MM-dd")
        comment = self.comment_edit.text().strip()
        if not comment:
            comment = None

        add_meter_event({
            'service_key': self.service_key,
            'event_type': 'installation',
            'meter_state': 'active',
            'date': date_iso,
            'date_start': None,
            'date_end': None,
            'old_final': 0.0,
            'new_start': start_value,
            'amount_norm': None,
            'is_paid': 0,
            'comment': comment,
        })

        service = services.get(self.service_key)
        if service is not None:
            service.meter_state = 'active'
            service.start_value = start_value
            service.tariff = tariff_value

        save_settings()
        recalculate_service_meter_state(self.service_key)
        super().accept()


class ProviderInfoDialog(QDialog):
    def __init__(self, provider_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Реквизиты организации"))
        self.setMinimumWidth(400)
        self.setStyleSheet("background-color: white;")
        layout = QVBoxLayout(self)

        fields = [
            (self.tr("Организация"), provider_data.get('name', '')),
            (self.tr("ИНН"), provider_data.get('inn', '')),
            (self.tr("КПП"), provider_data.get('kpp', '')),
            (self.tr("Расчётный счёт"), provider_data.get('account', '')),
            (self.tr("Банк"), provider_data.get('bank', '')),
            (self.tr("БИК"), provider_data.get('bik', '')),
            (self.tr("Корреспондентский счёт"), provider_data.get('corr_account', '')),
            (self.tr("Лицевой счёт"), provider_data.get('personal_account', '')),
            (self.tr("Назначение платежа"), provider_data.get('payment_purpose', '')),
            (self.tr("Идентификатор платежа"), provider_data.get('payment_identifier', '')),
            (self.tr("Адрес"), provider_data.get('address', '')),
            (self.tr("Дополнительная информация"), provider_data.get('extra_info', ''))
        ]
        for label, value in fields:
            row = QHBoxLayout()
            row.addWidget(QLabel(f"<b>{label}:</b>"))
            # Вместо QLabel используем QLineEdit с readOnly и без рамки
            edit = QLineEdit(value)
            edit.setReadOnly(True)
            edit.setStyleSheet("""
                QLineEdit {
                    border: none;
                    background: transparent;
                    font-size: 12px;
                }
            """)
            # Чтобы курсор был виден (для выделения) – разрешаем
            edit.setCursor(Qt.IBeamCursor)
            row.addWidget(edit)
            layout.addLayout(row)

        close_btn = QPushButton(self.tr("Закрыть"))
        close_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #e0e0e0;
                        border: 1px solid #aaa;
                        border-radius: 4px;
                        padding: 4px;
                    }
                    QPushButton:hover {
                        background-color: #c0c0c0;
                    }
                    QPushButton:pressed {
                        background-color: #a0a0a0;
                    }
                """)
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignCenter)


class EditProviderDialog(QDialog):
    def __init__(self, service_key, provider_data=None, parent=None):
        super().__init__(parent)
        self.service_key = service_key
        self.provider_data = provider_data or {}
        self.setWindowTitle(self.tr("Редактирование реквизитов") if provider_data else self.tr("Добавление реквизитов"))
        self.setMinimumWidth(400)
        self.setStyleSheet("background-color: white;")

        layout = QVBoxLayout(self)

        fields = [
            (self.tr("Название организации"), 'name'),
            (self.tr("ИНН"), 'inn'),
            (self.tr("КПП"), 'kpp'),
            (self.tr("Расчётный счёт"), 'account'),
            (self.tr("Банк"), 'bank'),
            (self.tr("БИК"), 'bik'),
            (self.tr("Корреспондентский счёт"), 'corr_account'),
            (self.tr("Лицевой счёт"), 'personal_account'),
            (self.tr("Назначение платежа"), 'payment_purpose'),
            (self.tr("Идентификатор платежа"), 'payment_identifier'),
            (self.tr("Адрес"), 'address'),
            (self.tr("Дополнительная информация"), 'extra_info')

        ]
        self.inputs = {}
        for label, key in fields:
            row = QHBoxLayout()
            row.addWidget(QLabel(label + ":"))
            edit = QLineEdit()
            edit.setText(self.provider_data.get(key, ''))
            row.addWidget(edit)
            layout.addLayout(row)
            self.inputs[key] = edit

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        button_box.setStyleSheet("""
                    QPushButton {
                        background-color: #e0e0e0;
                        border: 1px solid #aaa;
                        border-radius: 4px;
                        padding: 4px;
                    }
                    QPushButton:hover {
                        background-color: #c0c0c0;
                    }
                    QPushButton:pressed {
                        background-color: #a0a0a0;
                    }
                """)
        # --- Меняем названия кнопок ---
        ok_btn = button_box.button(QDialogButtonBox.Ok)
        if ok_btn:
            ok_btn.setText(self.tr("Сохранить"))

        cancel_btn = button_box.button(QDialogButtonBox.Cancel)
        if cancel_btn:
            cancel_btn.setText(self.tr("Отмена"))
        layout.addWidget(button_box)

    def get_data(self):
        data = {}
        for key, edit in self.inputs.items():
            data[key] = edit.text().strip()
        if self.provider_data.get('id'):
            data['id'] = self.provider_data['id']
        return data

    def accept(self):
        from database import save_provider, set_service_provider
        data = self.get_data()
        if not data.get('name'):
            QMessageBox.warning(self, self.tr("Ошибка"), self.tr("Название организации обязательно"))
            return  # <-- если здесь return, диалог не закрывается
        provider_id = save_provider(data)
        if self.service_key:
            set_service_provider(self.service_key, provider_id)
        super().accept()

class PaymentConfirmationDialog(QDialog):
    def __init__(self, items, service_name, parent=None):
        from decimal import Decimal
        """
        items: список кортежей (описание, сумма) например [(self.tr("Расход до снятия"), 150.0), (self.tr("Сумма по нормативу"), 200.0)]
        service_name: название услуги (для отображения в заголовке)
        """
        super().__init__(parent)
        self.setWindowTitle(self.tr("Подтверждение оплаты"))
        self.setMinimumWidth(450)
        self.setStyleSheet("background-color: white;")
        layout = QVBoxLayout(self)

        # Заголовок
        layout.addWidget(QLabel(self.tr("<b>Оплата за услугу: {name}</b>").format(name=service_name)))
        layout.addWidget(QLabel(self.tr("Будут оплачены:")))

        # Список позиций
        total = Decimal('0')
        for desc, amount in items:
            layout.addWidget(QLabel(self.tr("  • {desc}: {amount} руб.").format(desc=desc, amount=f"{amount:.2f}")))
            total += Decimal(str(amount))

        # Итоговая сумма
        layout.addWidget(QLabel(self.tr("<b>Итого без комиссии: {total} руб.</b>").format(total=f"{total:.2f}")))

        # Чекбокс комиссии
        self.fee_check = QCheckBox(self.tr("Мой банк берёт комиссию"))
        layout.addWidget(self.fee_check)

        # Кнопки
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        button_box.setStyleSheet("""
                    QPushButton {
                        background-color: #e0e0e0;
                        border: 1px solid #aaa;
                        border-radius: 4px;
                        padding: 4px;
                    }
                    QPushButton:hover {
                        background-color: #c0c0c0;
                    }
                    QPushButton:pressed {
                        background-color: #a0a0a0;
                    }
                """)
        #Меняем название кнопки Cancel
        cancel_btn = button_box.button(QDialogButtonBox.Cancel)
        if cancel_btn:
            cancel_btn.setText(self.tr("Отмена"))
        layout.addWidget(button_box)

        self.total = total

    def get_result(self):
        """Возвращает словарь с общей суммой и флагом применения комиссии."""
        return {
            'total': self.total,
            'apply_fee': self.fee_check.isChecked()
        }

if __name__ == "__main__":
    app = QApplication(sys.argv)

    install_translators(app)

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
        QCalendarWidget QWidget {
            color: black;
            background-color: white;
        }
        QCalendarWidget QToolButton {
            color: black;
            background-color: white;
            padding: 4px;
        }
        QCalendarWidget QToolButton:hover {
            background-color: #e0e0e0;
        }
        QCalendarWidget QMenu {
            color: black;
            background-color: white;
        }
        QCalendarWidget QSpinBox {
            color: black;
            background-color: white;
        }
        QCalendarWidget QAbstractItemView:enabled {
            color: black;
            background-color: white;
            selection-background-color: #4a90d9;
            selection-color: white;
        }
    """)

    # Инициализация базы данных (создаст файл communal.db)
    init_db()

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
        load_settings() # ← перезагружаем config.services из БД как объекты
        # после мастера услуги добавлены

    # Запускаем главное окно
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
