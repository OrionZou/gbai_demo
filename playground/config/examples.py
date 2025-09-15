"""
示例数据配置
提供各种API测试的示例数据
"""


# Reward API 示例数据
REWARD_EXAMPLES = {
    "自定义输入": {},
    "简单示例 - 地理题": {
        "question": "世界上最大的海洋是哪个？",
        "candidates": ["大西洋", "太平洋", "印度洋", "北冰洋", "地中海"],
        "target_answer": "太平洋"
    },
    "复杂示例 - 阅读理解": {
        "question": "请总结《西游记》中唐僧西天取经的目的。",
        "candidates": [
            "唐僧带领孙悟空、猪八戒、沙僧历经九九八十一难前往西天取经，为了取得真经。",
            "唐僧此行是因为皇帝派遣他寻找宝物。",
            "取经的最终目的，是为了获取佛经，弘扬佛法，普度众生。",
            "唐僧和徒弟们一路降妖除魔，实际上是为了打败妖怪获得宝藏。",
            "这个故事主要讲述了团队合作、修行和坚持不懈的精神。"
        ],
        "target_answer": "唐僧此次取经的真正目的，是为了弘扬佛法，普度众生。"
    }
}


# Backward API 示例数据
BACKWARD_EXAMPLES = {
    "自定义输入": {
        "qas": [],
        "chapter_structure": None,
        "max_level": 3,
        "max_concurrent_llm": 10
    },
    "有现有章节示例(10条数据)": {
        "qas": [
            {
                "q": "什么是Docker容器？",
                "a": "Docker容器是轻量级的虚拟化技术，包含应用程序及其所有依赖项"
            },
            {
                "q": "容器与虚拟机的区别？",
                "a": "容器共享宿主机内核，虚拟机有独立的操作系统"
            },
            {
                "q": "Docker镜像是什么？",
                "a": "Docker镜像是创建容器的只读模板，包含运行应用所需的所有文件"
            },
            {
                "q": "如何构建Docker镜像？",
                "a": "使用Dockerfile文件和docker build命令来构建镜像"
            },
            {
                "q": "Docker Compose的作用是什么？",
                "a": "Docker Compose用于定义和运行多容器Docker应用程序"
            },
            {
                "q": "什么是Kubernetes？",
                "a": "Kubernetes是开源的容器编排平台，用于自动化部署、扩展和管理容器化应用"
            },
            {
                "q": "Pod是什么概念？",
                "a": "Pod是Kubernetes中最小的部署单元，可以包含一个或多个容器"
            },
            {
                "q": "什么是微服务架构？",
                "a": "微服务架构是将单一应用程序拆分为多个小型、独立服务的设计方法"
            },
            {
                "q": "容器网络如何工作？",
                "a": "容器网络通过虚拟网络接口和网桥技术实现容器间通信"
            },
            {
                "q": "Docker数据卷的作用？",
                "a": "Docker数据卷用于持久化存储容器数据，实现数据共享和备份"
            }
        ],
        "chapter_structure": {
            "nodes": {
                "chapter_1": {
                    "id": "chapter_1",
                    "title": "容器化基础",
                    "level": 1,
                    "parent_id": None,
                    "children": ["chapter_1_1", "chapter_1_2"],
                    "description": "容器化技术的基础概念和核心原理",
                    "related_qa_items": [],
                    "chapter_number": "1."
                },
                "chapter_1_1": {
                    "id": "chapter_1_1",
                    "title": "Docker核心概念",
                    "level": 2,
                    "parent_id": "chapter_1",
                    "children": [],
                    "description": "Docker容器、镜像等基础概念",
                    "related_qa_items": [],
                    "chapter_number": "1.1"
                },
                "chapter_1_2": {
                    "id": "chapter_1_2",
                    "title": "容器编排",
                    "level": 2,
                    "parent_id": "chapter_1",
                    "children": [],
                    "description": "Kubernetes和Docker Compose相关内容",
                    "related_qa_items": [],
                    "chapter_number": "1.2"
                }
            },
            "root_ids": ["chapter_1"],
            "max_level": 3
        },
        "max_level": 3,
        "max_concurrent_llm": 10
    },
    "无现有章节示例(10条数据)": {
        "qas": [
            {
                "q": "什么是机器学习？",
                "a": "机器学习是人工智能的一个分支，让计算机通过数据学习而无需明确编程"
            },
            {
                "q": "监督学习和无监督学习的区别？",
                "a": "监督学习使用标记数据训练，无监督学习从未标记数据中发现模式"
            },
            {
                "q": "什么是神经网络？",
                "a": "神经网络是模拟人脑神经元工作方式的计算模型"
            },
            {
                "q": "深度学习的特点是什么？",
                "a": "深度学习使用多层神经网络，能够自动提取数据特征"
            },
            {
                "q": "什么是自然语言处理？",
                "a": "自然语言处理是让计算机理解、解释和生成人类语言的技术"
            },
            {
                "q": "卷积神经网络的应用场景？",
                "a": "卷积神经网络主要用于图像识别、计算机视觉等领域"
            },
            {
                "q": "什么是强化学习？",
                "a": "强化学习是通过与环境交互来学习最优行为策略的机器学习方法"
            },
            {
                "q": "大语言模型是什么？",
                "a": "大语言模型是基于Transformer架构的大规模预训练语言模型"
            },
            {
                "q": "什么是数据预处理？",
                "a": "数据预处理是在机器学习前对原始数据进行清洗、转换和准备的过程"
            },
            {
                "q": "模型评估的重要性？",
                "a": "模型评估用于衡量机器学习模型的性能和泛化能力"
            }
        ],
        "chapter_structure": None,
        "max_level": 3,
        "max_concurrent_llm": 10
    }
}


# BQA Extract API 示例数据
BQA_EXTRACT_EXAMPLES = {
    "自定义输入": {
        "qa_lists": [],
        "context_extraction_mode": "auto",
        "preserve_session_info": True,
        "max_concurrent_processing": 3
    },
    "单个会话示例": {
        "qa_lists": [
            [
                {
                    "q": "什么是Python？",
                    "a": "Python是一种高级编程语言，以其简洁易读的语法而著称。"
                },
                {
                    "q": "它的主要特点是什么？",
                    "a": "Python具有语法简洁、跨平台、解释型等特点，适合快速开发。"
                },
                {
                    "q": "可以用来做什么？",
                    "a": "可以用于Web开发、数据分析、人工智能、自动化脚本等多个领域。"
                }
            ]
        ],
        "context_extraction_mode": "auto",
        "preserve_session_info": True,
        "max_concurrent_processing": 3
    },
    "多会话示例": {
        "qa_lists": [
            [
                {
                    "q": "什么是机器学习？",
                    "a": "机器学习是人工智能的一个分支，让计算机通过数据学习。"
                },
                {
                    "q": "有哪些类型？",
                    "a": "主要分为监督学习、无监督学习和强化学习三种类型。"
                },
                {
                    "q": "监督学习的特点是什么？",
                    "a": "监督学习使用标记数据进行训练，目标是学习输入到输出的映射关系。"
                }
            ],
            [
                {
                    "q": "什么是深度学习？",
                    "a": "深度学习是机器学习的一个子领域，使用多层神经网络。"
                },
                {
                    "q": "它与传统机器学习的区别？",
                    "a": "深度学习能自动提取特征，而传统机器学习需要手工设计特征。"
                },
                {
                    "q": "有什么应用场景？",
                    "a": "广泛应用于图像识别、自然语言处理、语音识别等领域。"
                }
            ]
        ],
        "context_extraction_mode": "detailed",
        "preserve_session_info": True,
        "max_concurrent_processing": 3
    },
    "最小化模式示例": {
        "qa_lists": [
            [
                {
                    "q": "什么是Docker？",
                    "a": "Docker是一个开源的容器化平台。"
                },
                {
                    "q": "容器和虚拟机的区别？",
                    "a": "容器共享宿主机内核，虚拟机有独立的操作系统。"
                },
                {
                    "q": "Docker的优势是什么？",
                    "a": "轻量级、快速启动、资源利用率高、易于部署。"
                }
            ]
        ],
        "context_extraction_mode": "minimal",
        "preserve_session_info": True,
        "max_concurrent_processing": 3
    }
}




# Agent管理示例数据
AGENT_EXAMPLES = {
    "reward_agent": {
        "name": "Reward Agent",
        "description": "语义一致性评估代理",
        "template_variables": ["question", "target_answer", "candidates"]
    },
    "cqa_agent": {
        "name": "CQA Agent", 
        "description": "问答转换代理",
        "template_variables": ["qas", "instructions"]
    },
    "chapter_structure_agent": {
        "name": "Chapter Structure Agent",
        "description": "章节结构生成代理",
        "template_variables": ["cqa_items", "max_level"]
    }
}


# LLM配置模板
LLM_CONFIG_TEMPLATES = {
    "DeepSeek Chat": {
        "api_key": "your_deepseek_api_key",
        "model": "deepseek-chat",
        "base_url": "https://api.deepseek.com/v1",
        "timeout": 180.0,
        "max_completion_tokens": 2048,
        "temperature": 0.0
    },
    "OpenAI GPT-4": {
        "api_key": "your_openai_api_key",
        "model": "gpt-4",
        "base_url": "https://api.openai.com/v1",
        "timeout": 120.0,
        "max_completion_tokens": 4096,
        "temperature": 0.0
    },
    "自定义配置": {}
}


# 示例CSV文件路径
EXAMPLE_CSV_PATHS = {
    "ospa_examples": {
        "示例1 (exp1.csv)": "ospa/exp1.csv",
        "示例2 (exp2.csv)": "ospa/exp2.csv",
        "示例3 (exp3.csv)": "ospa/exp3.csv"
    }
}


# 备用CSV数据（当文件不存在时使用）
FALLBACK_CSV_DATA = {
    "ospa": """O,S,p,A
什么是Python？,编程学习场景,请解释Python编程语言的特点和用途,Python是一种高级编程语言
如何定义变量？,Python基础场景,解释Python中变量的定义和使用方法,在Python中使用赋值语句定义变量
什么是函数？,函数编程场景,说明函数的概念和在编程中的作用,函数是可重复使用的代码块"""
}