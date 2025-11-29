#!/bin/bash

# Base URL
BASE_URL="http://localhost:8000/api"

# Test Data
NAME="John Doe"
ID_NUMBER="9001015009087"

echo "1. Registering User..."
curl -X POST "$BASE_URL/register" \
  -H "Content-Type: application/json" \
  -d "{\"name\": \"$NAME\", \"id_number\": \"$ID_NUMBER\"}"

echo -e "\n\n2. Logging in..."
curl -X POST "$BASE_URL/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=$ID_NUMBER&password=$ID_NUMBER"

echo -e "\n\nDone."
