.class public Lsoftware/morphe/kpn/AdSkipOverlayTask;
.super Ljava/lang/Object;
.implements Ljava/lang/Runnable;

.field private final activity:Landroid/app/Activity;

.method public constructor <init>(Landroid/app/Activity;)V
    .registers 2
    invoke-direct {p0}, Ljava/lang/Object;-><init>()V
    iput-object p1, p0, Lsoftware/morphe/kpn/AdSkipOverlayTask;->activity:Landroid/app/Activity;
    return-void
.end method

.method public run()V
    .registers 2
    iget-object v0, p0, Lsoftware/morphe/kpn/AdSkipOverlayTask;->activity:Landroid/app/Activity;
    invoke-static {v0}, Lsoftware/morphe/kpn/AdSkipButton;->show(Landroid/app/Activity;)V
    return-void
.end method
