#!/bin/sh
# shellcheck shell=dash

#
# Get current versions of Chromium
#
# Requires jq
#
# Usage: ./latest.sh [stable|beta|dev]
#

CHANNEL=${1:-beta}
CHANNEL=$(echo "${CHANNEL^}")
PLATFORM=${2:-linux64}
TARGET=${3:-chrome-headless-shell}
JSON_FILE="last-known-good-versions-with-downloads.json"
CHROMEDRIVER="chromedriver"

BUILD_BASE=$(pwd)

if [ -f "${JSON_FILE}" ]; then
  rm ${JSON_FILE}
fi

# こちらはChromiumなので残しておく
# VERSION=$(curl -s https://omahaproxy.appspot.com/all.json | \
#   jq -r ".[] | select(.os == \"linux\") | .versions[] | select(.channel == \"$CHANNEL\") | .current_version" \
# )

trap "rm ${JSON_FILE}" 0

wget https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json

VERSION=$(cat ${JSON_FILE} | jq -r ".channels.${CHANNEL}.version")
TARGET_DOWNLOAD_URL=$(cat ${JSON_FILE} | jq -r ".channels.${CHANNEL}.downloads.\"${TARGET}\"[] | select(.platform == \"${PLATFORM}\")".url)
CHROMEDRIVER_DOWNLOAD_URL=$(cat  ${JSON_FILE} | jq -r ".channels.${CHANNEL}.downloads.\"${CHROMEDRIVER}\"[] | select(.platform == \"${PLATFORM}\")".url)

echo "channel: ${CHANNEL^}"
echo "version: ${VERSION}"
echo "${TARGET}_download_url: ${TARGET_DOWNLOAD_URL}"
echo "chromedriver_download_url: ${CHROMEDRIVER_DOWNLOAD_URL}"

exit 0
