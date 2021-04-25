#!/bin/sh
# shellcheck shell=dash

#
# Build Chromium for Amazon Linux.
# Assumes root privileges. Or, more likely, Docker—take a look at
# the corresponding Dockerfile in this directory.
#
# Requires
#
# Usage: ./build.sh
#
# Further documentation: https://github.com/adieuadieu/serverless-chrome/blob/develop/docs/chrome.md
#

set -e

BUILD_BASE=$(pwd)
VERSION=${VERSION:-master}
# nishiyma locate
PROFILE=${PROFILE:-default}
S3BUCKET=${S3BUCKET:-nissy-jp-distfiles-tky}
S3PREFIX=${S3PREFIX:-build_lambda/lambda_layer}

cd "$BUILD_BASE"

# build distfile package
mkdir -p "${BUILD_BASE}/distfiles/headless-chromium"
strip -o "$BUILD_BASE/distfiles/headless-chromium/headless_shell" build/chromium/src/out/Headless/headless_shell
cp -rf /build/chromium/src/out/Headless/swiftshader "${BUILD_BASE}/distfiles/headless-chromium/"
cd "${BUILD_BASE}/distfiles/headless-chromium/"
ln -s ./swiftshader/libEGL.so ./libEGL.so
ln -s ./swiftshader/libEGL.so.TOC ./libEGL.so.TOC
ln -s ./swiftshader/libGLESv2.so ./libGLESv2.so
ln -s ./swiftshader/libGLESv2.so.TOC ./libGLESv2.so.TOC

# download chromedriver
cd "${BUILD_BASE}/distfiles/headless-chromium/"
echo "download stable chromedriver from google."
#curl https://chromedriver.storage.googleapis.com/86.0.4240.22/chromedriver_linux64.zip --output chromedriver_linux64.zip
curl https://chromedriver.storage.googleapis.com/90.0.4430.24/chromedriver_linux64.zip --output chromedriver_linux64.zip
unzip chromedriver_linux64.zip
rm chromedriver_linux64.zip
chmod 755 chromedriver
du -h -d 2./

# zip compress file
#cd "${BUILD_BASE}/distfiles"
zip -r headless-chromium_${VERSION}.zip *
cd ../
mv headless-chromium/headless-chromium_${VERSION}.zip ./
file headless-chromium_${VERSION}.zip
ls -l headless-chromium_${VERSION}.zip
echo "build finished." 

# upload s3 aws
echo "upload headless-choromium_${VERSION}.zip to s3://${S3BUCKET}/${S3PREFIX}/."
aws --profile ${PROFILE} s3 cp headless-chromium_${VERSION}.zip s3://${S3BUCKET}/${S3PREFIX}/
