#!/usr/bin/env python3
"""
基于 chapter_structure.json 生成 mermaid 结构图
"""
import json
import os
from typing import Dict, List, Any

def load_chapter_structure(file_path: str) -> Dict[str, Any]:
    """加载章节结构数据"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def sanitize_node_id(node_id: str) -> str:
    """清理节点ID，确保mermaid兼容"""
    # 移除特殊字符，替换为下划线
    sanitized = node_id.replace('-', '_').replace(' ', '_')
    return sanitized

def generate_mermaid_flowchart(chapter_data: Dict[str, Any]) -> str:
    """生成 mermaid 流程图代码"""
    nodes = chapter_data['nodes']
    root_ids = chapter_data['root_ids']
    
    mermaid_lines = [
        "```mermaid",
        "flowchart TD",
        "    %% 知识库章节结构图",
        ""
    ]
    
    # 定义节点样式
    level_styles = {
        1: ":::level1",
        2: ":::level2", 
        3: ":::level3"
    }
    
    # 生成节点定义
    mermaid_lines.append("    %% 节点定义")
    for node_id, node in nodes.items():
        sanitized_id = sanitize_node_id(node_id)
        title = node['title'].replace('"', '\\"')  # 转义引号
        level = node.get('level', 1)
        chapter_number = node.get('chapter_number', '')
        
        # 构建节点标签
        if chapter_number:
            label = f"{chapter_number} {title}"
        else:
            label = title
            
        # 根据层级选择节点形状
        if level == 1:
            node_def = f"    {sanitized_id}[\"{label}\"]"
        elif level == 2:
            node_def = f"    {sanitized_id}(\"{label}\")"
        else:
            node_def = f"    {sanitized_id}{{\"{label}\"}}"
            
        mermaid_lines.append(node_def)
    
    mermaid_lines.append("")
    
    # 生成连接关系
    mermaid_lines.append("    %% 层次关系")
    for node_id, node in nodes.items():
        if node.get('children'):
            sanitized_parent = sanitize_node_id(node_id)
            for child_id in node['children']:
                sanitized_child = sanitize_node_id(child_id)
                mermaid_lines.append(f"    {sanitized_parent} --> {sanitized_child}")
    
    mermaid_lines.append("")
    
    # 添加样式定义
    mermaid_lines.extend([
        "    %% 样式定义",
        "    classDef level1 fill:#e1f5fe,stroke:#01579b,stroke-width:3px,color:#000",
        "    classDef level2 fill:#f3e5f5,stroke:#4a148c,stroke-width:2px,color:#000", 
        "    classDef level3 fill:#fff3e0,stroke:#e65100,stroke-width:1px,color:#000",
        ""
    ])
    
    # 应用样式到节点
    mermaid_lines.append("    %% 应用样式")
    for node_id, node in nodes.items():
        sanitized_id = sanitize_node_id(node_id)
        level = node.get('level', 1)
        if level in level_styles:
            mermaid_lines.append(f"    class {sanitized_id} level{level}")
    
    mermaid_lines.append("```")
    
    return '\n'.join(mermaid_lines)

def generate_mermaid_mindmap(chapter_data: Dict[str, Any]) -> str:
    """生成 mermaid 思维导图代码"""
    nodes = chapter_data['nodes']
    root_ids = chapter_data['root_ids']
    
    mermaid_lines = [
        "```mermaid",
        "mindmap",
        "  root((知识库))",
        ""
    ]
    
    def add_node_recursive(node_id: str, indent: str = "    "):
        """递归添加节点"""
        if node_id not in nodes:
            return
            
        node = nodes[node_id]
        title = node['title']
        chapter_number = node.get('chapter_number', '')
        
        # 构建节点标签
        if chapter_number:
            label = f"{chapter_number} {title}"
        else:
            label = title
            
        # 根据层级选择节点样式
        level = node.get('level', 1)
        if level == 1:
            node_line = f"{indent}{label}"
        elif level == 2:
            node_line = f"{indent}({label})"
        else:
            node_line = f"{indent}[{label}]"
            
        mermaid_lines.append(node_line)
        
        # 递归处理子节点
        if node.get('children'):
            for child_id in node['children']:
                add_node_recursive(child_id, indent + "  ")
    
    # 从根节点开始构建
    for root_id in root_ids:
        add_node_recursive(root_id)
    
    mermaid_lines.append("```")
    
    return '\n'.join(mermaid_lines)

def generate_mermaid_tree(chapter_data: Dict[str, Any]) -> str:
    """生成 mermaid 树形图代码（Git Graph 风格）"""
    nodes = chapter_data['nodes']
    root_ids = chapter_data['root_ids']
    
    mermaid_lines = [
        "```mermaid",
        "graph TD",
        "    subgraph \"智能问答知识库结构\"",
        ""
    ]
    
    # 生成节点和连接
    for node_id, node in nodes.items():
        sanitized_id = sanitize_node_id(node_id)
        title = node['title']
        chapter_number = node.get('chapter_number', '')
        level = node.get('level', 1)
        
        # 构建节点标签
        if chapter_number:
            label = f"{chapter_number}<br/>{title}"
        else:
            label = title
            
        # 根据层级选择节点形状和颜色
        if level == 1:
            node_def = f"        {sanitized_id}[\"{label}\"]"
            mermaid_lines.append(node_def)
        elif level == 2:
            node_def = f"        {sanitized_id}(\"{label}\")"
            mermaid_lines.append(node_def)
        else:
            node_def = f"        {sanitized_id}{{\"{label}\"}}"
            mermaid_lines.append(node_def)
    
    mermaid_lines.append("")
    
    # 生成连接关系
    for node_id, node in nodes.items():
        if node.get('children'):
            sanitized_parent = sanitize_node_id(node_id)
            for child_id in node['children']:
                sanitized_child = sanitize_node_id(child_id)
                mermaid_lines.append(f"        {sanitized_parent} --> {sanitized_child}")
    
    mermaid_lines.append("    end")
    mermaid_lines.append("```")
    
    return '\n'.join(mermaid_lines)

def generate_statistics_table(chapter_data: Dict[str, Any]) -> str:
    """生成章节统计信息表格"""
    nodes = chapter_data['nodes']
    
    # 统计各层级章节数量
    level_counts = {}
    total_cqa_items = 0
    
    for node in nodes.values():
        level = node.get('level', 1)
        level_counts[level] = level_counts.get(level, 0) + 1
        
        cqa_items = node.get('related_cqa_items', [])
        total_cqa_items += len(cqa_items)
    
    table_lines = [
        "## 📊 章节结构统计",
        "",
        "| 层级 | 数量 | 描述 |",
        "|------|------|------|"
    ]
    
    level_descriptions = {
        1: "主要领域",
        2: "技术分支", 
        3: "具体主题"
    }
    
    for level in sorted(level_counts.keys()):
        desc = level_descriptions.get(level, f"第{level}层")
        table_lines.append(f"| {level} | {level_counts[level]} | {desc} |")
    
    table_lines.extend([
        "",
        f"**总章节数**: {len(nodes)}  ",
        f"**问答条目数**: {total_cqa_items}  ",
        f"**最大层级**: {max(level_counts.keys())}  ",
        ""
    ])
    
    return '\n'.join(table_lines)

def main():
    """主函数"""
    # 获取文件路径
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    input_file = os.path.join(project_root, "exps", "data", "chapter_structure.json")
    output_file = os.path.join(project_root, "docs", "CHAPTER_STRUCTURE_MERMAID.md")
    
    try:
        print("开始生成 mermaid 结构图...")
        
        # 加载数据
        chapter_data = load_chapter_structure(input_file)
        
        # 生成不同类型的图表
        print("生成流程图...")
        flowchart = generate_mermaid_flowchart(chapter_data)
        
        print("生成思维导图...")
        mindmap = generate_mermaid_mindmap(chapter_data)
        
        print("生成树形图...")
        tree_graph = generate_mermaid_tree(chapter_data)
        
        print("生成统计表格...")
        statistics = generate_statistics_table(chapter_data)
        
        # 组合生成完整文档
        full_content = f"""# 智能问答知识库结构图

基于 `chapter_structure.json` 生成的章节结构可视化图表。

{statistics}

## 🌲 层次结构流程图

{flowchart}

## 🧠 思维导图

{mindmap}

## 📋 树形结构图

{tree_graph}

## 📝 使用说明

### 图表说明
- **矩形框**: 一级章节（主要领域）
- **圆角框**: 二级章节（技术分支）
- **菱形框**: 三级章节（具体主题）

### 颜色含义
- **蓝色**: 一级章节（主要技术领域）
- **紫色**: 二级章节（细分技术方向）
- **橙色**: 三级章节（具体实现主题）

### 在线预览
可以将 mermaid 代码复制到以下平台进行在线预览：
- [Mermaid Live Editor](https://mermaid.live/)
- [GitHub Markdown](https://github.com) (原生支持)
- [GitLab](https://gitlab.com) (原生支持)

---
*生成时间: {chapter_data.get('syncTime', 'Unknown')}*
"""
        
        # 保存文件
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(full_content)
        
        print(f"\n✅ Mermaid 结构图生成完成!")
        print(f"输出文件: {output_file}")
        print(f"包含 {len(chapter_data['nodes'])} 个章节节点")
        
    except Exception as e:
        print(f"❌ 生成失败: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)