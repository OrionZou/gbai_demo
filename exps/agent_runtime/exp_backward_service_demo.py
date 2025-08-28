"""
BackwardService演示脚本

该脚本演示如何使用BackwardService进行反向知识处理，
包括问答对聚合、章节生成和OSPA转换的完整工作流。

Author: AI Assistant
Date: 2025-08-25
"""

import os
import sys
import asyncio
from typing import List, Tuple, Optional

from agent_runtime.clients.llm.openai_client import LLM
from agent_runtime.services.backward_service import BackwardService


async def demo_backward_service() -> Optional[Tuple[List, List]]:
    """BackwardService核心功能演示
    
    演示完整的反向知识处理流程：
    1. 准备测试问答对数据
    2. 初始化服务
    3. 执行backward处理
    4. 展示结果
    """
    print("=" * 60)
    print("BackwardService 反向知识处理演示")
    print("=" * 60)

    # 1. 准备测试数据 - 多领域技术问答对
    test_qas: List[Tuple[str, str]] = [
        # Python编程相关
        ("Python如何定义变量？", "在Python中使用赋值语句定义变量，如 x = 10，变量名遵循标识符规则"),
        ("Python中什么是列表？", "列表是Python中的可变序列类型，使用[]定义，如 my_list = [1, 2, 3]"),
        ("Python如何定义函数？",
         "使用def关键字定义函数，语法为 def function_name(parameters): 函数体"),

        # 数据库相关
        ("什么是数据库索引？", "索引是提高数据库查询效率的数据结构，类似书籍的目录，能快速定位数据"),
        ("什么是SQL JOIN？",
         "JOIN是SQL中用于连接多个表的操作，包括INNER、LEFT、RIGHT JOIN等"),

        # 算法相关
        ("什么是时间复杂度？",
         "时间复杂度描述算法执行时间与输入规模的关系，用大O记号表示，如O(n)、O(log n)"),
        ("什么是递归算法？", "递归算法是指函数调用自身来解决问题的算法，包含基准条件和递归条件"),

        # Web开发相关
        ("什么是RESTful API？",
         "RESTful API是遵循REST架构风格的Web服务接口，使用HTTP方法进行资源操作"),
        ("什么是HTTP状态码？", "HTTP状态码表示服务器对请求的处理结果，如200成功、404未找到、500服务器错误")
    ]

    print(f"📝 准备了 {len(test_qas)} 个测试问答对")
    for i, (q, a) in enumerate(test_qas, 1):
        print(f"  {i}. Q: {q[:30]}...")

    print("\n🔧 初始化BackwardService...")
    try:
        # 2. 初始化LLM客户端和BackwardService
        llm_client = LLM()
        backward_service = BackwardService(llm_client)
        print("✅ BackwardService初始化成功")

        # 3. 执行反向知识处理
        print("\n🚀 开始执行反向知识处理...")
        chapters, ospa_list = await backward_service.backward(
            qas=test_qas,
            chapters_extra_instructions="请按技术领域分类，确保每个章节主题明确且不重叠",
            gen_p_extra_instructions="生成专业的技术文档风格提示词，注重准确性和实用性"
        )

        print(f"✅ 处理完成！生成了 {len(chapters)} 个章节，"
              f"{len(ospa_list)} 个OSPA条目")

        # 4. 展示处理结果
        print("\n" + "=" * 60)
        print("📊 处理结果详情")
        print("=" * 60)

        print("\n📚 生成的章节概览：")
        for i, chapter in enumerate(chapters, 1):
            print(f"\n--- 章节 {i}: {chapter.chapter_name} ---")
            print(f"聚合原因: {chapter.reason}")
            print(f"包含问答: {len(chapter.qas)} 个")
            print(f"提示词长度: {len(chapter.prompt or '未生成')} 字符")

            # 显示该章节的问答对
            print("问答对列表:")
            for j, qa in enumerate(chapter.qas, 1):
                print(f"  {j}. Q: {qa.q}")
                ans_preview = qa.a[:50] + ('...' if len(qa.a) > 50 else '')
                print(f"     A: {ans_preview}")

            # 显示生成的提示词
            if chapter.prompt:
                print("\n生成的辅助提示词:")
                prompt_preview = chapter.prompt[:100]
                if len(chapter.prompt) > 100:
                    prompt_preview += '...'
                print(f"  {prompt_preview}")

        # 5. 展示OSPA转换结果
        print(f"\n🔄 OSPA转换结果 (共{len(ospa_list)}个条目):")
        for i, ospa in enumerate(ospa_list[:3], 1):  # 只显示前3个作为示例
            print(f"\n--- OSPA条目 {i} ---")
            print(f"O (目标): {ospa.o}")
            print(f"S (场景): {ospa.s[:60]}{'...' if len(ospa.s) > 60 else ''}")
            print(f"P (提示): {ospa.p[:60]}{'...' if len(ospa.p) > 60 else ''}")
            print(f"A (答案): {ospa.a[:60]}{'...' if len(ospa.a) > 60 else ''}")

        if len(ospa_list) > 3:
            print(f"  ... 还有 {len(ospa_list) - 3} 个OSPA条目")

        # 6. 统计信息
        print("\n📈 统计信息:")
        print(f"  • 输入问答对数量: {len(test_qas)}")
        print(f"  • 生成章节数量: {len(chapters)}")
        print(f"  • 生成OSPA条目数量: {len(ospa_list)}")
        print(f"  • 平均每章节问答数: {len(test_qas) / len(chapters):.1f}")

        return chapters, ospa_list

    except Exception as e:
        print(f"❌ 演示过程中发生错误: {str(e)}")
        print("请检查LLM配置和网络连接")
        return None, None


async def demo_single_chapter_processing() -> Optional[Tuple[List, List]]:
    """单章节处理演示
    
    演示如何处理单个技术领域的问答对
    """
    print("\n" + "=" * 60)
    print("📖 单章节处理演示 - Python基础")
    print("=" * 60)

    # Python基础问答对
    python_qas: List[Tuple[str, str]] = [
        ("Python中如何创建类？", "使用class关键字创建类，语法为 class ClassName: 类体"),
        ("Python中什么是装饰器？", "装饰器是修改或增强函数功能的语法糖，使用@decorator语法"),
        ("Python如何处理异常？",
         "使用try-except语句处理异常，语法为 try: 代码块 except Exception: 异常处理"),
    ]

    try:
        llm_client = LLM()
        backward_service = BackwardService(llm_client)

        chapters, ospa_list = await backward_service.backward(
            qas=python_qas,
            chapters_extra_instructions="专注于Python编程语言的基础概念",
            gen_p_extra_instructions="生成适合Python初学者的清晰、准确的技术指导"
        )

        print("✅ 单章节处理完成！")
        if chapters:
            chapter = chapters[0]
            print(f"章节名称: {chapter.chapter_name}")
            print(f"聚合原因: {chapter.reason}")
            print(f"生成的提示词: {chapter.prompt[:200]}...")

        return chapters, ospa_list

    except Exception as e:
        print(f"❌ 单章节处理失败: {str(e)}")
        return None, None


def print_usage_tips() -> None:
    """打印使用提示"""
    print("\n" + "=" * 60)
    print("💡 使用提示")
    print("=" * 60)
    print("1. 确保已正确配置LLM客户端（API Key等）")
    print("2. 问答对数据质量直接影响聚合效果")
    print("3. 额外指令可以帮助优化聚合和提示词生成")
    print("4. OSPA格式便于后续的知识检索和问答")
    print("5. 生成的提示词可用于指导其他LLM任务")


async def main() -> None:
    """主函数 - 执行完整的演示流程"""
    print("🎯 BackwardService 综合演示开始")
    print("本演示将展示反向知识处理的完整工作流程\n")

    # 运行主要演示
    await demo_backward_service()

    # 运行单章节演示
    await demo_single_chapter_processing()

    # 显示使用提示
    print_usage_tips()

    print("\n🎉 演示完成！感谢使用BackwardService")


if __name__ == "__main__":
    # 运行演示
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⏹️  演示被用户中断")
    except Exception as e:
        print(f"\n❌ 演示执行失败: {str(e)}")
        print("请检查环境配置和依赖")
