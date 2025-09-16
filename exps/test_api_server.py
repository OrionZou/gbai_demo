#!/usr/bin/env python3
"""
测试重构后的API服务器
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import uvicorn
from fastapi import FastAPI
from agent_runtime.interface.chat_v2_api import router

app = FastAPI(title="Test Chat V2 API", version="1.0.0")
app.include_router(router, prefix="/api/v2", tags=["chat"])

if __name__ == "__main__":
    print("🚀 Starting test API server...")
    print("📖 API docs available at: http://localhost:8001/docs")
    print("🧪 Test endpoints:")
    print("  - POST /api/v2/chat")
    print("  - POST /api/v2/learn")
    print("  - GET  /api/v2/feedbacks")
    print("  - DELETE /api/v2/feedbacks")

    uvicorn.run(app, host="0.0.0.0", port=8001)