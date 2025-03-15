#!/bin/bash

url=$1
to=$2
subject=$3
body=${@:4}

curl -X 'POST' \
    "$url/api/send-by-convid" \
    -H 'Content-Type: application/json' \
    -d "{
    \"message\": \"$subject\n$body\",
    \"conversation_id\": \"$to\"
}"