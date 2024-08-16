#!/bin/sh
# shellcheck shell=dash

#
# Get current versions of Chromium
#
# Requires jq
#
# Usage: ./latest.sh [stable|beta|dev]
#
set -eo pipefail

CHANNEL=${1:-stable}
CHANNEL=$(echo "${CHANNEL^}")
PLATFORM=${2:-linux64}
TARGET=${3:-chrome-headless-shell}
JSON_FILE="last-known-good-versions-with-downloads.json"
CHROMEDRIVER="chromedriver"

BUILD_BASE=$(pwd)

if [ -f "${JSON_FILE}" ]; then
  rm ${JSON_FILE}
fi

trap "rm ${JSON_FILE}" EXIT

wget -q https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json

CHROME_VERSION=$(cat ${JSON_FILE} | jq -r ".channels.${CHANNEL}.version")
TARGET_DOWNLOAD_URL=$(cat ${JSON_FILE} | jq -r ".channels.${CHANNEL}.downloads.\"${TARGET}\"[] | select(.platform == \"${PLATFORM}\")".url)
CHROMEDRIVER_DOWNLOAD_URL=$(cat  ${JSON_FILE} | jq -r ".channels.${CHANNEL}.downloads.\"${CHROMEDRIVER}\"[] | select(.platform == \"${PLATFORM}\")".url)

echo "channel: ${CHANNEL^}"
echo "version: ${CHROME_VERSION}"
echo "${TARGET}_download_url: ${TARGET_DOWNLOAD_URL}"
echo "chromedriver_download_url: ${CHROMEDRIVER_DOWNLOAD_URL}"

export CHROME_VERSION="${CHROME_VERSION}"
export TARGET_DOWNLOAD_URL="${TARGET_DOWNLOAD_URL}"
export CHROMEDRIVER_DOWNLOAD_URL="${CHROMEDRIVER_DOWNLOAD_URL}"
