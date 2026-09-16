package software.morphe.patches.kpn.fingerprints

import app.revanced.patcher.fingerprint.MethodFingerprint
import com.android.tools.smali.dexlib2.AccessFlags
import com.android.tools.smali.dexlib2.Opcode

object VideoPlayerFingerprint : MethodFingerprint(
    returnType = "V",
    accessFlags = AccessFlags.PUBLIC.value,
    parameters = listOf("J"),
    strings = listOf(),
    opcodes = listOf(
        Opcode.IGET_OBJECT,
        Opcode.IF_EQZ,
        Opcode.INVOKE_INTERFACE
    ),
    customFingerprint = { method, _ ->
        method.name == "seekTo" && (
            method.definingClass.contains("VideoPlayer") ||
            method.definingClass.contains("videoplayer")
        )
    }
)
