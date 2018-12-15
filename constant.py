# -*- coding: utf-8 -*-

import re

DEBUG = False

# 每页请求个数
MEDIA_NUM = 50

# 并发线程数
THREADS = 20

GET_CH_PATTERN = re.compile(u"[\u4e00-\u9fa5]+")

# 设置请求超时时间
TIMEOUT = 20

# 尝试次数
RETRY = 5

# 分页请求的起始点
START = 0

# 是否下载图片
ISDOWNLOADIMG = True

#是否下载视频
ISDOWNLOADVIDEO = True
