#!/bin/bash

# 给群组发消息
# 在群组内@机器人，发送 convid 获取对话 ID
# 使用方法:
# bash teams-group.sh https://xxx.xyz ID subject content

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