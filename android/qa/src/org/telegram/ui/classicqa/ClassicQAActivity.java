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
    @Override public void onCreate(Bundle state) {
        ApplicationLoader.postInitApplication();
        UserConfig.selectedAccount = 0;
        Theme.applyTheme(Theme.getTheme(getIntent().getBooleanExtra("dark",false) ? "Dark Blue" : "Blue"), false);
        super.onCreate(state);
        new Handler().postDelayed(() -> {
            try {
                TLRPC.TL_user self = user(SELF, "Classic", "Demo");
                self.self = true;
                UserConfig.getInstance(0).setCurrentUser(self);
                MessagesController.getInstance(0).putUser(self, false);
                seed();
                clearFragments();
                boolean dark = getIntent().getBooleanExtra("dark",false);
                Theme.selectedAutoNightType = Theme.AUTO_NIGHT_TYPE_NONE;
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
                if ("chat".equals(screen)) {
                    Bundle args = new Bundle(); args.putLong("user_id",PEER);
                    chat = new ChatActivity(args);
                    presentFragment(chat);
                    new Handler().postDelayed(() -> loadFixtureMessages(chat), 750);
                } else chat = null;
                NotificationCenter.getInstance(0).postNotificationName(NotificationCenter.dialogsNeedReload);
                new Handler().postDelayed(() -> {
                    if (chat != null) {
                        if (!checkComposer(getWindow().getDecorView())) throw new AssertionError("Missing composer");
                        int cells=0;
                        for (int i=0;i<chat.getChatListView().getChildCount();i++) if (chat.getChatListView().getChildAt(i) instanceof org.telegram.ui.Cells.ChatMessageCell) cells++;
                        if (cells==0) throw new AssertionError("Missing message cells");
                        Log.i(TAG,"PASS message cells " + cells);
                    }
                    Log.i(TAG,"READY " + screen);
                }, 1500);
            } catch (Throwable failure) { Log.e(TAG,"FAILED",failure); throw new RuntimeException(failure); }
        }, 2000);
    }
    private ArrayList<MessageObject> fixtureMessages = new ArrayList<>();
    private void loadFixtureMessages(ChatActivity chat) {
        try {
            // Feed a completed offline load through the real screen's notification handler.
            java.lang.reflect.Field field=ChatActivity.class.getDeclaredField("waitingForLoad");
            field.setAccessible(true);
            ((ArrayList<Integer>)field.get(chat)).add(777);
            java.util.Collections.reverse(fixtureMessages);
            chat.didReceivedNotification(NotificationCenter.messagesDidLoad,0,PEER,fixtureMessages.size(),fixtureMessages,false,0,202,0,0,2,true,chat.getClassGuid(),777,0,0,0);
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
        for (TLRPC.Message message:messages) if(message.dialog_id==PEER) fixtureMessages.add(new MessageObject(0,message,false,false));
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
