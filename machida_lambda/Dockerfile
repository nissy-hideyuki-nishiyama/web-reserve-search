# ビルドステージ
FROM public.ecr.aws/lambda/python:3.12 AS builder

# Docker コンテナに必要なパッケージのビルドに必要なビルドツールをインストールする
RUN dnf update -y \
&& dnf install \
    procps-ng systemd sudo tree vim \
    tar unzip zip git jq gcc wget \
    openssl openssl-devel libffi-devel \
    -y

# Pythonのパッケージマネージャを最新化する
COPY ./requirements.txt ./
RUN pip install --upgrade pip \
    && pip install --prefix=/install -r requirements.txt

# 実行ステージ
FROM public.ecr.aws/lambda/python:3.12

# Chromiumの安定版のバージョンを取得する
ARG TARGET_DOWNLOAD_URL
ARG CHROMEDRIVER_DOWNLOAD_URL
ENV FONTCONFIG_PATH=/etc/fonts
ENV LANG=ja_JP.UTF-8

# yum update & install
RUN dnf update -y \
    && dnf install \
        # デバッグツール
        procps-ng systemd sudo tree vim \
        # ビルドツール
        tar unzip zip jq wget \
        # chrome-headless-shell で利用する
        nss dbus-libs atk at-spi2-atk fontconfig \
        libXcomposite libXdamage libXrandr libgbm alsa-lib \
        -y

# app配下をコンテナイメージにコピー
COPY ./app/ ./

# ビルドステージでビルドしたパッケージをコピーする
COPY --from=builder /install/lib/python3.12/site-packages /var/lang/lib/python3.12/site-packages

# install chrome-headless-shell
RUN mkdir -p /distfiles /usr/lib64/chromium-browser && cd /distfiles \
    && sudo wget ${TARGET_DOWNLOAD_URL} \
    && unzip ./chrome-headless-shell-linux64.zip \
    && ln -s /distfiles/chrome-headless-shell-linux64/chrome-headless-shell /usr/lib64/chromium-browser/headless_shell \
    && rm ./chrome-headless-shell-linux64.zip

# install chomedriver
RUN cd /distfiles \
    && wget ${CHROMEDRIVER_DOWNLOAD_URL} \
    && unzip ./chromedriver-linux64.zip \
    && ln -s /distfiles/chromedriver-linux64/chromedriver /usr/lib64/chromium-browser/chromedriver \
    && rm ./chromedriver-linux64.zip

# Lambda 用 Docker コンテナ
CMD [ "check_empty_reserves_multi_threads.main" ]
