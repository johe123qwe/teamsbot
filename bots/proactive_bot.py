# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import json
import os
from typing import Dict

from botbuilder.core import ActivityHandler, TurnContext
from botbuilder.schema import ChannelAccount, ConversationReference, Activity, ConversationAccount


class ProactiveBot(ActivityHandler):
    def __init__(self, conversation_references: Dict[str, ConversationReference], storage_file: str = "conversation_references.json"):
        self.conversation_references = conversation_references
        self.storage_file = storage_file
        self._load_conversation_references()

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
        
        # 检查消息内容是否为 "myid"
        if turn_context.activity.text.strip().lower() == "myid" or "myid" in turn_context.activity.text.lower():
            user_id = turn_context.activity.from_property.id
            await turn_context.send_activity(f"Your ID is: {user_id}")
        
        # 新增：检查消息内容是否为 "convid"
        elif turn_context.activity.text.strip().lower() == "convid" or "convid" in turn_context.activity.text.lower():
            conversation_id = turn_context.activity.conversation.id
            await turn_context.send_activity(f"Your Conversation ID is: {conversation_id}")
        
        elif turn_context.activity.text.strip().lower() == "myname" or "myname" in turn_context.activity.text.lower():
            user_name = turn_context.activity.from_property.name
            await turn_context.send_activity(f"Your Name is: {user_name}")
        else:
            await turn_context.send_activity(f"You sent: {turn_context.activity.text}")

    def _add_conversation_reference(self, activity: Activity):
        """
        This populates the shared Dictionary that holds conversation references. In this sample,
        this dictionary is used to send a message to members when /api/notify is hit.
        :param activity:
        :return:
        """
        conversation_reference = TurnContext.get_conversation_reference(activity)
        conversation_id = conversation_reference.conversation.id
        self.conversation_references[conversation_id] = conversation_reference
        self._save_conversation_references()

    def _load_conversation_references(self):
        if os.path.exists(self.storage_file):
            try:
                with open(self.storage_file, "r") as file:
                    data = json.load(file)
                    for user_id, reference in data.items():
                        self.conversation_references[user_id] = ConversationReference(
                            **self._deserialize_conversation_reference(reference)
                        )
            except json.JSONDecodeError:
                print(f"Error decoding JSON from {self.storage_file}. Initializing empty conversation references.")
                self.conversation_references = {}

    def _save_conversation_references(self):
        with open(self.storage_file, "w") as file:
            data = {user_id: self._serialize_conversation_reference(reference) for user_id, reference in self.conversation_references.items()}
            json.dump(data, file, indent=4)

    def _serialize_conversation_reference(self, reference: ConversationReference) -> dict:
        return {
            "activity_id": reference.activity_id,
            "bot": reference.bot.__dict__,
            "channel_id": reference.channel_id,
            "conversation": reference.conversation.__dict__,
            "service_url": reference.service_url,
            "user": reference.user.__dict__
        }

    def _deserialize_conversation_reference(self, data: dict) -> dict:
        return {
            "activity_id": data.get("activity_id"),
            "bot": ChannelAccount(**data.get("bot")),
            "channel_id": data.get("channel_id"),
            "conversation": ConversationAccount(**data.get("conversation")),
            "service_url": data.get("service_url"),
            "user": ChannelAccount(**data.get("user"))
        }

    def print_all_conversation_references(self):
        """
        打印所有用户的 ConversationReference 记录。
        """
        for user_id, reference in self.conversation_references.items():
            print(f"User ID: {user_id}")
            print(f"Service URL: {reference.service_url}")
            print(f"Channel ID: {reference.channel_id}")
            print(f"Conversation ID: {reference.conversation.id}")
            print(f"User Name: {reference.user.name}")
            print(f"Bot ID: {reference.bot.id}")
            print(f"Bot Name: {reference.bot.name}")
            print("-" * 40)
