#!/bin/bash
set -e

# 安装依赖
python3 -m pip install -r requirements.txt

# 启动服务
python3 -m uvicorn main:app --host 0.0.0.0 --port $PORT
