import json
import asyncio
from typing import List

from agent_runtime.agents.cqa_agent import CQAAgent
from agent_runtime.clients.llm.openai_client import LLM
from agent_runtime.data_format.qa_format import QAList, QAItem, CQAList


def load_test_data(file_path: str, limit: int = 1) -> List[dict]:
    """加载测试数据"""
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data[:limit]


def extract_qa_from_conversation(conversations: List[dict]) -> QAList:
    """从对话中提取Q&A对"""
    qa_list = QAList()

    q = ""
    a = ""
    last_conv = conversations[0]
    for conv in conversations:
        if last_conv["from"] == "gpt" and conv["from"] == "human":
            qa_list.add_qa(question=q, answer=a)
            q = ""
            a = ""
        if conv["from"] == "human":
            q = f"{q}\n" + conv["value"]
            last_conv = conv
        elif conv["from"] == "gpt":
            a = f"{a}\n" + conv["value"]
            last_conv = conv
    if last_conv["from"] == "gpt":
        qa_list.add_qa(question=q, answer=a)
        q = ""
        a = ""
    return qa_list


def export_cqa_to_json(cqa_list: CQAList, output_file: str) -> None:
    """导出CQA列表到JSON文件"""
    data = {
        "session_id": cqa_list.session_id,
        "items": []
    }
    
    for item in cqa_list.items:
        data["items"].append({
            "context": item.context,
            "question": item.question,
            "answer": item.answer,
            "metadata": item.metadata
        })
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"CQA数据已导出到: {output_file}")


async def test_cqa_agent():
    """测试CQAAgent"""
    print("开始测试CQAAgent...")

    # 初始化LLM客户端
    llm_engine = LLM()

    # 初始化CQAAgent
    cqa_agent = CQAAgent(llm_engine=llm_engine, agent_name="cqa_agent")

    # 加载测试数据
    test_data = load_test_data("./dataset/APIGen-MT-5k/apigen-mt_5k_zh10.json", limit=10)

    for i, data_item in enumerate(test_data):
        print(f"\n=== 测试样本 {i+1} ===")

        conversations = data_item["conversations"]
        print(f"原始对话轮数: {len(conversations)}")

        # 提取Q&A
        qa_list = extract_qa_from_conversation(conversations)
        print(f"提取到的Q&A对数: {len(qa_list.items)}")

        # 显示原始Q&A
        print("\n原始Q&A序列:")
        for j, qa_item in enumerate(qa_list.items):
            print(f"{j}. Q: {qa_item.question[:100]}...")
            print(f"   A: {qa_item.answer[:100]}...")

        # 转换为C&Q&A
        print("\n正在使用CQAAgent转换...")
        try:
            cqa_list = await cqa_agent.transform_qa_to_cqa(qa_list)

            print(f"转换后的C&Q&A对数: {len(cqa_list.items)}")

            # 显示转换结果
            print("\n转换后的C&Q&A序列:")
            for j, cqa_item in enumerate(cqa_list.items):
                # print(
                #     f"{j}. Context: {cqa_item.context[:150] if cqa_item.context else '(无上下文)'}..."
                # )
                # print(f"   Question: {cqa_item.question[:100]}...")
                # print(f"   Answer: {cqa_item.answer[:100]}...")
                print(cqa_item)

            # 导出CQA数据到JSON文件
            output_file = f"cqa_output_sample_{i+1}.json"
            export_cqa_to_json(cqa_list, output_file)

        except Exception as e:
            print(f"转换失败: {e}")
            continue


if __name__ == "__main__":
    # 然后测试完整的CQA转换（需要LLM）
    asyncio.run(test_cqa_agent())
