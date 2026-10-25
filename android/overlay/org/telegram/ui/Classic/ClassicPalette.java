package org.telegram.ui.Classic;
import org.telegram.ui.ActionBar.Theme;
/** Nullable override keeps media overlay, service and accessibility colours intact. */
public final class ClassicPalette {
    private ClassicPalette() {}
    public static Integer color(int key) {
        boolean dark = ClassicStyle.dark();
        if (key == Theme.key_windowBackgroundWhite || key == Theme.key_windowBackgroundGray || key == Theme.key_dialogBackground || key == Theme.key_dialogBackgroundGray || key == Theme.key_dialogInputField || key == Theme.key_chat_messagePanelBackground || key == Theme.key_chat_messagePanelShadow || key == Theme.key_chat_emojiPanelBackground || key == Theme.key_chats_menuBackground || key == Theme.key_chats_menuTopBackground || key == Theme.key_player_background || key == Theme.key_listSelector || key == Theme.key_chats_actionBackground || key == Theme.key_chat_messagePanelVoiceBackground) return ClassicStyle.surface();
        if (key == Theme.key_windowBackgroundWhiteBlackText || key == Theme.key_dialogTextBlack || key == Theme.key_chat_messageTextIn || key == Theme.key_chat_messageTextOut || key == Theme.key_chat_messagePanelText || key == Theme.key_chat_messagePanelSend || key == Theme.key_chat_messagePanelIcons || key == Theme.key_chat_messagePanelVoicePressed || key == Theme.key_chats_name || key == Theme.key_chats_nameMessage || key == Theme.key_chats_message || key == Theme.key_chats_menuItemText || key == Theme.key_chats_menuItemIcon || key == Theme.key_player_button || key == Theme.key_chats_actionIcon || key == Theme.key_glass_defaultIcon || key == Theme.key_glass_defaultText || key == Theme.key_chat_emojiPanelIcon) return ClassicStyle.text();
        if (key == Theme.key_windowBackgroundWhiteGrayText || key == Theme.key_windowBackgroundWhiteGrayText2 || key == Theme.key_dialogTextGray || key == Theme.key_dialogTextGray2 || key == Theme.key_chat_messagePanelHint || key == Theme.key_chats_date || key == Theme.key_chat_inTimeText || key == Theme.key_chat_outTimeText || key == Theme.key_player_time) return dark ? 0xffa0adb8 : 0xff606060;
        if (key == Theme.key_windowBackgroundWhiteBlueText || key == Theme.key_windowBackgroundWhiteBlueText2 || key == Theme.key_windowBackgroundWhiteBlueText3 || key == Theme.key_dialogTextBlue || key == Theme.key_dialogTextBlue2 || key == Theme.key_chat_messageLinkIn || key == Theme.key_chat_messageLinkOut || key == Theme.key_chats_unreadCounter || key == Theme.key_player_progress || key == Theme.key_chat_inReplyLine || key == Theme.key_chat_outReplyLine) return dark ? 0xff90b8ff : 0xff000080;
        if (key == Theme.key_actionBarDefaultSearch || key == Theme.key_actionBarDefaultSearchPlaceholder || key == Theme.key_actionBarDefaultTitle || key == Theme.key_actionBarDefaultSubtitle || key == Theme.key_actionBarDefaultIcon || key == Theme.key_chats_unreadCounterText) return 0xffffffff;
        if (key == Theme.key_actionBarDefault || key == Theme.key_actionBarDefaultArchived || key == Theme.key_actionBarActionModeDefault) return ClassicStyle.title();
        if (key == Theme.key_chat_inBubble) return dark ? 0xff202d3a : 0xffffffff;
        if (key == Theme.key_chat_outBubble) return dark ? 0xff263b58 : 0xffdbe8ff;
        if (key == Theme.key_chat_inBubbleSelected || key == Theme.key_chat_outBubbleSelected || key == Theme.key_chats_tabletSelectedOverlay) return dark ? 0xff3a5069 : 0xffb4c8e8;
        if (key == Theme.key_player_progressBackground) return dark ? 0xff405565 : 0xff808080;
        return null;
    }
}
