.class public Lsoftware/morphe/kpn/AdSkipHook;
.super Ljava/lang/Object;
.source "AdSkipHook.java"

# static fields
.field private static activePlayer:Ljava/lang/Object;

.field private static activeExoPlayer:Ljava/lang/Object;

.field public static activeActivity:Ljava/lang/ref/WeakReference;
    .annotation system Ldalvik/annotation/Signature;
        value = {
            "Ljava/lang/ref/WeakReference<",
            "Landroid/app/Activity;",
            ">;"
        }
    .end annotation
.end field

.field private static previousPositionMs:J

.field private static mediaStoreUri:Landroid/net/Uri;

.field private static isPlaying:Z

.field private static isInPipMode:Z

.field private static overlayView:Landroid/view/View;


# direct methods
.method static constructor <clinit>()V
    .registers 3

    const/4 v0, 0x0
    sput-object v0, Lsoftware/morphe/kpn/AdSkipHook;->activePlayer:Ljava/lang/Object;
    sput-object v0, Lsoftware/morphe/kpn/AdSkipHook;->activeExoPlayer:Ljava/lang/Object;
    sput-object v0, Lsoftware/morphe/kpn/AdSkipHook;->activeActivity:Ljava/lang/ref/WeakReference;
    sput-object v0, Lsoftware/morphe/kpn/AdSkipHook;->mediaStoreUri:Landroid/net/Uri;
    const-wide/16 v0, -0x1
    sput-wide v0, Lsoftware/morphe/kpn/AdSkipHook;->previousPositionMs:J

    const-string v1, "AdSkipHook class loaded (KPN_AdSkip)"
    invoke-static {v1}, Lsoftware/morphe/kpn/AdSkipHook;->log(Ljava/lang/String;)V
    return-void
.end method

.method public constructor <init>()V
    .registers 1

    invoke-direct {p0}, Ljava/lang/Object;-><init>()V
    return-void
.end method

.method public static registerPlayer(Ljava/lang/Object;)V
    .registers 3
    .param p0, "playerWrapper"    # Ljava/lang/Object;

    if-eqz p0, :cond_0
    sput-object p0, Lsoftware/morphe/kpn/AdSkipHook;->activePlayer:Ljava/lang/Object;

    new-instance v0, Ljava/lang/StringBuilder;
    invoke-direct {v0}, Ljava/lang/StringBuilder;-><init>()V
    const-string v1, "registerPlayer: "
    invoke-virtual {v0, v1}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    invoke-virtual {p0}, Ljava/lang/Object;->getClass()Ljava/lang/Class;
    move-result-object v1
    invoke-virtual {v1}, Ljava/lang/Class;->getName()Ljava/lang/String;
    move-result-object v1
    invoke-virtual {v0, v1}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    invoke-virtual {v0}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;
    move-result-object v0
    invoke-static {v0}, Lsoftware/morphe/kpn/AdSkipHook;->log(Ljava/lang/String;)V

    :cond_0
    return-void
.end method

.method public static registerExoPlayer(Ljava/lang/Object;)V
    .registers 3
    .param p0, "exoPlayer"    # Ljava/lang/Object;

    if-eqz p0, :cond_0
    sput-object p0, Lsoftware/morphe/kpn/AdSkipHook;->activeExoPlayer:Ljava/lang/Object;

    new-instance v0, Ljava/lang/StringBuilder;
    invoke-direct {v0}, Ljava/lang/StringBuilder;-><init>()V
    const-string v1, "registerExoPlayer: "
    invoke-virtual {v0, v1}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    invoke-virtual {p0}, Ljava/lang/Object;->getClass()Ljava/lang/Class;
    move-result-object v1
    invoke-virtual {v1}, Ljava/lang/Class;->getName()Ljava/lang/String;
    move-result-object v1
    invoke-virtual {v0, v1}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    invoke-virtual {v0}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;
    move-result-object v0
    invoke-static {v0}, Lsoftware/morphe/kpn/AdSkipHook;->log(Ljava/lang/String;)V

    :cond_0
    return-void
.end method

.method public static logNativeMethod(Ljava/lang/String;)V
    .registers 3
    .param p0, "methodName"    # Ljava/lang/String;

    new-instance v0, Ljava/lang/StringBuilder;
    invoke-direct {v0}, Ljava/lang/StringBuilder;-><init>()V
    const-string v1, "NATIVE_PLAYER call: "
    invoke-virtual {v0, v1}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    invoke-virtual {v0, p0}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    invoke-virtual {v0}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;
    move-result-object v0
    invoke-static {v0}, Lsoftware/morphe/kpn/AdSkipHook;->log(Ljava/lang/String;)V
    return-void
.end method

.method public static registerActivity(Landroid/app/Activity;)V
    .registers 5
    .param p0, "act"    # Landroid/app/Activity;

    if-eqz p0, :cond_0
    new-instance v0, Ljava/lang/ref/WeakReference;
    invoke-direct {v0, p0}, Ljava/lang/ref/WeakReference;-><init>(Ljava/lang/Object;)V
    sput-object v0, Lsoftware/morphe/kpn/AdSkipHook;->activeActivity:Ljava/lang/ref/WeakReference;

    invoke-virtual {p0}, Landroid/app/Activity;->getWindow()Landroid/view/Window;
    move-result-object v0
    invoke-virtual {v0}, Landroid/view/Window;->getDecorView()Landroid/view/View;
    move-result-object v0
    new-instance v1, Lsoftware/morphe/kpn/AdSkipOverlayTask;
    invoke-direct {v1, p0}, Lsoftware/morphe/kpn/AdSkipOverlayTask;-><init>(Landroid/app/Activity;)V
    const-wide/16 v2, 0x7d0
    invoke-virtual {v0, v1, v2, v3}, Landroid/view/View;->postDelayed(Ljava/lang/Runnable;J)Z

    :cond_0
    return-void
.end method

.method public static setPlaying(Z)V
    .registers 4
    .param p0, "playing"    # Z

    sput-boolean p0, Lsoftware/morphe/kpn/AdSkipHook;->isPlaying:Z

    new-instance v0, Ljava/lang/StringBuilder;
    invoke-direct {v0}, Ljava/lang/StringBuilder;-><init>()V
    const-string v1, "setPlaying("
    invoke-virtual {v0, v1}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    invoke-virtual {v0, p0}, Ljava/lang/StringBuilder;->append(Z)Ljava/lang/StringBuilder;
    const-string v1, ") calling setVisibility"
    invoke-virtual {v0, v1}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    invoke-virtual {v0}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;
    move-result-object v0
    invoke-static {v0}, Lsoftware/morphe/kpn/AdSkipHook;->log(Ljava/lang/String;)V

    invoke-static {p0}, Lsoftware/morphe/kpn/AdSkipButton;->setVisibility(Z)V

    # Start the 1Hz PiP watcher while playing: guaranteed overlay hide/show on
    # PiP entry/exit even if onPictureInPictureModeChanged never fires.
    if-eqz p0, :end
    invoke-static {}, Lsoftware/morphe/kpn/AdSkipPipWatcher;->schedule()V
    :end
    return-void
.end method

.method public static setPipMode(Z)V
    .registers 4
    .param p0, "inPipMode"    # Z

    sput-boolean p0, Lsoftware/morphe/kpn/AdSkipHook;->isInPipMode:Z

    new-instance v0, Ljava/lang/StringBuilder;
    invoke-direct {v0}, Ljava/lang/StringBuilder;-><init>()V
    const-string v1, "setPipMode("
    invoke-virtual {v0, v1}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    invoke-virtual {v0, p0}, Ljava/lang/StringBuilder;->append(Z)Ljava/lang/StringBuilder;
    const-string v1, ")"
    invoke-virtual {v0, v1}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    invoke-virtual {v0}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;
    move-result-object v0
    invoke-static {v0}, Lsoftware/morphe/kpn/AdSkipHook;->log(Ljava/lang/String;)V

    # Entering PiP: hide overlay immediately via setVisibility(true) — the PiP
    # guard inside setVisibility (flag just set above) hides the view. Playing
    # state does NOT change on PiP entry, so no other event would hide it.
    # Exiting PiP: restore overlay to match the actual playing state.
    # (Routing through the public setVisibility avoids any cross-class field
    # access — AdSkipButton.overlayView is private.)
    if-eqz p0, :exit_pip
    invoke-static {p0}, Lsoftware/morphe/kpn/AdSkipButton;->setVisibility(Z)V
    return-void

    :exit_pip
    sget-boolean v1, Lsoftware/morphe/kpn/AdSkipHook;->isPlaying:Z
    invoke-static {v1}, Lsoftware/morphe/kpn/AdSkipButton;->setVisibility(Z)V
    return-void
.end method

.method public static isInPipMode()Z
    .registers 1
    sget-boolean v0, Lsoftware/morphe/kpn/AdSkipHook;->isInPipMode:Z
    return v0
.end method

.method public static isPlaying()Z
    .registers 1
    sget-boolean v0, Lsoftware/morphe/kpn/AdSkipHook;->isPlaying:Z
    return v0
.end method

.method public static registerSeek(J)V
    .registers 4
    .param p0, "targetMs"    # J

    new-instance v0, Ljava/lang/StringBuilder;
    invoke-direct {v0}, Ljava/lang/StringBuilder;-><init>()V
    const-string v1, "VIDEOPLAYER seekTo target="
    invoke-virtual {v0, v1}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    invoke-virtual {v0, p0, p1}, Ljava/lang/StringBuilder;->append(J)Ljava/lang/StringBuilder;
    invoke-virtual {v0}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;
    move-result-object v0
    invoke-static {v0}, Lsoftware/morphe/kpn/AdSkipHook;->log(Ljava/lang/String;)V
    return-void
.end method

.method public static logPlay()V
    .registers 1

    const-string v0, "VIDEOPLAYER play()"
    invoke-static {v0}, Lsoftware/morphe/kpn/AdSkipHook;->log(Ljava/lang/String;)V
    return-void
.end method

.method public static logPause()V
    .registers 1

    const-string v0, "VIDEOPLAYER pause()"
    invoke-static {v0}, Lsoftware/morphe/kpn/AdSkipHook;->log(Ljava/lang/String;)V
    return-void
.end method

.method public static logDispose()V
    .registers 1

    const-string v0, "VIDEOPLAYER dispose()"
    invoke-static {v0}, Lsoftware/morphe/kpn/AdSkipHook;->log(Ljava/lang/String;)V
    return-void
.end method

.method public static registerMediaItem(Ljava/lang/Object;)V
    .registers 3

    if-eqz p0, :cond_done
    new-instance v0, Ljava/lang/StringBuilder;
    invoke-direct {v0}, Ljava/lang/StringBuilder;-><init>()V
    const-string v1, "MEDIA_ITEM: "
    invoke-virtual {v0, v1}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    invoke-virtual {p0}, Ljava/lang/Object;->toString()Ljava/lang/String;
    move-result-object v1
    invoke-virtual {v0, v1}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    invoke-virtual {v0}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;
    move-result-object v0
    invoke-static {v0}, Lsoftware/morphe/kpn/AdSkipHook;->log(Ljava/lang/String;)V

    :cond_done
    return-void
.end method

.method public static skipAdBreak()V
    .registers 2

    # Jump 4.5 minutes (270,000 ms) ahead
    const-wide/32 v0, 0x41eb0
    invoke-static {v0, v1}, Lsoftware/morphe/kpn/AdSkipHook;->relativeJump(J)V
    return-void
.end method

.method public static undoLastJump()V
    .registers 6

    sget-wide v0, Lsoftware/morphe/kpn/AdSkipHook;->previousPositionMs:J
    const-wide/16 v2, 0x0
    cmp-long v4, v0, v2
    if-gez v4, :cond_0
    return-void

    :cond_0
    invoke-static {}, Lsoftware/morphe/kpn/AdSkipHook;->getExoPlayer()Ljava/lang/Object;
    move-result-object v0
    if-nez v0, :cond_1
    return-void

    :cond_1
    :try_start_0
    invoke-virtual {v0}, Ljava/lang/Object;->getClass()Ljava/lang/Class;
    move-result-object v1
    const-string v2, "seekTo"
    const/4 v3, 0x1
    new-array v3, v3, [Ljava/lang/Class;
    sget-object v4, Ljava/lang/Long;->TYPE:Ljava/lang/Class;
    const/4 v5, 0x0
    aput-object v4, v3, v5
    invoke-virtual {v1, v2, v3}, Ljava/lang/Class;->getMethod(Ljava/lang/String;[Ljava/lang/Class;)Ljava/lang/reflect/Method;
    move-result-object v1

    const/4 v2, 0x1
    new-array v2, v2, [Ljava/lang/Object;
    sget-wide v3, Lsoftware/morphe/kpn/AdSkipHook;->previousPositionMs:J
    invoke-static {v3, v4}, Ljava/lang/Long;->valueOf(J)Ljava/lang/Long;
    move-result-object v3
    aput-object v3, v2, v5
    invoke-virtual {v1, v0, v2}, Ljava/lang/reflect/Method;->invoke(Ljava/lang/Object;[Ljava/lang/Object;)Ljava/lang/Object;

    const-wide/16 v0, -0x1
    sput-wide v0, Lsoftware/morphe/kpn/AdSkipHook;->previousPositionMs:J
    :try_end_0
    .catchall {:try_start_0 .. :try_end_0} :catchall_0

    :catchall_0
    return-void
.end method

.method public static relativeJump(J)V
    .registers 14
    .param p0, "deltaMs"    # J

    invoke-static {}, Lsoftware/morphe/kpn/AdSkipHook;->getExoPlayer()Ljava/lang/Object;
    move-result-object v0
    if-nez v0, :cond_0
    return-void

    :cond_0
    :try_start_0
    invoke-virtual {v0}, Ljava/lang/Object;->getClass()Ljava/lang/Class;
    move-result-object v1

    const-string v2, "getCurrentPosition"
    const/4 v3, 0x0
    new-array v4, v3, [Ljava/lang/Class;
    invoke-virtual {v1, v2, v4}, Ljava/lang/Class;->getMethod(Ljava/lang/String;[Ljava/lang/Class;)Ljava/lang/reflect/Method;
    move-result-object v2

    new-array v4, v3, [Ljava/lang/Object;
    invoke-virtual {v2, v0, v4}, Ljava/lang/reflect/Method;->invoke(Ljava/lang/Object;[Ljava/lang/Object;)Ljava/lang/Object;
    move-result-object v2
    check-cast v2, Ljava/lang/Long;
    invoke-virtual {v2}, Ljava/lang/Long;->longValue()J
    move-result-wide v4

    # Save previous position for undo
    sput-wide v4, Lsoftware/morphe/kpn/AdSkipHook;->previousPositionMs:J

    # Calculate target
    add-long v6, v4, p0
    const-wide/16 v8, 0x0
    cmp-long v2, v6, v8
    if-gez v2, :cond_1
    const-wide/16 v6, 0x0

    :cond_1
    const-string v2, "seekTo"
    const/4 v8, 0x1
    new-array v9, v8, [Ljava/lang/Class;
    sget-object v10, Ljava/lang/Long;->TYPE:Ljava/lang/Class;
    aput-object v10, v9, v3
    invoke-virtual {v1, v2, v9}, Ljava/lang/Class;->getMethod(Ljava/lang/String;[Ljava/lang/Class;)Ljava/lang/reflect/Method;
    move-result-object v1

    # Log the seek target before executing (v6/v7 still hold the primitive long)
    new-instance v11, Ljava/lang/StringBuilder;
    invoke-direct {v11}, Ljava/lang/StringBuilder;-><init>()V
    const-string v10, "seek to "
    invoke-virtual {v11, v10}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    invoke-virtual {v11, v6, v7}, Ljava/lang/StringBuilder;->append(J)Ljava/lang/StringBuilder;
    invoke-virtual {v11}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;
    move-result-object v11
    invoke-static {v11}, Lsoftware/morphe/kpn/AdSkipHook;->log(Ljava/lang/String;)V

    new-array v2, v8, [Ljava/lang/Object;
    invoke-static {v6, v7}, Ljava/lang/Long;->valueOf(J)Ljava/lang/Long;
    move-result-object v6
    aput-object v6, v2, v3

    invoke-virtual {v1, v0, v2}, Ljava/lang/reflect/Method;->invoke(Ljava/lang/Object;[Ljava/lang/Object;)Ljava/lang/Object;
    :try_end_0
    .catchall {:try_start_0 .. :try_end_0} :catchall_0

    :catchall_0
    return-void
.end method

.method public static onKeyDown(ILandroid/view/KeyEvent;)Z
    .registers 6
    .param p0, "keyCode"    # I
    .param p1, "event"      # Landroid/view/KeyEvent;

    invoke-virtual {p1}, Landroid/view/KeyEvent;->getAction()I
    move-result v0
    if-eqz v0, :cond_0
    const/4 v0, 0x0
    return v0

    :cond_0
    new-instance v2, Ljava/lang/StringBuilder;
    invoke-direct {v2}, Ljava/lang/StringBuilder;-><init>()V
    const-string v3, "KEYDOWN code="
    invoke-virtual {v2, v3}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    invoke-virtual {v2, p0}, Ljava/lang/StringBuilder;->append(I)Ljava/lang/StringBuilder;
    invoke-virtual {v2}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;
    move-result-object v2
    invoke-static {v2}, Lsoftware/morphe/kpn/AdSkipHook;->log(Ljava/lang/String;)V

    # Forward: 0x5a(90) MEDIA_FAST_FORWARD, 0x57(87) MEDIA_NEXT,
    #          0x16(22) DPAD_RIGHT, 0x22(34) F
    const/16 v0, 0x5a
    if-eq p0, v0, :do_forward
    const/16 v0, 0x57
    if-eq p0, v0, :do_forward
    const/16 v0, 0x16
    if-eq p0, v0, :do_forward
    const/16 v0, 0x22
    if-eq p0, v0, :do_forward

    # Rewind: 0x59(89) MEDIA_REWIND, 0x58(88) MEDIA_PREVIOUS,
    #         0x15(21) DPAD_LEFT, 0x2e(46) R
    const/16 v0, 0x59
    if-eq p0, v0, :do_rewind
    const/16 v0, 0x58
    if-eq p0, v0, :do_rewind
    const/16 v0, 0x15
    if-eq p0, v0, :do_rewind
    const/16 v0, 0x2e
    if-eq p0, v0, :do_rewind

    # Skip ad: 0x2f(47) S, 0x1d(29) A, 0x55(85) MEDIA_PLAY_PAUSE
    const/16 v0, 0x2f
    if-eq p0, v0, :do_skip_ad
    const/16 v0, 0x1d
    if-eq p0, v0, :do_skip_ad
    const/16 v0, 0x55
    if-eq p0, v0, :do_skip_ad

    # Undo: 0x36(54) Z
    const/16 v0, 0x36
    if-eq p0, v0, :do_undo

    const/4 v0, 0x0
    return v0

    :do_forward
    const-wide/16 v0, 0x7530
    invoke-static {v0, v1}, Lsoftware/morphe/kpn/AdSkipHook;->relativeJump(J)V
    const/4 v0, 0x1
    return v0

    :do_rewind
    const-wide/16 v0, -0x3a98
    invoke-static {v0, v1}, Lsoftware/morphe/kpn/AdSkipHook;->relativeJump(J)V
    const/4 v0, 0x1
    return v0

    :do_skip_ad
    invoke-static {}, Lsoftware/morphe/kpn/AdSkipHook;->skipAdBreak()V
    const/4 v0, 0x1
    return v0

    :do_undo
    invoke-static {}, Lsoftware/morphe/kpn/AdSkipHook;->undoLastJump()V
    const/4 v0, 0x1
    return v0
.end method

.method private static getExoPlayer()Ljava/lang/Object;
    .registers 6

    sget-object v0, Lsoftware/morphe/kpn/AdSkipHook;->activeExoPlayer:Ljava/lang/Object;
    const/4 v1, 0x0
    if-eqz v0, :cond_direct
    return-object v0

    :cond_direct
    sget-object v0, Lsoftware/morphe/kpn/AdSkipHook;->activePlayer:Ljava/lang/Object;
    if-nez v0, :cond_0
    return-object v1

    :cond_0
    :try_start_0
    invoke-virtual {v0}, Ljava/lang/Object;->getClass()Ljava/lang/Class;
    move-result-object v2
    const-string v3, "exoPlayer"
    invoke-virtual {v2, v3}, Ljava/lang/Class;->getDeclaredField(Ljava/lang/String;)Ljava/lang/reflect/Field;
    move-result-object v2
    const/4 v4, 0x1
    invoke-virtual {v2, v4}, Ljava/lang/reflect/Field;->setAccessible(Z)V
    invoke-virtual {v2, v0}, Ljava/lang/reflect/Field;->get(Ljava/lang/Object;)Ljava/lang/Object;
    move-result-object v0
    :try_end_0
    .catchall {:try_start_0 .. :try_end_0} :catchall_0

    return-object v0

    :catchall_0
    const-string v3, "getExoPlayer DID NOT FIND exoPlayer field (reflection failed)"
    invoke-static {v3}, Lsoftware/morphe/kpn/AdSkipHook;->log(Ljava/lang/String;)V
    return-object v1
.end method


.method public static log(Ljava/lang/String;)V
    .registers 4
    .param p0, "msg"    # Ljava/lang/String;

    # Always write to logcat (retrievable via: adb logcat -s KPN_AdSkip:E)
    const-string v0, "KPN_AdSkip"
    invoke-static {v0, p0}, Landroid/util/Log;->e(Ljava/lang/String;Ljava/lang/String;)I

    :try_start_0
    # Android 10+ (API 29): use MediaStore so the file really appears in Download
    sget v0, Landroid/os/Build$VERSION;->SDK_INT:I
    const/16 v1, 0x1d
    if-lt v0, v1, :cond_legacy
    invoke-static {p0}, Lsoftware/morphe/kpn/AdSkipHook;->appendMediaStore(Ljava/lang/String;)V
    goto :cond_files

    # Android 9-: direct write to /sdcard/Download
    :cond_legacy
    new-instance v0, Ljava/io/File;
    const-string v1, "/sdcard/Download/kpn_debug.log"
    invoke-direct {v0, v1}, Ljava/io/File;-><init>(Ljava/lang/String;)V
    invoke-static {v0, p0}, Lsoftware/morphe/kpn/AdSkipHook;->appendLog(Ljava/io/File;Ljava/lang/String;)V

    # Always: also write to app-specific external dir (scoped-storage safe and adb-accessible):
    #   /sdcard/Android/data/<package>/files/kpn_debug.log
    :cond_files
    invoke-static {}, Landroid/app/ActivityThread;->currentApplication()Landroid/app/Application;
    move-result-object v0
    if-eqz v0, :cond_skip
    const/4 v1, 0x0
    invoke-virtual {v0, v1}, Landroid/content/Context;->getExternalFilesDir(Ljava/lang/String;)Ljava/io/File;
    move-result-object v0
    if-eqz v0, :cond_skip
    new-instance v1, Ljava/io/File;
    const-string v2, "kpn_debug.log"
    invoke-direct {v1, v0, v2}, Ljava/io/File;-><init>(Ljava/io/File;Ljava/lang/String;)V
    invoke-static {v1, p0}, Lsoftware/morphe/kpn/AdSkipHook;->appendLog(Ljava/io/File;Ljava/lang/String;)V
    :cond_skip
    :try_end_0
    .catchall {:try_start_0 .. :try_end_0} :catchall_0

    :catchall_0
    return-void
.end method

.method private static appendLog(Ljava/io/File;Ljava/lang/String;)V
    .registers 7
    .param p0, "file"   # Ljava/io/File;
    .param p1, "msg"    # Ljava/lang/String;

    :try_start_0
    new-instance v0, Ljava/io/FileWriter;
    const/4 v1, 0x1
    invoke-direct {v0, p0, v1}, Ljava/io/FileWriter;-><init>(Ljava/io/File;Z)V

    new-instance v1, Ljava/lang/StringBuilder;
    invoke-direct {v1}, Ljava/lang/StringBuilder;-><init>()V
    new-instance v2, Ljava/text/SimpleDateFormat;
    const-string v3, "yyyy-MM-dd HH:mm:ss.SSS"
    sget-object v4, Ljava/util/Locale;->US:Ljava/util/Locale;
    invoke-direct {v2, v3, v4}, Ljava/text/SimpleDateFormat;-><init>(Ljava/lang/String;Ljava/util/Locale;)V
    new-instance v3, Ljava/util/Date;
    invoke-direct {v3}, Ljava/util/Date;-><init>()V
    invoke-virtual {v2, v3}, Ljava/text/SimpleDateFormat;->format(Ljava/util/Date;)Ljava/lang/String;
    move-result-object v2
    invoke-virtual {v1, v2}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    const-string v2, " | "
    invoke-virtual {v1, v2}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    invoke-virtual {v1, p1}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    const-string v2, "\n"
    invoke-virtual {v1, v2}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    invoke-virtual {v1}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;
    move-result-object v1
    invoke-virtual {v0, v1}, Ljava/io/Writer;->write(Ljava/lang/String;)V
    invoke-virtual {v0}, Ljava/io/OutputStreamWriter;->close()V
    :try_end_0
    .catchall {:try_start_0 .. :try_end_0} :catchall_0

    :catchall_0
    return-void
.end method

.method private static appendMediaStore(Ljava/lang/String;)V
    .registers 6
    .param p0, "msg"    # Ljava/lang/String;

    :try_start_0
    invoke-static {}, Landroid/app/ActivityThread;->currentApplication()Landroid/app/Application;
    move-result-object v0
    if-nez v0, :cond_done

    invoke-virtual {v0}, Landroid/content/Context;->getContentResolver()Landroid/content/ContentResolver;
    move-result-object v0
    if-nez v0, :cond_done

    # Reuse the previously inserted Uri so we append to the same Download file
    sget-object v1, Lsoftware/morphe/kpn/AdSkipHook;->mediaStoreUri:Landroid/net/Uri;
    if-nez v1, :cond_have_uri

    new-instance v1, Landroid/content/ContentValues;
    invoke-direct {v1}, Landroid/content/ContentValues;-><init>()V

    const-string v2, "_display_name"
    const-string v3, "kpn_debug.log"
    invoke-virtual {v1, v2, v3}, Landroid/content/ContentValues;->put(Ljava/lang/String;Ljava/lang/String;)V

    const-string v2, "mime_type"
    const-string v3, "text/plain"
    invoke-virtual {v1, v2, v3}, Landroid/content/ContentValues;->put(Ljava/lang/String;Ljava/lang/String;)V

    const-string v2, "relative_path"
    const-string v3, "Download/"
    invoke-virtual {v1, v2, v3}, Landroid/content/ContentValues;->put(Ljava/lang/String;Ljava/lang/String;)V

    sget-object v2, Landroid/provider/MediaStore$Downloads;->EXTERNAL_CONTENT_URI:Landroid/net/Uri;
    invoke-virtual {v0, v2, v1}, Landroid/content/ContentResolver;->insert(Landroid/net/Uri;Landroid/content/ContentValues;)Landroid/net/Uri;
    move-result-object v1
    if-eqz v1, :cond_done
    sput-object v1, Lsoftware/morphe/kpn/AdSkipHook;->mediaStoreUri:Landroid/net/Uri;

    :cond_have_uri
    const-string v2, "wa"
    invoke-virtual {v0, v1, v2}, Landroid/content/ContentResolver;->openOutputStream(Landroid/net/Uri;Ljava/lang/String;)Ljava/io/OutputStream;
    move-result-object v0
    if-nez v0, :cond_done

    new-instance v1, Ljava/lang/StringBuilder;
    invoke-direct {v1}, Ljava/lang/StringBuilder;-><init>()V
    invoke-virtual {v1, p0}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    const-string v2, "\n"
    invoke-virtual {v1, v2}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    invoke-virtual {v1}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;
    move-result-object v1
    invoke-virtual {v1}, Ljava/lang/String;->getBytes()[B
    move-result-object v1
    invoke-virtual {v0, v1}, Ljava/io/OutputStream;->write([B)V
    invoke-virtual {v0}, Ljava/io/OutputStream;->flush()V
    invoke-virtual {v0}, Ljava/io/OutputStream;->close()V
    :cond_done
    :try_end_0
    .catchall {:try_start_0 .. :try_end_0} :catchall_0

    :catchall_0
    return-void
.end method
