.class public Lsoftware/morphe/kpn/AdSkipButton;
.super Ljava/lang/Object;
.implements Landroid/view/View$OnClickListener;

.field private final action:I

.field private static overlayView:Landroid/view/View;

.method public constructor <init>(I)V
    .registers 2
    invoke-direct {p0}, Ljava/lang/Object;-><init>()V
    iput p1, p0, Lsoftware/morphe/kpn/AdSkipButton;->action:I
    return-void
.end method

.method public static setVisibility(Z)V
    .registers 4
    .param p0, "visible"    # Z

    # If hiding, skip PiP check
    if-eqz p0, :do_set

    # Check if in PiP mode — don't show overlay in PiP
    sget-object v0, Lsoftware/morphe/kpn/AdSkipHook;->activeActivity:Ljava/lang/ref/WeakReference;
    if-eqz v0, :do_set
    invoke-virtual {v0}, Ljava/lang/ref/WeakReference;->get()Ljava/lang/Object;
    move-result-object v0
    if-eqz v0, :do_set
    check-cast v0, Landroid/app/Activity;
    invoke-virtual {v0}, Landroid/app/Activity;->isInPictureInPictureMode()Z
    move-result v0
    if-eqz v0, :do_set
    # In PiP — hide overlay and bail
    sget-object v1, Lsoftware/morphe/kpn/AdSkipButton;->overlayView:Landroid/view/View;
    if-eqz v1, :return_early
    const/16 v2, 0x8
    invoke-virtual {v1, v2}, Landroid/view/View;->setVisibility(I)V
    :return_early
    return-void

    :do_set
    sget-object v0, Lsoftware/morphe/kpn/AdSkipButton;->overlayView:Landroid/view/View;
    if-eqz v0, :end
    if-eqz p0, :hide
    const/4 v1, 0x0
    invoke-virtual {v0, v1}, Landroid/view/View;->setVisibility(I)V
    return-void
    :hide
    const/16 v1, 0x8
    invoke-virtual {v0, v1}, Landroid/view/View;->setVisibility(I)V
    :end
    return-void
.end method

.method public onClick(Landroid/view/View;)V
    .registers 3
    iget v0, p0, Lsoftware/morphe/kpn/AdSkipButton;->action:I

    if-nez v0, :not_skip
    invoke-static {}, Lsoftware/morphe/kpn/AdSkipHook;->skipAdBreak()V
    return-void

    :not_skip
    const/4 v1, 0x1
    if-ne v0, v1, :not_rewind
    const-wide/16 v0, -0x3a98
    invoke-static {v0, v1}, Lsoftware/morphe/kpn/AdSkipHook;->relativeJump(J)V
    return-void

    :not_rewind
    const/4 v1, 0x2
    if-ne v0, v1, :not_forward
    const-wide/16 v0, 0x7530
    invoke-static {v0, v1}, Lsoftware/morphe/kpn/AdSkipHook;->relativeJump(J)V
    return-void

    :not_forward
    invoke-static {}, Lsoftware/morphe/kpn/AdSkipHook;->undoLastJump()V
    return-void
.end method

.method public static show(Landroid/app/Activity;)V
    .registers 16

    if-eqz p0, :end

    # Check PiP — don't create overlay in PiP
    invoke-virtual {p0}, Landroid/app/Activity;->isInPictureInPictureMode()Z
    move-result v0
    if-eqz v0, :not_pip
    return-void
    :not_pip

    const-string v0, "window"
    invoke-virtual {p0, v0}, Landroid/app/Activity;->getSystemService(Ljava/lang/String;)Ljava/lang/Object;
    move-result-object v0
    check-cast v0, Landroid/view/WindowManager;
    if-eqz v0, :end

    # Create horizontal LinearLayout container
    new-instance v1, Landroid/widget/LinearLayout;
    invoke-direct {v1, p0}, Landroid/widget/LinearLayout;-><init>(Landroid/content/Context;)V
    const/4 v2, 0x0
    invoke-virtual {v1, v2}, Landroid/widget/LinearLayout;->setOrientation(I)V
    # Semi-transparent dark background
    const v3, -0x66000000
    invoke-virtual {v1, v3}, Landroid/widget/LinearLayout;->setBackgroundColor(I)V
    # Small padding: 6px all sides
    const/4 v3, 0x6
    invoke-virtual {v1, v3, v3, v3, v3}, Landroid/widget/LinearLayout;->setPadding(IIII)V

    # Button size: 10sp text, white text color
    const/high16 v3, 0x41200000    # 10.0f (10sp)

    # << button (rewind 15s)
    new-instance v4, Landroid/widget/Button;
    invoke-direct {v4, p0}, Landroid/widget/Button;-><init>(Landroid/content/Context;)V
    const-string v5, "\u00ab"
    invoke-virtual {v4, v5}, Landroid/widget/Button;->setText(Ljava/lang/CharSequence;)V
    invoke-virtual {v4, v3}, Landroid/widget/Button;->setTextSize(F)V
    new-instance v5, Lsoftware/morphe/kpn/AdSkipButton;
    const/4 v6, 0x1
    invoke-direct {v5, v6}, Lsoftware/morphe/kpn/AdSkipButton;-><init>(I)V
    invoke-virtual {v4, v5}, Landroid/widget/Button;->setOnClickListener(Landroid/view/View$OnClickListener;)V
    invoke-virtual {v1, v4}, Landroid/widget/LinearLayout;->addView(Landroid/view/View;)V

    # SKIP button (skip ad break)
    new-instance v4, Landroid/widget/Button;
    invoke-direct {v4, p0}, Landroid/widget/Button;-><init>(Landroid/content/Context;)V
    const-string v5, "SKIP"
    invoke-virtual {v4, v5}, Landroid/widget/Button;->setText(Ljava/lang/CharSequence;)V
    invoke-virtual {v4, v3}, Landroid/widget/Button;->setTextSize(F)V
    new-instance v5, Lsoftware/morphe/kpn/AdSkipButton;
    invoke-direct {v5, v2}, Lsoftware/morphe/kpn/AdSkipButton;-><init>(I)V
    invoke-virtual {v4, v5}, Landroid/widget/Button;->setOnClickListener(Landroid/view/View$OnClickListener;)V
    invoke-virtual {v1, v4}, Landroid/widget/LinearLayout;->addView(Landroid/view/View;)V

    # >> button (forward 30s)
    new-instance v4, Landroid/widget/Button;
    invoke-direct {v4, p0}, Landroid/widget/Button;-><init>(Landroid/content/Context;)V
    const-string v5, "\u00bb"
    invoke-virtual {v4, v5}, Landroid/widget/Button;->setText(Ljava/lang/CharSequence;)V
    invoke-virtual {v4, v3}, Landroid/widget/Button;->setTextSize(F)V
    new-instance v5, Lsoftware/morphe/kpn/AdSkipButton;
    const/4 v6, 0x2
    invoke-direct {v5, v6}, Lsoftware/morphe/kpn/AdSkipButton;-><init>(I)V
    invoke-virtual {v4, v5}, Landroid/widget/Button;->setOnClickListener(Landroid/view/View$OnClickListener;)V
    invoke-virtual {v1, v4}, Landroid/widget/LinearLayout;->addView(Landroid/view/View;)V

    # UNDO button
    new-instance v4, Landroid/widget/Button;
    invoke-direct {v4, p0}, Landroid/widget/Button;-><init>(Landroid/content/Context;)V
    const-string v5, "UNDO"
    invoke-virtual {v4, v5}, Landroid/widget/Button;->setText(Ljava/lang/CharSequence;)V
    invoke-virtual {v4, v3}, Landroid/widget/Button;->setTextSize(F)V
    new-instance v5, Lsoftware/morphe/kpn/AdSkipButton;
    const/4 v6, 0x3
    invoke-direct {v5, v6}, Lsoftware/morphe/kpn/AdSkipButton;-><init>(I)V
    invoke-virtual {v4, v5}, Landroid/widget/Button;->setOnClickListener(Landroid/view/View$OnClickListener;)V
    invoke-virtual {v1, v4}, Landroid/widget/LinearLayout;->addView(Landroid/view/View;)V

    # WindowManager.LayoutParams
    new-instance v8, Landroid/view/WindowManager$LayoutParams;
    invoke-direct {v8}, Landroid/view/WindowManager$LayoutParams;-><init>()V
    const/4 v9, -0x2
    iput v9, v8, Landroid/view/WindowManager$LayoutParams;->width:I
    const/4 v9, -0x2
    iput v9, v8, Landroid/view/WindowManager$LayoutParams;->height:I
    const/16 v9, 0x7f6
    iput v9, v8, Landroid/view/WindowManager$LayoutParams;->type:I
    const/16 v9, 0x28
    iput v9, v8, Landroid/view/WindowManager$LayoutParams;->flags:I
    # Gravity: BOTTOM | END = 0x55
    const/16 v9, 0x55
    iput v9, v8, Landroid/view/WindowManager$LayoutParams;->gravity:I
    # Small margin from bottom-right corner
    const/16 v9, 0x8
    iput v9, v8, Landroid/view/WindowManager$LayoutParams;->x:I
    const/16 v9, 0x50
    iput v9, v8, Landroid/view/WindowManager$LayoutParams;->y:I

    :try_start_0
    invoke-interface {v0, v1, v8}, Landroid/view/WindowManager;->addView(Landroid/view/View;Landroid/view/ViewGroup$LayoutParams;)V
    sput-object v1, Lsoftware/morphe/kpn/AdSkipButton;->overlayView:Landroid/view/View;
    const/16 v9, 0x8
    invoke-virtual {v1, v9}, Landroid/view/View;->setVisibility(I)V
    const-string v9, "AdSkip"
    const-string v10, "Overlay added OK"
    invoke-static {v9, v10}, Landroid/util/Log;->e(Ljava/lang/String;Ljava/lang/String;)I
    :try_end_0
    .catch Ljava/lang/Exception; {:try_start_0 .. :try_end_0} :catch_0
    goto :end

    :catch_0
    move-exception v9
    const-string v10, "AdSkip"
    new-instance v11, Ljava/lang/StringBuilder;
    invoke-direct {v11}, Ljava/lang/StringBuilder;-><init>()V
    const-string v12, "Overlay FAILED: "
    invoke-virtual {v11, v12}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    invoke-virtual {v9}, Ljava/lang/Exception;->toString()Ljava/lang/String;
    move-result-object v12
    invoke-virtual {v11, v12}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    invoke-virtual {v11}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;
    move-result-object v11
    invoke-static {v10, v11}, Landroid/util/Log;->e(Ljava/lang/String;Ljava/lang/String;)I

    :end
    return-void
.end method
