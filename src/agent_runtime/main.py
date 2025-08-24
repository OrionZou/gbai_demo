from fastapi import FastAPI
from src.agent_runtime.interface import api as reward_api


def create_app() -> FastAPI:
    """
    创建 agent_runtime 服务应用入口
    """
    app = FastAPI(
        title="Agent Runtime API",
        description="Agent Runtime 提供的 API 接口服务",
        version="1.0.0",
    )

    # 挂载 reward API 路由
    app.include_router(reward_api.router, prefix="/agent")

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.agent_runtime.api:app",
        host="0.0.0.0",
        port=8011,
        reload=True,
    )