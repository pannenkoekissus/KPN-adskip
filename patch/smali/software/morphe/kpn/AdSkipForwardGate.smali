.class public Lsoftware/morphe/kpn/AdSkipForwardGate;
.super Ljava/lang/Object;
.implements Ljava/lang/Runnable;
.source "AdSkipForwardGate.java"

# Static: snapshot of the player position taken when the built-in 30s forward
# button was tapped.
.field private final lastPositionMs:J

.method public constructor <init>(J)V
    .registers 6

    invoke-direct {p0}, Ljava/lang/Object;-><init>()V
    iput-wide p1, p0, Lsoftware/morphe/kpn/AdSkipForwardGate;->lastPositionMs:J
    return-void
.end method

# Runs ~800ms after the button tap. If the app's own click handling already
# seeked (position moved ~30s), we do nothing -> avoids a double +30s jump.
# If nothing moved, the ad UI swallowed the tap -> we jump ourselves.
#
# DISCOVERY MODE: the actual relativeJump() is behind a const flag (0 = log
# only, 1 = execute). First build is discovery-only so we can see the real
# event/seek behavior in logcat before enabling the jump.
.method public run()V
    .registers 9

    invoke-static {}, Lsoftware/morphe/kpn/AdSkipHook;->getCurrentPositionMs()J
    move-result-wide v0
    iget-wide v2, p0, Lsoftware/morphe/kpn/AdSkipForwardGate;->lastPositionMs:J
    sub-long v0, v0, v2

    new-instance v6, Ljava/lang/StringBuilder;
    invoke-direct {v6}, Ljava/lang/StringBuilder;-><init>()V
    const-string v7, "A11Y_FWD gate: delta="
    invoke-virtual {v6, v7}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    invoke-virtual {v6, v0, v1}, Ljava/lang/StringBuilder;->append(J)Ljava/lang/StringBuilder;
    const-string v7, "ms"
    invoke-virtual {v6, v7}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    invoke-virtual {v6}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;
    move-result-object v6
    invoke-static {v6}, Lsoftware/morphe/kpn/AdSkipHook;->log(Ljava/lang/String;)V

    # delta >= 15000ms: the app already seeked ~30s on its own -> skip.
    const-wide/16 v4, 0x3a98
    cmp-long v6, v0, v4
    if-ltz v6, :do_jump

    const-string v6, "A11Y_FWD gate: native/Dart seek already happened, skipping own jump"
    invoke-static {v6}, Lsoftware/morphe/kpn/AdSkipHook;->log(Ljava/lang/String;)V
    return-void

    :do_jump
    # DISCOVERY MODE: flip this to 0x1 to actually execute the +30s jump.
    const/4 v6, 0x0
    if-nez v6, :really_jump
    const-string v6, "A11Y_FWD gate: would jump +30s (execution disabled - discovery build)"
    invoke-static {v6}, Lsoftware/morphe/kpn/AdSkipHook;->log(Ljava/lang/String;)V
    return-void

    :really_jump
    const-wide/16 v0, 0x7530
    invoke-static {v0, v1}, Lsoftware/morphe/kpn/AdSkipHook;->relativeJump(J)V
    return-void
.end method