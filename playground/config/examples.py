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
        "chapters_extra_instructions": "",
        "gen_p_extra_instructions": ""
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
        "chapters_extra_instructions": "请将Python相关的问题聚合到一个章节",
        "gen_p_extra_instructions": "生成专业的Python技术文档风格提示词"
    }
}


# Backward V2 API 示例数据
BACKWARD_V2_EXAMPLES = {
    "自定义输入": {
        "qa_lists": [],
        "chapter_structure": None,
        "max_level": 3
    },
    "简单示例 - 无现有章节": {
        "qa_lists": [
            {
                "items": [
                    {"question": "Python如何定义变量？", "answer": "在Python中使用赋值语句定义变量，如 x = 10"},
                    {"question": "如何查看变量类型？", "answer": "使用type()函数可以查看变量类型，如 type(x)"}
                ],
                "session_id": "session_1"
            },
            {
                "items": [
                    {"question": "什么是RESTful API？", "answer": "RESTful API是遵循REST架构风格的Web服务接口"},
                    {"question": "API设计有什么原则？", "answer": "API设计要遵循统一接口、无状态、可缓存等原则"}
                ],
                "session_id": "session_2"
            }
        ],
        "chapter_structure": None,
        "max_level": 3
    },
    "复杂示例 - 3个多轮对话": {
        "qa_lists": [
            {
                "items": [
                    {"question": "什么是机器学习？", "answer": "机器学习是人工智能的一个分支，让计算机通过数据学习并做出预测或决策，而无需明确编程。"},
                    {"question": "机器学习有哪些主要类型？", "answer": "主要有监督学习、无监督学习和强化学习三种类型。监督学习使用标记数据，无监督学习寻找数据中的模式，强化学习通过奖励机制学习。"},
                    {"question": "什么是神经网络？", "answer": "神经网络是模仿人类大脑神经元结构的计算模型，由多层相互连接的节点组成，能够学习复杂的数据模式。"},
                    {"question": "深度学习和机器学习有什么区别？", "answer": "深度学习是机器学习的一个子集，使用深度神经网络（多隐藏层）来学习数据的层次化表示，在图像、语音等领域表现出色。"},
                    {"question": "常用的机器学习算法有哪些？", "answer": "常用算法包括线性回归、逻辑回归、决策树、随机森林、支持向量机、K-means聚类、朴素贝叶斯等。"},
                    {"question": "如何评估机器学习模型的性能？", "answer": "可以使用准确率、精确率、召回率、F1分数、AUC-ROC曲线等指标。对于回归问题，常用MSE、MAE、R²等指标。"},
                    {"question": "什么是过拟合和欠拟合？", "answer": "过拟合是模型在训练数据上表现很好但在新数据上表现差；欠拟合是模型过于简单，无法捕获数据的潜在模式。可以通过正则化、交叉验证等方法解决。"},
                    {"question": "机器学习在实际中有哪些应用？", "answer": "广泛应用于推荐系统、图像识别、自然语言处理、金融风控、医疗诊断、自动驾驶、语音识别等领域。"}
                ],
                "session_id": "ml_conversation"
            },
            {
                "items": [
                    {"question": "什么是RESTful API？", "answer": "REST（Representational State Transfer）是一种架构风格，RESTful API是遵循REST原则设计的Web服务接口，使用HTTP方法进行资源操作。"},
                    {"question": "REST的主要原则有哪些？", "answer": "主要原则包括：无状态性、统一接口、客户端-服务器架构、可缓存性、分层系统和按需代码（可选）。"},
                    {"question": "HTTP方法在RESTful API中如何使用？", "answer": "GET用于获取资源，POST用于创建资源，PUT用于更新整个资源，PATCH用于部分更新，DELETE用于删除资源。"},
                    {"question": "什么是API版本控制？为什么重要？", "answer": "API版本控制是管理API变更的方法，确保向后兼容性。重要性在于保护现有客户端不受新版本影响。常见方式有URL路径版本、请求头版本等。"},
                    {"question": "API文档应该包含哪些内容？", "answer": "应包含端点描述、请求/响应格式、参数说明、状态码说明、认证方式、使用示例、错误处理等信息。"},
                    {"question": "如何设计API的错误处理？", "answer": "使用标准HTTP状态码，提供清晰的错误消息，包含错误代码和详细描述，保持错误格式一致性，避免暴露敏感信息。"},
                    {"question": "API安全有哪些最佳实践？", "answer": "使用HTTPS、实施身份认证和授权、API密钥管理、输入验证、速率限制、CORS配置、安全响应头等。"},
                    {"question": "什么是API网关？有什么作用？", "answer": "API网关是微服务架构中的入口点，提供路由、认证、限流、监控、协议转换等功能，简化客户端与后端服务的交互。"},
                    {"question": "如何进行API性能优化？", "answer": "可以通过缓存策略、分页处理、异步处理、数据库优化、CDN使用、响应压缩、连接池等方式提升API性能。"}
                ],
                "session_id": "api_design_conversation"
            },
            {
                "items": [
                    {"question": "什么是Docker？它解决了什么问题？", "answer": "Docker是容器化平台，解决了\"在我机器上能运行\"的环境一致性问题，提供轻量级虚拟化，简化应用部署和迁移。"},
                    {"question": "Docker容器和虚拟机有什么区别？", "answer": "容器共享宿主机内核，启动快、资源占用少；虚拟机有完整操作系统，隔离性更强但资源消耗大。容器更适合微服务架构。"},
                    {"question": "Dockerfile的作用是什么？", "answer": "Dockerfile是构建Docker镜像的脚本文件，包含一系列指令来定义镜像的构建过程，如基础镜像、依赖安装、文件复制等。"},
                    {"question": "什么是Docker Compose？", "answer": "Docker Compose是用于定义和运行多容器Docker应用的工具，通过YAML文件配置多个服务，简化复杂应用的管理和部署。"},
                    {"question": "Docker网络模式有哪些？", "answer": "主要有bridge（默认）、host、none、overlay等模式。bridge模式为容器创建独立网络，host模式共享宿主机网络，overlay用于跨主机通信。"},
                    {"question": "如何管理Docker数据持久化？", "answer": "可以使用数据卷（volumes）、绑定挂载（bind mounts）或临时文件系统（tmpfs）。数据卷是推荐方式，由Docker管理且持久化。"},
                    {"question": "什么是容器编排？Kubernetes的作用是什么？", "answer": "容器编排是管理多个容器的部署、扩展和运行的过程。Kubernetes是容器编排平台，提供自动部署、扩缩容、服务发现、负载均衡等功能。"},
                    {"question": "Docker镜像的分层机制是如何工作的？", "answer": "Docker镜像由多个只读层组成，每层包含文件系统的变更。容器运行时添加可写层。分层机制实现了镜像复用和高效存储。"},
                    {"question": "如何优化Docker镜像大小？", "answer": "使用轻量级基础镜像（如Alpine）、合并RUN命令、清理缓存、使用.dockerignore文件、多阶段构建等方法可以显著减小镜像大小。"},
                    {"question": "容器化微服务架构有什么优势和挑战？", "answer": "优势：服务独立部署、技术栈灵活、水平扩展容易。挑战：服务间通信复杂、数据一致性、监控难度增加、网络性能开销。"}
                ],
                "session_id": "docker_conversation"
            }
        ],
        "chapter_structure": None,
        "max_level": 3
    },
    "有现有章节示例": {
        "qa_lists": [
            {
                "items": [
                    {"question": "什么是Docker容器？", "answer": "Docker容器是轻量级的虚拟化技术"},
                    {"question": "容器与虚拟机的区别？", "answer": "容器共享宿主机内核，虚拟机有独立的操作系统"}
                ],
                "session_id": "session_3"
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
                    "related_cqa_items": [],
                    "related_cqa_ids": [],
                    "chapter_number": "1."
                }
            },
            "root_ids": ["chapter_1"],
            "max_level": 3
        },
        "max_level": 3
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
    "backward_v2": "exps/data/backward_v2_test_data.csv",
    "ospa_examples": {
        "示例1 (exp1.csv)": "ospa/exp1.csv",
        "示例2 (exp2.csv)": "ospa/exp2.csv",
        "示例3 (exp3.csv)": "ospa/exp3.csv"
    }
}


# 备用CSV数据（当文件不存在时使用）
FALLBACK_CSV_DATA = {
    "backward_v2": """session_id,question,answer
ai_conversation,什么是人工智能？,"人工智能(AI)是模拟人的智能的技术科学"
ai_conversation,机器学习是什么？,"机器学习是AI的一个重要分支"
web_conversation,什么是前端开发？,"前端开发是创建用户界面的过程"
web_conversation,什么是API？,"API是应用程序接口的缩写" """,
    
    "ospa": """O,S,p,A
什么是Python？,编程学习场景,请解释Python编程语言的特点和用途,Python是一种高级编程语言
如何定义变量？,Python基础场景,解释Python中变量的定义和使用方法,在Python中使用赋值语句定义变量
什么是函数？,函数编程场景,说明函数的概念和在编程中的作用,函数是可重复使用的代码块"""
}