import java.util.Properties
import org.jetbrains.kotlin.gradle.dsl.JvmTarget

plugins {
    alias(libs.plugins.kotlinMultiplatform)
    id("com.android.library")
    alias(libs.plugins.composeMultiplatform)
    alias(libs.plugins.composeCompiler)
    alias(libs.plugins.kotlinSerialization)
    alias(libs.plugins.ksp)
    alias(libs.plugins.androidx.room)
}

// Backend'in istediği uygulama anahtarı git'e girmesin diye local.properties'ten (gitignore'da) okunur
// ve build sırasında commonMain için bir Kotlin sabitine çevrilir. commonMain'de Android'in BuildConfig'i yok.
val dusApiKey: String = Properties().apply {
    rootProject.file("local.properties").takeIf { it.exists() }?.inputStream()?.use { load(it) }
}.getProperty("dus.apiKey", "")

val apiConfigUret by tasks.registering {
    val cikti = layout.buildDirectory.dir("generated/apiConfig/commonMain/kotlin")
    inputs.property("dusApiKey", dusApiKey)
    outputs.dir(cikti)
    doLast {
        if (dusApiKey.isBlank()) {
            throw GradleException("local.properties içinde dus.apiKey tanımlı değil (backend'deki APP_API_KEY ile aynı değer).")
        }
        val klasor = cikti.get().asFile.resolve("com/ilhanaltunbas/dusassistant/data/remote")
        klasor.mkdirs()
        klasor.resolve("ApiConfig.kt").writeText(
            """
            |package com.ilhanaltunbas.dusassistant.data.remote
            |
            |// Otomatik üretildi (shared/build.gradle.kts, apiConfigUret). Elle düzenleme.
            |internal object ApiConfig {
            |    const val API_KEY = "$dusApiKey"
            |}
            |""".trimMargin()
        )
    }
}

kotlin {
    androidTarget {
        compilerOptions {
            jvmTarget.set(JvmTarget.JVM_11)
        }
    }

    listOf(
        iosX64(),
        iosArm64(),
        iosSimulatorArm64()
    ).forEach { iosTarget ->
        iosTarget.binaries.framework {
            baseName = "Shared"
            isStatic = true
        }
    }
    
    sourceSets {
        // Üretilen ApiConfig.kt derlemeye dahil olur; derleme görevleri önce apiConfigUret'i çalıştırır.
        commonMain { kotlin.srcDir(apiConfigUret) }

        commonMain.dependencies {
            implementation(libs.compose.runtime)
            implementation(libs.compose.foundation)
            implementation(libs.compose.material3)
            implementation(libs.compose.ui)
            implementation(libs.compose.components.resources)
            implementation(libs.compose.materialIcons)
            implementation(libs.androidx.lifecycle.viewmodelCompose)
            implementation(libs.androidx.lifecycle.runtimeCompose)

            // Room KMP
            api(libs.androidx.room.runtime)
            implementation(libs.androidx.sqlite.bundled)

            implementation(libs.ktor.client.core)
            implementation(libs.ktor.client.content.negotiation)
            implementation(libs.ktor.serialization.kotlinx.json)
            implementation(libs.ktor.client.logging)
            implementation(libs.kotlinx.serialization.json)
            implementation(libs.kotlinx.datetime)
        }
        
        androidMain.dependencies {
            implementation(libs.compose.uiToolingPreview)
            implementation(libs.ktor.client.okhttp)
            implementation(libs.compose.uiTooling)
        }
        
        iosMain.dependencies {
            implementation(libs.ktor.client.darwin)
        }
        
        commonTest.dependencies {
            implementation(libs.kotlin.test)
            implementation("org.jetbrains.kotlinx:kotlinx-coroutines-core:1.11.0")
        }
    }
}

android {
    namespace = "com.ilhanaltunbas.dusassistant.shared"
    compileSdk = libs.versions.android.compileSdk.get().toInt()
    defaultConfig {
        minSdk = libs.versions.android.minSdk.get().toInt()
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_11
        targetCompatibility = JavaVersion.VERSION_11
    }
}

room {
    schemaDirectory("$projectDir/schemas")
}

dependencies {
    // Room kod üreticisi (KSP) her target için
    add("kspAndroid", libs.androidx.room.compiler)
    add("kspIosX64", libs.androidx.room.compiler)
    add("kspIosArm64", libs.androidx.room.compiler)
    add("kspIosSimulatorArm64", libs.androidx.room.compiler)
}
