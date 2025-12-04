ARG BUILD_FROM=ghcr.io/hassio-addons/debian-base:9.1.0
# hadolint ignore=DL3006
FROM ${BUILD_FROM}

# Set shell
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Copy root filesystem
COPY rootfs /

# Setup base
ARG BUILD_ARCH=amd64
ARG AIRCAST_VERSION="1.9.3"
RUN \
    apt-get update \
    && apt-get install -y --no-install-recommends \
        unzip \
        python3 \
        python3-pip \
        python3-requests \
        ffmpeg \
        build-essential \
        git \
        autoconf \
        automake \
        libtool \
        libpopt-dev \
        libconfig-dev \
        libasound2-dev \
        libnss-mdns \
        libavahi-client-dev \
        libssl-dev \
        libsoxr-dev \
        libplist-dev \
        libsodium-dev \
        libavahi-compat-libdnssd-dev \
        libavformat-dev \
        libasound2-plugins \
        xxd \
    \
    && curl -J -L -o /tmp/airconnect.zip \
      "https://github.com/philippe44/AirConnect/releases/download/${AIRCAST_VERSION}/AirConnect-${AIRCAST_VERSION}.zip" \
    && unzip -d /tmp /tmp/airconnect.zip \
    \
    && if [ "${BUILD_ARCH}" = "aarch64" ]; then AIRCONNECT_ARCH="aarch64"; \
    elif [ "${BUILD_ARCH}" = "amd64" ]; then AIRCONNECT_ARCH="x86_64"; fi \
    \
    && cp "/tmp/aircast-linux-${AIRCONNECT_ARCH}-static" /usr/bin/aircast \
    && chmod a+x /usr/bin/aircast \
    \
    && git clone https://github.com/mikebrady/shairport-sync.git /tmp/shairport-sync \
    && cd /tmp/shairport-sync \
    && autoreconf -fi \
    && ./configure \
        --with-alsa \
        --with-avahi \
        --with-ssl=openssl \
        --with-soxr \
        --with-metadata \
        --with-stdout \
        --with-pipe \
        --sysconfdir=/etc \
    && make -j$(nproc) \
    && make install \
    \
    && chmod a+x /usr/bin/esphome-discovery.py \
    && chmod a+x /usr/bin/esphome-airplay-bridge.py \
    && chmod a+x /usr/bin/shairport-manager.py \
    && chmod a+x /usr/bin/shairport-play-handler.py \
    \
    && apt-get purge -y --auto-remove \
        unzip \
        build-essential \
        git \
        autoconf \
        automake \
        libtool \
        libpopt-dev \
        libconfig-dev \
        libasound2-dev \
        libavahi-client-dev \
        libssl-dev \
        libsoxr-dev \
        libplist-dev \
        libsodium-dev \
        libavahi-compat-libdnssd-dev \
        libavformat-dev \
    && apt-mark manual \
        ffmpeg \
        libnss-mdns \
        libasound2-plugins \
        python3 \
        python3-requests \
    && rm -fr \
        /tmp/* \
        /var/{cache,log}/* \
        /var/lib/apt/lists/*

# Build arguments
ARG BUILD_ARCH
ARG BUILD_DATE
ARG BUILD_DESCRIPTION
ARG BUILD_NAME
ARG BUILD_REF
ARG BUILD_REPOSITORY
ARG BUILD_VERSION

# Labels
LABEL \
    io.hass.name="${BUILD_NAME}" \
    io.hass.description="${BUILD_DESCRIPTION}" \
    io.hass.arch="${BUILD_ARCH}" \
    io.hass.type="addon" \
    io.hass.version=${BUILD_VERSION} \
    maintainer="Franck Nijhof <frenck@addons.community>" \
    org.opencontainers.image.title="${BUILD_NAME}" \
    org.opencontainers.image.description="${BUILD_DESCRIPTION}" \
    org.opencontainers.image.vendor="Home Assistant Community Add-ons" \
    org.opencontainers.image.authors="Franck Nijhof <frenck@addons.community>" \
    org.opencontainers.image.licenses="MIT" \
    org.opencontainers.image.url="https://addons.community" \
    org.opencontainers.image.source="https://github.com/${BUILD_REPOSITORY}" \
    org.opencontainers.image.documentation="https://github.com/${BUILD_REPOSITORY}/blob/main/README.md" \
    org.opencontainers.image.created=${BUILD_DATE} \
    org.opencontainers.image.revision=${BUILD_REF} \
    org.opencontainers.image.version=${BUILD_VERSION}
