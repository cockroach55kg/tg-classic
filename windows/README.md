# TG Classic Windows x64

The Windows package builds the same pinned Telegram Desktop source and Classic patches as the Mac application. It requires an MSVC x64 build host; renaming the Mac binary cannot produce a Windows executable.

`windows/build.ps1` prepares upstream dependencies, builds Debug, verifies the x64 PE header, and produces a portable ZIP. The `TG Classic Windows` workflow runs this on a Windows runner and keeps downloadable artifacts for 30 days. The workflow is manual and uses a private development preview by default. Own Telegram API credentials can be supplied as `TGCLASSIC_API_ID` and `TGCLASSIC_API_HASH` secrets.

On a Windows machine, prepare the pinned checkout with `python apply.py`, initialize recursive submodules and run the script from an MSVC x64 Native Tools terminal. `TGCLASSIC_TEST_API=true` explicitly enables the same limited upstream development credentials used by the local Mac preview. Only Debug is built. No account data belongs in the output ZIP.
