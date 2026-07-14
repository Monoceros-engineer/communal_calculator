; Скрипт для установки Калькулятора коммуналки (версия 1.2)
; Сборка через Nuitka, папка main_pyside6.dist

[Setup]
AppName=Калькулятор коммуналки
AppVersion=1.2
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
OutputBaseFilename=CommunalCalculator_Setup_v1.2

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
var
  DeleteDataPage: TInputOptionWizardPage;

procedure InitializeWizard;
begin
  // Создаём страницу с галочкой для деинсталляции (она появится только при удалении)
  DeleteDataPage := CreateInputOptionPage(wpSelectTasks,
    'Удаление данных',
    'Удалить сохранённые данные?',
    'При удалении программы вы можете также удалить папку с вашими сохранениями (база данных, настройки).' + #13#10#13#10 +
    'Если вы планируете переустановить программу, оставьте данные, чтобы не потерять историю.',
    True, False);
  DeleteDataPage.Add('Удалить папку %APPDATA%\CommunalCalculator (включая базу данных communal.db)');
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  DataPath: string;
begin
  if CurUninstallStep = usUninstall then
  begin
    // Проверяем, поставлена ли галочка
    if DeleteDataPage.Values[0] then
    begin
      DataPath := ExpandConstant('{userappdata}\CommunalCalculator');
      if DirExists(DataPath) then
      begin
        if DelTree(DataPath, True, True, True) then
          MsgBox('Папка с сохранениями удалена.', mbInformation, MB_OK)
        else
          MsgBox('Не удалось полностью удалить папку с сохранениями. Проверьте, не запущена ли программа.', mbError, MB_OK);
      end;
    end;
  end;
end;