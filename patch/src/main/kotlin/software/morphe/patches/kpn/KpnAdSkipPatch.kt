package software.morphe.patches.kpn

import app.revanced.patcher.data.BytecodeContext
import app.revanced.patcher.extensions.InstructionExtensions.addInstructions
import app.revanced.patcher.patch.BytecodePatch
import app.revanced.patcher.patch.annotation.CompatiblePackage
import app.revanced.patcher.patch.annotation.Patch
import com.android.tools.smali.dexlib2.iface.instruction.OneRegisterInstruction
import com.android.tools.smali.dexlib2.iface.instruction.ReferenceInstruction
import com.android.tools.smali.dexlib2.iface.reference.FieldReference
import com.android.tools.smali.dexlib2.iface.reference.MethodReference
import software.morphe.patches.kpn.fingerprints.MainActivityFingerprint
import software.morphe.patches.kpn.fingerprints.VideoPlayerFingerprint

@Patch(
    name = "KPN TV+ AdSkip & Seek Unlock",
    description = "Deblokkeert doorspoelen tijdens reclameblokken en maakt directe sprongen mogelijk via afstandsbediening of overlay.",
    version = "2.1.0",
    compatiblePackages = [
        CompatiblePackage("com.kpn.epg")
    ]
)
@Suppress("unused")
class KpnAdSkipPatch : BytecodePatch(
    setOf(
        VideoPlayerFingerprint,
        MainActivityFingerprint
    )
) {
    override fun execute(context: BytecodeContext) {
        // 1. Hook into VideoPlayer.seekTo(J) or constructor to register active player instance
        val videoPlayerResult = VideoPlayerFingerprint.result
            ?: throw IllegalStateException("VideoPlayer fingerprint niet gevonden")

        val seekMethod = videoPlayerResult.mutableMethod
        seekMethod.addInstructions(
            0,
            """
                invoke-static {p0}, Lsoftware/morphe/kpn/AdSkipHook;->registerPlayer(Ljava/lang/Object;)V
            """
        )

        // 2. Hook into MainActivity.onKeyDown to capture remote control / shortcut keys
        val mainActivityResult = MainActivityFingerprint.result
        if (mainActivityResult != null) {
            val onKeyDownMethod = mainActivityResult.mutableMethod
            onKeyDownMethod.addInstructions(
                0,
                """
                    invoke-static {p1, p2}, Lsoftware/morphe/kpn/AdSkipHook;->onKeyDown(ILandroid/view/KeyEvent;)Z
                    move-result v0
                    if-eqz v0, :cond_skip_default
                    const/4 v0, 0x1
                    return v0
                    :cond_skip_default
                """
            )
        }

        // 3. Inject AdSkipHook bytecode into context
        // In Morphe/ReVanced builds, AdSkipHook class is packaged alongside the patch
    }
}
