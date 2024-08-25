FROM amazonlinux:2023

# Chromiumの安定版のバージョンを取得する
ARG CHROMEDRIVER_DOWNLOAD_URL

# yum update & install
RUN dnf update -y \
    && dnf install \
        # コンテナビルドに必要なパッケージ
        tar unzip sudo zip git python3-pip wget jq python3.11 python3.11-pip python3.11-setuptools \
        # python3.12の野良ビルドに必要。パッケージが出たらコメントアウト
        openssl openssl-devel bzip2-devel libffi-devel \
        # 常時稼働コンテナして必要なパッケージ
        procps-ng systemd cronie crontabs man-db-cron rpm-cron logrotate rsyslog rsyslog-logrotate sysstat \
        # 保守のために必要なパッケージ
        screen tree iperf3 iproute vim \
        -y

# python3.12の野良ビルドに必要。パッケージが出たらコメントアウト
RUN dnf groupinstall "Development Tools" -y

# running daemon service
# RUN systemctl enable rsyslog.service \
#     && systemctl start rsyslog.service \
#     && systemctl enable crond.service \
#     && systemctl start crond.service \
#     && systemctl enable sysstat.service \
#     && systemctl start sysstat.service

# make work directory
RUN sudo mkdir -p /distfiles && sudo chmod 755 /distfiles \
    && sudo mkdir -p /var/log/webscribe

# install aws cli v2
RUN cd /distfiles \
    && curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" \
    && unzip awscliv2.zip \
    && sudo ./aws/install \
    && rm awscliv2.zip

# create user
RUN useradd "ec2-user" && echo "ec2-user ALL=NOPASSWD: ALL" >> /etc/sudoers

# install google-chrome-stable
RUN cd /distfiles \
    && sudo wget https://dl.google.com/linux/direct/google-chrome-stable_current_x86_64.rpm \
    && sudo dnf install -y ./google-chrome-stable_current_x86_64.rpm \
    && sudo mkdir -p /usr/lib64/chromium-browser \
    && sudo ln -s /usr/bin/google-chrome-stable /usr/lib64/chromium-browser/google-chrome-stable \
    && sudo ln -s /usr/bin/google-chrome-stable /usr/lib64/chromium-browser/headless_shell \
    && rm ./google-chrome-stable_current_x86_64.rpm

# install chromedriver
RUN cd /distfiles \
    && sudo wget {CHROMEDRIVER_DOWNLOAD_URL} \
    && unzip ./chromedriver-linux64.zip \
    && ln -s /distfiles/chromedriver-linux64/chromedriver /usr/lib64/chromium-browser/chromedriver \
    && rm ./chromedriver-linux64.zip

# init
CMD ["/sbin/init"]
