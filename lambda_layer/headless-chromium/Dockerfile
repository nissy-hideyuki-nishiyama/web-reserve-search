#
# Build with:
# docker build --compress -t adieuadieu/chromium-for-amazonlinux-base:62.0.3202.62 --build-arg VERSION=62.0.3202.62 .
#
# Jump into the container with:
# docker run -i -t --rm --entrypoint /bin/bash  adieuadieu/chromium-for-amazonlinux-base
#
# Launch headless Chromium with:
# docker run -d --rm --name headless-chromium -p 9222:9222 adieuadieu/headless-chromium-for-aws-lambda
#

#FROM headless-chrome:${VERSION}
#FROM headless-chromium:${VERSION}
#FROM headless-chromium:86.0.4240.111
FROM headless-chromium:90.0.4430.72
ARG VERSION
ENV VERSION ${VERSION:-master}

WORKDIR /

#RUN amazon-linux-extras install epel && \
#  yum update && \
#  echo "install epel-release repo."

#RUN yum install -y chromium chromium-common
RUN yum install -y awscli
RUN mkdir -p /root/.aws

ADD build.sh /
COPY aws /root/.aws

# copy aws user's credentials
#ADD ${HOME}/.aws ${HOME}/
#COPY .aws ${HOME}/

# build distfile.zip
RUN sh /build.sh
