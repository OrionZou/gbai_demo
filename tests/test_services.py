"""
测试Application层服务
"""

import pytest
from unittest.mock import Mock, patch
from uuid import uuid4

from workbook_ai.application.services import DataImportService
from workbook_ai.domain.entities import (
    ConversationRecord,
    ImportResult,
    QueryResult
)


class TestDataImportService:
    """测试DataImportService"""
    
    def test_init_with_default_clients(self) -> None:
        """测试使用默认客户端初始化"""
        with patch('ai_knowledge_base.application.services.WeaviateClient') as mock_weaviate, \
             patch('ai_knowledge_base.application.services.Neo4jClient') as mock_neo4j:
            
            service = DataImportService()
            
            assert service.weaviate_client is not None
            assert service.neo4j_client is not None
            mock_weaviate.assert_called_once()
            mock_neo4j.assert_called_once()
    
    def test_init_with_custom_clients(self) -> None:
        """测试使用自定义客户端初始化"""
        mock_weaviate = Mock()
        mock_neo4j = Mock()
        
        service = DataImportService(
            weaviate_client=mock_weaviate,
            neo4j_client=mock_neo4j
        )
        
        assert service.weaviate_client == mock_weaviate
        assert service.neo4j_client == mock_neo4j
    
    @patch('ai_knowledge_base.application.services.WeaviateClient')
    @patch('ai_knowledge_base.application.services.Neo4jClient')
    def test_initialize_schemas(self, mock_neo4j_class: Mock, mock_weaviate_class: Mock) -> None:
        """测试初始化数据库schema"""
        mock_weaviate = Mock()
        mock_neo4j = Mock()
        mock_weaviate_class.return_value = mock_weaviate
        mock_neo4j_class.return_value = mock_neo4j
        
        service = DataImportService()
        
        mock_weaviate.create_collection.assert_called_once()
        mock_neo4j.create_collection.assert_called_once_with("ConversationRecord")
    
    def test_parse_csv_content_success(self) -> None:
        """测试成功解析CSV内容"""
        service = DataImportService()
        csv_content = """No.,User input,s,s',prompt,Agent output
1,你好,/,1.用户发起闲聊,测试提示词,您好！请问有什么关于爱车的问题需要咨询吗？
2,没啥问题,1.用户发起闲聊,1.1引导用户询问业务问题,测试提示词2,那您最近车辆使用上有没有什么让您感到不太满意的地方？"""
        
        records = service._parse_csv_content(csv_content)
        
        assert len(records) == 2
        assert records[0]['No.'] == '1'
        assert records[0]['User input'] == '你好'
        assert records[0]['s'] == '/'
        assert records[1]['No.'] == '2'
        assert records[1]['User input'] == '没啥问题'
    
    def test_parse_csv_content_empty(self) -> None:
        """测试解析空CSV内容"""
        service = DataImportService()
        csv_content = ""
        
        records = service._parse_csv_content(csv_content)
        
        assert len(records) == 0
    
    def test_parse_csv_content_with_empty_values(self) -> None:
        """测试解析包含空值的CSV内容"""
        service = DataImportService()
        csv_content = """No.,User input,s,s',prompt,Agent output
1,你好,/,,测试提示词,回复1
,,,,,
2,再见,状态2,状态3,,回复2"""
        
        records = service._parse_csv_content(csv_content)
        
        assert len(records) == 2  # 空行被跳过
        assert records[0]['No.'] == '1'
        assert records[1]['No.'] == '2'
    
    def test_create_record_chain(self) -> None:
        """测试创建记录链条"""
        service = DataImportService()
        csv_records = [
            {
                'No.': '1',
                'User input': '你好',
                's': '/',
                "s'": '1.用户发起闲聊',
                'prompt': '测试提示词1',
                'Agent output': '回复1'
            },
            {
                'No.': '2',
                'User input': '没啥问题',
                's': '1.用户发起闲聊',
                "s'": '1.1引导用户询问业务问题',
                'prompt': '测试提示词2',
                'Agent output': '回复2'
            }
        ]
        
        chain = service._create_record_chain(csv_records)
        
        assert len(chain.records) == 2
        assert chain.records[0].sequence_number == 1
        assert chain.records[0].user_input == '你好'
        assert chain.records[1].sequence_number == 2
        assert chain.records[1].user_input == '没啥问题'
        
        # 验证链接关系
        assert chain.records[0].next_record_id == chain.records[1].record_id
        assert chain.records[1].previous_record_id == chain.records[0].record_id
    
    def test_create_record_chain_with_invalid_data(self) -> None:
        """测试创建包含无效数据的记录链条"""
        service = DataImportService()
        csv_records = [
            {
                'No.': 'invalid',  # 无效的序号
                'User input': '你好',
                's': '/',
                'prompt': '测试提示词',
                'Agent output': '回复'
            }
        ]
        
        chain = service._create_record_chain(csv_records)
        
        # 应该跳过无效记录
        assert len(chain.records) == 0
    
    @patch('ai_knowledge_base.application.services.WeaviateClient')
    @patch('ai_knowledge_base.application.services.Neo4jClient')
    def test_import_to_weaviate_success(self, mock_neo4j_class: Mock, mock_weaviate_class: Mock) -> None:
        """测试成功导入到Weaviate"""
        mock_weaviate = Mock()
        mock_weaviate.import_data.return_value = ImportResult(
            success=True,
            total_records=1,
            imported_records=1,
            failed_records=0,
            error_messages=[]
        )
        mock_weaviate_class.return_value = mock_weaviate
        mock_neo4j_class.return_value = Mock()
        
        service = DataImportService()
        record = ConversationRecord(
            sequence_number=1,
            user_input="你好",
            current_state="/",
            prompt="测试提示词",
            agent_output="回复"
        )
        
        result = service._import_to_weaviate([record])
        
        assert result.success is True
        assert result.imported_records == 1
        mock_weaviate.import_data.assert_called_once()
        
        # 验证传递给Weaviate的数据格式
        call_args = mock_weaviate.import_data.call_args
        assert call_args[0][0] == "ConversationRecord"
        weaviate_data = call_args[0][1]
        assert len(weaviate_data) == 1
        assert weaviate_data[0]["userInput"] == "你好"
    
    @patch('ai_knowledge_base.application.services.WeaviateClient')
    @patch('ai_knowledge_base.application.services.Neo4jClient')
    def test_import_to_weaviate_without_client(self, mock_neo4j_class: Mock, mock_weaviate_class: Mock) -> None:
        """测试在没有Weaviate客户端时导入"""
        mock_weaviate_class.return_value = Mock()
        mock_neo4j_class.return_value = Mock()
        
        service = DataImportService()
        service.weaviate_client = None
        
        record = ConversationRecord(
            sequence_number=1,
            user_input="你好",
            current_state="/",
            prompt="测试提示词",
            agent_output="回复"
        )
        
        result = service._import_to_weaviate([record])
        
        assert result.success is False
        assert "Weaviate客户端未初始化" in result.error_messages
    
    @patch('ai_knowledge_base.application.services.WeaviateClient')
    @patch('ai_knowledge_base.application.services.Neo4jClient')
    def test_import_to_neo4j_success(self, mock_neo4j_class: Mock, mock_weaviate_class: Mock) -> None:
        """测试成功导入到Neo4j"""
        mock_neo4j = Mock()
        mock_neo4j.import_data.return_value = ImportResult(
            success=True,
            total_records=2,
            imported_records=2,
            failed_records=0,
            error_messages=[]
        )
        mock_weaviate_class.return_value = Mock()
        mock_neo4j_class.return_value = mock_neo4j
        
        service = DataImportService()
        record1 = ConversationRecord(
            sequence_number=1,
            user_input="你好",
            current_state="/",
            prompt="测试提示词1",
            agent_output="回复1"
        )
        record2 = ConversationRecord(
            sequence_number=2,
            user_input="再见",
            current_state="状态2",
            prompt="测试提示词2",
            agent_output="回复2"
        )
        record1.link_next(record2)
        
        result = service._import_to_neo4j([record1, record2])
        
        assert result.success is True
        assert result.imported_records == 2
        mock_neo4j.import_data.assert_called_once()
        
        # 验证传递给Neo4j的数据格式
        call_args = mock_neo4j.import_data.call_args
        nodes = call_args[0][0]
        relationships = call_args[0][1]
        
        assert len(nodes) == 2
        assert len(relationships) == 1
        assert nodes[0]["userInput"] == "你好"
        assert relationships[0]["from_id"] == str(record1.record_id)
        assert relationships[0]["to_id"] == str(record2.record_id)
    
    @patch('ai_knowledge_base.application.services.WeaviateClient')
    @patch('ai_knowledge_base.application.services.Neo4jClient')
    def test_import_from_csv_success(self, mock_neo4j_class: Mock, mock_weaviate_class: Mock) -> None:
        """测试成功从CSV导入"""
        mock_weaviate = Mock()
        mock_weaviate.import_data.return_value = ImportResult(
            success=True,
            total_records=1,
            imported_records=1,
            failed_records=0,
            error_messages=[]
        )
        mock_neo4j = Mock()
        mock_neo4j.import_data.return_value = ImportResult(
            success=True,
            total_records=1,
            imported_records=1,
            failed_records=0,
            error_messages=[]
        )
        mock_weaviate_class.return_value = mock_weaviate
        mock_neo4j_class.return_value = mock_neo4j
        
        service = DataImportService()
        csv_content = """No.,User input,s,s',prompt,Agent output
1,你好,/,1.用户发起闲聊,测试提示词,您好！请问有什么关于爱车的问题需要咨询吗？"""
        
        result = service.import_from_csv(csv_content)
        
        assert result.success is True
        assert result.total_records == 1
        assert result.imported_records == 1
        assert result.failed_records == 0
        assert result.chain_id is not None
    
    @patch('ai_knowledge_base.application.services.WeaviateClient')
    @patch('ai_knowledge_base.application.services.Neo4jClient')
    def test_import_from_csv_empty(self, mock_neo4j_class: Mock, mock_weaviate_class: Mock) -> None:
        """测试从空CSV导入"""
        mock_weaviate_class.return_value = Mock()
        mock_neo4j_class.return_value = Mock()
        
        service = DataImportService()
        csv_content = ""
        
        result = service.import_from_csv(csv_content)
        
        assert result.success is False
        assert result.total_records == 0
        assert "CSV数据为空或格式错误" in result.error_messages
    
    @patch('ai_knowledge_base.application.services.WeaviateClient')
    @patch('ai_knowledge_base.application.services.Neo4jClient')
    def test_query_similar_conversations_success(self, mock_neo4j_class: Mock, mock_weaviate_class: Mock) -> None:
        """测试成功查询相似对话"""
        mock_weaviate = Mock()
        mock_weaviate.query.return_value = [
            {
                "recordId": "test-id",
                "sequenceNumber": 1,
                "userInput": "你好",
                "currentState": "/",
                "nextState": "1.用户发起闲聊",
                "prompt": "测试提示词",
                "agentOutput": "回复"
            }
        ]
        mock_weaviate_class.return_value = mock_weaviate
        mock_neo4j_class.return_value = Mock()
        
        service = DataImportService()
        result = service.query_similar_conversations("你好", limit=5)
        
        assert isinstance(result, QueryResult)
        assert result.query_text == "你好"
        assert result.total_count == 1
        assert len(result.results) == 1
        assert result.results[0].user_input == "你好"
        
        mock_weaviate.query.assert_called_once_with(
            collection_name="ConversationRecord",
            query_text="你好",
            limit=5
        )
    
    @patch('ai_knowledge_base.application.services.WeaviateClient')
    @patch('ai_knowledge_base.application.services.Neo4jClient')
    def test_query_similar_conversations_without_client(self, mock_neo4j_class: Mock, mock_weaviate_class: Mock) -> None:
        """测试在没有Weaviate客户端时查询"""
        mock_weaviate_class.return_value = Mock()
        mock_neo4j_class.return_value = Mock()
        
        service = DataImportService()
        service.weaviate_client = None
        
        result = service.query_similar_conversations("你好")
        
        assert isinstance(result, QueryResult)
        assert result.query_text == "你好"
        assert result.total_count == 0
        assert len(result.results) == 0
    
    @patch('ai_knowledge_base.application.services.WeaviateClient')
    @patch('ai_knowledge_base.application.services.Neo4jClient')
    def test_get_conversation_history_success(self, mock_neo4j_class: Mock, mock_weaviate_class: Mock) -> None:
        """测试成功获取对话历史"""
        mock_neo4j = Mock()
        mock_neo4j.get_conversation_chain.return_value = [
            {
                "recordId": "test-id-1",
                "sequenceNumber": 1,
                "userInput": "你好",
                "currentState": "/",
                "nextState": "1.用户发起闲聊",
                "prompt": "测试提示词1",
                "agentOutput": "回复1"
            },
            {
                "recordId": "test-id-2",
                "sequenceNumber": 2,
                "userInput": "再见",
                "currentState": "1.用户发起闲聊",
                "nextState": "",
                "prompt": "测试提示词2",
                "agentOutput": "回复2"
            }
        ]
        mock_weaviate_class.return_value = Mock()
        mock_neo4j_class.return_value = mock_neo4j
        
        service = DataImportService()
        result = service.get_conversation_history("test-id-1")
        
        assert len(result) == 2
        assert result[0].user_input == "你好"
        assert result[1].user_input == "再见"
        
        mock_neo4j.get_conversation_chain.assert_called_once_with("test-id-1")
    
    @patch('ai_knowledge_base.application.services.WeaviateClient')
    @patch('ai_knowledge_base.application.services.Neo4jClient')
    def test_get_conversation_history_without_client(self, mock_neo4j_class: Mock, mock_weaviate_class: Mock) -> None:
        """测试在没有Neo4j客户端时获取历史"""
        mock_weaviate_class.return_value = Mock()
        mock_neo4j_class.return_value = Mock()
        
        service = DataImportService()
        service.neo4j_client = None
        
        result = service.get_conversation_history("test-id")
        
        assert len(result) == 0