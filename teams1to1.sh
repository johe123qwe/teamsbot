#!/bin/bash

url=$1
to=$2
subject=$3
body=${@:4}

curl -X 'POST' \
    "$url/api/send-message" \
    -H 'Content-Type: application/json' \
    -d "{
    \"message\": \"$subject\n$body\",
    \"user_id\": \"$to\"
}"