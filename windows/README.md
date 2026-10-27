# TG Classic Windows x64

Готовые файлы: [установщик EXE](https://github.com/cockroach55kg/tg-classic/releases/download/v0.1.0-preview.1/TG-Classic-Windows-x64-Setup.exe) и [portable ZIP](https://github.com/cockroach55kg/tg-classic/releases/download/v0.1.0-preview.1/TG-Classic-Windows-x64.zip). Установщик рассчитан на Windows 10/11 x64, использует прежнюю иконку TG Classic и предлагает русский или английский язык.

Установка выполняется для текущего пользователя в `%LOCALAPPDATA%\Programs\TG Classic`. Ярлык в меню «Пуск» запускает клиент с отдельным профилем `%APPDATA%\TG Classic`; ярлык рабочего стола предлагается отдельно. Удаление программы сохраняет профиль. Portable-профили автоматически не переносятся. В работающий клиент установщик принудительно не вмешивается.

Исходники установщика: `installer.iss`, `package-installer.ps1`, `verify-installer.ps1`. Манифест `installer-manifest.json` закрепляет SHA-256 исходного ZIP и исполняемого файла. Рабочий процесс `windows-installer.yml` собирает пакет через Inno Setup 6 и проверяет установку, ярлыки, повторную установку, запуск нативного окна и удаление в отдельной Windows VM. В проверке используется только пустой профиль и собственный тестовый файл. Логи и результат проверки публикуются вместе с артефактом сборки.

```powershell
./windows/package-installer.ps1 -Archive ./artifacts/windows/TG-Classic-Windows-x64.zip
```

`verify-installer.ps1` разрешает установку и удаление только в одноразовой GitHub Actions VM и отказывается трогать существующие приложение, профиль или ярлыки. Обычная установка выполняется запуском готового EXE.

The Windows package builds the same pinned Telegram Desktop source and Classic patches as the Mac application. It requires an MSVC x64 build host; renaming the Mac binary cannot produce a Windows executable.

`windows/build.ps1` prepares upstream dependencies, builds Debug, verifies the x64 PE header, and produces a portable ZIP. The `TG Classic Windows` workflow runs this on a Windows runner and keeps downloadable artifacts for 30 days. The workflow is manual and uses a private development preview by default. Own Telegram API credentials can be supplied as `TGCLASSIC_API_ID` and `TGCLASSIC_API_HASH` secrets.

On a Windows machine, prepare the pinned checkout with `python apply.py`, initialize recursive submodules and run the script from an MSVC x64 Native Tools terminal. `TGCLASSIC_TEST_API=true` explicitly enables the same limited upstream development credentials used by the local Mac preview. Only Debug is built. No account data belongs in the output ZIP.

## Проверенный пакет

Первый Windows x64 Debug пакет собран: [run 40186825974](https://github.com/cockroach55kg/tg-classic/actions/runs/40186825974), исходная ревизия `14dde67`. Отдельная [проверка пакета](https://github.com/cockroach55kg/tg-classic/actions/runs/40212157556) подтвердила контрольную сумму, создание нативного окна и работу процесса 15 секунд с пустым профилем. Артефакт `TG-Classic-Windows-x64-verified` доступен 30 дней через Actions после входа в GitHub.

Локальный файл: `artifacts/windows/TG-Classic-Windows-x64.zip`. Распакуйте всю папку и запустите `TG Classic.exe`; DLL должны остаться рядом. Это portable-сборка без Authenticode-подписи, с ограниченными реквизитами upstream для личной проверки. Для публичного релиза нужны собственные [API ID и Hash](https://core.telegram.org/api/obtaining_api_id). Вход, обмен сообщениями и звонки в этом прогоне не проверялись. В первой сборке свойства PE-файла ещё содержат исходные данные Telegram Desktop; `brand.py` применяет имя TG Classic к этим полям при следующей сборке. Имя окна, файл и иконка уже TG Classic.

ZIP: 152 217 653 байта. SHA-256: `0fb59040f3a491760e9637229a0b90fcc75c278ba3ab146c71ee8dabffbb369d`. Дополнительный прогон сохранил снимок окна; оформление визуально проверено. Исполняемый файл в ZIP совпадает с проверенным процессом побайтово. Будущие артефакты содержат ZIP и результаты проверки без повторной копии распакованного приложения.
