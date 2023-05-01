#!/bin/sh
# shellcheck shell=dash

#
# Get current versions of Chrome Driver
#
# Requires jq
#
# Usage: ./chromedriver_version.sh [stable|beta|dev]
#

CHANNEL=${1:-stable}

VERSION=$(curl -s https://omahaproxy.appspot.com/all.json | \
  jq -r ".[] | select(.os == \"linux\") | .versions[] | select(.channel == \"$CHANNEL\") | .current_version" \
)

MAJORVER=$(echo "$VERSION" | gawk -F . '{ print $1 }')

CHROME_DRIVER_VERSION=$(curl -s https://chromedriver.chromium.org/downloads | grep -e "^If you are using Chrome version ${MAJORVER}," | head -1 | gawk '{ print $NF }')

# echo "VERSION: ${VERSION}"
# echo "MAJORVER: ${MAJORVER}"
# echo "CHROME_DRIVER_VERSION: ${CHROME_DRIVER_VERSION}"

echo "${CHROME_DRIVER_VERSION}"