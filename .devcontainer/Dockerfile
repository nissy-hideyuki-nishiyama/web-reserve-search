FROM ubuntu:22.04

# Chromiumの安定版のバージョンを取得する
ARG MY_CHROME_DRIVER_VERSION
ENV CHROME_DRIVER_VERSION=${MY_CHROME_DRIVER_VERSION}

# yum update & install
RUN apt update -y \
    && apt install \
        systemd \
        unzip \
        sudo \
        zip \
        lsb \
        wget \
        curl \
        iproute2 \
        screen \
        tree \
        iperf3 \
        git \
        vim \
        python3-pip \
        python3.10-venv \
        jq \
        gawk \
        # snapd \
        -y

# custom installed packages
# RUN apt install 
#     -y

# make work directory
RUN sudo mkdir -p /distfiles && sudo chmod 755 /distfiles \
    && sudo mkdir -p /var/log/webscribe && sudo chmod 755 /var/log/webscribe \
    && sudo mkdir -p /var/lib/apt/lists && sudo chmod 755 /var/lib/apt/lists

# install aws cli v2
RUN cd /distfiles \
    && curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" \
    && unzip awscliv2.zip \
    && sudo ./aws/install \
    && rm awscliv2.zip

# install google-chrome-stable
RUN cd /distfiles \
    && wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && sudo apt install -y ./google-chrome-stable_current_amd64.deb \
    && sudo mkdir -p /usr/lib64/chromium-browser \
    && sudo ln -s /usr/bin/google-chrome-stable /usr/lib64/chromium-browser/google-chrome-stable \
    && sudo ln -s /usr/bin/google-chrome-stable /usr/lib64/chromium-browser/headless_shell \
    && rm ./google-chrome-stable_current_amd64.deb

# install chromedriver
RUN cd /distfiles \
    && sudo wget https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/${CHROME_DRIVER_VERSION}/linux64/chromedriver-linux64.zip \
    && sudo unzip ./chromedriver_linux64.zip \
    && sudo ln -s /distfiles/chromedriver-linux64/chromedriver /usr/lib64/chromium-browser/chromedriver \
    && sudo rm ./chromedriver_linux64.zip

# Lambdaの開発でAWS SAM におけるローカルデバッグ環境が必要であり、Dockerコンテナを使うので、Dockerをインストールする。
# 実際に使うのは、docker cli, docker-compose コマンドのみ
RUN sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg \
    && sudo echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null \
    && sudo apt update \
    && sudo apt install docker-ce-cli docker-compose docker-compose-plugin -y

# AWS SAM と AWS Toolkitのインストール
# RUN cd /distfiles \
#     && sudo wget https://github.com/aws/aws-sam-cli/releases/latest/download/aws-sam-cli-linux-x86_64.zip \
#     && sudo unzip aws-sam-cli-linux-x86_64.zip -d sam-installation \
#     && sudo ./sam-installation/install \
#     && sam --version

# 開発環境なので、initは不要
# だが、Dockerコンテナでローカルデバッグするため必要となる
# CMD ["/sbin/init"]

