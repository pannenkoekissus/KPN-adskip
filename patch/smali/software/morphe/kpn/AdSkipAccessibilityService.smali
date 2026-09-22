.class public Lsoftware/morphe/kpn/AdSkipAccessibilityService;
.super Landroid/accessibilityservice/AccessibilityService;
.source "AdSkipAccessibilityService.java"

# In-process AccessibilityService for the KPN TV+ patched build.
#
# Configured at runtime (setServiceInfo) because the base.apk manifest is edited
# as raw binary AXML and cannot reference an xml/ config resource.
#
# The service:
#   - logs every accessibility event it sees from the app's windows
#     (discovery phase: lets us map the built-in 30s-forward button / seek bar)
#   - detects taps on the forward button (contentDescription with 30/vooruit/
#     forward + a Button-ish class) and schedules AdSkipForwardGate to decide
#     whether the app already seeked
#   - detects seek-bar drags (TYPE_VIEW_SCROLLED on a SeekBar) and mirrors them
#     with an absolute ExoPlayer seekTo (ad bypass makes direct seeks work)

.method public constructor <init>()V
    .registers 1

    invoke-direct {p0}, Landroid/accessibilityservice/AccessibilityService;-><init>()V
    return-void
.end method

.method protected onServiceConnected()V
    .registers 4

    const-string v0, "A11Y service connected"
    invoke-static {v0}, Lsoftware/morphe/kpn/AdSkipHook;->log(Ljava/lang/String;)V

    new-instance v0, Landroid/accessibilityservice/AccessibilityServiceInfo;
    invoke-direct {v0}, Landroid/accessibilityservice/AccessibilityServiceInfo;-><init>()V

    # 0x1870 = CLICKED|LONG_CLICKED|WINDOW_STATE_CHANGED|WINDOW_CONTENT_CHANGED|SCROLLED
    const/16 v1, 0x1870
    iput v1, v0, Landroid/accessibilityservice/AccessibilityServiceInfo;->eventTypes:I

    # FEEDBACK_GENERIC (silent observer)
    const/16 v1, 0x10
    iput v1, v0, Landroid/accessibilityservice/AccessibilityServiceInfo;->feedbackType:I

    # 0x52 = INCLUDE_NOT_IMPORTANT_VIEWS | REPORT_VIEW_IDS | RETRIEVE_INTERACTIVE_WINDOWS
    const/16 v1, 0x52
    iput v1, v0, Landroid/accessibilityservice/AccessibilityServiceInfo;->flags:I

    # 100ms notification coalescing
    const-wide/16 v1, 0x64
    iput-wide v1, v0, Landroid/accessibilityservice/AccessibilityServiceInfo;->notificationTimeout:J

    invoke-virtual {p0, v0}, Landroid/accessibilityservice/AccessibilityService;->setServiceInfo(Landroid/accessibilityservice/AccessibilityServiceInfo;)V

    const-string v0, "A11Y serviceInfo set (events=0x1870 feedback=0x10 flags=0x52 timeout=100ms)"
    invoke-static {v0}, Lsoftware/morphe/kpn/AdSkipHook;->log(Ljava/lang/String;)V
    return-void
.end method

.method public onAccessibilityEvent(Landroid/view/accessibility/AccessibilityEvent;)V
    .registers 6

    if-eqz p1, :return

    invoke-virtual {p1}, Landroid/view/accessibility/AccessibilityEvent;->getEventType()I
    move-result v0

    # --- discovery log, restricted to our app's windows ---
    invoke-virtual {p1}, Landroid/view/accessibility/AccessibilityEvent;->getPackageName()Ljava/lang/CharSequence;
    move-result-object v1
    if-eqz v1, :not_ours
    invoke-virtual {v1}, Ljava/lang/CharSequence;->toString()Ljava/lang/String;
    move-result-object v1
    const-string v2, "com.kpn.epg"
    invoke-virtual {v1, v2}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z
    move-result v1
    if-eqz v1, :not_ours

    new-instance v1, Ljava/lang/StringBuilder;
    invoke-direct {v1}, Ljava/lang/StringBuilder;-><init>()V
    const-string v2, "A11Y type="
    invoke-virtual {v1, v2}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    invoke-virtual {v1, v0}, Ljava/lang/StringBuilder;->append(I)Ljava/lang/StringBuilder;
    const-string v2, " cls="
    invoke-virtual {v1, v2}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    invoke-virtual {p1}, Landroid/view/accessibility/AccessibilityEvent;->getClassName()Ljava/lang/CharSequence;
    move-result-object v2
    if-nez v2, :cond_cls
    const-string v2, "?"
    :cond_cls
    invoke-virtual {v1, v2}, Ljava/lang/StringBuilder;->append(Ljava/lang/CharSequence;)Ljava/lang/StringBuilder;
    const-string v2, " cd="
    invoke-virtual {v1, v2}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    invoke-virtual {p1}, Landroid/view/accessibility/AccessibilityEvent;->getContentDescription()Ljava/lang/CharSequence;
    move-result-object v2
    if-nez v2, :cond_cd
    const-string v2, "?"
    :cond_cd
    invoke-virtual {v1, v2}, Ljava/lang/StringBuilder;->append(Ljava/lang/CharSequence;)Ljava/lang/StringBuilder;
    const-string v2, " t="
    invoke-virtual {v1, v2}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    invoke-virtual {p1}, Landroid/view/accessibility/AccessibilityEvent;->getText()Ljava/util/List;
    move-result-object v2
    invoke-virtual {v1, v2}, Ljava/lang/StringBuilder;->append(Ljava/lang/Object;)Ljava/lang/StringBuilder;
    invoke-virtual {v1}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;
    move-result-object v1
    invoke-static {v1}, Lsoftware/morphe/kpn/AdSkipHook;->log(Ljava/lang/String;)V

    # --- dispatch on click / scroll (only for our app's windows) ---
    const/16 v1, 0x10
    if-eq v0, v1, :do_click
    const/16 v1, 0x1000
    if-eq v0, v1, :do_scroll
    return-void

    :do_click
    invoke-virtual {p1}, Landroid/view/accessibility/AccessibilityEvent;->getSource()Landroid/view/accessibility/AccessibilityNodeInfo;
    move-result-object v1
    invoke-static {v1}, Lsoftware/morphe/kpn/AdSkipAccessibilityService;->handleClick(Landroid/view/accessibility/AccessibilityNodeInfo;)V
    return-void

    :do_scroll
    invoke-virtual {p1}, Landroid/view/accessibility/AccessibilityEvent;->getSource()Landroid/view/accessibility/AccessibilityNodeInfo;
    move-result-object v1
    invoke-static {v1}, Lsoftware/morphe/kpn/AdSkipAccessibilityService;->handleScroll(Landroid/view/accessibility/AccessibilityNodeInfo;)V
    return-void

    :not_ours
    return-void

    :return
    return-void
.end method

.method private static handleClick(Landroid/view/accessibility/AccessibilityNodeInfo;)V
    .registers 10

    if-eqz p0, :return

    invoke-virtual {p0}, Landroid/view/accessibility/AccessibilityNodeInfo;->getClassName()Ljava/lang/CharSequence;
    move-result-object v1
    invoke-virtual {p0}, Landroid/view/accessibility/AccessibilityNodeInfo;->getContentDescription()Ljava/lang/CharSequence;
    move-result-object v2
    new-instance v3, Landroid/graphics/Rect;
    invoke-direct {v3}, Landroid/graphics/Rect;-><init>()V
    invoke-virtual {p0, v3}, Landroid/view/accessibility/AccessibilityNodeInfo;->getBoundsInScreen(Landroid/graphics/Rect;)V

    new-instance v4, Ljava/lang/StringBuilder;
    invoke-direct {v4}, Ljava/lang/StringBuilder;-><init>()V
    const-string v5, "A11Y_CLICK cls="
    invoke-virtual {v4, v5}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    invoke-virtual {v4, v1}, Ljava/lang/StringBuilder;->append(Ljava/lang/CharSequence;)Ljava/lang/StringBuilder;
    const-string v5, " cd="
    invoke-virtual {v4, v5}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    invoke-virtual {v4, v2}, Ljava/lang/StringBuilder;->append(Ljava/lang/CharSequence;)Ljava/lang/StringBuilder;
    const-string v5, " bounds="
    invoke-virtual {v4, v5}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    invoke-virtual {v4, v3}, Ljava/lang/StringBuilder;->append(Ljava/lang/Object;)Ljava/lang/StringBuilder;
    invoke-virtual {v4}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;
    move-result-object v4
    invoke-static {v4}, Lsoftware/morphe/kpn/AdSkipHook;->log(Ljava/lang/String;)V

    # --- forward-button candidate: cd contains 30 / vooruit / forward ---
    if-eqz v2, :return
    invoke-virtual {v2}, Ljava/lang/CharSequence;->toString()Ljava/lang/String;
    move-result-object v4
    const-string v5, "30"
    invoke-virtual {v4, v5}, Ljava/lang/String;->contains(Ljava/lang/CharSequence;)Z
    move-result v5
    if-nez v5, :has_token

    const-string v5, "vooruit"
    invoke-virtual {v4, v5}, Ljava/lang/String;->contains(Ljava/lang/CharSequence;)Z
    move-result v5
    if-nez v5, :has_token

    const-string v5, "forward"
    invoke-virtual {v4, v5}, Ljava/lang/String;->contains(Ljava/lang/CharSequence;)Z
    move-result v5
    if-nez v5, :has_token

    return-void

    :has_token
    # the control should look like a button
    if-eqz v1, :return
    invoke-virtual {v1}, Ljava/lang/CharSequence;->toString()Ljava/lang/String;
    move-result-object v4
    const-string v5, "Button"
    invoke-virtual {v4, v5}, Ljava/lang/String;->contains(Ljava/lang/CharSequence;)Z
    move-result v4
    if-eqz v4, :return

    # --- forward tapped: snapshot position + schedule the gate ---
    const-string v4, "A11Y_FWD candidate (30s button)"
    invoke-static {v4}, Lsoftware/morphe/kpn/AdSkipHook;->log(Ljava/lang/String;)V

    invoke-static {}, Lsoftware/morphe/kpn/AdSkipHook;->getCurrentPositionMs()J
    move-result-wide v4

    new-instance v6, Lsoftware/morphe/kpn/AdSkipForwardGate;
    invoke-direct {v6, v4, v5}, Lsoftware/morphe/kpn/AdSkipForwardGate;-><init>(J)V

    invoke-static {}, Landroid/os/Looper;->getMainLooper()Landroid/os/Looper;
    move-result-object v4
    new-instance v7, Landroid/os/Handler;
    invoke-direct {v7, v4}, Landroid/os/Handler;-><init>(Landroid/os/Looper;)V

    const-wide/16 v4, 0x320
    invoke-virtual {v7, v6, v4, v5}, Landroid/os/Handler;->postDelayed(Ljava/lang/Runnable;J)Z

    :return
    return-void
.end method

.method private static handleScroll(Landroid/view/accessibility/AccessibilityNodeInfo;)V
    .registers 14

    if-eqz p0, :return

    # only care about seek bars
    invoke-virtual {p0}, Landroid/view/accessibility/AccessibilityNodeInfo;->getClassName()Ljava/lang/CharSequence;
    move-result-object v1
    if-eqz v1, :return
    invoke-virtual {v1}, Ljava/lang/CharSequence;->toString()Ljava/lang/String;
    move-result-object v1
    const-string v2, "SeekBar"
    invoke-virtual {v1, v2}, Ljava/lang/String;->contains(Ljava/lang/CharSequence;)Z
    move-result v1
    if-eqz v1, :return

    invoke-virtual {p0}, Landroid/view/accessibility/AccessibilityNodeInfo;->getRangeInfo()Landroid/view/accessibility/AccessibilityNodeInfo$RangeInfo;
    move-result-object v1
    if-eqz v1, :return

    invoke-virtual {v1}, Landroid/view/accessibility/AccessibilityNodeInfo$RangeInfo;->getMin()F
    move-result v2
    invoke-virtual {v1}, Landroid/view/accessibility/AccessibilityNodeInfo$RangeInfo;->getCurrent()F
    move-result v3
    invoke-virtual {v1}, Landroid/view/accessibility/AccessibilityNodeInfo$RangeInfo;->getMax()F
    move-result v4

    # frac = (cur - min) / (max - min)
    sub-float v5, v3, v2
    sub-float v6, v4, v2
    const/high16 v10, 0x0
    cmpl-float v9, v6, v10
    if-lez v9, :return
    div-float v5, v5, v6

    # clamp frac to [0, 1]
    const/high16 v6, 0x3f800000
    cmpl-float v9, v5, v6
    if-lez v9, :le_one
    move v5, v6
    :le_one
    const/high16 v6, 0x0
    cmpl-float v9, v5, v6
    if-gez v9, :ge_zero
    move v5, v6
    :ge_zero

    # duration must be known
    invoke-static {}, Lsoftware/morphe/kpn/AdSkipHook;->getDurationMs()J
    move-result-wide v7
    const-wide/16 v9, 0x0
    cmp-long v6, v7, v9
    if-lez v6, :return

    # target = (long)(frac * duration)
    float-to-long v9, v5
    mul-long v11, v9, v7
    invoke-static {v11, v12}, Lsoftware/morphe/kpn/AdSkipHook;->seekToPosition(J)V

    :return
    return-void
.end method

.method public onInterrupt()V
    .registers 1
    return-void
.end method