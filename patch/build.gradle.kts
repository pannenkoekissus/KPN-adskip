import org.jetbrains.kotlin.gradle.dsl.JvmTarget

plugins {
    kotlin("jvm") version "2.4.21"
}

group = "software.morphe.patches"
version = "2.3.0"

repositories {
    mavenCentral()
    // R8/D8 is published on Google's Maven repository.
    google()
}

// Morphe publishes the patcher and the Gradle plugin to GitHub Packages only.
// Until `gpr.user` / `gpr.key` credentials are available, compile against the
// patcher bundled inside the Morphe Desktop CLI jar. Override the location with
// the MORPHE_DESKTOP_JAR environment variable or `-PmorpheDesktopJar=...`.
val morpheDesktopJar: String = providers.gradleProperty("morpheDesktopJar").orNull
    ?: providers.environmentVariable("MORPHE_DESKTOP_JAR").orNull
    ?: layout.projectDirectory.file("lib/morphe-desktop.jar").asFile.absolutePath

// Only used to dex the patch classes for the bundle. It must not leak into the
// bundle itself, hence a separate configuration.
val dexer: Configuration by configurations.creating

dependencies {
    compileOnly(files(morpheDesktopJar))
    dexer("com.android.tools:r8:8.13.25")
}

kotlin {
    compilerOptions {
        jvmTarget.set(JvmTarget.JVM_17)
    }
}

java {
    sourceCompatibility = JavaVersion.VERSION_17
    targetCompatibility = JavaVersion.VERSION_17
}

// The hook implementation is the smali in ./smali (assembled into extensions/kpn.mpe).
// src/main/java contains an older, incomplete Java draft that targets the Android SDK and
// is not part of the bundle.
sourceSets {
    main {
        java.setSrcDirs(emptyList<String>())
    }
}

private val extensionDexFile = layout.buildDirectory.file("extensions/kpn.mpe")
private val patchClassesJarFile = layout.buildDirectory.file("dex/input/patches-classes.jar")
private val patchDexFile = layout.buildDirectory.file("dex/output/classes.dex")

val assembleExtension by tasks.registering(JavaExec::class) {
    description = "Assembles patch/smali into the extension DEX merged by Morphe."
    group = "build"

    inputs.dir(layout.projectDirectory.dir("smali"))
    outputs.file(extensionDexFile)

    classpath = files(morpheDesktopJar)
    mainClass.set("com.android.tools.smali.smali.Main")
    args(
        "assemble",
        "-o", extensionDexFile.get().asFile.absolutePath,
        layout.projectDirectory.dir("smali").asFile.absolutePath,
    )

    doFirst {
        extensionDexFile.get().asFile.parentFile.mkdirs()
    }
}

val patchClassesJar by tasks.registering(Jar::class) {
    description = "Packs the compiled patch classes for D8."
    group = "build"

    dependsOn(tasks.named("classes"))

    archiveFileName.set(patchClassesJarFile.get().asFile.name)
    destinationDirectory.set(patchClassesJarFile.get().asFile.parentFile)
    from(sourceSets.main.get().output)
}

// Morphe Manager loads bundles on Android, where .class files cannot be read:
// it rejects an .mpp without a non-empty DEX entry. The CLI loads the .class
// files, so the bundle carries both, exactly like the official Morphe bundles.
val dexPatches by tasks.registering(JavaExec::class) {
    description = "Dexes the compiled patch classes into classes.dex for the .mpp."
    group = "build"

    dependsOn(patchClassesJar)

    classpath = dexer
    mainClass.set("com.android.tools.r8.D8")

    inputs.file(patchClassesJarFile)
    outputs.file(patchDexFile)

    doFirst {
        patchDexFile.get().asFile.parentFile.apply {
            deleteRecursively()
            mkdirs()
        }
        args = listOf(
            "--release",
            "--min-api", "24",
            "--output", patchDexFile.get().asFile.parentFile.absolutePath,
            patchClassesJarFile.get().asFile.absolutePath,
        )
    }
}

val bundleMpp by tasks.registering(Jar::class) {
    description = "Builds the loadable Morphe patch bundle (.mpp)."
    group = "build"

    dependsOn(tasks.named("classes"), assembleExtension, dexPatches)

    archiveFileName.set("kpn-tvplus-adskip.mpp")
    destinationDirectory.set(layout.buildDirectory.dir("output"))

    from(sourceSets.main.get().output)
    from(extensionDexFile) {
        into("extensions")
    }
    from(patchDexFile)

    manifest {
        attributes(
            "Name" to "KPN TV+ AdSkip Patches",
            "Description" to "Ad-break skipping and +30 s seek for KPN TV+.",
            "Version" to project.version,
            "Timestamp" to System.currentTimeMillis().toString(),
            "Source" to "https://github.com/pannenkoekissus/KPN-adskip",
            "Author" to "KPN-adskip contributors",
            "Contact" to "na",
            "Website" to "na",
            "License" to "GPLv3",
            "Patcher-Version" to "2.4.0",
        )
    }
}

tasks.named("build") {
    dependsOn(bundleMpp)
}
