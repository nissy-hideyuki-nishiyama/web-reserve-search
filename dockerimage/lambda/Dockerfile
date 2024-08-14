# Lambda - Python用コンテナイメージを使用
FROM public.ecr.aws/lambda/python:3.12

# Chromiumの安定版のバージョンを取得する
# ARG MY_CHROME_VERSION
# ARG MY_CHROME_DRIVER_VERSION
ARG TARGET_DOWNLOAD_URL
ARG CHROMEDRIVER_DOWNLOAD_URL
ENV FONTCONFIG_PATH=/etc/fonts
ENV LANG=ja_JP.UTF-8

# yum update & install
RUN dnf update -y \
    && dnf install \
        procps-ng \
        systemd \
        tar \
        unzip \
        sudo \
        zip \
        -y

# custom installed packages
RUN dnf install wget \
    iproute \
    screen \
    tree \
    iperf3 \
    git \
    vim \
    python3-pip \
    jq \
    # python3.12の野良ビルドに必要。パッケージが出たらコメントアウト
    openssl \
    openssl-devel \
    bzip2-devel \
    libffi-devel \
    # python3.11 のインストール
    # python3.11 \
    # python3.11-pip \
    # python3.11-setuptools \
    # chrome-headless-shell で利用する
    nss \
    dbus-libs \
    atk at-spi2-atk \
    libXcomposite libXdamage libXrandr libgbm \
    alsa-lib \
    fontconfig \
    -y

# Pythonのパッケージマネージャを最新化
# RUN pip install --upgrade pip

# api配下をコンテナイメージにコピー
COPY . ./

# install aws cli v2
# RUN sudo mkdir /distfiles && sudo chmod 755 /distfiles && cd /distfiles \
#     && curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" \
#     && unzip awscliv2.zip \
#     && sudo ./aws/install \
#     && rm -rf ./aws \
#     && rm awscliv2.zip

# requirements.txtで記述した依存パッケージを一括インストール
# RUN pip install -r requirements.txt

# install chrome-headless-shell
RUN mkdir -p /distfiles /usr/lib64/chromium-browser && cd /distfiles \
    # && sudo wget https://storage.googleapis.com/chrome-for-testing-public/${MY_CHROME_VERSION}/linux64/chrome-headless-shell-linux64.zip \
    && sudo wget ${TARGET_DOWNLOAD_URL} \
    && unzip ./chrome-headless-shell-linux64.zip \
    && ln -s /distfiles/chrome-headless-shell-linux64/chrome-headless-shell /usr/lib64/chromium-browser/headless_shell \
    && rm ./chrome-headless-shell-linux64.zip

# install chomedriver
RUN cd /distfiles \
    # && wget https://storage.googleapis.com/chrome-for-testing-public/${MY_CHROME_DRIVER_VERSION}/linux64/chromedriver-linux64.zip \
    && wget ${CHROMEDRIVER_DOWNLOAD_URL} \
    && unzip ./chromedriver-linux64.zip \
    && ln -s /distfiles/chromedriver-linux64/chromedriver /usr/lib64/chromium-browser/chromedriver \
    && rm ./chromedriver-linux64.zip
    
# コンテナ起動時の実行関数を定義
# CMD ["check_empty_reserves_multi_threads.lambda_handler"]

# dbusサービスに接続する必要があるため、systemdサービスを起動する
CMD ["/sbin/init"]
