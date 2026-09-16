.class public Lsoftware/morphe/kpn/AdSkipHook;
.super Ljava/lang/Object;
.source "AdSkipHook.java"

# static fields
.field private static activePlayer:Ljava/lang/Object;

.field private static activeActivity:Ljava/lang/ref/WeakReference;
    .annotation system Ldalvik/annotation/Signature;
        value = {
            "Ljava/lang/ref/WeakReference<",
            "Landroid/app/Activity;",
            ">;"
        }
    .end annotation
.end field

.field private static previousPositionMs:J


# direct methods
.method static constructor <clinit>()V
    .registers 2

    const/4 v0, 0x0
    sput-object v0, Lsoftware/morphe/kpn/AdSkipHook;->activePlayer:Ljava/lang/Object;
    sput-object v0, Lsoftware/morphe/kpn/AdSkipHook;->activeActivity:Ljava/lang/ref/WeakReference;
    const-wide/16 v0, -0x1
    sput-wide v0, Lsoftware/morphe/kpn/AdSkipHook;->previousPositionMs:J
    return-void
.end method

.method public constructor <init>()V
    .registers 1

    invoke-direct {p0}, Ljava/lang/Object;-><init>()V
    return-void
.end method

.method public static registerPlayer(Ljava/lang/Object;)V
    .registers 1
    .param p0, "playerWrapper"    # Ljava/lang/Object;

    if-eqz p0, :cond_0
    sput-object p0, Lsoftware/morphe/kpn/AdSkipHook;->activePlayer:Ljava/lang/Object;

    :cond_0
    return-void
.end method

.method public static registerActivity(Landroid/app/Activity;)V
    .registers 2
    .param p0, "act"    # Landroid/app/Activity;

    if-eqz p0, :cond_0
    new-instance v0, Ljava/lang/ref/WeakReference;
    invoke-direct {v0, p0}, Ljava/lang/ref/WeakReference;-><init>(Ljava/lang/Object;)V
    sput-object v0, Lsoftware/morphe/kpn/AdSkipHook;->activeActivity:Ljava/lang/ref/WeakReference;

    :cond_0
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
    .registers 5

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
    .registers 4
    .param p0, "keyCode"    # I
    .param p1, "event"      # Landroid/view/KeyEvent;

    invoke-virtual {p1}, Landroid/view/KeyEvent;->getAction()I
    move-result v0
    if-eqz v0, :cond_0
    const/4 v0, 0x0
    return v0

    :cond_0
    # Key 0x5a (90: KEYCODE_MEDIA_FAST_FORWARD) or 0x57 (87: KEYCODE_MEDIA_NEXT)
    const/16 v0, 0x5a
    if-eq p0, v0, :cond_skip_30s
    const/16 v0, 0x57
    if-ne p0, v0, :cond_check_rewind

:cond_skip_30s
    const-wide/16 v0, 0x7530    # +30,000 ms
    invoke-static {v0, v1}, Lsoftware/morphe/kpn/AdSkipHook;->relativeJump(J)V
    const/4 v0, 0x1
    return v0

:cond_check_rewind
    # Key 0x59 (89: KEYCODE_MEDIA_REWIND) or 0x58 (88: KEYCODE_MEDIA_PREVIOUS)
    const/16 v0, 0x59
    if-eq p0, v0, :cond_skip_back
    const/16 v0, 0x58
    if-ne p0, v0, :cond_check_adbreak

:cond_skip_back
    const-wide/16 v0, -0x3a98    # -15,000 ms
    invoke-static {v0, v1}, Lsoftware/morphe/kpn/AdSkipHook;->relativeJump(J)V
    const/4 v0, 0x1
    return v0

:cond_check_adbreak
    # Key 0x2f (47: KEYCODE_S) or 0x1d (29: KEYCODE_A)
    const/16 v0, 0x2f
    if-eq p0, v0, :cond_skip_ad
    const/16 v0, 0x1d
    if-ne p0, v0, :cond_check_undo

:cond_skip_ad
    invoke-static {}, Lsoftware/morphe/kpn/AdSkipHook;->skipAdBreak()V
    const/4 v0, 0x1
    return v0

:cond_check_undo
    # Key 0x36 (54: KEYCODE_Z)
    const/16 v0, 0x36
    if-ne p0, v0, :cond_default

    invoke-static {}, Lsoftware/morphe/kpn/AdSkipHook;->undoLastJump()V
    const/4 v0, 0x1
    return v0

:cond_default
    const/4 v0, 0x0
    return v0
.end method

.method private static getExoPlayer()Ljava/lang/Object;
    .registers 5

    sget-object v0, Lsoftware/morphe/kpn/AdSkipHook;->activePlayer:Ljava/lang/Object;
    const/4 v1, 0x0
    if-nez v0, :cond_0
    return-object v1

    :cond_0
    :try_start_0
    invoke-virtual {v0}, Ljava/lang/Object;->getClass()Ljava/lang/Class;
    move-result-object v2
    const-string v3, "exoPlayer"
    invoke-virtual {v2, v3}, Ljava/lang/Class;->getDeclaredField(Ljava/lang/String;)Ljava/lang/reflect/Field;
    move-result-object v2
    const/4 v3, 0x1
    invoke-virtual {v2, v3}, Ljava/lang/reflect/Field;->setAccessible(Z)V
    invoke-virtual {v2, v0}, Ljava/lang/reflect/Field;->get(Ljava/lang/Object;)Ljava/lang/Object;
    move-result-object v0
    :try_end_0
    .catchall {:try_start_0 .. :try_end_0} :catchall_0

    return-object v0

    :catchall_0
    return-object v1
.end method
