# Offline Android UI fixtures

The opt-in `tgclassicQa=true` build uses a separate `com.tgclassic.client.web.qa` package. It includes a QA-only activity that opens the actual Telegram screens with fictional local users/messages and checks bitmap avatar rendering. Normal `android/build.py` explicitly sets `tgclassicQa=false`; this activity and its manifest entry must be absent from delivered APKs.

Run `python3 android/qa/prepare.py` before the QA Gradle build to generate its manifest under ignored `android/local/`. QA Java sources are included only by that explicit Gradle property. This is a developer fixture build, never an end-user client.

After installing the SDK/emulator and building the QA APK into `artifacts/android-qa/TG-Classic-QA.apk`, use `python3 android/qa/run.py dialogs --install`, then `settings` and `chat`; add `--dark` for the night palette. The runner refuses physical devices or any emulator other than `TGClassicQA` on port5556. It disables networking and verifies airplane mode before launching. Screenshots/logs go to `evidence/android-r2/`. The fixture asserts the palette, square bitmap rendering, editor insets and visible real message cells. The runner verifies the settings UI tree and opens its actual navigation tab when needed.

These fixtures verify rendering and navigation only. They do not verify server authorization, delivery, calling, recording or background notifications. Real account data and attached user screenshots are never part of these fixtures.
