package org.telegram.ui.classicqa;

import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.graphics.Color;
import android.os.Bundle;
import android.os.Handler;
import android.util.Log;
import org.telegram.messenger.*;
import org.telegram.tgnet.TLRPC;
import org.telegram.ui.*;
import org.telegram.ui.ActionBar.Theme;
import java.util.ArrayList;

/** Offline-only fixtures, compiled only with tgclassicQa=true into a separate package. */
public class ClassicQAActivity extends LaunchActivity {
    private static final String TAG = "TG_CLASSIC_QA_FIXTURE_ONLY";
    private static final long SELF = 999000101L;
    private static final long PEER = 999000102L;
    private static final long GROUP = 999001001L;
    private long fixtureDialog = PEER;
    @Override public void onCreate(Bundle state) {
        ApplicationLoader.postInitApplication();
        UserConfig.selectedAccount = 0;
        super.onCreate(state);
        new Handler().postDelayed(() -> {
            try {
                TLRPC.TL_user self = user(SELF, "Classic", "Demo");
                self.self = true;
                UserConfig.getInstance(0).setCurrentUser(self);
                MessagesController.getInstance(0).putUser(self, false);
                boolean group = "group".equals(getIntent().getStringExtra("screen"));
                fixtureDialog = group ? -GROUP : PEER;
                seed();
                if ("folders".equals(getIntent().getStringExtra("screen"))) seedFilters();
                clearFragments();
                boolean dark = getIntent().getBooleanExtra("dark",false);
                Theme.selectedAutoNightType = Theme.AUTO_NIGHT_TYPE_SYSTEM;
                Theme.cancelAutoNightThemeCallbacks();
                Theme.applyTheme(Theme.getTheme(dark ? "Dark Blue" : "Blue"), false, dark);
                if (Theme.isCurrentThemeDark() != dark) throw new AssertionError("Wrong fixture palette");
                Log.i(TAG,"PASS palette " + (dark ? "dark" : "light"));
                getActionBarLayout().addFragmentToStack(new MainTabsActivity());
                getActionBarLayout().showLastFragment();
                checkBitmapMask();
                String screen = getIntent().getStringExtra("screen");
                if ("settings".equals(screen)) presentFragment(new SettingsActivity());
                final ChatActivity chat;
                if ("chat".equals(screen) || "group".equals(screen)) {
                    Bundle args = new Bundle(); args.putLong(group ? "chat_id" : "user_id",group ? GROUP : PEER);
                    chat = new ChatActivity(args);
                    getActionBarLayout().addFragmentToStack(chat);
                    getActionBarLayout().showLastFragment();
                    new Handler().postDelayed(() -> {
                        loadFixtureMessages(chat);
                        if (group) chat.getChatActivityEnterView().setBotsCount(1,true,false,false);
                    }, 750);
                } else chat = null;
                NotificationCenter.getInstance(0).postNotificationName(NotificationCenter.dialogsNeedReload);
                new Handler().postDelayed(() -> {
                    if (chat != null) {
                        if (!checkComposer(getWindow().getDecorView())) throw new AssertionError("Missing composer");
                        int cells=0;
                        for (int i=0;i<chat.getChatListView().getChildCount();i++) if (chat.getChatListView().getChildAt(i) instanceof org.telegram.ui.Cells.ChatMessageCell) cells++;
                        if (cells==0) throw new AssertionError("Missing message cells");
                        Log.i(TAG,"PASS message cells " + cells);
                        if (group) checkGroupFrames(chat);
                        checkComposerGeometry(chat);
                    }
                    monitorPalette(dark);
                    Log.i(TAG,"READY " + screen);
                }, 2300);
            } catch (Throwable failure) { Log.e(TAG,"FAILED",failure); throw new RuntimeException(failure); }
        }, 2000);
    }
    private void monitorPalette(boolean dark) {
        new Handler().postDelayed(() -> {
            if (isFinishing() || isDestroyed()) return;
            if (Theme.isCurrentThemeDark() != dark) throw new AssertionError("Palette changed during fixture interactions");
            monitorPalette(dark);
        }, 250);
    }
    private ArrayList<MessageObject> fixtureMessages = new ArrayList<>();
    private void loadFixtureMessages(ChatActivity chat) {
        try {
            // Feed a completed offline load through the real screen's notification handler.
            java.lang.reflect.Field field=ChatActivity.class.getDeclaredField("waitingForLoad");
            field.setAccessible(true);
            ((ArrayList<Integer>)field.get(chat)).add(777);
            java.util.Collections.reverse(fixtureMessages);
            chat.didReceivedNotification(NotificationCenter.messagesDidLoad,0,fixtureDialog,fixtureMessages.size(),fixtureMessages,false,0,202,0,0,2,true,chat.getClassGuid(),777,0,0,0);
        } catch (Exception e) { throw new RuntimeException(e); }
    }
    private TLRPC.TL_user user(long id, String first, String last) {
        TLRPC.TL_user u = new TLRPC.TL_user();u.id=id;u.flags=2 | 4;u.first_name=first;u.last_name=last;u.phone="";return u;
    }
    private void seed() {
        MessagesController mc=MessagesController.getInstance(0);
        ArrayList<TLRPC.User> users=new ArrayList<>();
        ArrayList<TLRPC.Message> messages=new ArrayList<>();
        for(int i=0;i<8;i++) {
            long id=PEER+i;
            TLRPC.TL_user u=user(id, new String[]{"Anna","Project team","Design notes","Weekend plans","Archive demo","Music","Family","Photo club"}[i], "");
            users.add(u);mc.putUser(u,false);
            TLRPC.TL_dialog d=new TLRPC.TL_dialog();d.id=id;d.peer=new TLRPC.TL_peerUser();d.peer.user_id=id;d.top_message=100+i;d.last_message_date=(int)(System.currentTimeMillis()/1000)-i*60;d.unread_count=i==1?4:0;
            TLRPC.TL_message m=new TLRPC.TL_message();m.id=100+i;m.dialog_id=id;m.peer_id=d.peer;m.from_id=d.peer;m.flags=256;m.date=d.last_message_date;m.message=new String[]{"Hello! How does Classic look?","The next build is ready.","Rectangular buttons and readable text","A little bit of Windows on a phone","Messages stay in place.","Let's listen later.","See you soon!","New photos"}[i];
            messages.add(m);
            ArrayList<MessageObject> objects=new ArrayList<>();objects.add(new MessageObject(0,m,false,false));mc.dialogMessage.put(id,objects);
            if(mc.dialogs_dict.get(id)==null) { mc.getAllDialogs().add(d);mc.dialogsServerOnly.add(d);mc.dialogs_dict.put(id,d); }
        }
        for (int i=0;i<2;i++) {
            TLRPC.TL_message m=new TLRPC.TL_message();m.id=201+i;m.dialog_id=PEER;m.peer_id=new TLRPC.TL_peerUser();m.peer_id.user_id=PEER;m.from_id=new TLRPC.TL_peerUser();m.from_id.user_id=i==0?PEER:SELF;m.out=i==1;m.flags=256;m.date=(int)(System.currentTimeMillis()/1000)+i;
            m.message=i==0?"Long text layout check.\n\nA classic frame should leave enough room for every line and the timestamp.\n\nExample address: 192.0.2.24":"Emoji check: \uD83D\uDE42 \uD83D\uDC4D  All controls stay inside the composer.";
            messages.add(m);
        }
        MessagesStorage.getInstance(0).putUsersAndChats(users,null,true,true);
        MessagesStorage.getInstance(0).putMessages(messages,true,true,false,0,0,0);
        fixtureMessages.clear();
        if (fixtureDialog == -GROUP) {
            TLRPC.TL_chat group = new TLRPC.TL_chat();group.id=GROUP;group.title="Classic test group";group.creator=true;group.default_banned_rights=new TLRPC.TL_chatBannedRights();group.participants_count=3;group.photo=new TLRPC.TL_chatPhotoEmpty();
            mc.putChat(group,false);
            ArrayList<TLRPC.Chat> groups=new ArrayList<>();groups.add(group);MessagesStorage.getInstance(0).putUsersAndChats(null,groups,true,true);
            for (int i=0;i<10;i++) {
                TLRPC.TL_message m=new TLRPC.TL_message();m.id=301+i;m.dialog_id=-GROUP;m.peer_id=new TLRPC.TL_peerChat();m.peer_id.chat_id=GROUP;m.from_id=new TLRPC.TL_peerUser();m.from_id.user_id=PEER+(i/3)%2;m.flags=256;m.date=(int)(System.currentTimeMillis()/1000)-60+i;
                m.message=new String[]{"Morning!", "A second message from the same person", "Short follow-up", "The frame starts on the same line", "Even when the author changes", "Another follow-up", "Emoji check: \uD83D\uDE42 \uD83D\uDC4D", "Longer text wraps inside the message frame, without moving the next message.", "Almost done", "Composer with an extra bot button"}[i];
                fixtureMessages.add(new MessageObject(0,m,false,false));
            }
        } else for (TLRPC.Message message:messages) if(message.dialog_id==PEER) fixtureMessages.add(new MessageObject(0,message,false,false));
    }
    private void seedFilters() {
        MessagesController mc=MessagesController.getInstance(0);mc.dialogFilters.clear();mc.dialogFiltersById.clear();mc.dialogFiltersLoaded=true;
        for(int i=0;i<4;i++) {
            MessagesController.DialogFilter filter=new MessagesController.DialogFilter();filter.id=i;filter.name=new String[]{"All","People","Projects","Study"}[i];filter.flags=MessagesController.DIALOG_FILTER_FLAG_ALL_CHATS;filter.order=i;filter.dialogs.addAll(mc.getAllDialogs());
            mc.dialogFilters.add(filter);mc.dialogFiltersById.put(i,filter);
        }
    }
    private void checkGroupFrames(ChatActivity chat) {
        try {
            java.lang.reflect.Field f=org.telegram.ui.Cells.ChatMessageCell.class.getDeclaredField("currentBackgroundDrawable");f.setAccessible(true);
            java.util.HashSet<Integer> edges=new java.util.HashSet<>();
            for(int i=0;i<chat.getChatListView().getChildCount();i++) {
                android.view.View v=chat.getChatListView().getChildAt(i);
                if (!(v instanceof org.telegram.ui.Cells.ChatMessageCell)) continue;
                android.graphics.drawable.Drawable d=(android.graphics.drawable.Drawable)f.get(v);if(d==null)continue;
                Bitmap b=Bitmap.createBitmap(v.getWidth(),v.getHeight(),Bitmap.Config.ARGB_8888);d.draw(new Canvas(b));
                int y=Math.max(0,Math.min(b.getHeight()-1,d.getBounds().centerY()));
                for(int x=0;x<b.getWidth();x++)if(Color.alpha(b.getPixel(x,y))>127){edges.add(x);break;}
                b.recycle();
            }
            if(edges.size()!=1)throw new AssertionError("Group bubble edges differ: "+edges);
            Log.i(TAG,"PASS group aligned edges " + edges);
        } catch(Exception e){throw new RuntimeException(e);}
    }
    private android.graphics.Rect screenRect(android.view.View v) {
        int[] xy=new int[2];v.getLocationOnScreen(xy);return new android.graphics.Rect(xy[0],xy[1],xy[0]+v.getWidth(),xy[1]+v.getHeight());
    }
    private void checkComposerGeometry(ChatActivity chat) {
        try {
            org.telegram.ui.Components.ChatActivityEnterView enter=chat.getChatActivityEnterView();
            java.lang.reflect.Field editField=org.telegram.ui.Components.ChatActivityEnterView.class.getDeclaredField("messageEditText");editField.setAccessible(true);
            android.view.View editor=(android.view.View)editField.get(enter);android.graphics.Rect e=screenRect(editor);
            int right=Integer.MAX_VALUE;
            for(String name:new String[]{"emojiButton","attachButton","botButton","notifyButton","scheduledButton","audioVideoButtonContainer"}) {
                java.lang.reflect.Field f=org.telegram.ui.Components.ChatActivityEnterView.class.getDeclaredField(name);f.setAccessible(true);android.view.View v=(android.view.View)f.get(enter);
                if(v==null||!v.isShown()||v.getAlpha()<0.99f)continue;
                android.graphics.Rect r=screenRect(v);
                if(Math.abs(r.bottom-e.bottom)>AndroidUtilities.dp(1))throw new AssertionError("Composer baseline "+name+" "+r+" editor "+e);
                if("emojiButton".equals(name)) {
                    if(Math.abs(r.right-e.left)>AndroidUtilities.dp(1))throw new AssertionError("Emoji/editor gap "+r+" "+e);
                } else right=Math.min(right,r.left);
            }
            if(right!=Integer.MAX_VALUE&&Math.abs(right-e.right)>AndroidUtilities.dp(1))throw new AssertionError("Editor/control gap "+e+" next="+right);
            Log.i(TAG,"PASS composer aligned controls");
        } catch(Exception e){throw new RuntimeException(e);}
    }
    private boolean checkComposer(android.view.View v) {
        if (!v.isShown()) return false;
        if (v instanceof android.widget.EditText) {
            if (v.getPaddingLeft() < AndroidUtilities.dp(6) || v.getPaddingRight() < AndroidUtilities.dp(6)) throw new AssertionError("Composer content touches frame");
            Log.i(TAG,"PASS composer inset " + v.getPaddingLeft() + "/" + v.getPaddingRight());
            return true;
        }
        if (v instanceof android.view.ViewGroup) {
            android.view.ViewGroup group=(android.view.ViewGroup)v;
            for(int i=0;i<group.getChildCount();i++) if(checkComposer(group.getChildAt(i))) return true;
        }
        return false;
    }
    private void checkBitmapMask() {
        Bitmap source=Bitmap.createBitmap(96,96,Bitmap.Config.ARGB_8888);source.eraseColor(0xff40a060);
        Bitmap output=Bitmap.createBitmap(96,96,Bitmap.Config.ARGB_8888);
        ImageReceiver receiver=new ImageReceiver();receiver.setRoundRadius(48);receiver.setImageCoords(0,0,96,96);receiver.setImageBitmap(source);receiver.draw(new Canvas(output));
        if(Color.alpha(output.getPixel(48,48))==0 || Color.alpha(output.getPixel(8,8))==0) throw new AssertionError("Missing square bitmap avatar");
        Log.i(TAG,"PASS square bitmap avatar center and corner");
    }
}
