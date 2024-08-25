#!/bin/bash

#################################################
#
# 本スクリプトは、Dockerホスト上で実施し、Dockerイメージをビルドし、Dockerコンテナを常時起動コンテナとして登録する
# これは常時稼働コンテナのserverコンテナのDockerイメージをビルドし、serverコンテナを登録するものである
# 前提条件
#  ‐ https://github.com/nissy-hideyuki-nishiyama/web-reserve-search　にアクセス権があること
#  - Ubuntu 22.04 LTS を稼働しているPCがあり、下記のパッケージがインストールされていること
#    ‐ docker-ce, docker-ce-cli, docker-ce-root, docker-compose, docker-compose-plugin
#    ‐ python3.12, python3.12-venv
#  ‐ このPC＆Ubuntuにコンソールログインできること
#  ‐ Do
# 事前準備:
#  1. PCコンソールにログインする
#  2. dockerコンテナを稼働させたいディレクトリに移動する
#  3. 上記のgithubリポジトリをクローンする
#  4. WEBスクライブ対象となるサイトの設定ファイルが保存されているディレクトリを web-reserve-search以下にコピーする(web-server-search/config/)
#  5. web-reserve-search ディレクトリに移動する
#  6. 本スクリプトはここから開始する
#
##################################################

set -xeou

# 設定値
declare -a TARGET_SITE_DIR
TARGET_SITE_DIRS=(
    chofu
    hachioji
    kawasaki
    machida
    martgd
    tama
)
PYTHON_VENV_DIR=".venv"

# 実行環境の値を取得する
WORK_DIR="$(pwd)"
echo "WORK_DIR: ${WORK_DIR}"

# 正常終了後の処理
# trap "rm -f ${WORK_DIR}/app/requirements.txt && rm -rf ${WORK_DIR}/app/reserve_tools" EXIT

# 事前準備
## ビルド前の準備
## 全プログラムで利用する python のvenv環境を作成する
echo "making python venv environment to use all webscribe programs."
if [ -d "${WORK_DIR}/.venv" ]; then
    echo "found Older python venv directory. delete older python venv directory"
    rm -rf "${WORK_DIR}/.venv"
fi
echo "make new python venv environment."
python3.12 -m venv .venv
source .venv/bin/activate

echo "install pip packages with tama_lambda/requirements.txt"
pip3 install -r "${WORK_DIR}/tama_lambda/requirements.txt"
pip-review --auto
deactivate

## 共通ライブラリの reserve_tools/ の reserve_tools.py public_holiday.json court_map.json menu_map.json
echo "copy config to target site directory."
for site_name in ${TARGET_SITE_DIRS[@]}
do
    cp -rf "${WORK_DIR}/config/${site_name}"/* "${WORK_DIR}/${site_name}/"
    if [ ! -h "${WORK_DIR}/${site_name}/public_holiday.json" ];
        ln -s "${WORK_DIR}/reserve_tools/public_holiday.json" "${WORK_DIR}/${site_name}/public_holiday.json"
    fi
    if [ ! -h "${WORK_DIR}/${site_name}/reserve_tools" ];
        ln -s "${WORK_DIR}/reserve_tools" "${WORK_DIR}/${site_name}/reserve_tools"
    fi
done

# Dockerイメージのビルド
## Chromeの最新バージョン情報を取得し、環境変数に設定する
echo "Get Latest Chrome Version Info."
source ${WORKDIR}/server/build/GetLatestChromeVersion.sh

# あれば、追加の環境変数を設定する

# docker compose で、Lambda 用の Selenium + Chrome-headless-shell の
# WEB スクライブ用 Docker イメージを作成する
docker compose -f ./docker-compose.yml build

exit 0
