#!/usr/bin/env bash

set -e

ROOT_INSTALL_PATH=${ROOT_INSTALL_PATH:-"/usr"}
PANDOC_URL=https://github.com/jgm/pandoc/releases/download/3.7.0.2/pandoc-3.7.0.2-linux-amd64.tar.gz
DOWNLOAD_PATH=/tmp/pandoc.tar.gz

echo "Install pandoc ..."
echo " * ROOT_INSTALL_PATH = ${ROOT_INSTALL_PATH}"
echo " * PANDOC_URL = ${PANDOC_URL}"
echo " * DOWNLOAD_PATH = ${DOWNLOAD_PATH}"

wget -O "$DOWNLOAD_PATH" "$PANDOC_URL"
tar -xvzf "$DOWNLOAD_PATH" --strip-components 1 -C "$ROOT_INSTALL_PATH"
rm -f "$DOWNLOAD_PATH"
