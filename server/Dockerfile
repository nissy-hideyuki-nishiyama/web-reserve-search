FROM amazonlinux:2023

# Chromiumの安定版のバージョンを取得する
ARG MY_CHROME_DRIVER_VERSION
ENV CHROME_DRIVER_VERSION=${MY_CHROME_DRIVER_VERSION}

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
    -y

# custom installed packages for running server
RUN dnf install \
    cronie \
    crontabs \
    man-db-cron \
    rpm-cron \
    logrotate \
    rsyslog \
    rsyslog-logrotate \
    sysstat \
    python3.11 \
    python3.11-pip \
    python3.11-setuptools \
    -y

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
    && sudo wget https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/${CHROME_DRIVER_VERSION}/linux64/chromedriver-linux64.zip \
    && unzip ./chromedriver-linux64.zip \
    && ln -s /distfiles/chromedriver-linux64/chromedriver /usr/lib64/chromium-browser/chromedriver \
    && rm ./chromedriver-linux64.zip

# init
CMD ["/sbin/init"]
