#!/usr/bin/env bash

set -e

# #############################################################################
# Configuration
# #############################################################################

# Target image name
DST_IMAGE=p4-vscode-devel

# Directory for host SSH keys
SSH_KEY_DIR=~/docker/docker_ssh_keys

# Base image name and dockerfile
FROM_IMAGE=""
DOCKERFILE=Dockerfile.alma9

function usage() {
    echo "Usage: $0 [OPTION]..."
    echo "Build a container image for remote Visual Studio Code development"
    echo ""
    echo "Options:"
    echo "  -d, --dockerfile=FILE           Use the following dockerfile for build (default=$DOCKERFILE)"
    echo "  -k, --key-dir=DIR               Store generated SSH keys in DIR (default=${SSH_KEY_DIR})"
    echo "  -i, --image=NAME                Image name to generate (default=${DST_IMAGE})"
    echo "  -f, --from=IMAGE                Base image used for the build (default: almalinux:9 for Dockerfile.alma9, ubuntu:24.04 for Dockerfile.ubuntu)"
    echo "  -h, --help                      Display this help message"
}

# Generate a host SSH key
# Arguments:
# * msg - message
# * type - key type to generate
function create_key() {
    if [ $# -ne 2 ]; then
        echo "Two arguments are expected: msg keytype"
        exit 1
    fi

    # Parse arguments
    msg="$1"
    keytype="$2"
    file=$SSH_KEY_DIR/ssh_host_${keytype}_key

    # Generate keys
    echo "$msg"
    ssh-keygen -q -f "$file" -N '' -t "$keytype"
    ssh-keygen -l -f "$file.pub"
}

# Parse command line options
OPTIONS=$(getopt -o ":k:i:hf:d:" -l "key-dir:,image:,help,from:,dockerfile:" -- "$@")
if [ $? != 0 ] ; then
    echo "Error: invalid option(s)"
    echo ""
    usage
    exit 1
fi

eval set -- "$OPTIONS"

while true ; do
    case $1 in
        -k|--key-dir)
            SSH_KEY_DIR=$2
            shift
            ;;
        -i|--image)
            DST_IMAGE=$2
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        -f|--from)
            FROM_IMAGE=$2
            shift
            ;;
        -d|--dockerfile)
            DOCKERFILE=$2
            shift
            ;;
        --)
            shift
            break
            ;;
    esac
    shift
done

# Set default base image if not explicitly set
if [ -z "$FROM_IMAGE" ]; then
    if [[ "$DOCKERFILE" == *"ubuntu"* ]]; then
        FROM_IMAGE="ubuntu:24.04"
    elif [[ "$DOCKERFILE" == *"alma8"* ]]; then
        FROM_IMAGE="almalinux:8"
    else
        FROM_IMAGE="almalinux:9"
    fi
fi

# Detect container tool (docker or podman)
CONTAINER_TOOL=$(command -v docker 2>/dev/null || command -v podman 2>/dev/null || echo "docker")

# Copy everything into temporary directory
TMP_KEY_DIR=$(mktemp -p . -d)
trap 'rm -rf "$TMP_KEY_DIR"' EXIT

if [ -e "$HOME/.ssh/authorized_keys" ]; then
   echo "Copying current authorized keys..."
   cp "$HOME/.ssh/authorized_keys" "$TMP_KEY_DIR/authorized_keys"
else 
   echo "No authorized_keys was found; creating an empty one ..."
   echo "" > "$TMP_KEY_DIR/authorized_keys"
fi

# Generate SSH keys
if [ ! -d "$SSH_KEY_DIR" ] ; then
    echo "Creating host SSH keys..."
    mkdir -p "$SSH_KEY_DIR"
    create_key "Creating SSH2 RSA key; this may take some time ..." rsa
    create_key "Creating SSH2 DSA key; this may take some time ..." dsa
    create_key "Creating SSH2 ECDSA key; this may take some time ..." ecdsa
    create_key "Creating SSH2 ED25519 key; this may take some time ..." ed25519
fi

echo "Copying individual keys ..."
for key in rsa dsa ecdsa ed25519 ; do
    for ext in "" ".pub"  ; do
        cp -v "$SSH_KEY_DIR/ssh_host_${key}_key${ext}" "$TMP_KEY_DIR"
    done
done

# Image build
echo "Building container image using ${CONTAINER_TOOL} with base ${FROM_IMAGE} and dockerfile ${DOCKERFILE}..."
${CONTAINER_TOOL} build -f "${DOCKERFILE}" -t "${DST_IMAGE}" . \
    --build-arg USER="${USER}" \
    --build-arg GROUP="$(id -gn)" \
    --build-arg UID="$(id -u)" \
    --build-arg GID="$(id -g)" \
    --build-arg KEY_DIR="${TMP_KEY_DIR}" \
    --build-arg DOCKER_BASE_IMAGE="${FROM_IMAGE}"

echo "Build completed successfully."
exit 0
