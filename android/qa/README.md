# Offline Android UI fixtures

The opt-in `tgclassicQa=true` build uses a separate `com.tgclassic.client.web.qa` package. It includes a QA-only activity that opens the actual Telegram screens with fictional local users/messages and checks bitmap avatar rendering. Normal `android/build.py` explicitly sets `tgclassicQa=false`; this activity and its manifest entry must be absent from delivered APKs.

Run `python3 android/qa/prepare.py` before the QA Gradle build to generate its manifest under ignored `android/local/`. QA Java sources are included only by that explicit Gradle property. This is a developer fixture build, never an end-user client.

After installing the SDK/emulator and building the QA APK into `artifacts/android-qa/TG-Classic-QA.apk`, use `python3 android/qa/run.py group --install`. Supported screens are `dialogs`, `settings`, `chat`, `group` and `folders`; add `--dark` for the night palette. The runner refuses physical devices or any emulator other than `TGClassicQA` on port5556. It disables networking and verifies airplane mode before launching. Screenshots/logs go to `evidence/android-r3/`.

The fixture asserts the palette, square bitmap rendering, editor insets and visible real message cells. Group frames are rendered from actual cell drawables to verify that connected and standalone messages share one edge. Composer controls must share a baseline and meet the editor without gaps or overlap, including the extra bot command button. The runner verifies the settings UI tree and opens its actual navigation tab when needed.

Run `python3 android/qa/regressions.py` after the QA install for both palettes, real popup menu rows, folder scrolling and typing with the keyboard shown and hidden. The runner sets the emulator's system night mode before each fixture; the activity continuously asserts that the requested palette stays active during interactions. Framebuffer RGB checks cover the body, popup and editor, allowing at most two levels per channel for GPU compositing. This catches a palette reset even when theme metadata still looks plausible. The suite writes a screenshot checksum report in `evidence/android-r3/verification.json`. Inspect the screenshots as well as the assertions; passing the fixture alone is not a complete visual review.

These fixtures verify rendering and navigation only. They do not verify server authorization, delivery, calling, recording or background notifications. Real account data and attached user screenshots are never part of these fixtures.
