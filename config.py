#!/usr/bin/env python3
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import os

""" Bot Configuration """


class DefaultConfig:
    """ Bot Configuration """

    PORT = 13978
    APP_ID = os.environ.get("MicrosoftAppId", "f8d1650f-266f-48d4-8d41-cb96c4a5f078")
    APP_PASSWORD = os.environ.get("MicrosoftAppPassword", "nVe8Q~H-f5afBRBoT2clO1HTv4mVJ6bqQbZDocO7")
    APP_TYPE = os.environ.get("MicrosoftAppType", "MultiTenant")
    APP_TENANTID = os.environ.get("MicrosoftAppTenantId", "c7c94f0b-d168-4f27-80cc-82d8d4f7444a")
