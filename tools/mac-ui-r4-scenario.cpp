#ifdef _DEBUG
#include "test/test_runner.h"
#include "test/test_log.h"
#include "test/test_palette.h"
#include "test/test_widgets.h"
#include "chat_helpers/message_field.h"
#include "media/audio/media_audio.h"
#include "media/view/media_view_playback_controls.h"
#include "media/player/media_player_button.h"
#include "ui/classic_style.h"
#include "ui/controls/emoji_button.h"
#include "ui/controls/send_button.h"
#include "ui/effects/animation_value.h"
#include "ui/widgets/fields/input_field.h"
#include "ui/widgets/continuous_sliders.h"
#include "ui/widgets/dropdown_menu.h"
#include "window/main_window.h"
#include "styles/style_chat_helpers.h"
#include "styles/style_media_view.h"
#include <QtWidgets/QApplication>
#include <QtWidgets/QTextEdit>
#include <QtGui/QTextDocument>
#include <QtGui/QMouseEvent>

// Exercise the production geometry initializer without requiring an account.
void InitMessageFieldGeometry(not_null<Ui::InputField*> field);

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
QColor Pixel(const QImage &image, QPoint point) {
	return image.pixelColor(point * image.devicePixelRatio());
}
void Relief(const QImage &image, QRect rect, bool raised, const QString &name) {
	const auto top = Pixel(image, rect.topLeft() + QPoint(4, 0));
	const auto bottom = Pixel(image, rect.bottomRight() - QPoint(4, 0));
	Check(top.alpha() == 255 && bottom.alpha() == 255
		&& (raised ? top.lightness() > bottom.lightness() : top.lightness() < bottom.lightness()),
		name + (raised ? u" raised opaque frame"_q : u" pressed opaque frame"_q));
}
class Delegate final : public Media::View::PlaybackControls::Delegate {
public:
	int play = 0, pause = 0, fullscreen = 0, restore = 0, pip = 0, mute = 0, seek = 0;
	float64 volume = .7, speed = 1.;
	void playbackControlsPlay() override { ++play; }
	void playbackControlsPause() override { ++pause; }
	void playbackControlsSeekProgress(crl::time) override {}
	void playbackControlsSeekFinished(crl::time) override { ++seek; }
	void playbackControlsVolumeChanged(float64 v) override { volume = v; }
	float64 playbackControlsCurrentVolume() override { return volume; }
	void playbackControlsVolumeToggled() override { ++mute; volume = volume ? 0. : .7; }
	void playbackControlsVolumeChangeFinished() override {}
	void playbackControlsSpeedChanged(float64 s) override { speed = s; }
	float64 playbackControlsCurrentSpeed(bool) override { return speed; }
	std::vector<Media::VideoQuality> playbackControlsQualities() override { return { {.height = 720} }; }
	Media::VideoQuality playbackControlsCurrentQuality() override { return {.height = 720}; }
	void playbackControlsQualityChanged(Media::VideoQuality) override {}
	void playbackControlsToFullScreen() override { ++fullscreen; }
	void playbackControlsFromFullScreen() override { ++restore; }
	void playbackControlsToPictureInPicture() override { ++pip; }
	void playbackControlsRotate() override {}
};
struct Row {
	Ui::RpWidget *wrap = nullptr;
	Ui::IconButton *attach = nullptr;
	Ui::InputField *field = nullptr;
	Ui::EmojiButton *emoji = nullptr;
	Ui::SendButton *send = nullptr;
};
struct State {
	QPointer<Ui::RpWidget> preview;
	QPointer<Media::View::PlaybackControls> player;
	Delegate delegate;
	QPointer<Ui::DropdownMenu> menu;
	std::vector<Row> rows;
	std::vector<Ui::IconButton*> buttons;
};
Row CreateRow(Ui::RpWidget *parent, int top, int width, QString text, Ui::SendButton::Type type) {
	Row row;
	row.wrap = new Ui::RpWidget(parent);
	row.attach = new Ui::IconButton(row.wrap, st::historyAttach);
	row.field = new Ui::InputField(row.wrap, st::historyComposeField,
		Ui::InputField::Mode::MultiLine, rpl::single(u"Write a message..."_q), text);
	InitMessageFieldGeometry(row.field);
	row.emoji = new Ui::EmojiButton(row.wrap, st::historyAttachEmoji);
	row.send = new Ui::SendButton(row.wrap, st::historySend);
	row.send->setState({ .type = type });
	row.send->finishAnimating();
	const auto layout = [=] {
		row.field->resizeToWidth(width - 2 * st::historySendRight
			- row.attach->width() - row.emoji->width() - row.send->width());
		row.wrap->setGeometry(16, top, width, row.field->height() + 2 * st::historySendPadding);
		const auto buttonTop = row.wrap->height() - st::historySendPadding - row.attach->height();
		row.attach->moveToLeft(st::historySendRight, buttonTop);
		row.field->moveToLeft(st::historySendRight + row.attach->width(), st::historySendPadding);
		row.send->moveToRight(st::historySendRight, buttonTop);
		row.emoji->moveToRight(st::historySendRight + row.send->width(), buttonTop);
	};
	layout();
	row.field->heightChanges() | rpl::on_next(layout, row.wrap->lifetime());
	row.send->widthValue() | rpl::skip(1) | rpl::on_next(layout, row.wrap->lifetime());
	row.wrap->paintRequest() | rpl::on_next([=] {
		auto p = QPainter(row.wrap);
		Ui::Classic::Panel(p, row.wrap->rect(), Ui::Classic::Surface(), st::lineWidth);
	}, row.wrap->lifetime());
	row.attach->show(); row.field->show(); row.emoji->show(); row.send->show(); row.wrap->show();
	return row;
}
void Create(State *state, Window::MainWindow *window) {
	window->resize(920, 780);
	const auto preview = new Ui::RpWidget(window->body().get());
	state->preview = preview;
	preview->setGeometry(8, 40, 890, 650);
	preview->paintRequest() | rpl::on_next([=] {
		auto p = QPainter(preview);
		p.fillRect(preview->rect(), Ui::Classic::Surface());
		p.setPen(Ui::Classic::Text()); p.setFont(st::normalFont->f);
		p.drawText(16, 26, u"TG Classic: production playback controls and assembled composer controls"_q);
	}, preview->lifetime());
	state->player = new Media::View::PlaybackControls(preview, &state->delegate);
	state->player->setGeometry(16, 46, st::mediaviewControllerSize.width(), st::mediaviewControllerSize.height());
	state->player->updatePlayback({ .state = Media::Player::State::Playing,
		.position = 3 * 48000, .length = 379 * 48000, .frequency = 48000 });
	state->player->show();
	for (const auto child : state->player->children()) {
		if (const auto button = dynamic_cast<Ui::IconButton*>(child)) state->buttons.push_back(button);
	}
	state->rows.push_back(CreateRow(preview, 146, 820, {}, Ui::SendButton::Type::Record));
	state->rows.push_back(CreateRow(preview, 218, 820, u"😋 😀 🥳"_q, Ui::SendButton::Type::Send));
	state->rows.push_back(CreateRow(preview, 290, 820, u"First line 😋\nSecond line 😀\nThird line 🥳"_q, Ui::SendButton::Type::Save));
	state->rows.push_back(CreateRow(preview, 424, 340, u"Emoji 😋"_q, Ui::SendButton::Type::Round));
	preview->show(); preview->raise();
}
void Inspect(State *state, const QImage &image) {
	const auto player = state->player;
	Relief(image, player->geometry(), true, u"video control panel"_q);
	Check(Pixel(image, player->pos() + QPoint(3, 3)) == Ui::Classic::Surface(), u"video panel has opaque square corners"_q);
	Check(state->buttons.size() == 4, u"play, sound, fullscreen and picture in picture controls exist"_q);
	for (const auto button : state->buttons) {
		const auto rect = button->geometry().translated(player->pos());
		Relief(image, rect, true, button->accessibleName());
		Check(!button->toolTip().isEmpty(), u"video control explains its action on hover"_q);
		auto ink = 0;
		for (auto y = rect.top() + 5; y < rect.bottom() - 4; ++y) {
			for (auto x = rect.left() + 5; x < rect.right() - 4; ++x) {
				ink += std::abs(Pixel(image, QPoint(x,y)).lightness() - Ui::Classic::Text().lightness()) < 20;
			}
		}
		Check(ink > 10, u"video glyph contrasts with its button surface"_q, QString::number(ink));
	}
	for (const auto child : player->children()) {
		if (const auto button = dynamic_cast<Media::Player::SettingsButton*>(child)) {
			Relief(image, button->geometry().translated(player->pos()), true, u"video settings button"_q);
		}
	}
	for (const auto &row : state->rows) {
		const auto label = u"composer %1px"_q.arg(row.wrap->width());
		Check(row.wrap->rect().adjusted(2, 2, -2, -2).contains(row.attach->geometry())
			&& row.wrap->rect().adjusted(2, 2, -2, -2).contains(row.send->geometry()), label + u" buttons fit inside the outer frame"_q);
		Check(row.attach->y() == row.emoji->y() && row.emoji->y() == row.send->y()
			&& row.attach->geometry().bottom() == row.field->geometry().bottom(), label + u" controls align at the bottom"_q);
		Check(row.attach->geometry().right()+1 == row.field->x()
			&& row.field->geometry().right()+1 == row.emoji->x()
			&& row.emoji->geometry().right()+1 == row.send->x(), label + u" no gaps or overlap between controls"_q);
		Relief(image, row.send->geometry().translated(row.wrap->pos()), true, u"send or recording button"_q);
		const auto inner = row.field->rawTextEdit();
		Check(row.field->rect().adjusted(3, 3, -3, -3).contains(inner->geometry()), label + u" text editor is inside its bevel"_q,
			u"field=%1x%2 editor=%3,%4 %5x%6"_q.arg(row.field->width()).arg(row.field->height())
				.arg(inner->x()).arg(inner->y()).arg(inner->width()).arg(inner->height()));
		Check(inner->document()->size().height() <= inner->viewport()->height() + 1, label + u" text and emoji fit without vertical clipping"_q);
	}
}
} // namespace
void SetupScenario(not_null<Runner*> runner) {
	const auto state = std::make_shared<State>();
	const auto disabled = anim::Disabled();
	runner->onFinish([=] { delete state->preview.data(); anim::SetDisabled(disabled); });
	runner->waitEvent(u"launch_finished"_q);
	runner->actOnWidget(u"assemble playback and compose controls"_q, Primary, [=](QWidget *widget) {
		anim::SetDisabled(true); Create(state.get(), static_cast<Window::MainWindow*>(widget));
	});
	std::shared_ptr<const PaletteSwitch> switched;
	for (const auto night : {false,true}) {
		const auto mode = night ? u"night"_q : u"day"_q;
		if (night) switched = AppendPaletteSwitch(runner, { .name = u"live playback palette"_q,
			.mode = PaletteMode::Night, .sampleLabel = u"windowBg"_q, .sample = [] { return st::windowBg->c; } });
		runner->captureAndInspect(u"playback-composer-"_q + mode, [=] { return state->preview.data(); }, {},
			[=](QWidget*, const QImage &image) { Inspect(state.get(), image); });
		runner->add({ .name = u"playback actions "_q + mode, .run = [=] {
			const auto before = state->delegate;
			Click(state->buttons[0]); Click(state->buttons[1]); Click(state->buttons[2]); Click(state->buttons[3]);
			Check(state->delegate.pause == before.pause + 1 && state->delegate.mute == before.mute + 1
				&& state->delegate.fullscreen == before.fullscreen+1 && state->delegate.pip == before.pip+1,
				u"video buttons dispatch distinct playback actions"_q);
			state->player->setInFullScreen(true); Click(state->buttons[2]); state->player->setInFullScreen(false);
			Check(state->delegate.restore == before.restore + 1, u"fullscreen button switches to restore action"_q);
			for (const auto child : state->player->children()) {
				if (const auto slider = dynamic_cast<Ui::MediaSlider*>(child)) Click(slider);
			}
			Check(state->delegate.seek == before.seek+1, u"video seek slider dispatches seeking"_q);
		}});
		runner->add({.name = u"open playback settings "_q + mode, .run = [=] {
			for (const auto child : state->player->children()) {
				if (const auto button = dynamic_cast<Media::Player::SettingsButton*>(child)) {
					const auto point = QPointF(button->rect().center());
					const auto global = QPointF(button->mapToGlobal(point.toPoint()));
					auto press = QMouseEvent(QEvent::MouseButtonPress, point, global,
						Qt::LeftButton, Qt::LeftButton, Qt::NoModifier);
					auto release = QMouseEvent(QEvent::MouseButtonRelease, point, global,
						Qt::LeftButton, Qt::NoButton, Qt::NoModifier);
					QApplication::sendEvent(button, &press);
					QApplication::sendEvent(button, &release);
				}
			}
			for (const auto child : state->preview->children()) {
				if (const auto menu = dynamic_cast<Ui::DropdownMenu*>(child)) {
					state->menu = menu;
					menu->setAutoHiding(false);
					menu->otherEnter();
					menu->finishAnimating();
					menu->showFast();
				}
			}
			Check(state->player->hasMenu(), u"playback settings opens without a crash"_q);
		}});
		runner->captureAndInspect(u"playback-settings-"_q + mode, [=] { return state->menu.data(); }, {},
			[=](QWidget*, const QImage &image) {
				Check(state->menu->menu()->st().itemFg->c == Ui::Classic::Text(), u"playback settings uses Classic text colours"_q);
				Check(!state->menu->actions().empty(), u"playback settings keeps speed and quality actions"_q);
				Relief(image, state->menu->rect().marginsRemoved(state->menu->st().padding), true, u"playback settings"_q);
			});
		runner->add({.name=u"close playback settings"_q, .run=[=]{ if (state->menu) state->menu->hideFast();
			for (const auto child : state->player->children()) {
				if (const auto button = dynamic_cast<Media::Player::SettingsButton*>(child)) {
					auto leave = QEvent(QEvent::Leave); QApplication::sendEvent(button, &leave);
				}
			} }});
		for (const auto type : {Ui::SendButton::Type::Record, Ui::SendButton::Type::Round,
			Ui::SendButton::Type::Send, Ui::SendButton::Type::Save, Ui::SendButton::Type::Cancel,
			Ui::SendButton::Type::Schedule, Ui::SendButton::Type::Stop}) {
			runner->add({.name = u"switch send button mode"_q, .run = [=] {
				state->rows[0].send->setState({.type = type}); state->rows[0].send->finishAnimating();
				state->rows[0].send->setSynteticDown(true);
			}});
			runner->captureAndInspect(u"send-pressed-%1-%2"_q.arg(int(type)).arg(mode), [=] {return state->rows[0].send;}, {},
				[=](QWidget *widget, const QImage &image) { Relief(image, widget->rect(), false, u"all send and recording modes"_q); });
		}
		runner->add({.name=u"restore record button"_q, .run=[=]{
			state->rows[0].send->setSynteticDown(false);
			state->rows[0].send->setState({.type = Ui::SendButton::Type::Record}); state->rows[0].send->finishAnimating();
		}});
	}
	[[maybe_unused]] const auto restored = AppendPaletteRestore(runner, switched);
	runner->add({.name = u"close r4 preview"_q, .run = [=] { delete state->preview.data(); }});
}
} // namespace Test
#endif
