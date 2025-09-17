from fastapi import FastAPI
from agent_runtime.interface import api
from agent_runtime.interface import chat_api




def create_app() -> FastAPI:
    """
    创建 agent_runtime 服务应用入口
    """
    app = FastAPI(
        title="Agent Runtime API",
        docs_url="/docs",
        openapi_url="/openapi.json",
        description="Agent Runtime 提供的 API 接口服务",
        version="1.0.0",
    )

    # 健康检查端点
    @app.get("/", tags=["Health"])
    async def health_check():
        """
        Health check endpoint.
        """
        return {"status": "ok"}

    # 挂载 API 路由
    app.include_router(api.router, prefix="/agent", tags=["agent_runtime"])
    app.include_router(chat_api.router, prefix="/v1.5", tags=["agent_v1.5"])

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "agent_runtime.main:app",
        host="0.0.0.0",
        port=8011,
        reload=True,
    )