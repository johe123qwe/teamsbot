# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import logging
from typing import Dict, Optional

from botbuilder.core import ActivityHandler, TurnContext
from botbuilder.schema import ChannelAccount, ConversationReference, Activity
from .redis_storage import RedisConversationReferences

logger = logging.getLogger(__name__)


class ProactiveBot(ActivityHandler):
    def __init__(self, redis_host: str = "localhost", redis_port: str = "6378", 
                 redis_db: str = "1", redis_password: Optional[str] = None):
        """
        初始化机器人
        
        Args:
            redis_host: Redis服务器地址
            redis_port: Redis端口
            redis_db: Redis数据库编号
            redis_password: Redis密码（可选）
            json_backup_file: JSON备份文件路径
        """
        try:
            self.redis_storage = RedisConversationReferences(
                redis_host=redis_host,
                redis_port=redis_port,
                redis_db=redis_db,
                redis_password=redis_password
            )
            print(redis_password, redis_db, redis_host, redis_port, 34)

            # 如果是首次启动，尝试从JSON文件迁移数据
            # self.redis_storage.migrate_from_json(json_backup_file)
            
            # logger.info("ProactiveBot initialized with Redis storage")
            
        except Exception as e:
            logger.error(f"Failed to initialize Redis storage: {e}")
            raise
    
    def migrate_from_json_job(self, json_backup_file):
        print('45, migrating from JSON...')
        self.redis_storage.migrate_from_json(json_backup_file)
        logger.info("ProactiveBot initialized with Redis storage")

    async def on_conversation_update_activity(self, turn_context: TurnContext):
        self._add_conversation_reference(turn_context.activity)
        return await super().on_conversation_update_activity(turn_context)

    async def on_members_added_activity(
        self, members_added: [ChannelAccount], turn_context: TurnContext
    ):
        for member in members_added:
            if member.id != turn_context.activity.recipient.id:
                await turn_context.send_activity(
                    "Welcome to the group!"
                )

    async def on_message_activity(self, turn_context: TurnContext):
        self._add_conversation_reference(turn_context.activity)
        
        message_text = turn_context.activity.text.strip().lower()
        
        # 检查消息内容是否为 "myid"
        if message_text == "myid" or "myid" in message_text:
            user_id = turn_context.activity.from_property.id
            await turn_context.send_activity(f"Your ID is: {user_id}")
        
        # 检查消息内容是否为 "convid"
        elif message_text == "convid" or "convid" in message_text:
            conversation_id = turn_context.activity.conversation.id
            await turn_context.send_activity(f"Your Conversation ID is: {conversation_id}")
        
        # 检查消息内容是否为 "myname"
        elif message_text == "myname" or "myname" in message_text:
            user_name = turn_context.activity.from_property.name
            await turn_context.send_activity(f"Your Name is: {user_name}")
        
        # 新增：检查Redis状态
        elif message_text == "redis" or "redis" in message_text:
            redis_info = self.redis_storage.get_connection_info()
            info_text = f"Redis Info: {redis_info}"
            await turn_context.send_activity(info_text)
        
        # 新增：显示所有对话引用数量
        elif message_text == "count" or "count" in message_text:
            references = self.redis_storage.get_all_conversation_references()
            await turn_context.send_activity(f"Total conversation references: {len(references)}")
        
        else:
            await turn_context.send_activity(f"You sent: {turn_context.activity.text}")

    def _add_conversation_reference(self, activity: Activity):
        """
        添加对话引用到Redis存储
        """
        try:
            conversation_reference = TurnContext.get_conversation_reference(activity)
            conversation_id = conversation_reference.conversation.id
            
            self.redis_storage.add_conversation_reference(conversation_id, conversation_reference)
            logger.debug(f"Added conversation reference for {conversation_id}")
            
        except Exception as e:
            logger.error(f"Failed to add conversation reference: {e}")

    def get_conversation_references(self) -> Dict[str, ConversationReference]:
        """
        获取所有对话引用
        """
        try:
            return self.redis_storage.get_all_conversation_references()
        except Exception as e:
            logger.error(f"Failed to get conversation references: {e}")
            return {}

    def get_conversation_reference(self, conversation_id: str) -> Optional[ConversationReference]:
        """
        获取特定对话引用
        """
        try:
            return self.redis_storage.get_conversation_reference(conversation_id)
        except Exception as e:
            logger.error(f"Failed to get conversation reference for {conversation_id}: {e}")
            return None

    def print_all_conversation_references(self):
        """
        打印所有用户的 ConversationReference 记录
        """
        try:
            references = self.redis_storage.get_all_conversation_references()
            
            if not references:
                print("No conversation references found.")
                return
            
            print(f"Found {len(references)} conversation references:")
            print("=" * 50)
            
            for conversation_id, reference in references.items():
                print(f"Conversation ID: {conversation_id}")
                print(f"Service URL: {reference.service_url}")
                print(f"Channel ID: {reference.channel_id}")
                print(f"User ID: {reference.user.id if reference.user else 'N/A'}")
                print(f"User Name: {reference.user.name if reference.user else 'N/A'}")
                print(f"Bot ID: {reference.bot.id if reference.bot else 'N/A'}")
                print(f"Bot Name: {reference.bot.name if reference.bot else 'N/A'}")
                print(f"Is Group: {reference.conversation.is_group if reference.conversation else 'N/A'}")
                print("-" * 40)
                
        except Exception as e:
            logger.error(f"Failed to print conversation references: {e}")

    def export_to_json(self, file_path: str = "conversation_references_backup.json"):
        """
        导出对话引用到JSON文件作为备份
        """
        try:
            self.redis_storage.export_to_json(file_path)
            logger.info(f"Conversation references exported to {file_path}")
        except Exception as e:
            logger.error(f"Failed to export to JSON: {e}")

    def clear_all_references(self):
        """
        清空所有对话引用（谨慎使用）
        """
        try:
            self.redis_storage.clear_all_references()
            logger.info("All conversation references cleared")
        except Exception as e:
            logger.error(f"Failed to clear references: {e}")