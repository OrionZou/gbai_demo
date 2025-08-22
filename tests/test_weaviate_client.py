"""
测试Weaviate客户端
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import List, Dict, Any

from workbook_ai.infrastructure.weaviate_client import (
    WeaviateClient,
    CONVERSATION_RECORD_SCHEMA
)
from workbook_ai.domain.entities import ImportResult


class TestWeaviateClient:
    """测试WeaviateClient"""
    
    @patch('ai_knowledge_base.infrastructure.weaviate_client.weaviate')
    def test_init_with_weaviate_available(self, mock_weaviate: Mock) -> None:
        """测试在weaviate可用时的初始化"""
        mock_client = Mock()
        mock_weaviate.Client.return_value = mock_client
        
        client = WeaviateClient("http://test:8080")
        
        assert client.url == "http://test:8080"
        assert client.client == mock_client
        mock_weaviate.Client.assert_called_once_with(url="http://test:8080")
    
    @patch('ai_knowledge_base.infrastructure.weaviate_client.weaviate', None)
    def test_init_without_weaviate(self) -> None:
        """测试在weaviate不可用时的初始化"""
        client = WeaviateClient()
        
        assert client.url == "http://localhost:8855"
        assert client.client is None
    
    @patch('ai_knowledge_base.infrastructure.weaviate_client.weaviate')
    def test_connect_success(self, mock_weaviate: Mock) -> None:
        """测试连接成功"""
        mock_client = Mock()
        mock_weaviate.Client.return_value = mock_client
        
        client = WeaviateClient()
        
        assert client.client == mock_client
    
    @patch('ai_knowledge_base.infrastructure.weaviate_client.weaviate')
    def test_connect_failure(self, mock_weaviate: Mock) -> None:
        """测试连接失败"""
        mock_weaviate.Client.side_effect = Exception("连接失败")
        
        client = WeaviateClient()
        
        assert client.client is None
    
    def test_create_collection_without_client(self) -> None:
        """测试在没有客户端时创建collection"""
        client = WeaviateClient()
        client.client = None
        
        result = client.create_collection("TestCollection", {})
        
        assert result is False
    
    @patch('ai_knowledge_base.infrastructure.weaviate_client.weaviate')
    def test_create_collection_already_exists(self, mock_weaviate: Mock) -> None:
        """测试创建已存在的collection"""
        mock_client = Mock()
        mock_client.schema.exists.return_value = True
        mock_weaviate.Client.return_value = mock_client
        
        client = WeaviateClient()
        result = client.create_collection("TestCollection", {})
        
        assert result is True
        mock_client.schema.exists.assert_called_once_with("TestCollection")
    
    @patch('ai_knowledge_base.infrastructure.weaviate_client.weaviate')
    def test_create_collection_success(self, mock_weaviate: Mock) -> None:
        """测试成功创建collection"""
        mock_client = Mock()
        mock_client.schema.exists.return_value = False
        mock_weaviate.Client.return_value = mock_client
        
        client = WeaviateClient()
        schema = {"class": "TestCollection"}
        result = client.create_collection("TestCollection", schema)
        
        assert result is True
        mock_client.schema.create_class.assert_called_once_with(schema)
    
    @patch('ai_knowledge_base.infrastructure.weaviate_client.weaviate')
    def test_create_collection_failure(self, mock_weaviate: Mock) -> None:
        """测试创建collection失败"""
        mock_client = Mock()
        mock_client.schema.exists.return_value = False
        mock_client.schema.create_class.side_effect = Exception("创建失败")
        mock_weaviate.Client.return_value = mock_client
        mock_weaviate.exceptions.WeaviateException = Exception
        
        client = WeaviateClient()
        result = client.create_collection("TestCollection", {})
        
        assert result is False
    
    def test_import_data_without_client(self) -> None:
        """测试在没有客户端时导入数据"""
        client = WeaviateClient()
        client.client = None
        
        result = client.import_data("TestCollection", [{"test": "data"}])
        
        assert isinstance(result, ImportResult)
        assert result.success is False
        assert result.total_records == 1
        assert result.imported_records == 0
        assert result.failed_records == 1
        assert "Weaviate客户端未连接" in result.error_messages
    
    @patch('ai_knowledge_base.infrastructure.weaviate_client.weaviate')
    def test_import_data_success(self, mock_weaviate: Mock) -> None:
        """测试成功导入数据"""
        mock_client = Mock()
        mock_batch = Mock()
        mock_client.batch = mock_batch
        mock_batch.__enter__ = Mock(return_value=mock_batch)
        mock_batch.__exit__ = Mock(return_value=None)
        mock_weaviate.Client.return_value = mock_client
        
        client = WeaviateClient()
        data = [
            {"recordId": "1", "userInput": "你好"},
            {"recordId": "2", "userInput": "再见"}
        ]
        
        result = client.import_data("TestCollection", data)
        
        assert isinstance(result, ImportResult)
        assert result.success is True
        assert result.total_records == 2
        assert result.imported_records == 2
        assert result.failed_records == 0
    
    @patch('ai_knowledge_base.infrastructure.weaviate_client.weaviate')
    def test_import_data_with_vector(self, mock_weaviate: Mock) -> None:
        """测试导入带向量的数据"""
        mock_client = Mock()
        mock_batch = Mock()
        mock_client.batch = mock_batch
        mock_batch.__enter__ = Mock(return_value=mock_batch)
        mock_batch.__exit__ = Mock(return_value=None)
        mock_weaviate.Client.return_value = mock_client
        
        client = WeaviateClient()
        data = [
            {
                "recordId": "1", 
                "userInput": "你好",
                "vector": [0.1, 0.2, 0.3]
            }
        ]
        
        result = client.import_data("TestCollection", data)
        
        assert result.success is True
        mock_batch.add_data_object.assert_called_once()
        call_args = mock_batch.add_data_object.call_args
        assert call_args[1]["vector"] == [0.1, 0.2, 0.3]
        assert "vector" not in call_args[1]["data_object"]
    
    def test_query_without_client(self) -> None:
        """测试在没有客户端时查询"""
        client = WeaviateClient()
        client.client = None
        
        result = client.query("TestCollection")
        
        assert result == []
    
    @patch('ai_knowledge_base.infrastructure.weaviate_client.weaviate')
    def test_query_with_vector(self, mock_weaviate: Mock) -> None:
        """测试向量查询"""
        mock_client = Mock()
        mock_query_builder = Mock()
        mock_client.query.get.return_value = mock_query_builder
        mock_query_builder.with_near_vector.return_value = mock_query_builder
        mock_query_builder.with_limit.return_value = mock_query_builder
        mock_query_builder.do.return_value = {
            "data": {
                "Get": {
                    "TestCollection": [
                        {"recordId": "1", "userInput": "你好"}
                    ]
                }
            }
        }
        mock_weaviate.Client.return_value = mock_client
        
        client = WeaviateClient()
        result = client.query(
            "TestCollection", 
            query_vector=[0.1, 0.2, 0.3],
            limit=5
        )
        
        assert len(result) == 1
        assert result[0]["recordId"] == "1"
        mock_query_builder.with_near_vector.assert_called_once_with({
            "vector": [0.1, 0.2, 0.3]
        })
        mock_query_builder.with_limit.assert_called_once_with(5)
    
    @patch('ai_knowledge_base.infrastructure.weaviate_client.weaviate')
    def test_query_with_text(self, mock_weaviate: Mock) -> None:
        """测试文本查询"""
        mock_client = Mock()
        mock_query_builder = Mock()
        mock_client.query.get.return_value = mock_query_builder
        mock_query_builder.with_near_text.return_value = mock_query_builder
        mock_query_builder.with_limit.return_value = mock_query_builder
        mock_query_builder.do.return_value = {
            "data": {
                "Get": {
                    "TestCollection": [
                        {"recordId": "1", "userInput": "你好"}
                    ]
                }
            }
        }
        mock_weaviate.Client.return_value = mock_client
        
        client = WeaviateClient()
        result = client.query(
            "TestCollection", 
            query_text="你好",
            limit=10
        )
        
        assert len(result) == 1
        assert result[0]["recordId"] == "1"
        mock_query_builder.with_near_text.assert_called_once_with({
            "concepts": ["你好"]
        })
    
    @patch('ai_knowledge_base.infrastructure.weaviate_client.weaviate')
    def test_query_empty_result(self, mock_weaviate: Mock) -> None:
        """测试查询空结果"""
        mock_client = Mock()
        mock_query_builder = Mock()
        mock_client.query.get.return_value = mock_query_builder
        mock_query_builder.with_near_text.return_value = mock_query_builder
        mock_query_builder.with_limit.return_value = mock_query_builder
        mock_query_builder.do.return_value = {"data": {"Get": {}}}
        mock_weaviate.Client.return_value = mock_client
        
        client = WeaviateClient()
        result = client.query("TestCollection", query_text="不存在")
        
        assert result == []
    
    @patch('ai_knowledge_base.infrastructure.weaviate_client.weaviate')
    def test_delete_collection_success(self, mock_weaviate: Mock) -> None:
        """测试成功删除collection"""
        mock_client = Mock()
        mock_weaviate.Client.return_value = mock_client
        
        client = WeaviateClient()
        result = client.delete_collection("TestCollection")
        
        assert result is True
        mock_client.schema.delete_class.assert_called_once_with("TestCollection")
    
    def test_delete_collection_without_client(self) -> None:
        """测试在没有客户端时删除collection"""
        client = WeaviateClient()
        client.client = None
        
        result = client.delete_collection("TestCollection")
        
        assert result is False
    
    @patch('ai_knowledge_base.infrastructure.weaviate_client.weaviate')
    def test_get_schema_success(self, mock_weaviate: Mock) -> None:
        """测试成功获取schema"""
        mock_client = Mock()
        expected_schema = {"classes": []}
        mock_client.schema.get.return_value = expected_schema
        mock_weaviate.Client.return_value = mock_client
        
        client = WeaviateClient()
        result = client.get_schema()
        
        assert result == expected_schema
    
    def test_get_schema_without_client(self) -> None:
        """测试在没有客户端时获取schema"""
        client = WeaviateClient()
        client.client = None
        
        result = client.get_schema()
        
        assert result == {}
    
    def test_close(self) -> None:
        """测试关闭连接"""
        client = WeaviateClient()
        mock_client = Mock()
        client.client = mock_client
        
        client.close()
        
        assert client.client is None
    
    def test_conversation_record_schema(self) -> None:
        """测试ConversationRecord schema定义"""
        schema = CONVERSATION_RECORD_SCHEMA
        
        assert schema["class"] == "ConversationRecord"
        assert schema["description"] == "对话记录向量存储"
        assert schema["vectorizer"] == "none"
        assert len(schema["properties"]) == 9
        
        # 检查必要的属性
        property_names = [prop["name"] for prop in schema["properties"]]
        expected_properties = [
            "recordId", "sequenceNumber", "userInput", 
            "currentState", "nextState", "prompt", 
            "agentOutput", "previousRecordId", "nextRecordId"
        ]
        
        for prop in expected_properties:
            assert prop in property_names