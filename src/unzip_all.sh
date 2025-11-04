#!/bin/bash
# unzip_all.sh — unzip all .zip files and remove .zip files
set -e  # stop if any command fails
for zipfile in "$1"/*.zip; do
  echo "Unzipping: $zipfile"
  # Unzip into that directory
  if unzip -q "$zipfile" -d "$1"; then
    echo "Removing: $zipfile"
    rm "$zipfile"
  else
    echo "Failed to unzip $zipfile — keeping the archive."
  fi
done
