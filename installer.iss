; Скрипт для установки Калькулятора коммуналки (версия 1.1)
; Установка в Program Files, данные в %APPDATA%

[Setup]
AppName=Калькулятор коммуналки
AppVersion=1.1
AppPublisher=Monoceros-engineer
AppPublisherURL=https://github.com/Monoceros-engineer/communal_calculator
AppSupportURL=https://github.com/Monoceros-engineer/communal_calculator
AppUpdatesURL=https://github.com/Monoceros-engineer/communal_calculator

; Папка установки (Program Files, требует прав администратора)
DefaultDirName={commonpf}\CommunalCalculator
DefaultGroupName=Калькулятор коммуналки
UninstallDisplayIcon={app}\CommunalCalculator.exe

; Сжатие и выходной файл
Compression=lzma2
SolidCompression=yes
OutputDir=Output
OutputBaseFilename=CommunalCalculator_Setup_v1.1

; Иконка установщика
SetupIconFile=icon.ico

; Фоновое изображение мастера (164x314, BMP) – опционально
WizardImageFile=setup.bmp
; Mаленькая иконка в углу (55х55)
WizardSmallImageFile=small.bmp

; Требуем права администратора для установки в Program Files
PrivilegesRequired=admin

; Русский язык
ShowLanguageDialog=yes
LanguageDetectionMethod=uilanguage
[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

; Файлы для копирования
[Files]
Source: "CommunalCalculator.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "help.html"; DestDir: "{app}"; Flags: ignoreversion
Source: "icon.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "icon.png"; DestDir: "{app}"; Flags: ignoreversion
; Копируем папку assets (фоны и эффекты)
Source: "assets\*"; DestDir: "{app}\assets"; Flags: recursesubdirs

; Создаем ярлык на рабочем столе
[Tasks]
Name: "desktopicon"; Description: "Создать ярлык на рабочем столе"; GroupDescription: "Дополнительные задачи:"; Flags: unchecked

; Ярлыки
[Icons]
Name: "{group}\Калькулятор коммуналки"; Filename: "{app}\CommunalCalculator.exe"
Name: "{commondesktop}\Калькулятор коммуналки"; Filename: "{app}\CommunalCalculator.exe"; Tasks: desktopicon
Name: "{group}\Удалить программу"; Filename: "{uninstallexe}"

; Запуск после установки
[Run]
Filename: "{app}\CommunalCalculator.exe"; Description: "Запустить программу"; Flags: postinstall nowait skipifsilent