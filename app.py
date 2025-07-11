# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import traceback
import uuid
import logging
import functools
from datetime import datetime
from http import HTTPStatus

from aiohttp import web
from aiohttp.web import Request, Response, json_response
from botbuilder.core import TurnContext
from botbuilder.core.integration import aiohttp_error_middleware
from botbuilder.integration.aiohttp import CloudAdapter, ConfigurationBotFrameworkAuthentication
from botbuilder.schema import Activity, ActivityTypes, ConversationReference, Attachment, ErrorResponseException
from botbuilder.core import MessageFactory

from bots import ProactiveBot
from config import DefaultConfig

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

CONFIG = DefaultConfig()

API_KEY = CONFIG.API_KEY

# Create adapter.
ADAPTER = CloudAdapter(ConfigurationBotFrameworkAuthentication(CONFIG))

# 添加认证装饰器
def require_api_key(func):
    @functools.wraps(func)
    async def wrapper(req: Request) -> Response:
        # 支持多种认证方式
        # 1. 检查 X-API-Key header
        api_key = req.headers.get("X-API-Key")
        
        # 2. 检查 Authorization header (Bearer token)
        if not api_key:
            auth_header = req.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                api_key = auth_header[7:]  # 移除 "Bearer " 前缀
        
        # 3. 检查查询参数
        if not api_key:
            api_key = req.query.get("api_key")
        
        # 验证 API Key
        if not api_key:
            logger.warning(f"Unauthorized access attempt to {req.path} - No API key provided")
            return json_response(
                {"error": "Unauthorized: API key is required"}, 
                status=401
            )
        
        if api_key != API_KEY:
            logger.warning(f"Unauthorized access attempt to {req.path} - Invalid API key")
            return json_response(
                {"error": "Unauthorized: Invalid API key"}, 
                status=401
            )
        
        logger.info(f"Authorized access to {req.path}")
        return await func(req)
    return wrapper


# Error handler
async def on_error(context: TurnContext, error: Exception):
    # 检查是否是 Bot 不在对话列表中的错误
    if isinstance(error, ErrorResponseException) and "BotNotInConversationRoster" in str(error):
        logger.warning("Bot is not part of the conversation roster. The bot may have been removed from the team/chat.")
        return
    
    # 其他错误的处理
    logger.error(f"Unhandled error: {error}")
    traceback.print_exc()

    try:
        # 尝试发送错误消息
        await context.send_activity("The bot encountered an error or bug.")
        await context.send_activity("To continue to run this bot, please fix the bot source code.")
        
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
        logger.error(f"Failed to send error message: {send_error}")

ADAPTER.on_turn_error = on_error

# App ID
APP_ID = CONFIG.APP_ID if CONFIG.APP_ID else uuid.uuid4()

# 创建机器人实例，配置Redis连接信息
try:
    BOT = ProactiveBot(
        redis_host=CONFIG.REDIS_HOST,
        redis_port=CONFIG.REDIS_PORT,
        redis_db=CONFIG.REDIS_DB,
        redis_password=CONFIG.REDIS_PASSWORD
    )
    logger.info("Bot initialized successfully with Redis storage")
except Exception as e:
    logger.error(f"Failed to initialize bot: {e}")
    raise

# Listen for incoming requests on /api/messages.
async def messages(req: Request) -> Response:
    return await ADAPTER.process(req, BOT)

# Listen for requests on /api/notify, and send a messages to all conversation members.
async def notify(req: Request) -> Response:
    await _send_proactive_message()
    return Response(status=HTTPStatus.OK, text="Proactive messages have been sent")

# 发送自定义消息给特定用户
async def notify_custom(req: Request) -> Response:
    try:
        data = await req.json()
        message = data.get("message", None)
        user_id = data.get("user_id", None)
        
        if not message or not user_id:
            return json_response({"error": "Missing 'message' or 'user_id' in request payload."}, status=400)
    except Exception as e:
        return json_response({"error": f"Invalid JSON payload: {e}"}, status=400)
    
    # 从Redis获取对话引用
    conversation_reference = BOT.get_conversation_reference(user_id)
    if not conversation_reference:
        return json_response({"error": f"No conversation reference found for user {user_id}"}, status=404)
    
    await _send_proactive_message_custom(message, conversation_reference)
    logger.info(f"Proactive message sent to user {user_id}: {message}")
    return Response(status=HTTPStatus.OK, text=f"Proactive message sent to user {user_id}: {message}")

# 通过对话ID发送消息
async def send_message_by_conversation_id(req: Request) -> Response:
    try:
        data = await req.json()
        message = data.get("message", None)
        conversation_id = data.get("conversation_id", None)
        
        if not message or not conversation_id:
            return json_response({"error": "Missing 'message' or 'conversation_id' in request payload."}, status=400)
    except Exception as e:
        return json_response({"error": f"Invalid JSON payload: {e}"}, status=400)
    
    # 从Redis获取对话引用
    conversation_reference = BOT.get_conversation_reference(conversation_id)
    if not conversation_reference:
        return json_response({"error": f"No conversation reference found for conversation ID {conversation_id}"}, status=404)
    
    await _send_message_by_conversation_id(message, conversation_reference)
    logger.info(f"Message sent to conversation {conversation_id}: {message}")
    return Response(status=HTTPStatus.OK, text=f"Message sent to conversation {conversation_id}: {message}")

# 新增：获取所有对话引用的API
@require_api_key
async def get_all_references(req: Request) -> Response:
    try:
        references = BOT.get_conversation_references()
        
        # 转换为可JSON序列化的格式
        serialized_refs = {}
        for conv_id, ref in references.items():
            serialized_refs[conv_id] = {
                "conversation_id": conv_id,
                "user_id": ref.user.id if ref.user else None,
                "user_name": ref.user.name if ref.user else None,
                "channel_id": ref.channel_id,
                "service_url": ref.service_url,
                "is_group": ref.conversation.is_group if ref.conversation else None,
                "bot_name": ref.bot.name if ref.bot else None
            }
        
        return json_response({
            "total_count": len(references),
            "references": serialized_refs
        })
    except Exception as e:
        logger.error(f"Failed to get references: {e}")
        return json_response({"error": f"Failed to get references: {e}"}, status=500)

# 新增：导出数据到JSON的API
@require_api_key
async def export_to_json(req: Request) -> Response:
    try:
        filename = f"conversation_references_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        BOT.export_to_json(filename)
        return json_response({"message": f"Data exported to {filename}"})
    except Exception as e:
        logger.error(f"Failed to export: {e}")
        return json_response({"error": f"Failed to export: {e}"}, status=500)

@require_api_key
async def migrate(req: Request) -> Response:
    try:
        BOT.migrate_from_json_job("conversation_references.json")
        return json_response({"message": "Data migrated from JSON successfully."})
    except Exception as e:
        logger.error(f"Failed to migrate from JSON: {e}")
        return json_response({"error": f"Failed to migrate from JSON: {e}"}, status=500)

# 新增：获取Redis状态的API
@require_api_key
async def redis_status(req: Request) -> Response:
    try:
        redis_info = BOT.redis_storage.get_connection_info()
        return json_response(redis_info)
    except Exception as e:
        logger.error(f"Failed to get Redis status: {e}")
        return json_response({"error": f"Failed to get Redis status: {e}"}, status=500)

# 内部方法：发送自定义主动消息
async def _send_proactive_message_custom(message: str, conversation_reference: ConversationReference):
    # 处理消息格式
    lines = message.replace("<br />", "\n").replace("<p>", "").replace("</p>", "\n")
    paragraphs = lines.split("\n")
    paragraphs = [p.strip() for p in paragraphs if p.strip()]  # 移除空行
    
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

# 内部方法：通过对话ID发送消息
async def _send_message_by_conversation_id(message: str, conversation_reference: ConversationReference):
    # 处理消息格式
    lines = message.replace("<br />", "\n").replace("<p>", "").replace("</p>", "\n")
    paragraphs = lines.split("\n")
    paragraphs = [p.strip() for p in paragraphs if p.strip()]  # 移除空行
    
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

# 发送消息给所有对话成员
async def _send_proactive_message():
    try:
        references = BOT.get_conversation_references()
        
        for conversation_reference in references.values():
            await ADAPTER.continue_conversation(
                conversation_reference,
                lambda turn_context: turn_context.send_activity("proactive hello from Redis storage!"),
                APP_ID,
            )
        
        logger.info(f"Sent proactive message to {len(references)} conversations")
    except Exception as e:
        logger.error(f"Failed to send proactive messages: {e}")

# 设置路由
APP = web.Application(middlewares=[aiohttp_error_middleware])
APP.router.add_post("/api/messages", messages)
APP.router.add_get("/api/notify", notify)
APP.router.add_post("/api/send-message", notify_custom)
APP.router.add_post("/api/send-by-convid", send_message_by_conversation_id)
APP.router.add_get("/api/references", get_all_references)
APP.router.add_get("/api/export", export_to_json)
APP.router.add_get("/api/redis-status", redis_status)
APP.router.add_get("/api/migrate-from-json", migrate)

if __name__ == "__main__":
    try:
        logger.info(f"Starting bot server on port {CONFIG.PORT}")
        web.run_app(APP, host="127.0.0.1", port=CONFIG.PORT)
    except Exception as error:
        logger.error(f"Failed to start server: {error}")
        raise error