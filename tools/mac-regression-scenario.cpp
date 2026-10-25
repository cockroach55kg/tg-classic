#ifdef _DEBUG
#include "test/test_runner.h"
#include "test/test_log.h"
#include "test/test_palette.h"
#include "boxes/connection_box.h"
#include "core/application.h"
#include "core/core_settings.h"
#include "main/main_account.h"
#include "dialogs/ui/dialogs_stories_list.h"
#include "ui/boxes/confirm_box.h"
#include "ui/classic_style.h"
#include "ui/dynamic_image.h"
#include "ui/effects/outline_segments.h"
#include "ui/image/image_prepare.h"
#include "ui/round_rect.h"
#include "ui/ui_utility.h"
#include "ui/widgets/fields/input_field.h"
#include "window/main_window.h"
#include "window/notifications_utilities.h"
#include "window/window_controller.h"
#include "styles/style_dialogs.h"
#include "styles/style_layers.h"
#include "styles/style_widgets.h"
#include "styles/style_window.h"
#include <QtWidgets/QApplication>
#include <QtWidgets/QMenuBar>
#include <cmath>

namespace Test {
namespace {

Window::MainWindow *Primary() {
	for (const auto widget : QApplication::topLevelWidgets()) {
		if (const auto window = dynamic_cast<Window::MainWindow*>(widget)) {
			if (window->isPrimary() && window->isVisible()) return window;
		}
	}
	return nullptr;
}

double Contrast(QColor a, QColor b) {
	const auto luminance = [](QColor c) {
		const auto channel = [](double v) {
			return (v <= .04045) ? v / 12.92 : std::pow((v + .055) / 1.055, 2.4);
		};
		return .2126 * channel(c.redF()) + .7152 * channel(c.greenF()) + .0722 * channel(c.blueF());
	};
	const auto x = luminance(a), y = luminance(b);
	return (std::max(x, y) + .05) / (std::min(x, y) + .05);
}

class Thumbnail final : public Ui::DynamicImage {
public:
	explicit Thumbnail(QColor color) : _color(color) {}
	std::shared_ptr<Ui::DynamicImage> clone() override {
		return std::make_shared<Thumbnail>(_color);
	}
	QImage image(int size) override {
		auto image = QImage(QSize(size, size), QImage::Format_ARGB32_Premultiplied);
		image.fill(_color);
		return image;
	}
	void subscribeToUpdates(Fn<void()>) override {}
private:
	QColor _color;
};

} // namespace

void SetupScenario(not_null<Runner*> runner) {
	struct State {
		QPointer<Ui::RpWidget> preview;
		QPointer<Dialogs::Stories::List> stories;
	};
	const auto state = std::make_shared<State>();
	runner->onFinish([=] { delete state->preview.data(); });
	runner->waitEvent(u"launch_finished"_q);
	runner->add({ .name = u"square-corner crash regression"_q, .run = [] {
		const auto corners = Images::PrepareCorners(0, st::boxBg);
		for (const auto &corner : corners) {
			Check(!corner.isNull(), u"zero-radius corner has a valid raster"_q);
			Check(corner.pixelColor(0, 0) == st::boxBg->c,
				u"zero-radius corner is square and filled"_q);
		}
		const auto rect = Ui::RoundRect(0, st::boxBg);
		Check(!Core::App().settings().nativeNotifications(),
			u"classic notifications are the default"_q);
		auto image = QImage(64, 64, QImage::Format_ARGB32_Premultiplied);
		image.fill(Qt::transparent);
		auto p = QPainter(&image);
		Ui::PaintOutlineSegments(p, QRectF(4, 4, 56, 56), { { QBrush(Qt::red), 2. } });
		p.end();
		for (const auto point : { QPoint(4, 4), QPoint(60, 4), QPoint(4, 60), QPoint(60, 60) }) {
			Check(image.pixelColor(point).alpha() > 0, u"story outline keeps its square corners"_q);
		}
	}});
	std::shared_ptr<const PaletteSwitch> switched;
	for (const auto night : { false, true }) {
		const auto mode = night ? u"night"_q : u"day"_q;
		if (night) {
			switched = AppendPaletteSwitch(runner, {
				.name = u"classic night"_q,
				.mode = PaletteMode::Night,
				.sampleLabel = u"windowBg"_q,
				.sample = [] { return st::windowBg->c; },
			});
		}
		runner->actOnWidget(u"palette checks "_q + mode, Primary, [=](QWidget *widget) {
			Check((Ui::Classic::Surface().lightness() < 128) == night,
				u"classic surface follows the active palette"_q);
			Check(Contrast(Ui::Classic::TitleText(), Ui::Classic::Title()) >= 4.5,
				u"title text is readable in both themes"_q);
			Check(Contrast(Ui::Classic::Text(), Ui::Classic::Surface()) >= 7.,
				u"classic text has strong contrast"_q);
			Check(Contrast(st::defaultInputField.textFg->c, st::defaultInputField.textBg->c) >= 4.5,
				u"input text is readable on its actual background"_q);
			const auto bars = widget->findChildren<QMenuBar*>();
			Check(bars.size() == 1 && bars.front()->styleSheet().contains(Ui::Classic::Surface().name()),
				u"menu palette refreshes after switching themes"_q);
			const auto window = dynamic_cast<Window::MainWindow*>(widget);
			window->controller().show(ProxiesBoxController::CreateOwningBox(&window->account()),
				Ui::LayerOption::KeepOther, anim::type::instant);
			Check(window->controller().isLayerShown(), u"proxy settings open without a crash"_q);
		});
		runner->captureWidget(u"proxy-"_q + mode, Primary);
		runner->actOnWidget(u"delete confirmation "_q + mode, Primary, [](QWidget *widget) {
			const auto window = dynamic_cast<Window::MainWindow*>(widget);
			window->controller().hideLayer(anim::type::instant);
			window->controller().show(Ui::MakeConfirmBox({
				.text = u"Delete this demonstration message?"_q,
				.confirmed = [] {},
				.confirmText = u"Delete"_q,
				.cancelText = u"Cancel"_q,
			}), Ui::LayerOption::KeepOther, anim::type::instant);
			Check(window->controller().isLayerShown(),
				u"confirmation uses the repaired modal frame"_q);
		});
		runner->captureWidget(u"confirmation-"_q + mode, Primary);
		runner->actOnWidget(u"classic visual preview "_q + mode, Primary, [=](QWidget *widget) {
			const auto window = dynamic_cast<Window::MainWindow*>(widget);
			window->controller().hideLayer(anim::type::instant);
			delete state->preview.data();
			const auto preview = new Ui::RpWidget(window->body().get());
			state->preview = preview;
			preview->setGeometry(10, 45, 760, 430);
			preview->paintRequest() | rpl::on_next([=] {
				auto p = QPainter(preview);
				Ui::Classic::Panel(p, preview->rect(), Ui::Classic::Surface(), st::lineWidth);
			}, preview->lifetime());
			const auto field = new Ui::InputField(preview, st::defaultInputField,
				rpl::single(u"Message"_q), u"Readable input text"_q);
			field->setGeometry(20, 18, 450, 48);
			field->show();
			auto content = Dialogs::Stories::Content();
			for (auto i = 0; i != 4; ++i) {
				auto element = Dialogs::Stories::Element();
				element.id = i + 1;
				element.name = u"Story %1"_q.arg(i + 1);
				element.thumbnail = std::make_shared<Thumbnail>(QColor::fromHsv(i * 70, 110, 180));
				element.count = 4;
				element.unreadCount = i;
				content.elements.push_back(std::move(element));
			}
			content.total = 4;
			const auto stories = new Dialogs::Stories::List(preview, st::dialogsStoriesList,
				rpl::single(std::move(content)));
			state->stories = stories;
			stories->setLayoutConstraints(QPoint(20, 90), style::al_left,
				QRect(20, 90, 700, st::dialogsStoriesList.full.height));
			stories->setExpandedHeight(st::dialogsStoriesList.full.height);
			stories->show();
			const auto notification = new Ui::RpWidget(preview);
			notification->setGeometry(20, 270, st::notifyWidth, st::notifyMinHeight);
			notification->paintRequest() | rpl::on_next([=] {
				auto p = QPainter(notification);
				Window::Notifications::PaintClassicNotificationFrame(p, notification->rect());
				p.setPen(Ui::Classic::Text());
				p.setFont(st::normalFont->f);
				p.drawText(st::notifyPhotoPos.x(), st::notifyItemTop + st::normalFont->ascent,
					u"New message"_q);
			}, notification->lifetime());
			notification->show();
			preview->show();
			preview->raise();
			Check(st::notifyPhotoPos.y() + st::notifyPhotoSize < st::notifyMinHeight,
				u"notification content fits below the title bar"_q);
		});
		runner->captureWidget(u"classic-preview-"_q + mode, [=] { return state->preview.data(); });
		runner->add({ .name = u"collapse stories "_q + mode, .run = [=] {
			state->stories->setExpandedHeight(0);
		}});
		runner->captureWidget(u"classic-collapsed-"_q + mode, [=] { return state->preview.data(); });
		runner->actOnWidget(u"remove preview "_q + mode, Primary, [=](QWidget*) {
			delete state->preview.data();
		});
	}
	const auto restored = AppendPaletteRestore(runner, switched);
	runner->add({ .name = u"theme restored"_q, .then = [=] {
		Check(restored->restored(), u"day theme restored after regression checks"_q);
	}});
}

} // namespace Test
#endif // _DEBUG
