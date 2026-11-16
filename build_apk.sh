#!/usr/bin/env bash
set -e

export JAVA_HOME=/home/realsky/.build_tools/jdk17
export PATH=$JAVA_HOME/bin:$PATH
export ANDROID_HOME=/home/realsky/.build_tools/android-sdk

cd /home/realsky/bluevolume/android
/home/realsky/.build_tools/gradle-8.4/bin/gradle assembleDebug --no-daemon
