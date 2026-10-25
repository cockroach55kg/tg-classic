# TG Classic Windows x64

The Windows package builds the same pinned Telegram Desktop source and Classic patches as the Mac application. It requires an MSVC x64 build host; renaming the Mac binary cannot produce a Windows executable.

`windows/build.ps1` prepares upstream dependencies, builds Debug, verifies the x64 PE header, and produces a portable ZIP. The `TG Classic Windows` workflow runs this on a Windows runner and keeps downloadable artifacts for 30 days. The workflow is manual and uses a private development preview by default. Own Telegram API credentials can be supplied as `TGCLASSIC_API_ID` and `TGCLASSIC_API_HASH` secrets.

On a Windows machine, prepare the pinned checkout with `python apply.py`, initialize recursive submodules and run the script from an MSVC x64 Native Tools terminal. `TGCLASSIC_TEST_API=true` explicitly enables the same limited upstream development credentials used by the local Mac preview. Only Debug is built. No account data belongs in the output ZIP.

## Проверенный пакет

Первый Windows x64 Debug пакет собран: [run 40186825974](https://github.com/cockroach55kg/tg-classic/actions/runs/40186825974), исходная ревизия `14dde67`. Отдельная [проверка пакета](https://github.com/cockroach55kg/tg-classic/actions/runs/40211639958) подтвердила контрольную сумму, создание нативного окна и работу процесса 15 секунд с пустым профилем. Артефакт `TG-Classic-Windows-x64-verified` доступен 30 дней через Actions после входа в GitHub.

Локальный файл: `artifacts/windows/TG-Classic-Windows-x64.zip`. Распакуйте всю папку и запустите `TG Classic.exe`; DLL должны остаться рядом. Это portable-сборка без Authenticode-подписи, с ограниченными реквизитами upstream для личной проверки. Для публичного релиза нужны собственные [API ID и Hash](https://core.telegram.org/api/obtaining_api_id). Вход, обмен сообщениями и звонки в этом прогоне не проверялись. В первой сборке свойства PE-файла ещё содержат исходные данные Telegram Desktop; `brand.py` применяет имя TG Classic к этим полям при следующей сборке. Имя окна, файл и иконка уже TG Classic.
