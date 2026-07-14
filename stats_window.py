from PySide6.QtWidgets import (QDialog,
                               QVBoxLayout,
                               QHBoxLayout,
                               QLabel,
                               QComboBox,
                               QSizePolicy,
                               QPushButton,
                               QScrollArea,
                               QWidget
                               )
from PySide6.QtCore import Qt

class StatisticsWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Статистика")
        self.setMinimumSize(1200, 700)
        self.setStyleSheet("background-color: white;")

        # Основной layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Верхняя панель: две группы управления
        top_layout = QHBoxLayout()
        top_layout.setSpacing(20)
        # Левая группа: Год
        left_group = QHBoxLayout()
        left_group.addWidget(QLabel("Год:"))
        self.year_combo = QComboBox()
        self.year_combo.currentIndexChanged.connect(self.update_stats)
        left_group.addWidget(self.year_combo)
        left_group.addStretch()
        top_layout.addLayout(left_group)
     
        # Правая группа: Группировка
        right_group = QHBoxLayout()
        right_group.addWidget(QLabel("Группировка:"))
        self.group_combo = QComboBox()
        self.group_combo.addItems(["По месяцам", "По кварталам", "По годам"])
        self.group_combo.currentIndexChanged.connect(self.update_stats)
        right_group.addWidget(self.group_combo)
        right_group.addStretch()
        top_layout.addLayout(right_group)

        layout.addLayout(top_layout)

        # Холсты для графиков (matplotlib)
        from matplotlib.figure import Figure
        from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
        self.figure = Figure(figsize=(8, 5), dpi=100)
        # Левый холст для круговой диаграммы
        self.figure_pie = Figure(figsize=(4, 4), dpi=100)
        self.canvas_pie = FigureCanvas(self.figure_pie)
        self.canvas_pie.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Правый холст (линейный график) с заголовком
        self.figure_line = Figure(figsize=(6, 4), dpi=100)
        self.canvas_line = FigureCanvas(self.figure_line)
        self.canvas_line.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Создаём контейнер для правой части (заголовок + холст + прокрутка)
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(5)

        # Заголовок над линейным графиком
        self.line_title = QLabel("Динамика расходов")
        self.line_title.setAlignment(Qt.AlignCenter)
        self.line_title.setStyleSheet("font-weight: bold; font-size: 14px;")
        right_layout.addWidget(self.line_title)

        # Оборачиваем холст в QScrollArea
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setWidget(self.canvas_line)
        right_layout.addWidget(self.scroll_area)


        # Размещаем два холста в горизонтальном layout
        charts_layout = QHBoxLayout()
        charts_layout.addWidget(self.canvas_pie, 1)
        charts_layout.addWidget(right_widget, 1)      # правый – содержит заголовок + скролл
        layout.addLayout(charts_layout)

        BUTTON_STYLE = """
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

        # Кнопка закрытия
        close_btn = QPushButton("Закрыть")
        close_btn.setStyleSheet(BUTTON_STYLE)
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignCenter)

        # Загружаем доступные годы
        self.load_years()

    def load_years(self):
        """Заполняет комбобокс годами из БД."""
        import sqlite3
        from paths import get_db_path
        self.year_combo.clear()
        try:
            conn = sqlite3.connect(get_db_path())
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT strftime('%Y', date) as year FROM bills ORDER BY year DESC")
            years = [row[0] for row in cursor.fetchall()]
            conn.close()
            if years:
                self.year_combo.addItem("Все годы") 
                self.year_combo.addItems(years)
            else:
                self.year_combo.addItem("Нет данных")
                self.year_combo.setEnabled(False)
        except Exception as e:
            self.year_combo.addItem("Ошибка")
            self.year_combo.setEnabled(False)

    def update_stats(self):
        """Обновляет графики при выборе года."""
        if self.year_combo.count() == 0 or not self.year_combo.isEnabled():
            return
        selected = self.year_combo.currentText()
        if selected in ("Нет данных", "Ошибка"):
            return
        
        # Получаем выбранную группировку
        group = self.group_combo.currentText()

        import sqlite3
        import pandas as pd
        from paths import get_db_path

        try:
            conn = sqlite3.connect(get_db_path())

            # Определяем условие для фильтрации
            if selected == "Все годы":
                condition = "1=1"          # без фильтра по году
                params = ()
            else:
                condition = "strftime('%Y', bills.date) = ?"
                params = (selected,)

            # --- Круговая диаграмма (без изменений) ---
            query_pie = f"""
                SELECT service_name, SUM(total) as total
                FROM bill_details
                JOIN bills ON bills.id = bill_details.bill_id
                WHERE {condition}
                GROUP BY service_name
                ORDER BY total DESC
            """
            df_pie = pd.read_sql_query(query_pie, conn, params=params)

        # --- Линейный график с группировкой ---
        # В зависимости от выбранной группировки формируем выражение для периода
            if group == "По месяцам":
                period_expr = "strftime('%Y-%m', date)"
            elif group == "По кварталам":
                period_expr = "strftime('%Y', date) || '-Q' || ((strftime('%m', date) + 2) / 3)"
            else:  # "По годам"
                period_expr = "strftime('%Y', date)"

            query_line = f"""
                SELECT {period_expr} as period, SUM(total_with_fee) as total
                FROM bills
                WHERE {condition}
                GROUP BY period
                ORDER BY MIN(date)
            """
            df_line = pd.read_sql_query(query_line, conn, params=params)

            conn.close()

            # Очищаем оба холста
            self.figure_pie.clf()
            self.figure_line.clf()
                        
            # Круговая диаграмма на левом холсте
            ax1 = self.figure_pie.add_subplot(111)
            if not df_pie.empty:
                ax1.pie(df_pie['total'], labels=df_pie['service_name'], autopct='%1.1f%%')
                ax1.set_title("Распределение расходов")
            else:
                ax1.text(0.5, 0.5, "Нет данных", ha='center', va='center')
            self.canvas_pie.draw()

            # Линейный график на правом холсте
            ax2 = self.figure_line.add_subplot(111)
            if not df_line.empty:
                # Проверяем, есть ли колонка 'period' (если нет, используем первый столбец)
                if 'period' in df_line.columns:
                    x_data = df_line['period']
                else:
                    x_data = df_line.iloc[:, 0]  # берём первый столбец

                ax2.plot(x_data, df_line['total'], marker='o', linestyle='-', color='#2E86C1')
                ax2.set_xlabel("Период")
                ax2.set_ylabel("Сумма, руб.")
                ax2.grid(True, linestyle='--', alpha=0.6)

                # Настройка подписей оси X
                if len(x_data) > 10:
                    # Если точек много, поворачиваем подписи и прореживаем
                    step = max(1, len(x_data) // 10)
                    tick_positions = range(0, len(x_data), step)
                    ax2.set_xticks(tick_positions)
                    ax2.set_xticklabels([x_data.iloc[i] for i in tick_positions], rotation=45, ha='right')
                else:
                    ax2.set_xticks(range(len(x_data)))
                    ax2.set_xticklabels(x_data, rotation=45, ha='right')

                # Адаптация ширины для длинных рядов
                if selected == "Все годы" and self.group_combo.currentText() == "По месяцам" and len(x_data) > 20:
                    extra_width = max(0, (len(x_data) - 20) * 30)
                    new_width = 600 + extra_width
                    self.figure_line.set_figwidth(new_width / 100)
                    self.canvas_line.setFixedWidth(new_width)
                else:
                    self.figure_line.set_figwidth(6)
                    self.canvas_line.setFixedWidth(600)
            else:
                ax2.text(0.5, 0.5, "Нет данных", ha='center', va='center')
            self.canvas_line.draw()

        except Exception as e:
            print("Ошибка обновления статистики:", e)
            # Можно показать сообщение пользователю, но для простоты оставим так