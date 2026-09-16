plugins {
    kotlin("jvm") version "2.0.0"
}

group = "software.morphe.patches"
version = "2.1.0"

repositories {
    mavenCentral()
    google()
    maven("https://jitpack.io")
}

dependencies {
    // Morphe / ReVanced Patcher dependency
    compileOnly("app.revanced:patcher:20.0.0")
    compileOnly("com.android.tools.smali:smali-dexlib2:3.0.8")
    
    // Android compile stubs for AdSkipHook
    compileOnly("com.google.android:android:4.1.1.4")
}

kotlin {
    jvmToolchain(17)
}
