# Импортируем необходимые модули
import sys
from cx_Freeze import setup, Executable

# Настройка базового приложения
base = None
if sys.platform == 'win32': 
    base = 'Win32GUI'  # Используем Win32GUI для скрытия консоли у GUI-приложений
    # Если нужно консольное приложение - оставьте base=None

# Опции для сборки
build_options = {
    # Включаем дополнительные файлы (изображения, данные и т.д.)
    'include_files': ['icon.ico', 'icon.png', 'calculator.py',
                      'communal_calculator.py','config.py',
                      'file_manager.py', 'gui.py','readme.md'],
       
    # Включаем пакеты, которые использует ваше приложение
    'packages': ['tkinter', 'decimal', 'json', 'datetime', 'webbrowser', 'tempfile', 'os', 'sys'],
    
    # Включаем системные библиотеки Visual C++ для совместимости
    'include_msvcr': True,
    
    # Исключаем ненужные модули для уменьшения размера
    'excludes': ['test']
}

# Основная функция настройки cx_Freeze
setup(
    # Основная информация о программе
    name='Communal calculator',                    # Название вашей программы
    version='1.0',                   # Версия программы
    description='Calculates expenditures for house communal resourses',  # Описание
    author='Monoceros-engineer',              # Автор
    
    # Настройки сборки
    options={'build_exe': build_options},  # Применяем наши опции сборки
    
    # Настройки исполняемого файла
    executables=[
        Executable(
            'main.py',              # Главный файл вашей программы
            base=base,               # База (GUI или Console)
            target_name='Communal_calculator.exe',  # Имя итогового .exe файла
            icon='icon.ico'
        )
    ],
    
    # Классификаторы (для публикации, необязательно)
    classifiers=[
        # Указываем совместимые операционные системы
        'Operating System :: Microsoft :: Windows :: Windows 7',
        'Operating System :: Microsoft :: Windows :: Windows 10', 
        'Operating System :: Microsoft :: Windows :: Windows 11',
    ]
)
