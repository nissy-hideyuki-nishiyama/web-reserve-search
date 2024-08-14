#!/bin/bash

# Chromeの最新バージョン情報を取得する
echo "Get Latest Chrome Version Info."
source ./GetLatestChromeVersion.sh

# echo "CHROME_VERSION:             ${CHROME_VERSION}"
# echo "TARGET_DOWNLOAD_URL:        ${TARGET_DOWNLOAD_URL}"
# echo "CHROMEDRIVER_DOWNLOAD_URL:  ${CHROMEDRIVER_DOWNLOAD_URL}"

# あれば、追加の環境変数を設定する

# docker compose で、Lambda 用の Selenium + Chrome-headless-shell の
# WEB スクライブ用 Docker イメージを作成する
docker compose -f ./docker-compose.yml up --build
