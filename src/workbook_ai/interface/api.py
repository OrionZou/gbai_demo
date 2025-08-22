"""
Interface层API接口
提供REST API接口供外部调用
"""

import logging
from typing import List, Dict, Any
from uuid import UUID

try:
    from fastapi import FastAPI, HTTPException, UploadFile, File
    from fastapi.responses import JSONResponse
    from pydantic import BaseModel
except ImportError:
    # 在没有安装fastapi时提供占位符
    FastAPI = None
    HTTPException = None
    UploadFile = None
    File = None
    JSONResponse = None
    BaseModel = object

from workbook_ai.application.services import DataImportService
from workbook_ai.domain.entities import (
    ConversationRecord, 
    ImportResult, 
    QueryResult
)


logger = logging.getLogger(__name__)


# API请求/响应模型
class ImportCSVRequest(BaseModel):
    """CSV导入请求"""
    csv_content: str


class QueryRequest(BaseModel):
    """查询请求"""
    query_text: str
    limit: int = 10


class HistoryRequest(BaseModel):
    """历史查询请求"""
    record_id: str


# 创建FastAPI应用
if FastAPI:
    app = FastAPI(
        title="AI知识库API",
        description="基于DDD架构的AI知识库系统API",
        version="1.0.0"
    )
else:
    app = None


# 初始化服务
data_import_service = DataImportService()


@app.get("/") if app else lambda: None
async def root():
    """根路径"""
    return {"message": "AI知识库API服务正在运行", "version": "1.0.0"}


@app.get("/health") if app else lambda: None
async def health_check():
    """健康检查"""
    return {"status": "healthy", "service": "ai-knowledge-base"}


@app.post("/import/csv", response_model=ImportResult) if app else lambda: None
async def import_csv_data(request: ImportCSVRequest):
    """
    导入CSV格式的对话数据
    
    Args:
        request: CSV导入请求
        
    Returns:
        ImportResult: 导入结果
    """
    try:
        logger.info("开始导入CSV数据")
        result = data_import_service.import_from_csv(request.csv_content)
        
        if result.success:
            logger.info(f"CSV导入成功: {result.imported_records}条记录")
        else:
            logger.warning(f"CSV导入部分失败: {result.error_messages}")
        
        return result
        
    except Exception as e:
        logger.error(f"CSV导入API调用失败: {e}")
        raise HTTPException(status_code=500, detail=f"导入失败: {e}")


@app.post("/import/csv/file") if app else lambda: None
async def import_csv_file(file: UploadFile = File(...)):
    """
    通过文件上传导入CSV数据
    
    Args:
        file: 上传的CSV文件
        
    Returns:
        ImportResult: 导入结果
    """
    try:
        # 检查文件类型
        if not file.filename.endswith('.csv'):
            raise HTTPException(
                status_code=400, 
                detail="只支持CSV文件格式"
            )
        
        # 读取文件内容
        content = await file.read()
        csv_content = content.decode('utf-8')
        
        logger.info(f"开始导入CSV文件: {file.filename}")
        result = data_import_service.import_from_csv(csv_content)
        
        if result.success:
            logger.info(f"CSV文件导入成功: {result.imported_records}条记录")
        else:
            logger.warning(f"CSV文件导入部分失败: {result.error_messages}")
        
        return result
        
    except Exception as e:
        logger.error(f"CSV文件导入API调用失败: {e}")
        raise HTTPException(status_code=500, detail=f"文件导入失败: {e}")


@app.post("/query/similar", response_model=QueryResult) if app else lambda: None
async def query_similar_conversations(request: QueryRequest):
    """
    查询相似对话
    
    Args:
        request: 查询请求
        
    Returns:
        QueryResult: 查询结果
    """
    try:
        logger.info(f"开始查询相似对话: {request.query_text}")
        result = data_import_service.query_similar_conversations(
            query_text=request.query_text,
            limit=request.limit
        )
        
        logger.info(f"查询完成，返回{result.total_count}条结果")
        return result
        
    except Exception as e:
        logger.error(f"相似对话查询API调用失败: {e}")
        raise HTTPException(status_code=500, detail=f"查询失败: {e}")


@app.post("/query/history") if app else lambda: None
async def get_conversation_history(request: HistoryRequest):
    """
    获取对话历史
    
    Args:
        request: 历史查询请求
        
    Returns:
        List[ConversationRecord]: 历史记录列表
    """
    try:
        logger.info(f"开始获取对话历史: {request.record_id}")
        history = data_import_service.get_conversation_history(
            record_id=request.record_id
        )
        
        logger.info(f"获取历史记录完成，共{len(history)}条记录")
        return history
        
    except Exception as e:
        logger.error(f"对话历史查询API调用失败: {e}")
        raise HTTPException(status_code=500, detail=f"历史查询失败: {e}")


@app.get("/records/{record_id}") if app else lambda: None
async def get_record_by_id(record_id: str):
    """
    根据ID获取单条记录
    
    Args:
        record_id: 记录ID
        
    Returns:
        ConversationRecord: 对话记录
    """
    try:
        logger.info(f"开始获取记录: {record_id}")
        
        # 通过查询服务获取记录
        result = data_import_service.query_similar_conversations(
            query_text=record_id,
            limit=1
        )
        
        if result.results:
            record = result.results[0]
            logger.info(f"成功获取记录: {record_id}")
            return record
        else:
            logger.warning(f"记录不存在: {record_id}")
            raise HTTPException(status_code=404, detail="记录不存在")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取记录API调用失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取记录失败: {e}")


@app.get("/stats/database") if app else lambda: None
async def get_database_stats():
    """
    获取数据库统计信息
    
    Returns:
        Dict[str, Any]: 统计信息
    """
    try:
        logger.info("开始获取数据库统计信息")
        
        stats = {
            "weaviate_status": "connected" if data_import_service.weaviate_client else "disconnected",
            "neo4j_status": "connected" if data_import_service.neo4j_client else "disconnected",
            "service_status": "running"
        }
        
        # 尝试获取更详细的统计信息
        try:
            if data_import_service.weaviate_client:
                schema = data_import_service.weaviate_client.get_schema()
                stats["weaviate_collections"] = len(schema.get("classes", []))
        except:
            pass
        
        try:
            if data_import_service.neo4j_client:
                transitions = data_import_service.neo4j_client.get_state_transitions()
                stats["neo4j_state_transitions"] = len(transitions)
        except:
            pass
        
        logger.info("数据库统计信息获取完成")
        return stats
        
    except Exception as e:
        logger.error(f"获取数据库统计信息失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {e}")


# 异常处理器
@app.exception_handler(Exception) if app else lambda: None
async def global_exception_handler(request, exc):
    """全局异常处理器"""
    logger.error(f"未处理的异常: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "内部服务器错误"}
    )


# 启动函数
def create_app() -> FastAPI:
    """创建FastAPI应用实例"""
    if not app:
        raise RuntimeError("FastAPI未安装，请运行: pip install fastapi uvicorn")
    
    logger.info("AI知识库API服务已启动")
    return app


if __name__ == "__main__":
    try:
        import uvicorn
        uvicorn.run(
            "ai_knowledge_base.interface.api:app",
            host="0.0.0.0",
            port=8000,
            reload=True
        )
    except ImportError:
        print("uvicorn未安装，请运行: pip install uvicorn")
    except Exception as e:
        print(f"启动API服务失败: {e}")