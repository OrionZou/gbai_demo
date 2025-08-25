"""
BackwardService _generate_chapter_prompt 方法测试演示
演示如何使用 _generate_chapter_prompt 方法为章节生成辅助提示词
"""

import asyncio
import sys
import os
from typing import List

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from agent_runtime.services.backward_service import (
    BackwardService, ChapterGroup, QAItem
)
from agent_runtime.data_format.context_ai import AIContext
from agent_runtime.clients.llm.openai_client import LLM


def create_sample_chapter_groups() -> List[ChapterGroup]:
    """创建示例章节组用于测试"""
    
    # Python基础章节
    python_chapter = ChapterGroup(
        chapter_name="Python基础语法",
        reason="包含Python编程语言的基础语法概念，适合初学者了解Python核心特性",
        qas=[
            QAItem(q="Python如何定义变量？", a="在Python中使用赋值语句定义变量，如 x = 10"),
            QAItem(q="Python如何定义函数？", a="使用def关键字定义函数，如 def func_name():"),
            QAItem(q="Python中的列表和元组有什么区别？", a="列表是可变的，元组是不可变的"),
            QAItem(q="Python如何处理异常？", a="使用try-except语句捕获和处理异常"),
            QAItem(q="Python中的装饰器是什么？", a="装饰器是修改函数行为的语法糖")
        ]
    )
    
    # 数据结构章节
    ds_chapter = ChapterGroup(
        chapter_name="基础数据结构",
        reason="涵盖计算机科学中常用的基础数据结构概念，帮助理解算法实现的基础",
        qas=[
            QAItem(q="什么是栈？", a="栈是一种后进先出(LIFO)的线性数据结构"),
            QAItem(q="什么是队列？", a="队列是一种先进先出(FIFO)的线性数据结构"),
            QAItem(q="什么是哈希表？", a="哈希表是基于哈希函数实现的键值对存储结构"),
            QAItem(q="什么是二叉树？", a="二叉树是每个节点最多有两个子节点的树形数据结构")
        ]
    )
    
    # 面向对象编程章节
    oop_chapter = ChapterGroup(
        chapter_name="面向对象编程原理",
        reason="介绍面向对象编程的核心概念和原理，是现代软件开发的重要编程范式",
        qas=[
            QAItem(q="什么是面向对象编程？", a="面向对象编程是一种以对象为中心的编程范式"),
            QAItem(q="什么是继承？", a="继承是面向对象编程中子类获得父类属性和方法的机制"),
            QAItem(q="什么是多态？", a="多态是同一接口在不同对象上表现出不同行为的能力"),
            QAItem(q="什么是封装？", a="封装是将数据和操作数据的方法绑定在一起的机制")
        ]
    )
    
    return [python_chapter, ds_chapter, oop_chapter]


async def demo_generate_single_chapter_prompt() -> bool:
    """演示为单个章节生成提示词"""
    print("=" * 80)
    print("BackwardService _generate_chapter_prompt 方法演示 - 单章节测试")
    print("=" * 80)
    
    # 初始化LLM客户端和服务
    print("1. 初始化LLM客户端和BackwardService...")
    llm_client = LLM()
    backward_service = BackwardService(llm_client=llm_client)
    
    # 创建测试章节
    print("2. 创建测试章节...")
    sample_chapters = create_sample_chapter_groups()
    test_chapter = sample_chapters[0]  # 使用Python基础章节
    
    print(f"   → 章节名称: {test_chapter.chapter_name}")
    print(f"   → 聚合原因: {test_chapter.reason}")
    print(f"   → 包含Q&A数量: {len(test_chapter.qas)}")
    
    # 显示章节中的Q&A
    print("\n3. 章节中的Q&A内容:")
    for i, qa in enumerate(test_chapter.qas, 1):
        print(f"   {i}. Q: {qa.q}")
        print(f"      A: {qa.a}")
    
    # 测试生成提示词
    print("\n4. 调用 _generate_chapter_prompt 方法...")
    try:
        # 添加额外指令
        extra_instructions = "请生成专业、准确、简洁的技术文档风格提示词，强调基于提供的示例回答问题"
        
        # 创建新的AIContext用于测试
        ctx = AIContext()
        
        # 调用方法
        result_chapter = await backward_service._generate_chapter_prompt(
            chapter_group=test_chapter,
            extra_instructions=extra_instructions,
            ctx=ctx
        )
        
        print("   ✓ 提示词生成完成！")
        
        # 显示生成的提示词
        print("\n5. 生成的章节提示词:")
        print("-" * 60)
        print(result_chapter.prompt)
        print("-" * 60)
        
        # 验证结果
        print("\n6. 验证结果:")
        print(f"   → 原章节名称: {test_chapter.chapter_name}")
        print(f"   → 结果章节名称: {result_chapter.chapter_name}")
        prompt_len = len(result_chapter.prompt) if result_chapter.prompt else 0
        print(f"   → 提示词长度: {prompt_len} 字符")
        print(f"   → 是否成功生成: {'是' if result_chapter.prompt else '否'}")
        
    except Exception as e:
        print(f"   ✗ 提示词生成失败: {e}")
        return False
    
    return True


async def demo_generate_multiple_chapters_prompt() -> bool:
    """演示为多个章节生成提示词"""
    print("\n" + "=" * 80)
    print("BackwardService _generate_chapter_prompt 方法演示 - 多章节测试")
    print("=" * 80)
    
    # 初始化LLM客户端和服务
    print("1. 初始化LLM客户端和BackwardService...")
    llm_client = LLM()
    backward_service = BackwardService(llm_client=llm_client)
    
    # 创建测试章节
    print("2. 创建多个测试章节...")
    sample_chapters = create_sample_chapter_groups()
    
    print(f"   → 总共创建了 {len(sample_chapters)} 个章节")
    for i, chapter in enumerate(sample_chapters, 1):
        print(f"   {i}. {chapter.chapter_name} ({len(chapter.qas)} 个Q&A)")
    
    # 为每个章节生成提示词
    print("\n3. 为每个章节生成提示词...")
    results = []
    
    for i, chapter in enumerate(sample_chapters, 1):
        print(f"\n   处理章节 {i}: {chapter.chapter_name}")
        
        try:
            # 为不同章节使用不同的额外指令
            extra_instructions_map = {
                "Python基础语法": "重点关注代码示例和语法规则，提供实用的编程指导",
                "基础数据结构": "强调概念定义和应用场景，帮助理解数据结构的选择和使用",
                "面向对象编程原理": "注重原理解释和概念关系，建立清晰的OOP思维框架"
            }
            
            extra_instructions = extra_instructions_map.get(
                chapter.chapter_name, 
                "请基于提供的示例生成准确、专业的回答"
            )
            
            # 创建独立的AIContext
            ctx = AIContext()
            
            # 调用方法
            result_chapter = await backward_service._generate_chapter_prompt(
                chapter_group=chapter,
                extra_instructions=extra_instructions,
                ctx=ctx
            )
            
            results.append(result_chapter)
            print(f"   ✓ 章节 {i} 提示词生成完成")
            
        except Exception as e:
            print(f"   ✗ 章节 {i} 提示词生成失败: {e}")
            results.append(chapter)  # 保留原章节
    
    # 显示所有结果
    print("\n4. 所有章节的提示词生成结果:")
    for i, chapter in enumerate(results, 1):
        print(f"\n--- 章节 {i}: {chapter.chapter_name} ---")
        if chapter.prompt:
            print(f"提示词长度: {len(chapter.prompt)} 字符")
            print("提示词内容:")
            if len(chapter.prompt) > 200:
                print(chapter.prompt[:200] + "...")
            else:
                print(chapter.prompt)
        else:
            print("⚠ 未生成提示词")
    
    # 统计结果
    success_count = sum(1 for chapter in results if chapter.prompt)
    print("\n5. 生成统计:")
    print(f"   → 总章节数: {len(sample_chapters)}")
    print(f"   → 成功生成: {success_count}")
    print(f"   → 失败数量: {len(sample_chapters) - success_count}")
    print(f"   → 成功率: {success_count / len(sample_chapters) * 100:.1f}%")
    
    return success_count == len(sample_chapters)


async def demo_prompt_template_validation() -> bool:
    """演示提示词模板验证"""
    print("\n" + "=" * 80)
    print("提示词模板验证演示")
    print("=" * 80)
    
    from agent_runtime.services.backward_service import (
        gen_p_user_template, GEN_P_SYS
    )
    
    print("1. 显示系统提示词模板:")
    print("-" * 60)
    print(GEN_P_SYS)
    print("-" * 60)
    
    print("\n2. 测试用户提示词模板渲染:")
    sample_chapter = create_sample_chapter_groups()[0]
    
    rendered = gen_p_user_template.render(
        chapter_name=sample_chapter.chapter_name,
        reason=sample_chapter.reason,
        qas=sample_chapter.qas,
        extra_instructions="这是测试额外指令"
    )
    
    print("渲染结果:")
    print("-" * 60)
    print(rendered)
    print("-" * 60)
    
    return True


async def main() -> None:
    """主函数"""
    print("开始 BackwardService _generate_chapter_prompt 方法演示...")
    
    # 单章节测试
    success1 = await demo_generate_single_chapter_prompt()
    
    # 多章节测试
    success2 = await demo_generate_multiple_chapters_prompt()
    
    # 模板验证
    success3 = await demo_prompt_template_validation()
    
    print("\n" + "=" * 80)
    print("演示总结:")
    print(f"单章节测试: {'✓ 成功' if success1 else '✗ 失败'}")
    print(f"多章节测试: {'✓ 成功' if success2 else '✗ 失败'}")
    print(f"模板验证: {'✓ 成功' if success3 else '✗ 失败'}")
    print("=" * 80)
    
    print("\n演示结束。")


if __name__ == "__main__":
    # 运行演示
    asyncio.run(main())