#!/bin/sh
# Собирает manifest.json для офлайн-пакета переноса в закрытый контур.
set -eu

TAG="$1"
COMMIT="$2"
IMAGE_REPO="$3"
IMAGE_DIGEST="$4"
BUNDLE_PATH="$5"

BUNDLE_SHA256=$(sha256sum "$BUNDLE_PATH" | awk '{print $1}')
BUNDLE_NAME=$(basename "$BUNDLE_PATH")
CREATED_AT=$(date -u +%Y-%m-%dT%H:%M:%SZ)

jq -n \
  --arg version "$TAG" \
  --arg created_at "$CREATED_AT" \
  --arg source_commit "$COMMIT" \
  --arg image_repo "$IMAGE_REPO" \
  --arg image_digest "$IMAGE_DIGEST" \
  --arg bundle_file "$BUNDLE_NAME" \
  --arg bundle_sha256 "$BUNDLE_SHA256" \
  '{
    package_version: $version,
    created_at: $created_at,
    source_commit: $source_commit,
    backend_image: {
      repository: $image_repo,
      digest: $image_digest
    },
    git_bundle: {
      file: $bundle_file,
      sha256: $bundle_sha256
    }
  }'
