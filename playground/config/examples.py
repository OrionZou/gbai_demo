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
    "简单示例 - Python基础": {
        "qas": [
            {
                "q": "Python如何定义变量？",
                "a": "在Python中使用赋值语句定义变量，如 x = 10"
            },
            {
                "q": "Python如何定义函数？",
                "a": "使用def关键字定义函数，如 def func_name():"
            },
            {
                "q": "什么是Python列表？",
                "a": "列表是Python中的可变序列，使用[]定义"
            }
        ],
        "chapter_structure": None,
        "max_level": 3,
        "max_concurrent_llm": 10
    },
    "多技术栈示例": {
        "qas": [
            {
                "q": "什么是RESTful API？",
                "a": "RESTful API是遵循REST架构风格的Web服务接口"
            },
            {
                "q": "什么是数据库索引？",
                "a": "索引是提高数据库查询效率的数据结构"
            },
            {
                "q": "什么是Docker容器？",
                "a": "Docker容器是轻量级的虚拟化技术"
            },
            {
                "q": "什么是Git版本控制？",
                "a": "Git是分布式版本控制系统"
            }
        ],
        "chapter_structure": None,
        "max_level": 3,
        "max_concurrent_llm": 10
    },
    "有现有章节示例": {
        "qas": [
            {
                "q": "什么是Docker容器？",
                "a": "Docker容器是轻量级的虚拟化技术"
            },
            {
                "q": "容器与虚拟机的区别？",
                "a": "容器共享宿主机内核，虚拟机有独立的操作系统"
            }
        ],
        "chapter_structure": {
            "nodes": {
                "chapter_1": {
                    "id": "chapter_1",
                    "title": "基础知识",
                    "level": 1,
                    "parent_id": None,
                    "children": [],
                    "description": "基础技术概念",
                    "related_qa_items": [],
                    "chapter_number": "1."
                }
            },
            "root_ids": ["chapter_1"],
            "max_level": 3
        },
        "max_level": 3,
        "max_concurrent_llm": 10
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