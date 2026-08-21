#!/usr/bin/env bash
set -euo pipefail

# Usage: check_image_size.sh [IMAGE_TAG]
# Default image tag: interview-agent-api:ci
#
# Max image size: 650 MB = 650 * 1024 * 1024 bytes
MAX_SIZE_BYTES=681574400

IMAGE="${1:-interview-agent-api:ci}"

SIZE_BYTES="$(docker image inspect --format='{{.Size}}' "$IMAGE")"

if (( SIZE_BYTES > MAX_SIZE_BYTES )); then
  SIZE_MB="$(awk "BEGIN {printf \"%.2f\", ${SIZE_BYTES} / (1024 * 1024)}")"
  MAX_MB="$(awk "BEGIN {printf \"%.2f\", ${MAX_SIZE_BYTES} / (1024 * 1024)}")"
  echo "ERROR: Docker image '${IMAGE}' exceeds size limit: ${SIZE_BYTES} bytes (${SIZE_MB} MB) > ${MAX_SIZE_BYTES} bytes (${MAX_MB} MB max)" >&2
  exit 1
fi

SIZE_MB="$(awk "BEGIN {printf \"%.2f\", ${SIZE_BYTES} / (1024 * 1024)}")"
echo "OK: Docker image '${IMAGE}' size ${SIZE_BYTES} bytes (${SIZE_MB} MB) is within ${MAX_SIZE_BYTES} bytes (650 MB) limit"
