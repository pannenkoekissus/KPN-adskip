package software.morphe.patches.kpn.fingerprints

import app.revanced.patcher.fingerprint.MethodFingerprint
import com.android.tools.smali.dexlib2.AccessFlags

object MainActivityFingerprint : MethodFingerprint(
    returnType = "Z",
    accessFlags = AccessFlags.PUBLIC.value,
    parameters = listOf("I", "Landroid/view/KeyEvent;"),
    customFingerprint = { method, _ ->
        method.name == "onKeyDown" && (
            method.definingClass.contains("MainActivity") ||
            method.definingClass.contains("FlutterActivity")
        )
    }
)
