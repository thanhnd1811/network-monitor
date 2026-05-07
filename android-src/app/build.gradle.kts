import java.util.Properties

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

// Read DASHBOARD_URL from app/url.properties (created at build time by CI)
// or fall back to a placeholder for local builds.
val urlProps = Properties().apply {
    val f = file("url.properties")
    if (f.exists()) load(f.inputStream())
}
val dashboardUrl: String = urlProps.getProperty(
    "DASHBOARD_URL",
    "https://example.github.io/network-monitor/"
)

android {
    namespace = "vn.edu.ftu.netmon"
    compileSdk = 34

    defaultConfig {
        applicationId = "vn.edu.ftu.netmon"
        minSdk = 24                // Android 7.0 (covers ~98% of devices)
        targetSdk = 34
        versionCode = 1
        versionName = "1.0"
        buildConfigField("String", "DASHBOARD_URL", "\"$dashboardUrl\"")
    }

    buildFeatures {
        viewBinding = true
        buildConfig  = true
    }

    buildTypes {
        debug {
            isMinifyEnabled = false
        }
        release {
            isMinifyEnabled = false
            // Use the default debug key so APK is sideload-installable without signing setup.
            // For Play Store, replace with a release keystore.
            signingConfig = signingConfigs.getByName("debug")
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }
}

dependencies {
    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.appcompat:appcompat:1.7.0")
    implementation("com.google.android.material:material:1.12.0")
    implementation("androidx.work:work-runtime-ktx:2.9.1")
    implementation("androidx.swiperefreshlayout:swiperefreshlayout:1.1.0")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.8.1")
}
