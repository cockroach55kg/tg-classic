#ifdef _DEBUG
#include "test/test_runner.h"
#include "test/test_log.h"
#include "lang/lang_keys.h"
#include "window/main_window.h"
#include "window/themes/classic_theme.h"

#include <QtGui/QAction>
#include <QtGui/QImage>
#include <QtWidgets/QApplication>
#include <QtWidgets/QMenu>
#include <QtWidgets/QMenuBar>

namespace Test {
namespace {

QWidget *PrimaryWindow() {
	for (const auto widget : QApplication::topLevelWidgets()) {
		if (const auto window = dynamic_cast<Window::MainWindow*>(widget)) {
			if (window->isPrimary() && window->isVisible()) {
				return window;
			}
		}
	}
	return nullptr;
}

} // namespace

void SetupScenario(not_null<Runner*> runner) {
	struct State {
		QPointer<QAction> wallpaper;
	};
	const auto state = std::make_shared<State>();
	runner->onFinish([=] { state->wallpaper = nullptr; });
	runner->waitEvent(u"launch_finished"_q);
	runner->actOnWidget(u"find classic menu"_q, PrimaryWindow, [=](QWidget *widget) {
		const auto bars = widget->findChildren<QMenuBar*>();
		Check(bars.size() == 1, u"one in-window menu bar"_q,
			u"count=%1"_q.arg(bars.size()));
		auto matches = 0;
		for (const auto bar : bars) {
			for (const auto entry : bar->actions()) {
				if (const auto menu = entry->menu()) {
					for (const auto action : menu->actions()) {
						if (action->text() == tr::lng_classic_wallpaper_visible(tr::now)) {
							state->wallpaper = action;
							++matches;
						}
					}
				}
			}
		}
		Check(matches == 1, u"wallpaper action exists once"_q,
			u"count=%1"_q.arg(matches));
		Check(!Window::Theme::Classic::WallpaperVisible(),
			u"fresh profile starts without wallpaper"_q);
	});
	for (const auto visible : { true, false }) {
		runner->add({
			.name = visible ? u"show wallpaper"_q : u"hide wallpaper"_q,
			.skipReason = [=] {
				return state->wallpaper ? QString() : u"menu action was not found"_q;
			},
			.run = [=] { state->wallpaper->trigger(); },
			.then = [=] {
				Check(Window::Theme::Classic::WallpaperVisible() == visible,
					u"menu updates wallpaper visibility"_q,
					u"expected=%1 actual=%2"_q.arg(visible).arg(
						Window::Theme::Classic::WallpaperVisible()));
				Check(state->wallpaper->isChecked() == visible,
					u"menu check follows wallpaper visibility"_q);
			},
		});
	}
	runner->captureAndInspect(u"mac-native-startup"_q, PrimaryWindow, {},
		[](QWidget *widget, const QImage &image) {
			const auto window = dynamic_cast<Window::MainWindow*>(widget);
			const auto title = window ? window->titleWidget() : nullptr;
			Check(title && title->isVisible(), u"custom title is visible"_q);
			if (!title) {
				return;
			}
			const auto scale = double(image.width()) / widget->width();
			const auto origin = title->mapTo(widget, QPoint());
			const auto band = QRect(
				qRound((origin.x() + 4) * scale),
				qRound((origin.y() + 4) * scale),
				qRound((title->width() - 104) * scale),
				qRound((title->height() - 8) * scale));
			const auto contained = !band.isEmpty() && image.rect().contains(band);
			Check(contained, u"title band is inside the captured window"_q);
			auto gray = 0;
			for (auto y = 0; y < image.height(); y += 2) {
				for (auto x = 0; x < image.width(); x += 2) {
					gray += (image.pixelColor(x, y).rgb() == qRgb(192, 192, 192));
				}
			}
			Check(gray > image.width() * image.height() / 12,
				u"classic gray covers the main window"_q,
				u"samples=%1"_q.arg(gray));
			if (contained) {
				auto navy = 0;
				auto samples = 0;
				for (auto y = band.top(); y <= band.bottom(); y += 2) {
					for (auto x = band.left(); x <= band.right(); x += 2) {
						++samples;
						navy += (image.pixelColor(x, y).rgb() == qRgb(0, 0, 128));
					}
				}
				Check(navy > samples / 2, u"navy title band is painted"_q,
					u"navy=%1 samples=%2"_q.arg(navy).arg(samples));
			}
		});
}

} // namespace Test
#endif // _DEBUG
