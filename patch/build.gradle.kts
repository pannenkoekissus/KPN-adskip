import org.jetbrains.kotlin.gradle.dsl.JvmTarget

plugins {
    kotlin("jvm") version "2.4.21"
}

group = "software.morphe.patches"
version = "2.2.0"

repositories {
    mavenCentral()
}

// Morphe publishes the patcher and the Gradle plugin to GitHub Packages only.
// Until `gpr.user` / `gpr.key` credentials are available, compile against the
// patcher bundled inside the Morphe Desktop CLI jar. Override the location with
// the MORPHE_DESKTOP_JAR environment variable or `-PmorpheDesktopJar=...`.
val morpheDesktopJar: String = providers.gradleProperty("morpheDesktopJar").orNull
    ?: providers.environmentVariable("MORPHE_DESKTOP_JAR").orNull
    ?: layout.projectDirectory.file("lib/morphe-desktop.jar").asFile.absolutePath

dependencies {
    compileOnly(files(morpheDesktopJar))
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

val bundleMpp by tasks.registering(Jar::class) {
    description = "Builds the loadable Morphe patch bundle (.mpp)."
    group = "build"

    dependsOn(tasks.named("classes"), assembleExtension)

    archiveFileName.set("kpn-tvplus-adskip.mpp")
    destinationDirectory.set(layout.buildDirectory.dir("output"))

    from(sourceSets.main.get().output)
    from(extensionDexFile) {
        into("extensions")
    }

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
