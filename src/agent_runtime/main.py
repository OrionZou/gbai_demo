from fastapi import FastAPI
from agent_runtime.interface import api
from agent_runtime.interface import chat_v2_api


def create_app() -> FastAPI:
    """
    创建 agent_runtime 服务应用入口
    """
    app = FastAPI(
        title="Agent Runtime API",
        docs_url="/agent/docs",
        openapi_url="/agent/openapi.json",
        description="Agent Runtime 提供的 API 接口服务",
        version="1.0.0",
    )
    # 挂载 API 路由
    app.include_router(api.router, prefix="/agent")
    app.include_router(chat_v2_api.router, prefix="/agent")

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