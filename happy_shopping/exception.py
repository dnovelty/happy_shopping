#!/usr/bin/env python
# -*- encoding=utf8 -*-


class BizException(Exception):

    def __init__(self, message):
        super().__init__(message)
