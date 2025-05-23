# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import sys
import traceback
import uuid
from datetime import datetime
from http import HTTPStatus
from typing import Dict

from aiohttp import web
from aiohttp.web import Request, Response, json_response
from botbuilder.core import (
    TurnContext,
)
from botbuilder.core.integration import aiohttp_error_middleware
from botbuilder.integration.aiohttp import CloudAdapter, ConfigurationBotFrameworkAuthentication
from botbuilder.schema import Activity, ActivityTypes, ConversationReference, Attachment
from botbuilder.core import MessageFactory

from bots import ProactiveBot
from config import DefaultConfig

CONFIG = DefaultConfig()

# Create adapter.
# See https://aka.ms/about-bot-adapter to learn more about how bots work.
ADAPTER = CloudAdapter(ConfigurationBotFrameworkAuthentication(CONFIG))

# Catch-all for errors.
import sys
import traceback
from botbuilder.schema import ErrorResponseException

# ...existing code...

async def on_error(context: TurnContext, error: Exception):
    # 检查是否是 Bot 不在对话列表中的错误
    if isinstance(error, ErrorResponseException) and "BotNotInConversationRoster" in str(error):
        print("Bot is not part of the conversation roster. The bot may have been removed from the team/chat.", 
              file=sys.stderr)
        return
    
    # 其他错误的处理
    print(f"\n [on_turn_error] unhandled error: {error}", file=sys.stderr)
    traceback.print_exc()

    try:
        # 尝试发送错误消息
        await context.send_activity("The bot encountered an error or bug.")
        await context.send_activity(
            "To continue to run this bot, please fix the bot source code."
        )
        
        # Send a trace activity if we're talking to the Bot Framework Emulator
        if context.activity.channel_id == "emulator":
            trace_activity = Activity(
                label="TurnError",
                name="on_turn_error Trace",
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                type=ActivityTypes.trace,
                value=f"{error}",
                value_type="https://www.botframework.com/schemas/error",
            )
            await context.send_activity(trace_activity)
    except Exception as send_error:
        print(f"Failed to send error message: {send_error}", file=sys.stderr)

ADAPTER.on_turn_error = on_error

# Create a shared dictionary.  The Bot will add conversation references when users
# join the conversation and send messages.
CONVERSATION_REFERENCES: Dict[str, ConversationReference] = dict()

# If the channel is the Emulator, and authentication is not in use, the AppId will be null.
# We generate a random AppId for this case only. This is not required for production, since
# the AppId will have a value.
APP_ID = CONFIG.APP_ID if CONFIG.APP_ID else uuid.uuid4()

# Create the Bot
BOT = ProactiveBot(CONVERSATION_REFERENCES)


# Listen for incoming requests on /api/messages.
async def messages(req: Request) -> Response:
    return await ADAPTER.process(req, BOT)


# Listen for requests on /api/notify, and send a messages to all conversation members.
async def notify(req: Request) -> Response:  # pylint: disable=unused-argument
    await _send_proactive_message()
    return Response(status=HTTPStatus.OK, text="Proactive messages have been sent")

# 新增 /api/notify_custom 路由，通过 POST 请求传入自定义消息和用户ID，并发送给特定用户
async def notify_custom(req: Request) -> Response:
    try:
        # 期望请求体为 JSON 格式，且包含 "message" 和 "user_id" 字段
        data = await req.json()
        message = data.get("message", None)
        user_id = data.get("user_id", None)
        if not message or not user_id:
            return json_response({"error": "Missing 'message' or 'user_id' in request payload."}, status=400)
    except Exception as e:
        return json_response({"error": f"Invalid JSON payload: {e}"}, status=400)
    
    # 检查用户ID是否存在于会话引用中
    if user_id not in CONVERSATION_REFERENCES:
        return json_response({"error": f"No conversation reference found for user {user_id}"}, status=404)
    
    await _send_proactive_message_custom(message, user_id)
    now = datetime.now()
    print(now, message, user_id, 95)
    return Response(status=HTTPStatus.OK, text=f"Proactive message sent to user {user_id}: {message}")

# 内部方法：发送自定义主动消息给特定用户
async def _send_proactive_message_custom(message: str, user_id: str):
    conversation_reference = CONVERSATION_REFERENCES.get(user_id)

    # 处理消息，分割成行
    lines = message.replace("<br />", "\n").replace("<p>", "").replace("</p>", "\n")
    paragraphs = lines.split("\n")
    paragraphs = [p for p in paragraphs if p.strip()]  # 移除空行
    
    # 创建 Adaptive Card
    card_content = {
        "type": "AdaptiveCard",
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "version": "1.3",
        "body": []
    }
    
    # 为每个段落添加一个TextBlock
    for paragraph in paragraphs:
        card_content["body"].append({
            "type": "TextBlock",
            "text": paragraph,
            "wrap": True,
            "separator": True
        })
    

    attachment = Attachment(
        content_type="application/vnd.microsoft.card.adaptive",
        content=card_content
    )
    
    await ADAPTER.continue_conversation(
        conversation_reference,
        lambda turn_context: turn_context.send_activity(MessageFactory.attachment(attachment)),
        APP_ID,
    )

# Send a message to all conversation members.
# This uses the shared Dictionary that the Bot adds conversation references to.
async def _send_proactive_message():
    for conversation_reference in CONVERSATION_REFERENCES.values():
        await ADAPTER.continue_conversation(
            conversation_reference,
            lambda turn_context: turn_context.send_activity("proactive hello2342424"),
            APP_ID,
        )

# 新增 /api/send-message-by-conversation-id 路由，通过 POST 请求传入消息和 Conversation ID，并发送给特定对话
async def send_message_by_conversation_id(req: Request) -> Response:
    try:
        # 期望请求体为 JSON 格式，且包含 "message" 和 "conversation_id" 字段
        data = await req.json()
        message = data.get("message", None)
        conversation_id = data.get("conversation_id", None)
        if not message or not conversation_id:
            return json_response({"error": "Missing 'message' or 'conversation_id' in request payload."}, status=400)
    except Exception as e:
        return json_response({"error": f"Invalid JSON payload: {e}"}, status=400)
    
    # 检查会话ID是否存在于会话引用中
    if conversation_id not in CONVERSATION_REFERENCES:
        return json_response({"error": f"No conversation reference found for conversation ID {conversation_id}"}, status=404)
    
    await _send_message_by_conversation_id(message, conversation_id)
    now = datetime.now()
    print(now, message, conversation_id, 133)
    return Response(status=HTTPStatus.OK, text=f"Message sent to conversation {conversation_id}: {message}")

# 内部方法：通过 Conversation ID 发送消息

async def _send_message_by_conversation_id(message: str, conversation_id: str):
    print(f"Attempting to send message to Conversation ID: {conversation_id}")
    conversation_reference = CONVERSATION_REFERENCES.get(conversation_id)
    
    # 处理消息，分割成行
    lines = message.replace("<br />", "\n").replace("<p>", "").replace("</p>", "\n")
    paragraphs = lines.split("\n")
    paragraphs = [p for p in paragraphs if p.strip()]  # 移除空行
    
    # 创建 Adaptive Card
    card_content = {
        "type": "AdaptiveCard",
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "version": "1.3",
        "body": []
    }
    
    # 为每个段落添加一个TextBlock
    for paragraph in paragraphs:
        card_content["body"].append({
            "type": "TextBlock",
            "text": paragraph,
            "wrap": True,
            "separator": True
        })
    

    attachment = Attachment(
        content_type="application/vnd.microsoft.card.adaptive",
        content=card_content
    )
    
    await ADAPTER.continue_conversation(
        conversation_reference,
        lambda turn_context: turn_context.send_activity(MessageFactory.attachment(attachment)),
        APP_ID,
    )

APP = web.Application(middlewares=[aiohttp_error_middleware])
APP.router.add_post("/api/messages", messages)
APP.router.add_get("/api/notify", notify)
APP.router.add_post("/api/send-message", notify_custom)
APP.router.add_post("/api/send-by-convid", send_message_by_conversation_id)

if __name__ == "__main__":
    try:
        web.run_app(APP, host="127.0.0.1", port=CONFIG.PORT)
    except Exception as error:
        raise error
