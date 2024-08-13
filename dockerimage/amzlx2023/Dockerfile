FROM amazonlinux:2023

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
    python3.11 \
    python3.11-pip \
    python3.11-setuptools \
    # chrome-headless-shell で利用する
    nss \
    dbus-libs \
    atk at-spi2-atk \
    libXcomposite libXdamage libXrandr libgbm \
    alsa-lib \
    fontconfig \
    -y

# python3.12の野良ビルドに必要。パッケージが出たらコメントアウト
# RUN dnf groupinstall "Development Tools" -y

# custom installed packages for running server
# RUN dnf install \
#     cronie \
#     crontabs \
#     man-db-cron \
#     rpm-cron \
#     logrotate \
#     rsyslog \
#     rsyslog-logrotate \
#     sysstat \
#     python3.11 \
#     python3.11-pip \
#     python3.11-setuptools \
#     -y

# running daemon service
# RUN systemctl enable rsyslog.service \
#     && systemctl start rsyslog.service \
#     && systemctl enable crond.service \
#     && systemctl start crond.service \
#     && systemctl enable sysstat.service \
#     && systemctl start sysstat.service

# make work directory
# RUN sudo mkdir -p /distfiles && sudo chmod 755 /distfiles \
#     && sudo mkdir -p /var/log/webscribe

# install aws cli v2
RUN sudo mkdir /distfiles && sudo chmod 755 /distfiles && cd /distfiles \
    && curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" \
    && unzip awscliv2.zip \
    && sudo ./aws/install \
    && rm -rf ./aws \
    && rm awscliv2.zip

# install lambda runtime interface client for python3.11
# RUN sudo pip3.11 install awslambdaric

# install pip3.11 packages
COPY ./requirements.txt /distfiles/
RUN cd /distfiles && pip3.11 install -r requirements.txt

# create user
# RUN useradd -m -s /bin/bash "ec2-user" \
#     # && echo "ec2-user:" | chpasswd \
#     && passwd -d "ec2-user" \
#     && usermod -aG wheel "ec2-user" \
#     && echo "ec2-user ALL=NOPASSWD: ALL" >> /etc/sudoers
# USER ec2-user

# install google-chrome-stable
# RUN cd /distfiles \
#     && sudo wget https://dl.google.com/linux/direct/google-chrome-stable_current_x86_64.rpm \
#     && sudo dnf install -y ./google-chrome-stable_current_x86_64.rpm \
#     && sudo mkdir -p /usr/lib64/chromium-browser \
#     && sudo ln -s /usr/bin/google-chrome-stable /usr/lib64/chromium-browser/google-chrome-stable \
#     && sudo ln -s /usr/bin/google-chrome-stable /usr/lib64/chromium-browser/headless_shell \
#     && rm ./google-chrome-stable_current_x86_64.rpm

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
    
# dbusサービスに接続する必要があるため、systemdサービスを起動する
CMD ["/sbin/init"]
