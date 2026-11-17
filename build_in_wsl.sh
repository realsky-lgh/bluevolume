#!/usr/bin/env bash
set -e

export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
export PATH=$JAVA_HOME/bin:$PATH
export ANDROID_HOME=/opt/android-sdk
export PATH=$ANDROID_HOME/cmdline-tools/latest/bin:$PATH

echo "Accepting licenses..."
yes | sdkmanager --licenses >/dev/null 2>&1 || true

echo "Installing platforms;android-34 and build-tools;34.0.0..."
sdkmanager "platforms;android-34" "build-tools;34.0.0"

# Install gradle if not present
if [ ! -d "/opt/gradle-8.4" ]; then
    echo "Downloading Gradle 8.4..."
    cd /opt
    wget -q https://services.gradle.org/distributions/gradle-8.4-bin.zip
    unzip -q gradle-8.4-bin.zip
    rm gradle-8.4-bin.zip
fi

echo "Building APK..."
cd /mnt/d/soft/bluevolume/bluevolume/android
/opt/gradle-8.4/bin/gradle assembleDebug --no-daemon

echo "Copying APK to project root..."
cp /mnt/d/soft/bluevolume/bluevolume/android/app/build/outputs/apk/debug/app-debug.apk /mnt/d/soft/bluevolume/bluevolume/bluevolume.apk

echo "SUCCESS! APK built and placed at /mnt/d/soft/bluevolume/bluevolume/bluevolume.apk"
