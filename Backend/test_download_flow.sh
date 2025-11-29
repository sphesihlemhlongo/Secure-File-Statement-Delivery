#!/bin/bash

# Base URL
BASE_URL="http://localhost:8000/api"
TOKEN="<REPLACE_WITH_ACCESS_TOKEN>"

# 1. List documents to get an ID
echo "1. Listing Documents..."
DOCS=$(curl -s -X GET "$BASE_URL/documents" -H "Authorization: Bearer $TOKEN")
echo $DOCS

# Extract first doc ID (requires jq, or manual copy-paste)
# For this script, we'll just ask user to input it if we can't parse it easily in bash without deps.
# But let's assume the user will replace it.
DOC_ID="<REPLACE_WITH_DOC_ID>"

echo -e "\n\n2. Requesting Download Token for Doc ID: $DOC_ID"
RESP=$(curl -s -X POST "$BASE_URL/documents/$DOC_ID/token" \
  -H "Authorization: Bearer $TOKEN")
echo $RESP

# Extract token (manual step for user in this example script)
DOWNLOAD_TOKEN="<REPLACE_WITH_DOWNLOAD_TOKEN>"

echo -e "\n\n3. Downloading File..."
curl -v -X GET "$BASE_URL/download?token=$DOWNLOAD_TOKEN" \
  --output downloaded_file.pdf

echo -e "\n\nDone. Check downloaded_file.pdf"
