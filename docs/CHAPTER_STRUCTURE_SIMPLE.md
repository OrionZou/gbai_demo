# 智能问答知识库结构图（简化版）

基于 `chapter_structure.json` 生成的简化版章节结构图。

## 📊 结构概览

- **3个主要领域**: 人工智能基础、前端开发基础、数据库基础概念
- **20个章节节点**: 包含3个层级的知识体系
- **45个问答条目**: 覆盖各技术领域的核心问题

## 🌲 知识库结构图

```mermaid
flowchart TD
    %% 主要领域（一级）
    AI["🤖 人工智能基础"]
    FE["💻 前端开发基础"] 
    DB["🗄️ 数据库基础概念"]
    
    %% 人工智能分支（二级）
    ML["📚 机器学习技术"]
    AI_BRANCH["🔬 人工智能分支领域"]
    
    %% 前端技术分支（二级）
    FE_CORE["⚡ 前端核心技术"]
    FE_ARCH["🏗️ 前端架构与工程化"]
    
    %% 数据库技术分支（二级）
    SQL["📝 SQL语言与操作"]
    PERF["⚡ 数据库性能优化"]
    TRANS["🔐 数据库事务与设计"]
    NOSQL["📊 NoSQL数据库"]
    
    %% 深度学习（三级）
    DL["🧠 深度学习"]
    
    %% 容器化（三级）
    DOCKER["🐳 容器化与部署"]
    
    %% 建立连接
    AI --> ML
    AI --> AI_BRANCH
    ML --> DL
    
    FE --> FE_CORE
    FE --> FE_ARCH
    FE_ARCH --> DOCKER
    
    DB --> SQL
    DB --> PERF
    DB --> TRANS
    DB --> NOSQL
    
    %% 样式定义
    classDef level1 fill:#e3f2fd,stroke:#1976d2,stroke-width:3px,color:#000
    classDef level2 fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px,color:#000
    classDef level3 fill:#fff8e1,stroke:#f57c00,stroke-width:2px,color:#000
    
    %% 应用样式
    class AI,FE,DB level1
    class ML,AI_BRANCH,FE_CORE,FE_ARCH,SQL,PERF,TRANS,NOSQL level2
    class DL,DOCKER level3
```

## 🧠 思维导图

```mermaid
mindmap
  root((🎯 智能问答知识库))
    🤖 人工智能基础
      📚 机器学习技术
        🧠 深度学习
      🔬 人工智能分支领域
    💻 前端开发基础
      ⚡ 前端核心技术
      🏗️ 前端架构与工程化
        🐳 容器化与部署
    🗄️ 数据库基础概念
      📝 SQL语言与操作
      ⚡ 数据库性能优化
      🔐 数据库事务与设计
      📊 NoSQL数据库
```

## 📋 技术领域分布

```mermaid
pie title 各技术领域章节分布
    "人工智能" : 4
    "前端开发" : 11
    "数据库技术" : 5
```

## 🎯 使用指南

### 图表说明
- **🤖/💻/🗄️**: 主要技术领域（一级章节）
- **📚/⚡/🏗️**: 技术分支（二级章节）
- **🧠/🐳**: 具体主题（三级章节）

### 在线预览
将上述 mermaid 代码复制到 [Mermaid Live Editor](https://mermaid.live/) 可进行在线预览和编辑。

### 关键特点
1. **层次清晰**: 从领域 → 分支 → 主题的3层结构
2. **覆盖全面**: 涵盖AI、前端、数据库三大技术方向
3. **实用性强**: 每个节点都包含相关的问答知识点

---
*基于 chapter_structure.json 自动生成*