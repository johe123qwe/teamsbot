import redis
import json
import logging
from typing import Dict, Optional
from botbuilder.schema import ConversationReference, ChannelAccount, ConversationAccount

logger = logging.getLogger(__name__)

class RedisConversationReferences:
    """Redis存储管理类，用于存储和管理对话引用"""
    
    def __init__(self, redis_host: str = "localhost", redis_port: int = 6379, 
                 redis_db: int = 0, redis_password: Optional[str] = None,
                 key_prefix: str = "bot_conv_ref:"):
        """
        初始化Redis连接
        
        Args:
            redis_host: Redis服务器地址
            redis_port: Redis端口
            redis_db: Redis数据库编号
            redis_password: Redis密码（可选）
            key_prefix: Redis键前缀
        """
        self.redis_client = redis.Redis(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            password=redis_password,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True
        )
        self.key_prefix = key_prefix
        
        # 测试连接
        try:
            self.redis_client.ping()
            logger.info("Redis connection established successfully")
        except redis.ConnectionError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    def _get_key(self, conversation_id: str) -> str:
        """生成Redis键名"""
        return f"{self.key_prefix}{conversation_id}"
    
    def add_conversation_reference(self, conversation_id: str, reference: ConversationReference):
        """添加或更新对话引用"""
        try:
            key = self._get_key(conversation_id)
            serialized_ref = self._serialize_conversation_reference(reference)
            self.redis_client.hset(key, mapping=serialized_ref)
            logger.debug(f"Added conversation reference for {conversation_id}")
        except Exception as e:
            logger.error(f"Failed to add conversation reference: {e}")
            raise
    
    def get_conversation_reference(self, conversation_id: str) -> Optional[ConversationReference]:
        """获取对话引用"""
        try:
            key = self._get_key(conversation_id)
            data = self.redis_client.hgetall(key)
            if not data:
                return None
            
            return self._deserialize_conversation_reference(data)
        except Exception as e:
            logger.error(f"Failed to get conversation reference: {e}")
            return None
    
    def get_all_conversation_references(self) -> Dict[str, ConversationReference]:
        """获取所有对话引用"""
        try:
            pattern = f"{self.key_prefix}*"
            keys = self.redis_client.keys(pattern)
            references = {}
            
            for key in keys:
                conversation_id = key.replace(self.key_prefix, "")
                data = self.redis_client.hgetall(key)
                if data:
                    references[conversation_id] = self._deserialize_conversation_reference(data)
            
            return references
        except Exception as e:
            logger.error(f"Failed to get all conversation references: {e}")
            return {}
    
    def remove_conversation_reference(self, conversation_id: str):
        """删除对话引用"""
        try:
            key = self._get_key(conversation_id)
            self.redis_client.delete(key)
            logger.debug(f"Removed conversation reference for {conversation_id}")
        except Exception as e:
            logger.error(f"Failed to remove conversation reference: {e}")
            raise
    
    def clear_all_references(self):
        """清空所有对话引用"""
        try:
            pattern = f"{self.key_prefix}*"
            keys = self.redis_client.keys(pattern)
            if keys:
                self.redis_client.delete(*keys)
            logger.info("Cleared all conversation references")
        except Exception as e:
            logger.error(f"Failed to clear all references: {e}")
            raise
    
    def _serialize_conversation_reference(self, reference: ConversationReference) -> dict:
        """序列化对话引用为字典"""
        return {
            "activity_id": reference.activity_id or "",
            "bot_id": reference.bot.id if reference.bot else "",
            "bot_name": reference.bot.name if reference.bot else "",
            "channel_id": reference.channel_id or "",
            "conversation_id": reference.conversation.id if reference.conversation else "",
            "conversation_is_group": str(reference.conversation.is_group) if reference.conversation and reference.conversation.is_group is not None else "",
            "service_url": reference.service_url or "",
            "user_id": reference.user.id if reference.user else "",
            "user_name": reference.user.name if reference.user else "",
        }
    
    def _deserialize_conversation_reference(self, data: dict) -> ConversationReference:
        """反序列化字典为对话引用"""
        bot = ChannelAccount(
            id=data.get("bot_id", ""),
            name=data.get("bot_name", "")
        )
        
        conversation = ConversationAccount(
            id=data.get("conversation_id", ""),
            is_group=data.get("conversation_is_group", "").lower() == "true" if data.get("conversation_is_group") else None
        )
        
        user = ChannelAccount(
            id=data.get("user_id", ""),
            name=data.get("user_name", "")
        )
        
        return ConversationReference(
            activity_id=data.get("activity_id") or None,
            bot=bot,
            channel_id=data.get("channel_id"),
            conversation=conversation,
            service_url=data.get("service_url"),
            user=user
        )
    
    def migrate_from_json(self, json_file_path: str):
        """从JSON文件迁移数据到Redis"""
        try:
            with open(json_file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
            
            for conversation_id, reference_data in data.items():
                # 重构引用数据
                reference = ConversationReference(
                    activity_id=reference_data.get("activity_id"),
                    bot=ChannelAccount(**reference_data.get("bot", {})),
                    channel_id=reference_data.get("channel_id"),
                    conversation=ConversationAccount(**reference_data.get("conversation", {})),
                    service_url=reference_data.get("service_url"),
                    user=ChannelAccount(**reference_data.get("user", {}))
                )
                
                self.add_conversation_reference(conversation_id, reference)
            
            logger.info(f"Successfully migrated {len(data)} conversation references from JSON to Redis")
            
        except FileNotFoundError:
            logger.warning(f"JSON file {json_file_path} not found, skipping migration")
        except Exception as e:
            logger.error(f"Failed to migrate from JSON: {e}")
            raise
    
    def export_to_json(self, json_file_path: str):
        """导出Redis数据到JSON文件"""
        try:
            references = self.get_all_conversation_references()
            export_data = {}
            
            for conversation_id, reference in references.items():
                export_data[conversation_id] = {
                    "activity_id": reference.activity_id,
                    "bot": reference.bot.__dict__ if reference.bot else {},
                    "channel_id": reference.channel_id,
                    "conversation": reference.conversation.__dict__ if reference.conversation else {},
                    "service_url": reference.service_url,
                    "user": reference.user.__dict__ if reference.user else {}
                }
            
            with open(json_file_path, 'w', encoding='utf-8') as file:
                json.dump(export_data, file, indent=4, ensure_ascii=False)
            
            logger.info(f"Successfully exported {len(export_data)} conversation references to JSON")
            
        except Exception as e:
            logger.error(f"Failed to export to JSON: {e}")
            raise
    
    def get_connection_info(self) -> dict:
        """获取Redis连接信息"""
        try:
            info = self.redis_client.info()
            return {
                "redis_version": info.get("redis_version"),
                "connected_clients": info.get("connected_clients"),
                "used_memory_human": info.get("used_memory_human"),
                "total_keys": len(self.redis_client.keys(f"{self.key_prefix}*"))
            }
        except Exception as e:
            logger.error(f"Failed to get Redis info: {e}")
            return {"error": str(e)}