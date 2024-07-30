#!/bin/sh
# shellcheck shell=dash

set -xeou

#
# Get current versions of Chrome
#
# Requires jq
#
# Usage: ./latest.sh [stable|beta|dev]Region
#

CHANNEL=${1:-beta}
CHANNEL=$(echo "${CHANNEL^}")
PLATFORM=${2:-linux64}
TARGET=${3:-chrome-headless-shell}
JSON_FILE="last-known-good-versions-with-downloads.json"
CHROMEDRIVER="chromedriver"

# 定数
REGION=ap-northeast-1
PROFILE=default
AWSCMD="aws --no-cli-pager --no-paginate --region ${REGION} --profile ${PROFILE}"
LAYER_NAME=headless-chrome_layer
S3_BUCKET=nissy-jp-distfiles-tky
S3_PATH=build_lambda/lambda_layer
Date=$(date +%Y%m%d-%H%M)

BUILD_BASE=$(pwd)

if [ -f "${JSON_FILE}" ]; then
  rm "${JSON_FILE}"
fi

if [ -d "${BUILD_BASE}/headless-chromium" ]; then
  rm -rf "${BUILD_BASE}/headless-chromium"
fi

wget https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json

VERSION=$(cat ${JSON_FILE} | jq -r ".channels.${CHANNEL}.version")
TARGET_DOWNLOAD_URL=$(cat ${JSON_FILE} | jq -r ".channels.${CHANNEL}.downloads.\"${TARGET}\"[] | select(.platform == \"${PLATFORM}\")".url)
CHROMEDRIVER_DOWNLOAD_URL=$(cat  ${JSON_FILE} | jq -r ".channels.${CHANNEL}.downloads.\"${CHROMEDRIVER}\"[] | select(.platform == \"${PLATFORM}\")".url)
ZIP_FILENAME="headless-chromium_${VERSION}.zip"

echo "version: ${VERSION}"
echo "${TARGET}_download_url: ${TARGET_DOWNLOAD_URL}"
echo "chromedriver_download_url: ${CHROMEDRIVER_DOWNLOAD_URL}"
echo 

trap "cd ${BUILD_BASE} && rm -rf ${JSON_FILE} ${ZIP_FILENAME} ${BUILD_BASE}/headless-chromium ${BUILD_BASE}/distfiles" 0

mkdir -p "${BUILD_BASE}"/headless-chromium
mkdir -p "${BUILD_BASE}"/distfiles

cd "${BUILD_BASE}"/distfiles
wget "${TARGET_DOWNLOAD_URL}"
wget "${CHROMEDRIVER_DOWNLOAD_URL}"

unzip chrome-headless-shell-linux64.zip
unzip chromedriver-linux64.zip

cp -a "${BUILD_BASE}"/distfiles/chrome-headless-shell-linux64/* "${BUILD_BASE}"/headless-chromium/
cp -a "${BUILD_BASE}"/distfiles/chromedriver-linux64/* "${BUILD_BASE}"/headless-chromium/

# zip compress file
cd "${BUILD_BASE}"
zip -ry "${ZIP_FILENAME}" headless-chromium
file "${ZIP_FILENAME}"
ls -lh "${ZIP_FILENAME}"
echo "build finished." 

# zipファイルを所定のディレクトリにアップロードする
echo "upload zip file to s3 bucket."
${AWSCMD} s3 cp "${ZIP_FILENAME}" s3://"${S3_BUCKET}"/"${S3_PATH}"/

# 所定のLambdaレイヤーに登録する
${AWSCMD} lambda publish-layer-version --layer-name "${LAYER_NAME}" \
  --description "headless_chrome_shell at ${Date}" \
  --license-info "BSD" --compatible-runtimes python3.11 python3.12 \
  --content S3Bucket="${S3_BUCKET}",S3Key="${S3_PATH}"/"${ZIP_FILENAME}"

exit 0
