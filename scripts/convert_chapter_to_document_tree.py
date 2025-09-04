#!/usr/bin/env python3
"""
将 chapter_structure.json 转换为 documentTree.json 格式
"""
import json
import sys
import os
from datetime import datetime
from typing import Dict, List, Any

def load_json(file_path: str) -> Dict[str, Any]:
    """加载JSON文件"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(data: Dict[str, Any], file_path: str):
    """保存JSON文件"""
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def convert_chapter_node_to_document(node: Dict[str, Any], node_id: str) -> Dict[str, Any]:
    """将章节节点转换为文档节点"""
    current_time = datetime.now().isoformat()
    
    # 构建content内容，包含原始信息
    content_parts = []
    
    # 添加标题和描述
    content_parts.append(f"# {node['title']}\n")
    if node.get('description'):
        content_parts.append(f"{node['description']}\n")
    
    # 添加章节内容
    if node.get('content'):
        content_parts.append(f"\n## 内容\n\n{node['content']}\n")
    
    # 添加相关问答
    if node.get('related_cqa_items'):
        content_parts.append("\n## 相关问答\n")
        for i, item in enumerate(node['related_cqa_items'], 1):
            content_parts.append(f"\n### 问答 {i}\n")
            content_parts.append(f"**问题**: {item['question']}\n")
            content_parts.append(f"**答案**: {item['answer']}\n")
            if item.get('context'):
                content_parts.append(f"**上下文**: {item['context']}\n")
    
    return {
        "id": int(datetime.now().timestamp() * 1000),  # 生成唯一ID
        "title": node['title'],
        "type": "document",
        "content": "".join(content_parts),
        "children": [],  # 子节点稍后填充
        "createdAt": current_time,
        "lastModified": current_time
    }

def build_document_tree(nodes: Dict[str, Any], root_ids: List[str]) -> List[Dict[str, Any]]:
    """构建文档树结构"""
    # 转换所有节点
    converted_nodes = {}
    for node_id, node in nodes.items():
        converted_nodes[node_id] = convert_chapter_node_to_document(node, node_id)
    
    # 构建父子关系
    for node_id, node in nodes.items():
        if node.get('children'):
            for child_id in node['children']:
                if child_id in converted_nodes:
                    converted_nodes[node_id]['children'].append(converted_nodes[child_id])
    
    # 返回根节点
    root_documents = []
    for root_id in root_ids:
        if root_id in converted_nodes:
            root_documents.append(converted_nodes[root_id])
    
    return root_documents

def convert_chapter_structure_to_document_tree(chapter_data: Dict[str, Any]) -> Dict[str, Any]:
    """主转换函数"""
    current_time = datetime.now().isoformat()
    
    # 构建文档树
    documents = build_document_tree(
        chapter_data['nodes'], 
        chapter_data['root_ids']
    )
    
    # 创建手册结构
    manual = {
        "id": int(datetime.now().timestamp() * 1000),
        "title": "智能问答知识库",
        "type": "manual", 
        "author": "系统转换",
        "tags": [],
        "document": documents,
        "createdAt": current_time,
        "description": "从章节结构转换而来的知识库文档"
    }
    
    # 构建完整的documentTree结构
    document_tree = {
        "manuals": [manual],
        "syncTime": current_time,
        "totalManuals": 1,
        "_metadata": {
            "uploadTime": current_time,
            "version": int(datetime.now().timestamp() * 1000),
            "convertedFrom": "chapter_structure.json"
        }
    }
    
    return document_tree

def main():
    """主函数"""
    # 获取项目根目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    
    # 输入和输出文件路径
    input_file = os.path.join(project_root, "exps", "data", "chapter_structure.json")
    output_file = os.path.join(project_root, "exps", "data", "converted_document_tree.json")
    
    try:
        print("开始转换章节结构到文档树格式...")
        
        # 加载源数据
        print(f"读取文件: {input_file}")
        chapter_data = load_json(input_file)
        
        # 执行转换
        print("执行格式转换...")
        document_tree = convert_chapter_structure_to_document_tree(chapter_data)
        
        # 保存结果
        print(f"保存结果到: {output_file}")
        save_json(document_tree, output_file)
        
        # 输出统计信息
        total_chapters = len(chapter_data['nodes'])
        total_documents = len(document_tree['manuals'][0]['document'])
        print(f"\n✅ 转换完成!")
        print(f"- 原始章节数: {total_chapters}")
        print(f"- 转换文档数: {total_documents}")
        print(f"- 输出文件: {output_file}")
        
    except FileNotFoundError as e:
        print(f"❌ 文件未找到: {e}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ JSON解析错误: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 转换失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()