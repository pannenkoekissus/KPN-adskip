package software.morphe.kpn;

import android.app.Activity;
import android.content.Context;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.os.Handler;
import android.os.Looper;
import android.view.Gravity;
import android.view.KeyEvent;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;

import java.lang.ref.WeakReference;
import java.lang.reflect.Field;
import java.lang.reflect.Method;

/**
 * KPN TV+ AdSkip & Trickplay Unlock Hook
 *
 * Provides version-independent ad skipping and seek unlock by hooking into the
 * underlying ExoPlayer instance in Flutter's video_player_android plugin.
 */
public class AdSkipHook {
    private static final String TAG = "KPN_AdSkip";
    
    // Default TV ad break skip is 4.5 minutes (270,000 ms), matching RTL commercial blocks
    public static final long DEFAULT_AD_BREAK_MS = 270_000L;
    public static final long JUMP_30S_MS = 30_000L;
    public static final long JUMP_BACK_15S_MS = -15_000L;

    private static WeakReference<Object> activeVideoPlayerRef = new WeakReference<>(null);
    private static WeakReference<Activity> activeActivityRef = new WeakReference<>(null);
    private static long previousPositionMs = -1L;
    private static View overlayView = null;
    private static final Handler mainHandler = new Handler(Looper.getMainLooper());

    static {
        try {
            Thread.UncaughtExceptionHandler defaultHandler = Thread.getDefaultUncaughtExceptionHandler();
            Thread.setDefaultUncaughtExceptionHandler((thread, throwable) -> {
                java.io.StringWriter sw = new java.io.StringWriter();
                throwable.printStackTrace(new java.io.PrintWriter(sw));
                log("FATAL_CRASH: " + sw.toString());
                if (defaultHandler != null) {
                    defaultHandler.uncaughtException(thread, throwable);
                }
            });
            log("AdSkipHook initialized - Crash logger active");
        } catch (Throwable t) {
            android.util.Log.e(TAG, "Failed to init crash handler: " + t.getMessage());
        }
    }

    /**
     * Writes debug log directly to /sdcard/Download/kpn_debug.log
     */
    public static void log(String msg) {
        android.util.Log.e(TAG, msg);
        try {
            java.io.File downloadDir = android.os.Environment.getExternalStoragePublicDirectory(
                    android.os.Environment.DIRECTORY_DOWNLOADS
            );
            if (downloadDir != null && downloadDir.exists()) {
                java.io.File logFile = new java.io.File(downloadDir, "kpn_debug.log");
                java.io.FileWriter fw = new java.io.FileWriter(logFile, true);
                String timestamp = new java.text.SimpleDateFormat("yyyy-MM-dd HH:mm:ss.SSS", java.util.Locale.US).format(new java.util.Date());
                fw.write(timestamp + " | " + msg + "\n");
                fw.flush();
                fw.close();
            }
        } catch (Throwable ignored) {}
    }

    /**
     * Called whenever VideoPlayer is initialized or seeks in Flutter
     */
    public static void registerPlayer(Object videoPlayer) {
        if (videoPlayer != null) {
            activeVideoPlayerRef = new WeakReference<>(videoPlayer);
        }
    }

    /**
     * Called from MainActivity.onCreate or onResume
     */
    public static void registerActivity(Activity activity) {
        activeActivityRef = new WeakReference<>(activity);
        mainHandler.post(() -> attachOverlayIfPossible(activity));
    }

    /**
     * Relative jump in milliseconds (+30s, -15s, etc.)
     */
    public static void relativeJump(long deltaMs) {
        Object playerObj = getExoPlayer();
        if (playerObj == null) {
            showToast("⚠️ Geen actieve videospeler gevonden", false);
            return;
        }

        try {
            Method getPosMethod = playerObj.getClass().getMethod("getCurrentPosition");
            Method getDurMethod = playerObj.getClass().getMethod("getDuration");
            Method seekMethod = playerObj.getClass().getMethod("seekTo", long.class);

            long current = (Long) getPosMethod.invoke(playerObj);
            long duration = (Long) getDurMethod.invoke(playerObj);
            long target = Math.max(0, current + deltaMs);
            if (duration > 0 && target > duration) {
                target = duration;
            }

            previousPositionMs = current;
            seekMethod.invoke(playerObj, target);

            String dir = deltaMs > 0 ? "+" : "";
            showToast(String.format("⏩ %s%ds naar %s", dir, deltaMs / 1000, formatTime(target)), true);
        } catch (Throwable t) {
            showToast("Fout bij springen: " + t.getMessage(), false);
        }
    }

    /**
     * Jump in 1 step over commercial ad break (4:30m ahead)
     */
    public static void skipAdBreak() {
        relativeJump(DEFAULT_AD_BREAK_MS);
    }

    /**
     * Undo last jump
     */
    public static void undoLastJump() {
        if (previousPositionMs < 0) {
            showToast("Geen vorige positie om te herstellen", false);
            return;
        }

        Object playerObj = getExoPlayer();
        if (playerObj == null) return;

        try {
            Method seekMethod = playerObj.getClass().getMethod("seekTo", long.class);
            seekMethod.invoke(playerObj, previousPositionMs);
            showToast("↩️ Hersteld naar " + formatTime(previousPositionMs), false);
            previousPositionMs = -1L;
        } catch (Throwable ignored) {}
    }

    /**
     * Intercepts key events (remote controls, keyboards, gamepads)
     * Returns true if consumed.
     */
    public static boolean onKeyDown(int keyCode, KeyEvent event) {
        if (event.getAction() != KeyEvent.ACTION_DOWN) {
            return false;
        }

        switch (keyCode) {
            case KeyEvent.KEYCODE_MEDIA_FAST_FORWARD:
            case KeyEvent.KEYCODE_MEDIA_SKIP_FORWARD:
                relativeJump(JUMP_30S_MS);
                return true;

            case KeyEvent.KEYCODE_MEDIA_REWIND:
            case KeyEvent.KEYCODE_MEDIA_SKIP_BACKWARD:
                relativeJump(JUMP_BACK_15S_MS);
                return true;

            // Key 'S' or 'A' (Skip ad break)
            case KeyEvent.KEYCODE_S:
            case KeyEvent.KEYCODE_A:
                skipAdBreak();
                return true;

            // Key 'Z' (Undo jump)
            case KeyEvent.KEYCODE_Z:
                undoLastJump();
                return true;

            // Long press or special D-Pad actions
            case KeyEvent.KEYCODE_DPAD_RIGHT:
                if (event.isShiftPressed() || event.isAltPressed()) {
                    skipAdBreak();
                    return true;
                }
                break;
        }
        return false;
    }

    /**
     * Extracts active ExoPlayer instance using reflection from VideoPlayer wrapper
     */
    private static Object getExoPlayer() {
        Object vp = activeVideoPlayerRef.get();
        if (vp == null) return null;

        try {
            Field field = vp.getClass().getDeclaredField("exoPlayer");
            field.setAccessible(true);
            return field.get(vp);
        } catch (Throwable t) {
            // Fallback: search for any field assignable to Player / ExoPlayer
            for (Field f : vp.getClass().getDeclaredFields()) {
                if (f.getType().getName().contains("ExoPlayer") || f.getType().getName().contains("Player")) {
                    try {
                        f.setAccessible(true);
                        return f.get(vp);
                    } catch (Throwable ignored) {}
                }
            }
        }
        return null;
    }

    /**
     * Displays a compact Toast or on-screen notification with undo action
     */
    public static void showToast(String message, boolean canUndo) {
        mainHandler.post(() -> {
            Activity act = activeActivityRef.get();
            Context ctx = (act != null) ? act : null;
            if (ctx != null) {
                Toast.makeText(ctx, "[KPN AdSkip] " + message, Toast.LENGTH_SHORT).show();
            }
        });
    }

    /**
     * Injects a floating on-screen skip pill onto the Activity decor view
     */
    public static void attachOverlayIfPossible(Activity activity) {
        if (activity == null || overlayView != null) return;

        try {
            ViewGroup decorView = (ViewGroup) activity.getWindow().getDecorView();
            FrameLayout root = new FrameLayout(activity);
            FrameLayout.LayoutParams rootParams = new FrameLayout.LayoutParams(
                    ViewGroup.LayoutParams.WRAP_CONTENT,
                    ViewGroup.LayoutParams.WRAP_CONTENT,
                    Gravity.TOP | Gravity.END
            );
            rootParams.topMargin = 40;
            rootParams.rightMargin = 40;

            LinearLayout panel = new LinearLayout(activity);
            panel.setOrientation(LinearLayout.HORIZONTAL);
            panel.setPadding(16, 10, 16, 10);

            GradientDrawable bg = new GradientDrawable();
            bg.setColor(Color.parseColor("#E60F141A"));
            bg.setCornerRadius(20);
            bg.setStroke(2, Color.parseColor("#4D00CC66"));
            panel.setBackground(bg);

            // Skip Ad Break button
            Button skipBtn = new Button(activity);
            skipBtn.setText("⏩ Skip Reclame");
            skipBtn.setTextColor(Color.WHITE);
            skipBtn.setTextSize(12f);
            skipBtn.setTypeface(null, Typeface.BOLD);
            GradientDrawable btnBg = new GradientDrawable();
            btnBg.setColor(Color.parseColor("#009933"));
            btnBg.setCornerRadius(14);
            skipBtn.setBackground(btnBg);
            skipBtn.setPadding(20, 8, 20, 8);
            skipBtn.setOnClickListener(v -> skipAdBreak());

            // +30s button
            Button plus30 = createSmallButton(activity, "+30s", () -> relativeJump(JUMP_30S_MS));
            Button min15 = createSmallButton(activity, "-15s", () -> relativeJump(JUMP_BACK_15S_MS));

            panel.addView(skipBtn);
            panel.addView(min15);
            panel.addView(plus30);

            root.addView(panel);
            decorView.addView(root, rootParams);
            overlayView = root;
        } catch (Throwable ignored) {}
    }

    private static Button createSmallButton(Context ctx, String text, Runnable action) {
        Button b = new Button(ctx);
        b.setText(text);
        b.setTextColor(Color.WHITE);
        b.setTextSize(11f);
        GradientDrawable bg = new GradientDrawable();
        bg.setColor(Color.parseColor("#33FFFFFF"));
        bg.setCornerRadius(10);
        b.setBackground(bg);
        b.setPadding(12, 6, 12, 6);
        b.setOnClickListener(v -> action.run());
        return b;
    }

    private static String formatTime(long ms) {
        long sec = Math.max(0, ms / 1000);
        long m = sec / 60;
        long s = sec % 60;
        return String.format("%d:%02d", m, s);
    }
}
