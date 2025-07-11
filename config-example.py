#!/usr/bin/env python3
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import os

""" Bot Configuration """


class DefaultConfig:
    """ Bot Configuration """

    PORT = 13978
    APP_ID = os.environ.get("MicrosoftAppId", "")
    APP_PASSWORD = os.environ.get("MicrosoftAppPassword", "")
    APP_TYPE = os.environ.get("MicrosoftAppType", "MultiTenant")
    APP_TENANTID = os.environ.get("MicrosoftAppTenantId", "")
    API_KEY = os.environ.get("API_KEY", "")
    REDIS_DB = 
    REDIS_HOST = 
    REDIS_PORT = 
    REDIS_PASSWORD = 
    JSON_BACKUP_FILE = os.environ.get("JSON_BACKUP_FILE", "conversation_references.json")
