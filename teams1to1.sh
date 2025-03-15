#!/bin/bash

# 给个人发消息
# 给机器人，发送 myid 获取对话 ID
# 使用方法:
# bash teams1to1.sh https://xxx.xyz ID subject content

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