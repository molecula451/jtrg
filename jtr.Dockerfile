FROM alpine:latest
MAINTAINER molecula451
VOLUME /golem/work /golem/output /golem/resource
RUN apk update
RUN apk add git make libressl-dev build-base zlib-dev yasm gmp-dev libpcap-dev libbz2 pkgconfig perl
WORKDIR /usr/src
RUN git clone https://github.com/openwall/john -b bleeding-jumbo
WORKDIR /usr/src/john/src
RUN ./configure && make -s clean && make -sj4
COPY ripper.sh /golem/entrypoints/ripper.sh
WORKDIR /golem/work
