package org.telegram.ui.Classic;

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.Rect;
import android.graphics.RectF;
import android.graphics.drawable.ShapeDrawable;
import android.graphics.drawable.shapes.RectShape;
import android.view.View;
import android.view.ViewGroup;
import android.widget.EditText;

import org.telegram.messenger.ApplicationLoader;
import org.telegram.ui.ActionBar.Theme;

/** Shared Classic paint code; it does not change messaging or account storage. */
public final class ClassicStyle {
    private ClassicStyle() {}
    public static boolean enabled() { return true; }
    public static boolean dark() {
        return Theme.getActiveTheme() != null && Theme.isCurrentThemeDark();
    }
    public static int surface() { return dark() ? 0xff18222c : 0xffc0c0c0; }
    public static int text() { return dark() ? 0xfff0f0f0 : Color.BLACK; }
    public static int title() { return dark() ? 0xff000060 : 0xff000080; }
    public static int unit() {
        Context context = ApplicationLoader.applicationContext;
        return Math.max(1, context == null ? 1 : Math.round(context.getResources().getDisplayMetrics().density));
    }
    public static void frame(Canvas canvas, RectF rect, boolean pressed, int alpha) {
        int unit = unit();
        if (rect.width() < 4 * unit || rect.height() < 4 * unit) return;
        Paint paint = new Paint();
        paint.setAlpha(alpha);
        int light = dark() ? 0xff405565 : Color.WHITE;
        int mid = dark() ? 0xff2d3e4d : 0xffdfdfdf;
        int shadow = dark() ? 0xff101820 : 0xff808080;
        int edge = dark() ? 0xff080d12 : 0xff404040;
        int[] colors = pressed ? new int[]{edge,shadow,light,mid} : new int[]{light,mid,edge,shadow};
        for (int i = 0; i < 2; i++) {
            float inset = i * unit;
            paint.setColor(colors[i]); paint.setAlpha(alpha);
            canvas.drawRect(rect.left+inset, rect.top+inset, rect.right-inset, rect.top+inset+unit, paint);
            canvas.drawRect(rect.left+inset, rect.top+inset, rect.left+inset+unit, rect.bottom-inset, paint);
            paint.setColor(colors[i+2]); paint.setAlpha(alpha);
            canvas.drawRect(rect.left+inset, rect.bottom-inset-unit, rect.right-inset, rect.bottom-inset, paint);
            canvas.drawRect(rect.right-inset-unit, rect.top+inset, rect.right-inset, rect.bottom-inset, paint);
        }
    }
    public static void panel(Canvas canvas, Rect bounds, int color, boolean pressed) {
        Paint paint = new Paint(); paint.setColor(color);
        canvas.drawRect(bounds, paint);
        frame(canvas, new RectF(bounds), pressed, Color.alpha(color));
    }
    public static ShapeDrawable shape(int color, boolean sunken) {
        ShapeDrawable result = new ShapeDrawable(new RectShape()) {
            @Override public void draw(Canvas canvas) {
                super.draw(canvas);
                frame(canvas, new RectF(getBounds()), sunken, getPaint().getAlpha());
            }
        };
        result.getPaint().setColor(color);
        return result;
    }
    public static void controlFrames(Canvas canvas, ViewGroup group) {
        for (int i=0; i<group.getChildCount(); i++) {
            View child = group.getChildAt(i);
            if (child.getVisibility() != View.VISIBLE || child.getAlpha() == 0) continue;
            if (child instanceof ViewGroup) {
                int save = canvas.save();
                canvas.translate(child.getLeft()+child.getTranslationX(), child.getTop()+child.getTranslationY());
                controlFrames(canvas, (ViewGroup)child); canvas.restoreToCount(save);
            }
            if ((child instanceof EditText || (child.isClickable() && (!(child instanceof android.widget.TextView) || child.hasOnClickListeners()))) && child.getWidth() >= unit()*28
                    && child.getHeight() >= unit()*28 && child.getHeight() <= unit()*240) {
                frame(canvas, new RectF(child.getLeft()+child.getTranslationX(), child.getTop()+child.getTranslationY(),
                        child.getRight()+child.getTranslationX(), child.getBottom()+child.getTranslationY()),
                        child instanceof EditText || child.isPressed(), Math.round(255*child.getAlpha()));
            }
        }
    }
    public static void frameControl(Canvas canvas, ViewGroup root, View child) {
        if (child == null || child.getVisibility() != View.VISIBLE || child.getAlpha() == 0) return;
        Rect bounds = new Rect(0, 0, child.getWidth(), child.getHeight());
        root.offsetDescendantRectToMyCoords(child, bounds);
        frame(canvas, new RectF(bounds), child.isPressed(), Math.round(255 * child.getAlpha()));
    }
    public static void storyArc(Canvas canvas, RectF bounds, float angle, float sweep, Paint paint) {
        if (!enabled()) { canvas.drawArc(bounds, angle, sweep, false, paint); return; }
        if (bounds.isEmpty() || sweep == 0) return;
        Paint.Cap cap = paint.getStrokeCap();
        paint.setStrokeCap(Paint.Cap.SQUARE);
        if (Math.abs(sweep) >= 359.9f) {
            canvas.drawRect(bounds, paint);
        } else {
            if (sweep < 0) { angle += sweep; sweep = -sweep; }
            android.graphics.Path outline = new android.graphics.Path();
            outline.addRect(bounds, android.graphics.Path.Direction.CW);
            android.graphics.PathMeasure measure = new android.graphics.PathMeasure(outline, true);
            float perimeter = measure.getLength();
            float start = ((angle % 360 + 360) % 360) / 360f * perimeter + bounds.width() + bounds.height() / 2;
            start %= perimeter;
            float distance = sweep / 360f * perimeter;
            android.graphics.Path segment = new android.graphics.Path();
            measure.getSegment(start, Math.min(perimeter, start + distance), segment, true);
            if (start + distance > perimeter) measure.getSegment(0, start + distance - perimeter, segment, true);
            canvas.drawPath(segment, paint);
        }
        paint.setStrokeCap(cap);
    }
    public static boolean wallpaperVisible() {
        Context context=ApplicationLoader.applicationContext;
        return context != null && context.getSharedPreferences("tg_classic",Context.MODE_PRIVATE)
                .getBoolean("wallpaper_visible",false);
    }
    public static void toggleWallpaper() {
        Context context=ApplicationLoader.applicationContext;
        if (context == null) return;
        context.getSharedPreferences("tg_classic",Context.MODE_PRIVATE).edit()
                .putBoolean("wallpaper_visible",!wallpaperVisible()).apply();
        Theme.reloadWallpaper(true);
    }
}
