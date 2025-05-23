#!/bin/bash

#################################################
#
# WEBスクライブプログラムを稼働させる python の venv 環境などを作成する。
# 本スクリプトは 常時稼働コンテナにログインして、実行する
#
# 前提条件
#  ‐ https://github.com/nissy-hideyuki-nishiyama/web-reserve-search　にアクセス権があること
#  ‐ 上記のリポジトリを複製し、/web-reserve-search にバインドされていること
#  - Docker コンテナ内に、python3.12.xのパッケージがインストールされていること
#  ‐ 
# 
#
##################################################

set -xeou

# パラメータ
PYTHON_VENV_DIR=".venv"
ROOT_DIR="/web-reserve-search"

# 実行環境の値を取得する
CURRENT_DIR="$(pwd)"
echo "CURRENT_DIR: ${CURRENT_DIR}"

# ログディレクトリを作成する
mkdir -p /var/log/webscribe

## 全プログラムで利用する python のvenv環境を作成する
echo "making python venv environment to use all webscribe programs."
if [ -d "${ROOT_DIR}/${PYTHON_VENV_DIR}" ]; then
    echo "found Older python venv directory. delete older python venv directory"
    rm -rf "${ROOT_DIR}/${PYTHON_VENV_DIR:?}"
fi

# python の venv　環境を作成する。コンテナ内のpython3.12.xを指定して、venvを作成する
echo "make python venv environment"
cd "${ROOT_DIR}"
/usr/local/bin/python3 -m venv "${PYTHON_VENV_DIR}"
# shellcheck source=src/util.sh
source "${ROOT_DIR}/${PYTHON_VENV_DIR}/bin/activate"

# 必要なPIPパッケージをインストールする
echo "install pip package for web scribing."
pip3 install -r "${ROOT_DIR}/tama_lambda/requirements.txt"
pip-review --auto
# aiohttp 3.10.11以上だとContent-Typeヘッダーが取れないため、しばらく固定する
pip3 install aiohttp==3.10.10

# cronジョブをインストールする
crontab -u root "${ROOT_DIR}/server/cron.d/root.cron"
crontab -l

# サーバの稼働状況を表示する
systemctl status
ps aux
ls -l /var/log/webscribe/*

cd "${CURRENT_DIR}"

exit 0
