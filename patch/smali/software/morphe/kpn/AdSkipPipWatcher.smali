.class public Lsoftware/morphe/kpn/AdSkipPipWatcher;
.super Ljava/lang/Object;
.implements Ljava/lang/Runnable;

.field private static scheduled:Z

.method public constructor <init>()V
    .registers 1
    invoke-direct {p0}, Ljava/lang/Object;-><init>()V
    return-void
.end method

.method public static schedule()V
    .registers 4

    # Already scheduled — the pending tick handles it
    sget-boolean v0, Lsoftware/morphe/kpn/AdSkipPipWatcher;->scheduled:Z
    if-nez v0, :return

    const/4 v0, 0x1
    sput-boolean v0, Lsoftware/morphe/kpn/AdSkipPipWatcher;->scheduled:Z

    invoke-static {}, Landroid/os/Looper;->getMainLooper()Landroid/os/Looper;
    move-result-object v0
    new-instance v1, Landroid/os/Handler;
    invoke-direct {v1, v0}, Landroid/os/Handler;-><init>(Landroid/os/Looper;)V

    new-instance v0, Lsoftware/morphe/kpn/AdSkipPipWatcher;
    invoke-direct {v0}, Lsoftware/morphe/kpn/AdSkipPipWatcher;-><init>()V

    const-wide/16 v2, 0x3e8
    invoke-virtual {v1, v0, v2, v3}, Landroid/os/Handler;->postDelayed(Ljava/lang/Runnable;J)Z

    :return
    return-void
.end method

.method public run()V
    .registers 7

    const/4 v0, 0x0
    sput-boolean v0, Lsoftware/morphe/kpn/AdSkipPipWatcher;->scheduled:Z

    # Only keep watching while the player is actually playing
    invoke-static {}, Lsoftware/morphe/kpn/AdSkipHook;->isPlaying()Z
    move-result v0
    if-eqz v0, :end

    # --- diagnostic probe: static flag vs activity PiP state (1/sec) ---
    invoke-static {}, Lsoftware/morphe/kpn/AdSkipHook;->isInPipMode()Z
    move-result v1
    sget-object v0, Lsoftware/morphe/kpn/AdSkipHook;->activeActivity:Ljava/lang/ref/WeakReference;
    if-eqz v0, :no_act
    invoke-virtual {v0}, Ljava/lang/ref/WeakReference;->get()Ljava/lang/Object;
    move-result-object v0
    if-eqz v0, :no_act
    check-cast v0, Landroid/app/Activity;
    invoke-virtual {v0}, Landroid/app/Activity;->isInPictureInPictureMode()Z
    move-result v2
    goto :have_act
    :no_act
    const/4 v2, 0x0
    :have_act
    new-instance v3, Ljava/lang/StringBuilder;
    invoke-direct {v3}, Ljava/lang/StringBuilder;-><init>()V
    const-string v4, "watch: flag="
    invoke-virtual {v3, v4}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    invoke-virtual {v3, v1}, Ljava/lang/StringBuilder;->append(Z)Ljava/lang/StringBuilder;
    const-string v4, " actPip="
    invoke-virtual {v3, v4}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    invoke-virtual {v3, v2}, Ljava/lang/StringBuilder;->append(Z)Ljava/lang/StringBuilder;
    invoke-virtual {v3}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;
    move-result-object v3
    invoke-static {v3}, Lsoftware/morphe/kpn/AdSkipHook;->log(Ljava/lang/String;)V

    # Enforce overlay visibility; the PiP guard inside setVisibility hides the
    # overlay whenever the app is in (system) PiP mode or PiP just started.
    const/4 v0, 0x1
    invoke-static {v0}, Lsoftware/morphe/kpn/AdSkipButton;->setVisibility(Z)V

    invoke-static {}, Lsoftware/morphe/kpn/AdSkipPipWatcher;->schedule()V

    :end
    return-void
.end method