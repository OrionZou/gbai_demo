"""
Feedback API Server

基于FastAPI的反馈API服务器
"""

import sys
import os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 添加src路径到sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from agent_runtime.interface.feedback_api import router as feedback_router
from agent_runtime.logging.logger import logger


def create_app() -> FastAPI:
    """创建FastAPI应用"""
    app = FastAPI(
        title="Agent Runtime Feedback API",
        description="API for managing agent feedbacks with vector search capabilities",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc"
    )

    # 添加CORS中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # 在生产环境中应该限制具体域名
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 注册路由
    app.include_router(feedback_router)

    # 根路径
    @app.get("/")
    async def root():
        return {
            "service": "Agent Runtime Feedback API",
            "version": "1.0.0",
            "status": "running",
            "docs": "/docs",
            "redoc": "/redoc"
        }

    # 健康检查
    @app.get("/health")
    async def health():
        return {"status": "healthy"}

    return app


app = create_app()


@app.on_event("startup")
async def startup_event():
    """启动事件"""
    logger.info("🚀 Feedback API Server starting up...")
    logger.info("📚 API documentation available at: /docs")
    logger.info("📖 Redoc documentation available at: /redoc")


@app.on_event("shutdown")
async def shutdown_event():
    """关闭事件"""
    logger.info("👋 Feedback API Server shutting down...")


if __name__ == "__main__":
    print("🚀 Starting Feedback API Server")
    print("=" * 35)
    print("📚 API docs: http://localhost:8000/docs")
    print("📖 Redoc: http://localhost:8000/redoc")
    print("🏥 Health: http://localhost:8000/health")
    print("⚠️  Make sure Weaviate is running on http://localhost:8080")
    print("💡 Set OPENAI_API_KEY for better embeddings")
    print()

    uvicorn.run(
        "feedback_api_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )