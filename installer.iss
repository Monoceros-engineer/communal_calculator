; Скрипт для установки Калькулятора коммуналки (версия 1.3)
; Сборка через Nuitka, папка main_pyside6.dist

[Setup]
AppName=Калькулятор коммуналки
AppVersion=1.3
AppPublisher=Monoceros-engineer
AppPublisherURL=https://github.com/Monoceros-engineer/communal_calculator
AppSupportURL=https://github.com/Monoceros-engineer/communal_calculator
AppUpdatesURL=https://github.com/Monoceros-engineer/communal_calculator

; Папка установки (Program Files, требует прав администратора)
DefaultDirName={commonpf}\CommunalCalculator
DefaultGroupName=Калькулятор коммуналки
UninstallDisplayIcon={app}\main_pyside6.exe

; Сжатие и выходной файл
Compression=lzma2
SolidCompression=yes
OutputDir=Output
OutputBaseFilename=CommunalCalculator_Setup_v1.3

; Иконка установщика
SetupIconFile=icon.ico

; Фоновое изображение мастера (164x314, BMP) – если есть
WizardImageFile=setup.bmp
; Маленькая иконка в углу (55x55)
WizardSmallImageFile=small.bmp

; Требуем права администратора для установки в Program Files
PrivilegesRequired=admin

; Русский язык
ShowLanguageDialog=yes
LanguageDetectionMethod=uilanguage
[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

; Файлы для копирования (всё из папки сборки Nuitka)
[Files]
Source: "main_pyside6.dist\*"; DestDir: "{app}"; Flags: recursesubdirs

; Создаем ярлык на рабочем столе
[Tasks]
Name: "desktopicon"; Description: "Создать ярлык на рабочем столе"; GroupDescription: "Дополнительные задачи:"; Flags: unchecked

; Ярлыки
[Icons]
Name: "{group}\Калькулятор коммуналки"; Filename: "{app}\main_pyside6.exe"
Name: "{commondesktop}\Калькулятор коммуналки"; Filename: "{app}\main_pyside6.exe"; Tasks: desktopicon
Name: "{group}\Удалить программу"; Filename: "{uninstallexe}"

; Запуск после установки
[Run]
Filename: "{app}\main_pyside6.exe"; Description: "Запустить программу"; Flags: postinstall nowait skipifsilent

; ======================================================================
; КОД ДЛЯ УДАЛЕНИЯ ДАННЫХ ПРИ ДЕИНСТАЛЛЯЦИИ
; ======================================================================

[Code]
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  DataPath: string;
begin
  if CurUninstallStep = usUninstall then
  begin
    if MsgBox('Удалить сохранённые данные (базу данных и настройки)?', mbConfirmation, MB_YESNO) = IDYES then
    begin
      DataPath := ExpandConstant('{userappdata}\CommunalCalculator');
      if DirExists(DataPath) then
        DelTree(DataPath, True, True, True);
    end;
  end;
end;