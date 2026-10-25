#ifdef _DEBUG
#include "test/test_runner.h"
#include "test/test_log.h"
#include "test/test_palette.h"
#include "core/version.h"
#include "history/view/media/history_view_media.h"
#include "info/profile/info_profile_top_bar_action_button.h"
#include "ui/classic_style.h"
#include "ui/controls/emoji_button.h"
#include "ui/controls/userpic_button.h"
#include "ui/effects/animation_value.h"
#include "ui/effects/round_area_with_shadow.h"
#include "ui/image/image_prepare.h"
#include "ui/widgets/fields/input_field.h"
#include "ui/widgets/menu/menu.h"
#include "ui/widgets/popup_menu.h"
#include "ui/widgets/side_bar_button.h"
#include "window/main_window.h"
#include "window/window_controller.h"
#include "styles/style_chat_helpers.h"
#include "styles/style_info.h"
#include "styles/style_menu_icons.h"
#include "styles/style_widgets.h"
#include "styles/style_window.h"
#include <QtGui/QTextDocument>
#include <QtWidgets/QApplication>
#include <QtWidgets/QTextEdit>
#include <CoreGraphics/CGGeometry.h>
#include <cmath>
#include <objc/message.h>
#include <objc/runtime.h>

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

template <typename R, typename... Args>
R Native(void *object, const char *selector, Args... args) {
	return reinterpret_cast<R (*)(void*, SEL, Args...)>(objc_msgSend)(
		object, sel_registerName(selector), args...);
}

QColor Pixel(const QImage &image, QPoint point) {
	return image.pixelColor(point * image.devicePixelRatio());
}

void CheckRelief(const QImage &image, QRect rect, bool raised, const QString &name) {
	const auto top = Pixel(image, rect.topLeft() + QPoint(4, 0));
	const auto bottom = Pixel(image, rect.bottomRight() - QPoint(4, 0));
	Check(top.alpha() == 255 && bottom.alpha() == 255, name + u" has opaque edges"_q);
	Check(raised ? (top.lightness() > bottom.lightness()) : (top.lightness() < bottom.lightness()),
		name + (raised ? u" is raised"_q : u" is pressed"_q));
}

// The fixture measures popup painting while the user may focus another app.
// Keep focus-loss dismissal out of this visual check; production is unchanged.
class PreviewPopupMenu final : public Ui::PopupMenu {
public:
	PreviewPopupMenu(QWidget *parent, const style::PopupMenu &st)
	: Ui::PopupMenu(parent, st) {
		// Qt::Popup can be dismissed by macOS before an asynchronous capture.
		// Keep the real painter and layout in a non-dismissable tool window.
		setWindowFlags(Qt::Tool | Qt::FramelessWindowHint | Qt::NoDropShadowWindowHint);
	}
protected:
	void focusOutEvent(QFocusEvent*) override {}
};

struct State {
	QPointer<Ui::RpWidget> preview;
	QPointer<Ui::EmojiButton> emoji;
	QPointer<Ui::InputField> field;
	QPointer<Ui::UserpicButton> photo;
	QPointer<Info::Profile::TopBarActionButton> action;
	QPointer<Ui::SettingsButton> media;
	QPointer<Ui::SideBarButton> folder;
	QPointer<Ui::PopupMenu> menu;
};

void Preview(not_null<State*> state, not_null<Window::MainWindow*> window) {
	delete state->preview.data();
	window->resize(940, 740);
	const auto preview = new Ui::RpWidget(window->body().get());
	state->preview = preview;
	preview->setGeometry(10, 45, 900, 600);
	preview->paintRequest() | rpl::on_next([=] {
		auto p = QPainter(preview);
		Ui::Classic::Panel(p, preview->rect(), Ui::Classic::Surface(), st::lineWidth);
		p.setFont(st::normalFont->f);
		p.setPen(Ui::Classic::Text());
		p.drawText(140, 30, u"Composer: real Telegram input and buttons"_q);
		p.drawText(140, 202, u"Profile and channel controls"_q);
		p.drawText(140, 452, u"Reaction toolbar renderer"_q);
	}, preview->lifetime());
	for (auto i = 0; i != 4; ++i) {
		const auto folder = new Ui::SideBarButton(preview,
			TextWithEntities{ i ? u"Folder %1"_q.arg(i) : u"All chats"_q }, st::windowFiltersButton);
		folder->setActive(!i);
		folder->setBadge(i == 2 ? u"7"_q : u"94"_q, false);
		folder->setIconOverride(&st::menuIconShowInFolder);
		folder->setGeometry(16, 16 + i * 100, 100, 94);
		folder->show();
		if (!i) state->folder = folder;
	}
	const auto field = new Ui::InputField(preview, st::historyComposeField,
		Ui::InputField::Mode::MultiLine, rpl::single(u"Message"_q), u"😋"_q);
	state->field = field;
	field->setMaxHeight(st::historyComposeFieldMaxHeight);
	field->setGeometry(140, 48, 560, field->height());
	field->show();
	const auto emoji = new Ui::EmojiButton(preview, st::historyAttachEmoji);
	state->emoji = emoji;
	emoji->move(710, 46);
	emoji->show();
	const auto attach = new Ui::IconButton(preview, st::historyAttach);
	attach->move(760, 46);
	attach->show();
	const auto photo = new Ui::UserpicButton(preview, &window->controller(),
		Ui::UserpicButton::Role::ChoosePhoto, st::infoProfileCover.photo);
	state->photo = photo;
	photo->setAttribute(Qt::WA_TransparentForMouseEvents);
	auto image = QImage(128, 128, QImage::Format_ARGB32_Premultiplied);
	image.fill(QColor(180, 90, 140));
	photo->showCustom(std::move(image));
	photo->move(140, 224);
	photo->show();
	for (auto i = 0; i != 3; ++i) {
		const auto button = new Info::Profile::TopBarActionButton(preview,
			i == 0 ? u"Unmute"_q : i == 1 ? u"Leave"_q : u"More"_q,
			i == 0 ? st::menuIconMute : i == 1 ? st::menuIconLeave : st::menuIconSettings);
		button->setGeometry(250 + i * 190, 224, 180, st::infoProfileTopBarActionButtonSize);
		button->show();
		if (!i) state->action = button;
	}
	for (auto i = 0; i != 3; ++i) {
		const auto button = new Ui::SettingsButton(preview,
			rpl::single(i == 0 ? u"128 photos"_q : i == 1 ? u"24 videos"_q : u"8 shared links"_q),
			st::infoSharedMediaButton);
		button->setGeometry(250, 286 + i * 44, 560, 42);
		button->show();
		if (!i) state->media = button;
	}
	const auto toolbar = new Ui::RpWidget(preview);
	toolbar->setGeometry(140, 465, 340, 66);
	const auto area = std::make_shared<Ui::RoundAreaWithShadow>(QSize(324, 50), QMargins(8, 8, 8, 8), 48);
	area->setBackgroundColor(Ui::Classic::Surface());
	area->setShadowColor(QColor(0, 0, 0, 60));
	toolbar->paintRequest() | rpl::on_next([=] {
		auto p = QPainter(toolbar);
		const auto frame = area->validateFrame(31, 1., 24.);
		p.drawImage(toolbar->rect(), *frame.image, frame.rect);
		p.setFont(st::normalFont->f);
		p.setPen(Ui::Classic::Text());
		p.drawText(QRect(16, 8, 308, 50), Qt::AlignCenter, u"⭐  ✍️  💡  📅  🔥  ⚡"_q);
	}, toolbar->lifetime());
	toolbar->show();
	preview->show();
	preview->raise();
}
} // namespace

void SetupScenario(not_null<Runner*> runner) {
	const auto state = std::make_shared<State>();
	const auto animationsDisabled = anim::Disabled();
	runner->onFinish([=] {
		delete state->menu.data();
		delete state->preview.data();
		anim::SetDisabled(animationsDisabled);
	});
	runner->waitEvent(u"launch_finished"_q);
	runner->add({ .name = u"deterministic visual states"_q,
		.run = [] { anim::SetDisabled(true); } });
	runner->actOnWidget(u"branding and native titlebar"_q, Primary, [](QWidget *widget) {
		Check(QString::fromLatin1(AppName) == u"TG Classic"_q, u"fork uses the requested TG Classic name"_q);
		Check(QApplication::applicationDisplayName() == u"TG Classic"_q,
			u"Qt and native application menus use the TG Classic display name"_q);
		const auto view = reinterpret_cast<void*>(widget->winId());
		const auto nativeWindow = Native<void*>(view, "window");
		Check(nativeWindow != nullptr, u"real NSWindow is available"_q);
		if (nativeWindow) {
			Check((Native<unsigned long>(nativeWindow, "styleMask") & (1UL << 15)) != 0,
				u"custom titlebar occupies the full native content area"_q);
			Check(Native<long>(nativeWindow, "titleVisibility") == 1,
				u"native macOS window title is hidden"_q);
			const auto contentView = Native<void*>(nativeWindow, "contentView");
			const auto content = Native<CGRect>(contentView, "frame");
			const auto frame = Native<CGRect>(nativeWindow, "frame");
			Check(std::abs(frame.size.height - content.size.height) < 2.,
				u"native titlebar does not reserve a second strip above the client"_q);
			const auto parent = Native<void*>(view, "superview");
			const auto bounds = Native<CGRect>(view, "bounds");
			const auto halfTitle = st::windowTitleHeight / 2.;
			const auto local = CGPointMake(bounds.size.width - halfTitle,
				Native<bool>(view, "isFlipped") ? halfTitle : bounds.size.height - halfTitle);
			const auto target = Native<CGPoint>(parent, "convertPoint:fromView:", local, view);
			const auto hit = Native<void*>(parent, "hitTest:", target);
			Check(hit && (hit == view || Native<bool>(hit, "isDescendantOf:", view)),
				u"native titlebar does not intercept the custom close button hit target"_q);
			for (auto type = 0UL; type != 3UL; ++type) {
				const auto button = Native<void*>(nativeWindow, "standardWindowButton:", type);
				Check(!button || Native<bool>(button, "isHidden"), u"native traffic-light button is hidden"_q);
			}
		}
		for (const auto rounding : { std::optional<Ui::BubbleRounding>(), std::optional(Ui::BubbleRounding{
			.topLeft = Ui::BubbleCornerRounding::Large,
			.topRight = Ui::BubbleCornerRounding::Small,
			.bottomLeft = Ui::BubbleCornerRounding::Large,
			.bottomRight = Ui::BubbleCornerRounding::Small,
		}) }) {
			Check(HistoryView::MediaRoundingMask(rounding).empty(),
				u"ordinary media does not acquire rounded clipping masks"_q);
			auto thumbnail = QImage(80, 60, QImage::Format_ARGB32_Premultiplied);
			thumbnail.fill(QColor(40, 120, 180));
			const auto prepared = Images::Round(std::move(thumbnail),
				HistoryView::MediaRoundingMask(rounding));
			Check(prepared.pixelColor(0, 0).alpha() == 255
				&& prepared.pixelColor(79, 0).alpha() == 255
				&& prepared.pixelColor(0, 59).alpha() == 255
				&& prepared.pixelColor(79, 59).alpha() == 255,
				u"prepared media raster keeps all four square corners opaque"_q);
		}
	});
	std::shared_ptr<const PaletteSwitch> switched;
	for (const auto night : { false, true }) {
		const auto mode = night ? u"night"_q : u"day"_q;
		if (night) switched = AppendPaletteSwitch(runner, {
			.name = u"classic night"_q, .mode = PaletteMode::Night,
			.sampleLabel = u"windowBg"_q, .sample = [] { return st::windowBg->c; },
		});
		runner->actOnWidget(u"create UI fixtures "_q + mode, Primary, [=](QWidget *widget) {
			Preview(state.get(), static_cast<Window::MainWindow*>(widget));
			Check(st::sideBarBadgeBgActive->c != st::sideBarBadgeFg->c,
				u"active folder badge text contrasts with its background"_q);
			if (!night) Check(st::sideBarBg->c == Ui::Classic::Surface(),
				u"light folder sidebar uses the Classic grey surface"_q);
		});
		runner->captureAndInspect(u"controls-"_q + mode, [=] { return state->preview.data(); }, {},
			[=](QWidget*, const QImage &image) {
				CheckRelief(image, state->emoji->geometry(), true, u"emoji button"_q);
				CheckRelief(image, state->action->geometry(), true, u"profile action tile"_q);
				CheckRelief(image, state->media->geometry(), true, u"profile media row"_q);
				CheckRelief(image, state->folder->geometry(), false, u"selected folder"_q);
				Check(Pixel(image, QPoint(24, 202)) == Ui::Classic::Surface(),
					u"inactive folder stays Classic grey even with a night sidebar palette"_q);
				const auto photo = state->photo;
				const auto rect = photo->geometry();
				Check(Pixel(image, rect.topLeft() + QPoint(4, 4)) == QColor(180, 90, 140),
					u"profile photo fills the square corner"_q);
				const auto inner = state->field->findChild<QTextEdit*>();
				Check(inner != nullptr, u"composer uses the real rich-text editor"_q);
				if (inner) {
					Check(state->field->rect().adjusted(3, 3, -3, -3).contains(inner->geometry()),
						u"typed emoji editor stays inside the bevel on all four edges"_q);
					Check(inner->document()->size().height() <= inner->viewport()->height() + 1,
						u"single emoji fits the editor height"_q);
				}
			});
		runner->add({ .name = u"press composer and profile "_q + mode, .run = [=] {
			state->emoji->setSynteticDown(true);
			state->action->setSynteticDown(true);
			state->field->setTextWithTags({ u"😋 😀 🥳\nEmoji on a second line 😎"_q });
		}});
		runner->captureAndInspect(u"pressed-and-multiline-"_q + mode, [=] { return state->preview.data(); }, {},
			[=](QWidget*, const QImage &image) {
				CheckRelief(image, state->emoji->geometry(), false, u"emoji button"_q);
				CheckRelief(image, state->action->geometry(), false, u"profile action tile"_q);
				const auto inner = state->field->findChild<QTextEdit*>();
				Check(inner && inner->document()->size().height() <= inner->viewport()->height() + 1,
					u"multiline emoji input grows to fit its document"_q);
			});
		runner->add({ .name = u"open real context menu "_q + mode, .run = [=] {
			state->emoji->setSynteticDown(false);
			state->action->setSynteticDown(false);
			const auto menu = new PreviewPopupMenu(state->preview, st::popupMenuWithIcons);
			state->menu = menu;
			menu->deleteOnHide(false);
			menu->addAction(u"Quote & Reply"_q, [] {}, &st::menuIconReply);
			menu->addAction(u"Copy Selected Text"_q, [] {}, &st::menuIconCopy);
			menu->addAction(u"Forward"_q, [] {}, &st::menuIconForward);
			menu->addAction(u"Delete"_q, [] {}, &st::menuIconDelete);
			menu->addSeparator();
			menu->addAction(u"Select"_q, [] {}, &st::menuIconSelect);
			menu->popup(state->preview->mapToGlobal(QPoint(480, 430)));
			menu->menu()->setSelected(3, false);
		}});
		runner->captureAndInspect(u"context-menu-"_q + mode, [=] { return state->menu.data(); }, {},
			[=](QWidget*, const QImage &image) {
				CheckRelief(image, state->menu->inner(), true, u"context popup frame"_q);
				Check(state->menu->st().radius == 0, u"message menu has square corners"_q);
				Check(state->menu->menu()->findSelectedAction() != nullptr,
					u"themed menu retains its selected action"_q);
			});
		runner->add({ .name = u"close fixtures "_q + mode, .run = [=] {
			delete state->menu.data();
			delete state->preview.data();
		}});
	}
	const auto restored = AppendPaletteRestore(runner, switched);
	runner->add({ .name = u"restore original palette"_q, .then = [=] {
		Check(restored->restored(), u"original light theme is restored"_q);
	}});
}
} // namespace Test
#endif
