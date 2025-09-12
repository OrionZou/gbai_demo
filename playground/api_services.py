"""
API服务模块
封装Agent Runtime API调用逻辑
"""
import asyncio
import aiohttp
import requests
from typing import List, Dict, Any, Tuple, Optional
from ospa_models import OSPAItem, ProcessingResult


class APIClient:
    """API客户端基类"""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')

    def check_connection(self) -> bool:
        """检查API连接状态"""
        try:
            response = requests.get(f"{self.base_url}/docs", timeout=5)
            return response.status_code == 200
        except Exception:
            return False


class ConfigService(APIClient):
    """LLM配置服务"""

    def get_config(self) -> Dict[str, Any]:
        """获取当前配置"""
        response = requests.get(f"{self.base_url}/config")
        response.raise_for_status()
        return response.json()

    def update_config(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """更新配置"""
        response = requests.post(f"{self.base_url}/config",
                                 json=config_data)
        response.raise_for_status()
        return response.json()


class RewardService(APIClient):
    """Reward API服务"""

    def process_single_item(self, item: OSPAItem) -> ProcessingResult:
        """处理单个项目的一致性检测"""
        try:
            reward_data = {
                "question": item.O,
                "candidates": [item.A_prime],
                "target_answer": item.A
            }

            response = requests.post(f"{self.base_url}/reward",
                                     json=reward_data,
                                     timeout=30)

            if response.status_code == 200:
                result = response.json()

                return ProcessingResult(success=True, data=result)
            else:
                return ProcessingResult(
                    success=False,
                    error=f"HTTP {response.status_code}: {response.text[:100]}"
                )

        except Exception as e:
            return ProcessingResult(success=False, error=f"请求失败: {str(e)}")

    async def process_multiple_items_concurrent(
            self,
            items: List[OSPAItem],
            max_concurrent: int = 5,
            progress_callback=None,
            status_callback=None) -> Dict[int, ProcessingResult]:
        """并发处理多个项目"""

        async def process_item_async(
                session: aiohttp.ClientSession,
                item: OSPAItem) -> Tuple[int, ProcessingResult]:
            try:
                reward_data = {
                    "question": item.O,
                    "candidates": [item.A_prime],
                    "target_answer": item.A
                }

                async with session.post(
                        f"{self.base_url}/reward",
                        json=reward_data,
                        timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status == 200:
                        result = await response.json()

                        return item.no, ProcessingResult(
                            success=True,
                            data=result,
                        )
                    else:
                        error_text = await response.text()
                        return item.no, ProcessingResult(
                            success=False,
                            error=f"HTTP {response.status}: "
                            f"{error_text[:100]}")

            except Exception as e:
                return item.no, ProcessingResult(success=False,
                                                 error=f"请求失败: {str(e)}")

        # 使用信号量控制并发数
        semaphore = asyncio.Semaphore(max_concurrent)

        async def process_with_semaphore(session: aiohttp.ClientSession,
                                         item: OSPAItem):
            async with semaphore:
                return await process_item_async(session, item)

        # 创建HTTP连接器和会话
        connector = aiohttp.TCPConnector(limit=max_concurrent)
        async with aiohttp.ClientSession(connector=connector) as session:
            # 创建所有任务
            tasks = [
                asyncio.create_task(process_with_semaphore(session, item))
                for item in items
            ]

            # 处理任务并更新进度
            results = {}
            completed = 0
            for task in asyncio.as_completed(tasks):
                item_no, result = await task
                results[item_no] = result
                completed += 1

                # 更新进度
                if progress_callback:
                    progress_callback(completed / len(items))
                if status_callback:
                    status_callback(f"一致性检测进度: {completed}/{len(items)}")

        return results

    def process_multiple_items_sequential(
            self,
            items: List[OSPAItem],
            progress_callback=None,
            status_callback=None) -> Dict[int, ProcessingResult]:
        """顺序处理多个项目"""
        results = {}

        for i, item in enumerate(items):
            if status_callback:
                status_callback(f"正在检测第 {item.no} 条数据的一致性... "
                                f"({i+1}/{len(items)})")

            result = self.process_single_item(item)
            results[item.no] = result

            if progress_callback:
                progress_callback((i + 1) / len(items))

        return results


class BackwardService(APIClient):
    """Backward API服务"""

    def process_qas(self,
                    qas: List[Dict[str, str]],
                    chapter_structure: Optional[Dict[str, Any]] = None,
                    max_level: int = 3,
                    max_concurrent_llm: int = 10) -> Dict[str, Any]:
        """处理问答对，生成章节结构和OSPA数据"""
        try:
            # 转换QA格式从q/a到question/answer
            formatted_qas = []
            for qa in qas:
                formatted_qas.append({
                    "question": qa.get("q", qa.get("question", "")),
                    "answer": qa.get("a", qa.get("answer", ""))
                })
            
            backward_data = {
                "qas": formatted_qas,
                "max_level": max_level,
                "max_concurrent_llm": max_concurrent_llm
            }
            
            if chapter_structure is not None:
                backward_data["chapter_structure"] = chapter_structure

            response = requests.post(f"{self.base_url}/backward",
                                     json=backward_data,
                                     timeout=120)

            response.raise_for_status()
            return response.json()

        except Exception as e:
            raise Exception(f"Backward API调用失败: {str(e)}")


class LLMService(APIClient):
    """LLM生成服务"""

    def generate_answer(self,
                        item: OSPAItem,
                        temperature: float = 0.3) -> ProcessingResult:
        """为单个项目生成答案"""
        try:
            # 构造消息格式
            messages = []

            # 如果有提示词，作为系统消息
            if item.p.strip():
                messages.append({"role": "system", "content": item.p})

            # 观察作为用户问题
            messages.append({"role": "user", "content": item.O})

            llm_data = {
                "messages": messages,
                "temperature": temperature,
                "stream": False
            }

            response = requests.post(f"{self.base_url}/llm/ask",
                                     json=llm_data,
                                     timeout=60)

            if response.status_code == 200:
                result = response.json()
                success = result.get("success", False)
                content = result.get("content")
                if success and content:
                    return ProcessingResult(
                        success=True,
                        data=result,
                        generated_answer=result["content"].strip(),
                    )
                else:
                    return ProcessingResult(
                        success=False,
                        error=f"LLM返回失败: success={result.get('success')}, "
                        f"message={result.get('message', '未知错误')}")
            else:
                return ProcessingResult(
                    success=False,
                    error=f"HTTP {response.status_code}: {response.text[:200]}"
                )

        except Exception as e:
            return ProcessingResult(success=False, error=f"请求失败: {str(e)}")

    async def generate_answers_concurrent(
            self,
            items: List[OSPAItem],
            temperature: float = 0.3,
            max_concurrent: int = 5,
            progress_callback=None,
            status_callback=None) -> Dict[int, ProcessingResult]:
        """并发生成多个答案"""

        async def generate_async(
                session: aiohttp.ClientSession,
                item: OSPAItem) -> Tuple[int, ProcessingResult]:
            try:
                # 构造消息格式
                messages = []

                if item.p.strip():
                    messages.append({"role": "system", "content": item.p})

                messages.append({"role": "user", "content": item.O})

                llm_data = {
                    "messages": messages,
                    "temperature": temperature,
                    "stream": False
                }

                async with session.post(
                        f"{self.base_url}/llm/ask",
                        json=llm_data,
                        timeout=aiohttp.ClientTimeout(total=60)) as response:
                    if response.status == 200:
                        result = await response.json()
                        success = result.get("success", False)
                        content = result.get("content")
                        if success and content:
                            return item.no, ProcessingResult(
                                success=True,
                                data=result,
                                generated_answer=result["content"].strip())
                        else:
                            msg = result.get('message', '未知错误')
                            return item.no, ProcessingResult(
                                success=False,
                                error=f"LLM返回失败: "
                                f"success={result.get('success')}, "
                                f"message={msg}")
                    else:
                        error_text = await response.text()
                        return item.no, ProcessingResult(
                            success=False,
                            error=f"HTTP {response.status}: {error_text[:200]}"
                        )

            except Exception as e:
                return item.no, ProcessingResult(success=False,
                                                 error=f"请求失败: {str(e)}")

        # 使用信号量控制并发数
        semaphore = asyncio.Semaphore(max_concurrent)

        async def generate_with_semaphore(session: aiohttp.ClientSession,
                                          item: OSPAItem):
            async with semaphore:
                return await generate_async(session, item)

        # 创建HTTP连接器和会话
        connector = aiohttp.TCPConnector(limit=max_concurrent)
        async with aiohttp.ClientSession(connector=connector) as session:
            # 创建所有任务
            tasks = [
                asyncio.create_task(generate_with_semaphore(session, item))
                for item in items
            ]

            # 处理任务并更新进度
            results = {}
            completed = 0
            for task in asyncio.as_completed(tasks):
                item_no, result = await task
                results[item_no] = result
                completed += 1

                # 更新进度
                if progress_callback:
                    progress_callback(completed / len(items))
                if status_callback:
                    status_callback(f"答案生成进度: {completed}/{len(items)}")

        return results

    def generate_answers_sequential(
            self,
            items: List[OSPAItem],
            temperature: float = 0.3,
            progress_callback=None,
            status_callback=None) -> Dict[int, ProcessingResult]:
        """顺序生成多个答案"""
        results = {}

        for i, item in enumerate(items):
            if status_callback:
                status_callback(f"正在生成第 {item.no} 条数据的答案... "
                                f"({i+1}/{len(items)})")

            result = self.generate_answer(item, temperature)
            results[item.no] = result

            if progress_callback:
                progress_callback((i + 1) / len(items))

        return results


class ServiceManager:
    """服务管理器，统一管理所有API服务"""

    def __init__(self, base_url: str):
        self.base_url = base_url
        self.config_service = ConfigService(base_url)
        self.reward_service = RewardService(base_url)
        self.backward_service = BackwardService(base_url)
        self.llm_service = LLMService(base_url)

    def check_connection(self) -> bool:
        """检查API连接状态"""
        return self.config_service.check_connection()

    def get_all_services(self) -> Dict[str, APIClient]:
        """获取所有服务实例"""
        return {
            'config': self.config_service,
            'reward': self.reward_service,
            'backward': self.backward_service,
            'llm': self.llm_service
        }


def run_async_in_streamlit(coro, *args, **kwargs):
    """在Streamlit中安全运行异步函数"""
    try:
        # 尝试获取现有的事件循环
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # 如果循环正在运行，创建新的事件循环
            import threading
            result = None
            exception = None

            def run_in_thread():
                nonlocal result, exception
                try:
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    result = new_loop.run_until_complete(coro(*args, **kwargs))
                    new_loop.close()
                except Exception as e:
                    exception = e

            thread = threading.Thread(target=run_in_thread)
            thread.start()
            thread.join()

            if exception:
                raise exception
            return result
        else:
            # 如果循环未运行，直接运行
            return loop.run_until_complete(coro(*args, **kwargs))
    except RuntimeError:
        # 如果没有事件循环，创建新的
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro(*args, **kwargs))
        finally:
            loop.close()
