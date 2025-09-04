#!/usr/bin/env python3
"""
将 chapter_structure.json 转换为 documentTree.json 格式
创建根节点，第一级章节放在根节点下，并在根节点内容中包含 mermaid 结构图
"""
import json
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

def generate_mermaid_structure(chapter_data: Dict[str, Any]) -> str:
    """生成基于章节结构的 mermaid 图表"""
    nodes = chapter_data['nodes']
    root_ids = chapter_data['root_ids']
    
    mermaid_lines = [
        "```mermaid",
        "flowchart TD",
        "    %% 智能问答知识库章节结构",
        "    ROOT[🎯 智能问答知识库]",
        ""
    ]
    
    # 生成节点定义
    for node_id, node in nodes.items():
        title = node['title']
        level = node.get('level', 1)
        chapter_number = node.get('chapter_number', '')
        
        # 根据层级选择图标和样式
        if level == 1:
            icon = "🔵"
            label = f"{chapter_number} {title}" if chapter_number else title
            node_def = f"    {node_id}[\"{icon} {label}\"]"
        elif level == 2:
            icon = "🔷"
            label = f"{chapter_number} {title}" if chapter_number else title
            node_def = f"    {node_id}(\"{icon} {label}\")"
        else:
            icon = "🔸"
            label = f"{chapter_number} {title}" if chapter_number else title
            node_def = f"    {node_id}{{\"{icon} {label}\"}}"
            
        mermaid_lines.append(node_def)
    
    mermaid_lines.append("")
    
    # 生成连接关系
    mermaid_lines.append("    %% 层次关系")
    
    # 根节点连接到一级章节
    for root_id in root_ids:
        mermaid_lines.append(f"    ROOT --> {root_id}")
    
    # 章节间的层次关系
    for node_id, node in nodes.items():
        if node.get('children'):
            for child_id in node['children']:
                mermaid_lines.append(f"    {node_id} --> {child_id}")
    
    mermaid_lines.append("")
    
    # 添加样式定义
    mermaid_lines.extend([
        "    %% 样式定义",
        "    classDef root fill:#ff6b6b,stroke:#c92a2a,stroke-width:3px,color:#fff",
        "    classDef level1 fill:#51cf66,stroke:#2b8a3e,stroke-width:2px,color:#000",
        "    classDef level2 fill:#74c0fc,stroke:#1971c2,stroke-width:2px,color:#000",
        "    classDef level3 fill:#ffd43b,stroke:#fab005,stroke-width:1px,color:#000",
        ""
    ])
    
    # 应用样式
    mermaid_lines.append("    %% 应用样式")
    mermaid_lines.append("    class ROOT root")
    
    for node_id, node in nodes.items():
        level = node.get('level', 1)
        mermaid_lines.append(f"    class {node_id} level{level}")
    
    mermaid_lines.append("```")
    
    return '\n'.join(mermaid_lines)

def convert_chapter_node_to_document(node: Dict[str, Any], node_id: str) -> Dict[str, Any]:
    """将章节节点转换为文档节点"""
    current_time = datetime.now().isoformat()
    
    # 构建content内容
    content_parts = []
    
    # 添加标题和描述
    content_parts.append(f"# {node['title']}\n")
    if node.get('description'):
        content_parts.append(f"{node['description']}\n")
    
    # 添加章节内容
    if node.get('content'):
        content_parts.append(f"\n## 章节内容\n\n{node['content']}\n")
    
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
        "id": int(datetime.now().timestamp() * 1000000 + hash(node_id) % 1000000),
        "title": node['title'],
        "type": "document",
        "content": "".join(content_parts),
        "children": [],
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
    
    # 返回一级章节（根节点的直接子节点）
    root_documents = []
    for root_id in root_ids:
        if root_id in converted_nodes:
            root_documents.append(converted_nodes[root_id])
    
    return root_documents

def create_root_document_with_mermaid(chapter_data: Dict[str, Any]) -> Dict[str, Any]:
    """创建包含 mermaid 结构图的根文档"""
    current_time = datetime.now().isoformat()
    
    # 生成 mermaid 结构图
    mermaid_structure = generate_mermaid_structure(chapter_data)
    
    # 统计信息
    total_nodes = len(chapter_data['nodes'])
    total_cqa = sum(len(node.get('related_cqa_items', [])) for node in chapter_data['nodes'].values())
    level_counts = {}
    for node in chapter_data['nodes'].values():
        level = node.get('level', 1)
        level_counts[level] = level_counts.get(level, 0) + 1
    
    # 构建根文档内容
    root_content = f"""# 智能问答知识库

## 📊 知识库概览

本知识库包含了人工智能、前端开发、数据库等技术领域的系统性知识内容。

### 统计信息
- **总章节数**: {total_nodes}
- **问答条目数**: {total_cqa}
- **技术领域**: {len(chapter_data['root_ids'])}个主要领域
- **知识层级**: {max(level_counts.keys())}层结构

### 章节层级分布
"""
    
    level_descriptions = {1: "主要技术领域", 2: "技术分支", 3: "具体主题"}
    for level in sorted(level_counts.keys()):
        desc = level_descriptions.get(level, f"第{level}层")
        root_content += f"- **{desc}**: {level_counts[level]}个章节\n"
    
    root_content += f"""
## 🌲 知识库结构图

{mermaid_structure}

## 📚 主要技术领域

"""
    
    # 添加主要领域介绍
    for root_id in chapter_data['root_ids']:
        if root_id in chapter_data['nodes']:
            node = chapter_data['nodes'][root_id]
            root_content += f"### {node['title']}\n\n{node.get('description', '')}\n\n"
    
    root_content += """## 🎯 使用说明

### 导航方式
1. **按领域浏览**: 从三大技术领域入手，逐层深入
2. **搜索关键词**: 利用问答内容快速定位相关知识点
3. **结构化学习**: 按照层次结构系统性学习技术知识

### 图表说明
- 🎯 **根节点**: 知识库总入口
- 🔵 **一级节点**: 主要技术领域（蓝色圆形）
- 🔷 **二级节点**: 技术分支（蓝色菱形）
- 🔸 **三级节点**: 具体主题（黄色六边形）

### 内容特色
- **系统性**: 完整的技术知识体系
- **实用性**: 包含大量实际问答案例
- **可视化**: 直观的结构图展示知识关系
- **分层级**: 从概念到实践的渐进式学习路径

---
*最后更新: {current_time}*
"""
    
    return {
        "id": int(datetime.now().timestamp() * 1000000),
        "title": "智能问答知识库",
        "type": "document",
        "content": root_content,
        "children": [],
        "createdAt": current_time,
        "lastModified": current_time
    }

def convert_chapter_structure_to_document_tree_with_root(chapter_data: Dict[str, Any]) -> Dict[str, Any]:
    """主转换函数 - 创建根节点结构"""
    current_time = datetime.now().isoformat()
    
    # 创建根文档（包含 mermaid 结构图）
    root_document = create_root_document_with_mermaid(chapter_data)
    
    # 构建一级章节的文档树
    first_level_documents = build_document_tree(chapter_data['nodes'], chapter_data['root_ids'])
    
    # 将一级章节添加到根文档的 children 中
    root_document['children'] = first_level_documents
    
    # 创建手册结构
    manual = {
        "id": int(datetime.now().timestamp() * 1000000 + 1),
        "title": "智能问答知识库手册",
        "type": "manual",
        "author": "系统生成",
        "tags": ["知识库", "技术文档", "智能问答"],
        "document": [root_document],  # 根文档作为唯一顶级文档
        "createdAt": current_time,
        "description": "基于章节结构生成的智能问答知识库，包含人工智能、前端开发、数据库等技术领域的系统性知识"
    }
    
    # 构建完整的documentTree结构
    document_tree = {
        "manuals": [manual],
        "syncTime": current_time,
        "totalManuals": 1,
        "_metadata": {
            "uploadTime": current_time,
            "version": int(datetime.now().timestamp() * 1000000),
            "convertedFrom": "chapter_structure.json",
            "conversionType": "with_mermaid_root_structure"
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
    output_file = os.path.join(project_root, "exps", "data", "document_tree_with_mermaid_root.json")
    
    try:
        print("开始转换章节结构到文档树格式（包含根节点和 mermaid 结构图）...")
        
        # 加载源数据
        print(f"读取文件: {input_file}")
        chapter_data = load_json(input_file)
        
        # 执行转换
        print("执行格式转换...")
        document_tree = convert_chapter_structure_to_document_tree_with_root(chapter_data)
        
        # 保存结果
        print(f"保存结果到: {output_file}")
        save_json(document_tree, output_file)
        
        # 输出统计信息
        total_chapters = len(chapter_data['nodes'])
        root_document = document_tree['manuals'][0]['document'][0]
        total_first_level = len(root_document['children'])
        
        print(f"\n✅ 转换完成!")
        print(f"- 原始章节数: {total_chapters}")
        print(f"- 根文档: 1个（包含 mermaid 结构图）")
        print(f"- 一级章节数: {total_first_level}")
        print(f"- 输出文件: {output_file}")
        print("\n🌲 结构特点:")
        print("- 创建了统一的根节点包含整体结构图")
        print("- 一级章节作为根节点的直接子节点")
        print("- 根节点内容包含完整的 mermaid 可视化图表")
        
    except FileNotFoundError as e:
        print(f"❌ 文件未找到: {e}")
        return False
    except json.JSONDecodeError as e:
        print(f"❌ JSON解析错误: {e}")
        return False
    except Exception as e:
        print(f"❌ 转换失败: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)