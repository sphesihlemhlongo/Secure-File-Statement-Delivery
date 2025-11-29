#!/bin/bash

# Base URL
BASE_URL="http://localhost:8000/api"
TOKEN="<REPLACE_WITH_ACCESS_TOKEN>"

# Create a dummy PDF
echo "dummy pdf content" > test.pdf

echo "1. Uploading Document..."
curl -X POST "$BASE_URL/documents" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@test.pdf;type=application/pdf"

echo -e "\n\n2. Listing Documents..."
curl -X GET "$BASE_URL/documents" \
  -H "Authorization: Bearer $TOKEN"

# Cleanup
rm test.pdf
