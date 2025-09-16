from typing import List, Dict, Any

from agent_runtime.agents.chat_agent import ChatAgent
from agent_runtime.data_format.feedback import (
    Feedback, add_feedbacks, get_feedbacks, delete_collection
)
from agent_runtime.logging.logger import logger

# 导入统一的API模型
from agent_runtime.interface.api_models import (
    ChatRequest, ChatResponse, LearnRequest, LearnResponse,
    GetFeedbackParam, DeleteFeedbackParam
)


class ChatV2Service:
    """
    Chat V2 服务类 - 处理chat、feedback和learn相关的业务逻辑
    """

    def __init__(self):
        self.chat_agent = ChatAgent()

    async def generate_chat(self, request: ChatRequest) -> ChatResponse:
        """
        生成聊天响应

        Args:
            request: 聊天请求

        Returns:
            聊天响应
        """
        try:
            logger.info(f"Generating chat for agent {request.settings.agent_name}")

            # 使用ChatAgent进行对话
            result = await self.chat_agent.chat_step(
                user_message=request.user_message,
                edited_last_response=request.edited_last_response,
                recall_last_user_message=request.recall_last_user_message,
                settings=request.settings,
                memory=request.memory,
                request_tools=request.request_tools
            )

            # 构造响应
            response = ChatResponse(
                response=result.get("response", ""),
                memory=result.get("memory"),
                result_type=result.get("result_type", "Success"),
                llm_calling_times=result.get("llm_calling_times", 0),
                total_input_token=result.get("total_input_token", 0),
                total_output_token=result.get("total_output_token", 0)
            )

            logger.info(f"Chat generated successfully for agent {request.settings.agent_name}")
            return response

        except Exception as e:
            logger.exception(f"Error generating chat for agent {request.settings.agent_name}", exc_info=e)
            raise e

    async def learn_from_feedback(self, request: LearnRequest) -> LearnResponse:
        """
        从反馈中学习

        Args:
            request: 学习请求

        Returns:
            学习响应
        """
        try:
            logger.info(f"Learning from feedback for agent {request.settings.agent_name}")

            # 添加反馈到Weaviate
            response_data = await add_feedbacks(request.settings, request.feedbacks)

            logger.info(f"Successfully learned from {len(request.feedbacks)} feedbacks for agent {request.settings.agent_name}")

            return LearnResponse(status="success", data=response_data)

        except Exception as e:
            logger.exception(f"Error learning from feedback for agent {request.settings.agent_name}", exc_info=e)
            raise e

    async def get_all_feedbacks(self, param: GetFeedbackParam) -> List[Feedback]:
        """
        获取所有反馈

        Args:
            param: 获取参数

        Returns:
            反馈列表
        """
        try:
            logger.info(f"Getting all feedbacks for agent {param.agent_name}")

            feedbacks = await get_feedbacks(
                param.agent_name,
                param.vector_db_url,
                param.offset,
                param.limit
            )

            logger.info(f"Retrieved {len(feedbacks)} feedbacks for agent {param.agent_name}")
            return feedbacks

        except Exception as e:
            logger.exception(f"Error getting feedbacks for agent {param.agent_name}", exc_info=e)
            raise e

    async def delete_all_feedbacks(self, param: DeleteFeedbackParam) -> None:
        """
        删除所有反馈

        Args:
            param: 删除参数
        """
        try:
            logger.info(f"Deleting all feedbacks for agent {param.agent_name}")

            await delete_collection(param.agent_name, param.vector_db_url)

            logger.info(f"Successfully deleted all feedbacks for agent {param.agent_name}")

        except Exception as e:
            logger.exception(f"Error deleting feedbacks for agent {param.agent_name}", exc_info=e)
            raise e