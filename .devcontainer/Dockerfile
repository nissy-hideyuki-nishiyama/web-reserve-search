FROM amazonlinux:2023

# Chromiumの安定版のバージョンを取得する
# jqを利用しているので、ここでは止める
#ENV CHROME_DRIVER_VERSION=$(/workspace/lambda_layer/headless-chromium/chromedriver_version.sh)

# install amazon-linux-extras install
#RUN amazon-linux-extras install -y

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
    && export CHROME_DRIVER_VERSION=$(/workspace/lambda_layer/headless-chromium/chromedriver_version.sh)
    && sudo wget https://chromedriver.storage.googleapis.com/${CHROME_DRIVER_VERSION}/chromedriver_linux64.zip \
    && unzip ./chromedriver_linux64.zip \
    && ln -s /distfiles/chromedriver /usr/lib64/chromium-browser/chromedriver \
    && rm ./chromedriver_linux64.zip

# 開発環境なので、initは不要
# CMD ["/sbin/init"]

