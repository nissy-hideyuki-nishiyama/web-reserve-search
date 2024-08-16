#!/bin/bash

set -xeou

# ビルド前の準備
WORK_DIR="$(pwd)"
echo "WORK_DIR: ${WORK_DIR}"

# 正常終了後の処理
trap "rm -f ${WORK_DIR}/app/requirements.txt && rm -rf ${WORK_DIR}/app/reserve_tools" EXIT

# Chromeの最新バージョン情報を取得する
echo "Get Latest Chrome Version Info."
source ./GetLatestChromeVersion.sh

# あれば、追加の環境変数を設定する

# ビルド前の準備
## 共通ライブラリの reserve_tools/ の reserve_tools.py public_holiday.json court_map.json menu_map.json をコピーする
echo "copy reserve_tools/[reserve_tools.py public_holiday.json court_map.json menu_map.json]"
mkdir -p "${WORK_DIR}/app/reserve_tools"
cp "${WORK_DIR}/requirements.txt" "${WORK_DIR}/app/"
cp "${WORK_DIR}/../reserve_tools/reserve_tools.py" "${WORK_DIR}/../reserve_tools/public_holiday.json" "${WORK_DIR}/../reserve_tools/court_map.json" "${WORK_DIR}/../reserve_tools/menu_map.json" "${WORK_DIR}/app/reserve_tools/"

# docker compose で、Lambda 用の Selenium + Chrome-headless-shell の
# WEB スクライブ用 Docker イメージを作成する
docker compose -f ./docker-compose.yml build

exit 0
