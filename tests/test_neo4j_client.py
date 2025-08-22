"""
测试Neo4j客户端
"""

import pytest
from unittest.mock import Mock, patch
from typing import List, Dict, Any

from workbook_ai.infrastructure.neo4j_client import Neo4jClient
from workbook_ai.domain.entities import ImportResult


class TestNeo4jClient:
    """测试Neo4jClient"""
    
    @patch('ai_knowledge_base.infrastructure.neo4j_client.GraphDatabase')
    def test_init_with_neo4j_available(self, mock_graph_db: Mock) -> None:
        """测试在neo4j可用时的初始化"""
        mock_driver = Mock()
        mock_session = Mock()
        mock_driver.session.return_value.__enter__ = Mock(return_value=mock_session)
        mock_driver.session.return_value.__exit__ = Mock(return_value=None)
        mock_graph_db.driver.return_value = mock_driver
        
        client = Neo4jClient(
            uri="bolt://test:7687",
            user="test_user",
            password="test_password"
        )
        
        assert client.uri == "bolt://test:7687"
        assert client.user == "test_user"
        assert client.password == "test_password"
        assert client.driver == mock_driver
        mock_graph_db.driver.assert_called_once_with(
            "bolt://test:7687",
            auth=("test_user", "test_password")
        )
    
    @patch('ai_knowledge_base.infrastructure.neo4j_client.GraphDatabase', None)
    def test_init_without_neo4j(self) -> None:
        """测试在neo4j不可用时的初始化"""
        client = Neo4jClient()
        
        assert client.uri == "bolt://localhost:7687"
        assert client.user == "neo4j"
        assert client.password == "password"
        assert client.driver is None
    
    @patch('ai_knowledge_base.infrastructure.neo4j_client.GraphDatabase')
    def test_connect_failure(self, mock_graph_db: Mock) -> None:
        """测试连接失败"""
        mock_graph_db.driver.side_effect = Exception("连接失败")
        
        client = Neo4jClient()
        
        assert client.driver is None
    
    def test_create_collection_without_driver(self) -> None:
        """测试在没有驱动时创建collection"""
        client = Neo4jClient()
        client.driver = None
        
        result = client.create_collection("TestCollection")
        
        assert result is False
    
    @patch('ai_knowledge_base.infrastructure.neo4j_client.GraphDatabase')
    def test_create_collection_success(self, mock_graph_db: Mock) -> None:
        """测试成功创建collection"""
        mock_driver = Mock()
        mock_session = Mock()
        mock_driver.session.return_value.__enter__ = Mock(return_value=mock_session)
        mock_driver.session.return_value.__exit__ = Mock(return_value=None)
        mock_graph_db.driver.return_value = mock_driver
        
        client = Neo4jClient()
        result = client.create_collection("TestCollection")
        
        assert result is True
        # 验证执行了约束和索引创建
        assert mock_session.run.call_count == 2
    
    @patch('ai_knowledge_base.infrastructure.neo4j_client.GraphDatabase')
    def test_create_collection_failure(self, mock_graph_db: Mock) -> None:
        """测试创建collection失败"""
        mock_driver = Mock()
        mock_session = Mock()
        mock_session.run.side_effect = Exception("创建失败")
        mock_driver.session.return_value.__enter__ = Mock(return_value=mock_session)
        mock_driver.session.return_value.__exit__ = Mock(return_value=None)
        mock_graph_db.driver.return_value = mock_driver
        mock_graph_db.exceptions.Neo4jError = Exception
        
        client = Neo4jClient()
        result = client.create_collection("TestCollection")
        
        assert result is False
    
    def test_import_data_without_driver(self) -> None:
        """测试在没有驱动时导入数据"""
        client = Neo4jClient()
        client.driver = None
        
        nodes = [{"recordId": "1", "userInput": "你好"}]
        relationships = []
        
        result = client.import_data(nodes, relationships)
        
        assert isinstance(result, ImportResult)
        assert result.success is False
        assert result.total_records == 1
        assert result.imported_records == 0
        assert result.failed_records == 1
        assert "Neo4j客户端未连接" in result.error_messages
    
    @patch('ai_knowledge_base.infrastructure.neo4j_client.GraphDatabase')
    def test_import_data_success(self, mock_graph_db: Mock) -> None:
        """测试成功导入数据"""
        mock_driver = Mock()
        mock_session = Mock()
        mock_driver.session.return_value.__enter__ = Mock(return_value=mock_session)
        mock_driver.session.return_value.__exit__ = Mock(return_value=None)
        mock_graph_db.driver.return_value = mock_driver
        
        client = Neo4jClient()
        
        nodes = [
            {"recordId": "1", "userInput": "你好"},
            {"recordId": "2", "userInput": "再见"}
        ]
        relationships = [
            {
                "from_id": "1",
                "to_id": "2",
                "properties": {"type": "NEXT_RECORD"}
            }
        ]
        
        result = client.import_data(nodes, relationships)
        
        assert isinstance(result, ImportResult)
        assert result.success is True
        assert result.total_records == 3  # 2 nodes + 1 relationship
        assert result.imported_records == 3
        assert result.failed_records == 0
        
        # 验证执行了节点和关系的导入
        assert mock_session.run.call_count == 3
    
    @patch('ai_knowledge_base.infrastructure.neo4j_client.GraphDatabase')
    def test_import_data_with_custom_label(self, mock_graph_db: Mock) -> None:
        """测试导入带自定义标签的数据"""
        mock_driver = Mock()
        mock_session = Mock()
        mock_driver.session.return_value.__enter__ = Mock(return_value=mock_session)
        mock_driver.session.return_value.__exit__ = Mock(return_value=None)
        mock_graph_db.driver.return_value = mock_driver
        
        client = Neo4jClient()
        
        nodes = [
            {
                "label": "CustomRecord",
                "recordId": "1", 
                "userInput": "你好"
            }
        ]
        relationships = []
        
        result = client.import_data(nodes, relationships)
        
        assert result.success is True
        # 验证使用了自定义标签
        call_args = mock_session.run.call_args_list[0]
        assert "CustomRecord" in call_args[0][0]
    
    def test_query_without_driver(self) -> None:
        """测试在没有驱动时查询"""
        client = Neo4jClient()
        client.driver = None
        
        result = client.query("RETURN 1")
        
        assert result == []
    
    @patch('ai_knowledge_base.infrastructure.neo4j_client.GraphDatabase')
    def test_query_success(self, mock_graph_db: Mock) -> None:
        """测试成功查询"""
        mock_driver = Mock()
        mock_session = Mock()
        mock_record1 = Mock()
        mock_record1.data.return_value = {"n": {"recordId": "1"}}
        mock_record2 = Mock()
        mock_record2.data.return_value = {"n": {"recordId": "2"}}
        mock_result = [mock_record1, mock_record2]
        mock_session.run.return_value = mock_result
        mock_driver.session.return_value.__enter__ = Mock(return_value=mock_session)
        mock_driver.session.return_value.__exit__ = Mock(return_value=None)
        mock_graph_db.driver.return_value = mock_driver
        
        client = Neo4jClient()
        result = client.query("MATCH (n) RETURN n", {"param": "value"})
        
        assert len(result) == 2
        assert result[0] == {"n": {"recordId": "1"}}
        assert result[1] == {"n": {"recordId": "2"}}
        mock_session.run.assert_called_once_with(
            "MATCH (n) RETURN n", 
            {"param": "value"}
        )
    
    @patch('ai_knowledge_base.infrastructure.neo4j_client.GraphDatabase')
    def test_query_with_default_parameters(self, mock_graph_db: Mock) -> None:
        """测试使用默认参数查询"""
        mock_driver = Mock()
        mock_session = Mock()
        mock_session.run.return_value = []
        mock_driver.session.return_value.__enter__ = Mock(return_value=mock_session)
        mock_driver.session.return_value.__exit__ = Mock(return_value=None)
        mock_graph_db.driver.return_value = mock_driver
        
        client = Neo4jClient()
        result = client.query("RETURN 1")
        
        assert result == []
        mock_session.run.assert_called_once_with("RETURN 1", {})
    
    @patch('ai_knowledge_base.infrastructure.neo4j_client.GraphDatabase')
    def test_get_conversation_chain(self, mock_graph_db: Mock) -> None:
        """测试获取对话链条"""
        mock_driver = Mock()
        mock_session = Mock()
        mock_record = Mock()
        mock_node1 = {"recordId": "1", "userInput": "你好"}
        mock_node2 = {"recordId": "2", "userInput": "再见"}
        mock_record.data.return_value = {"chain_nodes": [mock_node1, mock_node2]}
        mock_session.run.return_value = [mock_record]
        mock_driver.session.return_value.__enter__ = Mock(return_value=mock_session)
        mock_driver.session.return_value.__exit__ = Mock(return_value=None)
        mock_graph_db.driver.return_value = mock_driver
        
        client = Neo4jClient()
        result = client.get_conversation_chain("1")
        
        assert len(result) == 2
        assert result[0] == mock_node1
        assert result[1] == mock_node2
    
    @patch('ai_knowledge_base.infrastructure.neo4j_client.GraphDatabase')
    def test_get_conversation_chain_empty(self, mock_graph_db: Mock) -> None:
        """测试获取空对话链条"""
        mock_driver = Mock()
        mock_session = Mock()
        mock_session.run.return_value = []
        mock_driver.session.return_value.__enter__ = Mock(return_value=mock_session)
        mock_driver.session.return_value.__exit__ = Mock(return_value=None)
        mock_graph_db.driver.return_value = mock_driver
        
        client = Neo4jClient()
        result = client.get_conversation_chain("nonexistent")
        
        assert result == []
    
    @patch('ai_knowledge_base.infrastructure.neo4j_client.GraphDatabase')
    def test_get_state_transitions(self, mock_graph_db: Mock) -> None:
        """测试获取状态转换"""
        mock_driver = Mock()
        mock_session = Mock()
        mock_record = Mock()
        mock_record.data.return_value = {
            "from_state": "/",
            "to_state": "1.用户发起闲聊",
            "transition_count": 5
        }
        mock_session.run.return_value = [mock_record]
        mock_driver.session.return_value.__enter__ = Mock(return_value=mock_session)
        mock_driver.session.return_value.__exit__ = Mock(return_value=None)
        mock_graph_db.driver.return_value = mock_driver
        
        client = Neo4jClient()
        result = client.get_state_transitions()
        
        assert len(result) == 1
        assert result[0]["from_state"] == "/"
        assert result[0]["to_state"] == "1.用户发起闲聊"
        assert result[0]["transition_count"] == 5
    
    def test_delete_collection_without_driver(self) -> None:
        """测试在没有驱动时删除collection"""
        client = Neo4jClient()
        client.driver = None
        
        result = client.delete_collection("TestCollection")
        
        assert result is False
    
    @patch('ai_knowledge_base.infrastructure.neo4j_client.GraphDatabase')
    def test_delete_collection_success(self, mock_graph_db: Mock) -> None:
        """测试成功删除collection"""
        mock_driver = Mock()
        mock_session = Mock()
        mock_driver.session.return_value.__enter__ = Mock(return_value=mock_session)
        mock_driver.session.return_value.__exit__ = Mock(return_value=None)
        mock_graph_db.driver.return_value = mock_driver
        mock_graph_db.exceptions.Neo4jError = Exception
        
        client = Neo4jClient()
        result = client.delete_collection("TestCollection")
        
        assert result is True
        # 验证执行了删除节点、约束和索引的操作
        assert mock_session.run.call_count >= 3
    
    @patch('ai_knowledge_base.infrastructure.neo4j_client.GraphDatabase')
    def test_delete_collection_failure(self, mock_graph_db: Mock) -> None:
        """测试删除collection失败"""
        mock_driver = Mock()
        mock_session = Mock()
        mock_session.run.side_effect = Exception("删除失败")
        mock_driver.session.return_value.__enter__ = Mock(return_value=mock_session)
        mock_driver.session.return_value.__exit__ = Mock(return_value=None)
        mock_graph_db.driver.return_value = mock_driver
        mock_graph_db.exceptions.Neo4jError = Exception
        
        client = Neo4jClient()
        result = client.delete_collection("TestCollection")
        
        assert result is False
    
    def test_close_with_driver(self) -> None:
        """测试关闭有驱动的连接"""
        client = Neo4jClient()
        mock_driver = Mock()
        client.driver = mock_driver
        
        client.close()
        
        mock_driver.close.assert_called_once()
        assert client.driver is None
    
    def test_close_without_driver(self) -> None:
        """测试关闭没有驱动的连接"""
        client = Neo4jClient()
        client.driver = None
        
        # 应该不会抛出异常
        client.close()
        
        assert client.driver is None