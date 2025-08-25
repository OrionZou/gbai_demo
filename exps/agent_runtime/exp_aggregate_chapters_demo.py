"""
BackwardService _aggregate_chapters 方法测试演示
演示如何使用 _aggregate_chapters 方法将 Q&A 聚合成章节结构
"""

import asyncio
import sys
import os
from typing import List, Tuple

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from agent_runtime.services.backward_service import BackwardService
from agent_runtime.data_format.context_ai import AIContext
from agent_runtime.clients.llm.openai_client import LLM


def get_demo_qas_20() -> List[Tuple[str, str]]:
    """获取20个演示用的Q&A对"""
    return [
        # Python基础 (5个)
        ("Python如何定义变量？", "在Python中使用赋值语句定义变量，如 x = 10"),
        ("Python如何定义函数？", "使用def关键字定义函数，如 def func_name():"),
        ("Python中的列表和元组有什么区别？", "列表是可变的，元组是不可变的"),
        ("Python如何处理异常？", "使用try-except语句捕获和处理异常"),
        ("Python中的装饰器是什么？", "装饰器是修改函数行为的语法糖"),

        # 面向对象编程 (4个)
        ("什么是面向对象编程？", "面向对象编程是一种以对象为中心的编程范式"),
        ("什么是继承？", "继承是面向对象编程中子类获得父类属性和方法的机制"),
        ("什么是多态？", "多态是同一接口在不同对象上表现出不同行为的能力"),
        ("什么是封装？", "封装是将数据和操作数据的方法绑定在一起的机制"),

        # 数据结构 (4个)
        ("什么是栈？", "栈是一种后进先出(LIFO)的线性数据结构"),
        ("什么是队列？", "队列是一种先进先出(FIFO)的线性数据结构"),
        ("什么是哈希表？", "哈希表是基于哈希函数实现的键值对存储结构"),
        ("什么是二叉树？", "二叉树是每个节点最多有两个子节点的树形数据结构"),

        # 算法相关 (3个)
        ("什么是时间复杂度？", "时间复杂度是算法执行时间与输入规模的关系"),
        ("什么是递归？", "递归是函数调用自身的编程技术"),
        ("什么是动态规划？", "动态规划是通过分解子问题并存储结果来优化算法的方法"),

        # 数据库相关 (2个)
        ("什么是SQL？", "SQL是结构化查询语言，用于管理关系数据库"),
        ("什么是索引？", "索引是提高数据库查询效率的数据结构"),

        # 网络编程 (2个)
        ("什么是HTTP协议？", "HTTP是超文本传输协议，用于Web通信"),
        ("什么是RESTful API？", "RESTful API是遵循REST架构风格的Web服务接口")
    ]


async def demo_aggregate_chapters():
    """演示章节聚合功能"""
    print("=" * 60)
    print("BackwardService _aggregate_chapters 方法演示")
    print("=" * 60)

    # 初始化LLM客户端和服务
    print("1. 初始化模拟LLM客户端和BackwardService...")

    # 为了演示，我们创建一个模拟的LLM客户端
    llm_client = LLM()
    backward_service = BackwardService(llm_client=llm_client)

    # 准备测试数据
    print("2. 准备20个Q&A对...")
    qas = get_demo_qas_20()
    print(f"   → 总共准备了 {len(qas)} 个Q&A对")

    # 显示部分Q&A示例
    print("\n3. Q&A示例（前5个）:")
    # for i, (q, a) in enumerate(qas[:5], 1):
    #     print(f"   {i}. Q: {q}")
    #     print(f"      A: {a}")
    # print("   ...")

    # 执行章节聚合
    print("\n4. 执行章节聚合...")
    try:
        result = await backward_service._aggregate_chapters(
            qas, extra_instructions="请将相关主题的Q&A聚合到同一章节，每个章节包含3-7个问答")

        print("   ✓ 聚合完成！")

        # 显示聚合结果
        print("\n5. 聚合结果:")
        print(f"   → 总共生成了 {len(result.chapters)} 个章节")

        for i, chapter in enumerate(result.chapters, 1):
            print(f"\n   章节 {i}: {chapter.chapter_name}")
            print(f"   原因: {chapter.reason}")
            print(f"   包含Q&A数量: {len(chapter.qas)}")

            # 显示前3个Q&A
            for j, qa in enumerate(chapter.qas[:3], 1):
                print(f"     {j}. Q: {qa.q}")
                print(f"        A: {qa.a}")

            if len(chapter.qas) > 3:
                print(f"     ... 还有 {len(chapter.qas) - 3} 个Q&A")

        # 验证总Q&A数量
        total_qas = sum(len(chapter.qas) for chapter in result.chapters)
        print(f"   → 验证: 原始Q&A数量 {len(qas)}，聚合后Q&A数量 {total_qas}")

        if total_qas == len(qas):
            print("   ✓ Q&A数量匹配，聚合成功！")
        else:
            print("   ⚠ Q&A数量不匹配，可能存在丢失")

    except Exception as e:
        print(f"   ✗ 聚合失败: {e}")
        return False

    print("\n" + "=" * 60)
    print("演示完成！")
    print("=" * 60)
    return True


async def main():
    """主函数"""
    print("开始 BackwardService _aggregate_chapters 演示...")

    # 基础演示
    success = await demo_aggregate_chapters()

    print("\n演示结束。")


if __name__ == "__main__":
    # 运行演示
    asyncio.run(main())
