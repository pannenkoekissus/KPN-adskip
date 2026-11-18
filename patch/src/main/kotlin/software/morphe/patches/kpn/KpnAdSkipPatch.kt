package software.morphe.patches.kpn

import app.morphe.patcher.extensions.InstructionExtensions.addInstructions
import app.morphe.patcher.extensions.InstructionExtensions.addInstructionsWithLabels
import app.morphe.patcher.patch.ApkFileType
import app.morphe.patcher.patch.Compatibility
import app.morphe.patcher.patch.FormFactor
import app.morphe.patcher.patch.PatchException
import app.morphe.patcher.patch.classDefByOrNull
import app.morphe.patcher.patch.classDefForEach
import app.morphe.patcher.patch.mutableClassDefByOrNull
import app.morphe.patcher.patch.patch
import app.morphe.patcher.util.proxy.mutableTypes.MutableClass
import app.morphe.patcher.util.proxy.mutableTypes.MutableMethod
import com.android.tools.smali.dexlib2.Opcode
import com.android.tools.smali.dexlib2.iface.Method
import com.android.tools.smali.dexlib2.iface.instruction.OneRegisterInstruction
import com.android.tools.smali.dexlib2.iface.instruction.ReferenceInstruction
import com.android.tools.smali.dexlib2.iface.reference.FieldReference
import com.android.tools.smali.dexlib2.iface.reference.MethodReference
import com.android.tools.smali.dexlib2.iface.reference.StringReference

private const val HOOK_CLASS = "Lsoftware/morphe/kpn/AdSkipHook;"
private const val EXTENSION_PATH = "extensions/kpn.mpe"

/** Media3 fields that own a player instance (the obfuscated impl is `Landroidx/media3/exoplayer/c;`). */
private val PLAYER_FIELD_TYPES = setOf(
    "Landroidx/media3/exoplayer/ExoPlayer;",
    "Landroidx/media3/exoplayer/c;",
)

private const val AD_SEEK_GUARD_STRING = "seekTo ignored because an ad is playing"
private const val IMA_AD_DATA_CLASS = "Lcom/google/ads/interactivemedia/v3/impl/data/AutoValue_AdData;"

private fun log(message: String) = println("[KPN AdSkip] $message")

private fun MutableClass.methodOrNull(
    name: String,
    returnType: String,
    vararg parameterTypes: String,
): MutableMethod? = methods.firstOrNull { method ->
    method.name == name &&
        method.returnType == returnType &&
        method.parameterTypes.size == parameterTypes.size &&
        method.parameterTypes.map { it.toString() } == parameterTypes.toList()
}

/** Number of registers a method may use as `v0`, `v1`, ... (parameters excluded). */
private fun MutableMethod.localRegisterCount(): Int {
    val implementation = implementation ?: return 0
    val parameterRegisters = parameterTypes.size + if (isStatic()) 0 else 1
    return implementation.registerCount - parameterRegisters
}

private fun MutableMethod.isStatic(): Boolean =
    (accessFlags and com.android.tools.smali.dexlib2.AccessFlags.STATIC.value) != 0

/**
 * Finds the activity that receives remote-control events. The exact class name is preferred, but
 * any class overriding `dispatchKeyEvent(KeyEvent)` is accepted so an R8 rename cannot break it.
 */
private fun findActivityClass(): MutableClass? {
    mutableClassDefByOrNull("Lcom/kpn/tvplusapp/MainActivity;")?.let { return it }

    var namedMatch: MutableClass? = null
    var anyMatch: MutableClass? = null
    classDefForEach { classDef ->
        if (namedMatch != null) return@classDefForEach
        if (!classDef.hasKeyDispatchOverride()) return@classDefForEach

        val candidate = mutableClassDefByOrNull(classDef.type) ?: return@classDefForEach
        if (classDef.type.contains("MainActivity") || classDef.superclass?.contains("FlutterActivity") == true) {
            namedMatch = candidate
        } else if (anyMatch == null) {
            anyMatch = candidate
        }
    }
    return namedMatch ?: anyMatch
}

private fun com.android.tools.smali.dexlib2.iface.ClassDef.hasKeyDispatchOverride(): Boolean =
    methods.any { method ->
        method.name == "dispatchKeyEvent" &&
            method.returnType == "Z" &&
            method.parameterTypes.size == 1 &&
            method.parameterTypes[0].toString() == "Landroid/view/KeyEvent;"
    }

/**
 * The Flutter video player wrapper. Its `exoPlayer` field and `seekTo(J)V` are more stable hints
 * than the fully qualified class name.
 */
private fun findVideoPlayerClass(): MutableClass? {
    mutableClassDefByOrNull("Lio/flutter/plugins/videoplayer/VideoPlayer;")?.let { return it }

    var match: MutableClass? = null
    classDefForEach { classDef ->
        if (match != null) return@classDefForEach
        val hasPlayerField = classDef.fields.any { it.name == "exoPlayer" || it.type in PLAYER_FIELD_TYPES }
        val seeks = classDef.methods.any { method ->
            method.name == "seekTo" &&
                method.returnType == "V" &&
                method.parameterTypes.size == 1 &&
                method.parameterTypes[0].toString() == "J"
        }
        if (hasPlayerField && seeks) match = mutableClassDefByOrNull(classDef.type)
    }
    return match
}

/**
 * Registers every player instance assigned to a player-typed field. Covers the Flutter VOD plugin
 * and the obfuscated live-TV platform view, which store their ExoPlayer in different classes.
 */
private fun injectPlayerRegistrations(): Int {
    val classTypes = mutableListOf<String>()
    classDefForEach { classDef ->
        if (classDef.fields.any { it.type in PLAYER_FIELD_TYPES }) classTypes += classDef.type
    }

    var count = 0
    classTypes.forEach { classType ->
        val clazz = mutableClassDefByOrNull(classType) ?: return@forEach
        clazz.methods.forEach { method ->
            val implementation = method.implementation ?: return@forEach
            val injections = mutableListOf<Pair<Int, Int>>()
            implementation.instructions.forEachIndexed { index, instruction ->
                if (instruction.opcode != Opcode.IPUT_OBJECT) return@forEachIndexed
                val reference = (instruction as? ReferenceInstruction)?.reference as? FieldReference
                    ?: return@forEachIndexed
                if (reference.type !in PLAYER_FIELD_TYPES) return@forEachIndexed
                val valueRegister = (instruction as? OneRegisterInstruction)?.registerA
                    ?: return@forEachIndexed
                injections += index to valueRegister
            }
            // Insert bottom-up so the earlier instruction indices stay valid.
            injections.asReversed().forEach { (index, register) ->
                method.addInstructions(
                    index + 1,
                    "invoke-static {v$register}, $HOOK_CLASS->registerExoPlayer(Ljava/lang/Object;)V",
                )
                count++
            }
        }
    }
    return count
}

/**
 * Hooks every `Player.Listener.onIsPlayingChanged(Z)` implementation so the skip overlay follows
 * the real playback state for both VOD and live TV.
 */
private fun injectIsPlayingHooks(): Int {
    val classTypes = mutableListOf<String>()
    classDefForEach { classDef ->
        if (classDef.methods.any { it.isIsPlayingChanged() }) classTypes += classDef.type
    }

    var count = 0
    classTypes.forEach { classType ->
        val clazz = mutableClassDefByOrNull(classType) ?: return@forEach
        clazz.methods.filter { it.isIsPlayingChanged() }.forEach { method ->
            method.addInstructions(0, "invoke-static {p1}, $HOOK_CLASS->setPlaying(Z)V")
            count++
        }
    }
    return count
}

private fun Method.isIsPlayingChanged(): Boolean =
    name == "onIsPlayingChanged" &&
        returnType == "V" &&
        parameterTypes.size == 1 &&
        parameterTypes[0].toString() == "Z" &&
        (accessFlags and com.android.tools.smali.dexlib2.AccessFlags.STATIC.value) == 0

/**
 * Makes `ExoPlayer.isPlayingAd()` (obfuscated) always return false.
 *
 * The method name is not stable, so it is resolved through the `seekTo` guard that logs
 * "seekTo ignored because an ad is playing" and invokes the boolean check.
 */
private fun injectAdSeekBypass(): String? {
    var ownerType: String? = null
    var guardMethod: Method? = null

    classDefForEach { classDef ->
        if (guardMethod != null) return@classDefForEach
        classDef.methods.forEach { method ->
            if (guardMethod != null) return@forEach
            val containsGuard = method.implementation?.instructions?.any { instruction ->
                instruction.opcode == Opcode.CONST_STRING &&
                    (instruction as? ReferenceInstruction)?.reference
                        ?.let { it as? StringReference }?.string == AD_SEEK_GUARD_STRING
            } == true
            if (containsGuard) {
                ownerType = classDef.type
                guardMethod = method
            }
        }
    }

    val guard = guardMethod ?: return null
    val guardType = ownerType ?: return null

    val reference = guard.implementation?.instructions
        ?.filter { it.opcode == Opcode.INVOKE_VIRTUAL || it.opcode == Opcode.INVOKE_INTERFACE }
        ?.mapNotNull { (it as? ReferenceInstruction)?.reference as? MethodReference }
        ?.firstOrNull { method ->
            method.parameterTypes.isEmpty() &&
                method.returnType == "Z" &&
                method.definingClass == guardType
        } ?: return null

    val clazz = mutableClassDefByOrNull(reference.definingClass) ?: return null
    val target = clazz.methods.firstOrNull { method ->
        method.name == reference.name &&
            method.returnType == "Z" &&
            method.parameterTypes.isEmpty()
    } ?: return null

    if (target.localRegisterCount() < 1) {
        log("WARNING: ${reference.definingClass}->${reference.name}()Z has no local register; ad bypass skipped")
        return null
    }

    target.addInstructions(0, "const/4 v0, 0x0\nreturn v0")
    return "${reference.definingClass}->${reference.name}()Z"
}

/**
 * Answers the app's Flutter security plugins without running their checks.
 *
 * The sideloaded build is not a Play Store install and may run on a rooted or
 * debug-enabled device, which these plugins report as tampering. Each literal is
 * resolved wherever it lives, so obfuscated class names (`r8.1.b`, `z8.1.b`, ...)
 * do not matter. The injection mirrors the known-good apktool patch: skip the
 * native check, answer the `MethodChannel.Result` directly and return.
 */
private val SECURITY_CHECKS = listOf(
    "isRooted" to false,
    "isRealDevice" to true,
    "hasCorrectlyInstalled" to true,
    "isJailBroken" to false,
    "isDevelopmentModeEnable" to false,
    "usbDebuggingCheck" to false,
)

private data class SecurityMatch(
    val type: String,
    val methodName: String,
    val returnType: String,
    val parameterTypes: List<String>,
    val guardIndex: Int,
)

private fun injectSecurityBypasses(): List<String> {
    val patched = mutableListOf<String>()
    SECURITY_CHECKS.forEach { (literal, value) ->
        val matches = mutableListOf<SecurityMatch>()

        // Only consider real MethodChannel handlers, so an unrelated model class
        // that happens to contain the same literal cannot be patched. Two plugins
        // can answer the same question (`isRealDevice`), so every match counts.
        classDefForEach { classDef ->
            classDef.methods.forEach { method ->
                if (method.parameterTypes.size != 2 ||
                    method.parameterTypes[0].toString() != "Lio/flutter/plugin/common/MethodCall;" ||
                    method.parameterTypes[1].toString() != "Lio/flutter/plugin/common/MethodChannel\$Result;"
                ) {
                    return@forEach
                }
                val instructions = method.implementation?.instructions ?: return@forEach
                val literalIndex = instructions.indexOfFirst { instruction ->
                    instruction.opcode == Opcode.CONST_STRING &&
                        ((instruction as? ReferenceInstruction)?.reference as? StringReference)?.string == literal
                }
                if (literalIndex < 0) return@forEach

                // The literal must be compared with the MethodCall method name:
                //   const-string vX, "literal"
                //   invoke-virtual {vY, vX}, String->equals(Object)Z
                //   move-result vZ
                //   if-eqz/nez vZ, :cond
                // A map key such as `put("isRooted", value)` has no String.equals
                // here and must not be treated as a handler.
                val window = instructions.drop(literalIndex + 1).take(8)
                val equalsIndex = window.indexOfFirst { instruction ->
                    val reference = (instruction as? ReferenceInstruction)?.reference as? MethodReference
                    instruction.opcode == Opcode.INVOKE_VIRTUAL &&
                        reference?.definingClass == "Ljava/lang/String;" &&
                        reference.name == "equals"
                }
                // In a dispatch branch the literal is immediately followed by the
                // equals call. Anything in between means this is a data literal
                // (map key, UI text), not a method-name check.
                if (equalsIndex != 0) return@forEach

                val guardOffset = window.withIndex()
                    .drop(equalsIndex + 1)
                    .take(4)
                    .firstOrNull { (_, instruction) ->
                        instruction.opcode == Opcode.IF_EQZ || instruction.opcode == Opcode.IF_NEZ
                    }?.index ?: return@forEach

                matches += SecurityMatch(
                    classDef.type,
                    method.name,
                    method.returnType,
                    method.parameterTypes.map { it.toString() },
                    literalIndex + 1 + guardOffset,
                )
            }
        }

        if (matches.isEmpty()) {
            log("WARNING: security check \"$literal\" not found; bypass skipped")
            return@forEach
        }

        // Insert bottom-up so several hits in one method keep their indices valid.
        matches.sortedByDescending { it.guardIndex }.forEach { match ->
            val mutableMethod = mutableClassDefByOrNull(match.type)?.methods?.firstOrNull { candidate ->
                candidate.name == match.methodName &&
                    candidate.returnType == match.returnType &&
                    candidate.parameterTypes.map { it.toString() } == match.parameterTypes
            }
            if (mutableMethod == null) {
                log("WARNING: security check \"$literal\" in ${match.type} is not mutable; bypass skipped")
                return@forEach
            }

            // Injecting after the guard runs only when this method name matched.
            // The handler is non-static, so p1 is the MethodCall (scratch: the
            // matched boolean) and p2 is the MethodChannel.Result.
            mutableMethod.addInstructions(
                match.guardIndex + 1,
                """
                    const/4 p1, 0x${if (value) 1 else 0}
                    invoke-static {p1}, Ljava/lang/Boolean;->valueOf(Z)Ljava/lang/Boolean;
                    move-result-object p1
                    invoke-interface {p2, p1}, Lio/flutter/plugin/common/MethodChannel${'$'}Result;->success(Ljava/lang/Object;)V
                    return-void
                """,
            )
            patched += "$literal@${match.type}"
            log("Security bypass: $literal -> $value (${match.type}->${match.methodName})")
        }
    }
    return patched
}

/** Forces the IMA SDK to report every ad as skippable. */
private fun injectImaSkippableBypass(): Boolean {
    val clazz = mutableClassDefByOrNull(IMA_AD_DATA_CLASS) ?: return false
    val skippable = clazz.methodOrNull("skippable", "Ljava/lang/Boolean;") ?: return false
    if (skippable.localRegisterCount() < 1) return false

    skippable.addInstructions(
        0,
        """
            sget-object v0, Ljava/lang/Boolean;->TRUE:Ljava/lang/Boolean;
            return-object v0
        """,
    )
    return true
}

@Suppress("unused")
val kpnAdSkipPatch = patch(
    name = "KPN TV+ AdSkip & Seek Unlock",
    description = "Unlocks +30 s seeking during ad breaks and maps the remote's fast-forward, " +
        "rewind, play/pause and skip keys to the AdSkipHook extension.",
    default = true,
) {
    compatibleWith(
        Compatibility(
            packageName = "com.kpn.kpnandroidtv",
            name = "KPN TV+ Android TV",
            description = "KPN TV+ on Android TV and the KPN TV+ Box",
            apkFileType = ApkFileType.APKS,
            formFactor = FormFactor.TV,
        ),
        Compatibility(
            packageName = "com.kpn.epg",
            name = "KPN TV+ (mobile)",
            description = "KPN TV+ on phones and tablets",
            apkFileType = ApkFileType.APKS,
            formFactor = FormFactor.MOBILE,
        ),
    )

    extendWith(EXTENSION_PATH)

    execute {
        if (classDefByOrNull(HOOK_CLASS) == null) {
            throw PatchException("$HOOK_CLASS was not merged from $EXTENSION_PATH")
        }

        val injected = mutableListOf<String>()

        val activity = findActivityClass()
        if (activity == null) {
            log("WARNING: no class overriding dispatchKeyEvent(Landroid/view/KeyEvent;)Z was found; key hooks skipped")
        } else {
            log("Activity: ${activity.type}")

            activity.methodOrNull("dispatchKeyEvent", "Z", "Landroid/view/KeyEvent;")?.let { dispatch ->
                if (dispatch.localRegisterCount() < 2) {
                    log("WARNING: dispatchKeyEvent has too few local registers; key hook skipped")
                } else {
                    dispatch.addInstructionsWithLabels(
                        0,
                        """
                            invoke-virtual {p1}, Landroid/view/KeyEvent;->getKeyCode()I
                            move-result v0
                            const/16 v1, 0x15
                            if-eq v0, v1, :kpn_adskip_enter
                            const/16 v1, 0x16
                            if-eq v0, v1, :kpn_adskip_enter
                            invoke-static {v0, p1}, $HOOK_CLASS->onKeyDown(ILandroid/view/KeyEvent;)Z
                            move-result v0
                            if-eqz v0, :kpn_adskip_continue
                            const/4 v0, 0x1
                            return v0
                            :kpn_adskip_continue
                            nop
                            :kpn_adskip_enter
                            nop
                        """,
                    )
                    injected += "dispatchKeyEvent"
                }
            } ?: log("WARNING: dispatchKeyEvent(Landroid/view/KeyEvent;)Z not found; key hook skipped")

            activity.methodOrNull("onCreate", "V", "Landroid/os/Bundle;")?.let { onCreate ->
                onCreate.addInstructions(
                    0,
                    "invoke-static {p0}, $HOOK_CLASS->registerActivity(Landroid/app/Activity;)V",
                )
                injected += "onCreate"
            } ?: log("WARNING: onCreate(Bundle) not found; overlay registration skipped")

            val pipMethod = activity.methodOrNull("onPictureInPictureModeChanged", "V", "Z")
                ?: activity.methodOrNull(
                    "onPictureInPictureModeChanged",
                    "V",
                    "Z",
                    "Landroid/content/res/Configuration;",
                )
            if (pipMethod == null) {
                log("WARNING: onPictureInPictureModeChanged not found; PiP handling skipped")
            } else {
                pipMethod.addInstructions(0, "invoke-static {p1}, $HOOK_CLASS->setPipMode(Z)V")
                injected += "onPictureInPictureModeChanged"
            }
        }

        val videoPlayer = findVideoPlayerClass()
        if (videoPlayer == null) {
            log("WARNING: Flutter VideoPlayer not found; VideoPlayer hooks skipped")
        } else {
            log("VideoPlayer: ${videoPlayer.type}")

            videoPlayer.methodOrNull("seekTo", "V", "J")?.let { seekTo ->
                seekTo.addInstructions(
                    0,
                    """
                        invoke-static {p0}, $HOOK_CLASS->registerPlayer(Ljava/lang/Object;)V
                        invoke-static {p1, p2}, $HOOK_CLASS->registerSeek(J)V
                    """,
                )
                injected += "seekTo"
            } ?: log("WARNING: VideoPlayer.seekTo(J)V not found")

            videoPlayer.methods.firstOrNull { it.name == "<init>" }?.let { constructor ->
                // Inject after the super constructor call so the verifier never sees an
                // uninitialized `this` and `p2` is still the MediaItem.
                val superCallIndex = constructor.implementation?.instructions?.indexOfFirst { instruction ->
                    instruction.opcode == Opcode.INVOKE_DIRECT &&
                        (instruction as? ReferenceInstruction)?.reference
                            ?.let { it as? MethodReference }
                            ?.let { it.name == "<init>" && it.definingClass == videoPlayer.superclass } == true
                } ?: -1
                if (superCallIndex >= 0) {
                    constructor.addInstructions(
                        superCallIndex + 1,
                        """
                            invoke-static {p0}, $HOOK_CLASS->registerPlayer(Ljava/lang/Object;)V
                            invoke-static {p2}, $HOOK_CLASS->registerMediaItem(Ljava/lang/Object;)V
                        """,
                    )
                    injected += "VideoPlayer.<init>"
                }
            }

            videoPlayer.methodOrNull("play", "V")?.let {
                it.addInstructions(0, "invoke-static {}, $HOOK_CLASS->logPlay()V")
                injected += "play"
            }
            videoPlayer.methodOrNull("pause", "V")?.let {
                it.addInstructions(0, "invoke-static {}, $HOOK_CLASS->logPause()V")
                injected += "pause"
            }
            videoPlayer.methodOrNull("dispose", "V")?.let {
                it.addInstructions(0, "invoke-static {}, $HOOK_CLASS->logDispose()V")
                injected += "dispose"
            }
        }

        val playerRegistrations = injectPlayerRegistrations()
        if (playerRegistrations == 0) {
            log("WARNING: no player-typed field assignments found; live-TV seek may not work")
        } else {
            injected += "registerExoPlayer x$playerRegistrations"
        }

        val playingHooks = injectIsPlayingHooks()
        if (playingHooks == 0) {
            log("WARNING: no onIsPlayingChanged listener found; overlay state not tracked")
        } else {
            injected += "setPlaying x$playingHooks"
        }

        injectAdSeekBypass()?.let { injected += "ad seek bypass ($it)" }
            ?: log("WARNING: could not locate the ExoPlayer ad-seek guard; +30 s seek during ads may be ignored")

        if (injectImaSkippableBypass()) {
            injected += "IMA skippable"
        } else {
            log("WARNING: IMA AdData.skippable() not found; skip button may not appear")
        }

        val security = injectSecurityBypasses()
        if (security.isEmpty()) {
            log("WARNING: no Flutter security check was bypassed; the sideloaded build may refuse to play")
        } else {
            injected += "security bypass x${security.size}"
        }

        log("Injected ${injected.size} hook(s): ${injected.joinToString(", ")}")
    }
}
