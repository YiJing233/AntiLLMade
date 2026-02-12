#!/bin/bash
set -e

# 安装依赖
pip install -r requirements.txt

# 启动服务
uvicorn main:app --host 0.0.0.0 --port $PORT
