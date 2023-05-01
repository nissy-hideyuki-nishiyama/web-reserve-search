FROM amazonlinux:2023

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
    && export CHROME_DRIVER_VERSION=$(/workspace/lambda_layer/headless-chromium/chromedriver_version.sh)
    && sudo wget https://chromedriver.storage.googleapis.com/${CHROME_DRIVER_VERSION}/chromedriver_linux64.zip \
    && sudo dnf install -y ./google-chrome-stable_current_x86_64.rpm \
    && sudo mkdir -p /usr/lib64/chromium-browser \
    && sudo ln -s /usr/bin/google-chrome-stable /usr/lib64/chromium-browser/google-chrome-stable \
    && sudo ln -s /usr/bin/google-chrome-stable /usr/lib64/chromium-browser/headless_shell \
    && rm ./google-chrome-stable_current_x86_64.rpm

# install chromedriver
RUN cd /distfiles \
    && sudo wget https://chromedriver.storage.googleapis.com/112.0.5615.49/chromedriver_linux64.zip \
    && unzip ./chromedriver_linux64.zip \
    && ln -s /distfiles/chromedriver /usr/lib64/chromium-browser/chromedriver \
    && rm ./chromedriver_linux64.zip

# init
CMD ["/sbin/init"]
