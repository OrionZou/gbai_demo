"""
测试Domain层实体类
"""

import pytest
from datetime import datetime
from uuid import UUID, uuid4

from workbook_ai.domain.entities import (
    ConversationRecord,
    RecordChain,
    ImportResult,
    QueryResult
)


class TestConversationRecord:
    """测试ConversationRecord实体"""
    
    def test_create_conversation_record(self):
        """测试创建对话记录"""
        record = ConversationRecord(
            sequence_number=1,
            user_input="你好",
            current_state="/",
            next_state="1.用户发起闲聊",
            prompt="测试提示词",
            agent_output="您好！请问有什么关于爱车的问题需要咨询吗？"
        )
        
        assert record.sequence_number == 1
        assert record.user_input == "你好"
        assert record.current_state == "/"
        assert record.next_state == "1.用户发起闲聊"
        assert record.prompt == "测试提示词"
        assert record.agent_output == "您好！请问有什么关于爱车的问题需要咨询吗？"
        assert isinstance(record.record_id, UUID)
        assert isinstance(record.created_at, datetime)
        assert isinstance(record.updated_at, datetime)
    
    def test_link_previous_record(self):
        """测试链接上一条记录"""
        record1 = ConversationRecord(
            sequence_number=1,
            user_input="你好",
            current_state="/",
            prompt="测试提示词1",
            agent_output="回复1"
        )
        
        record2 = ConversationRecord(
            sequence_number=2,
            user_input="没啥问题",
            current_state="1.用户发起闲聊",
            prompt="测试提示词2",
            agent_output="回复2"
        )
        
        record2.link_previous(record1)
        
        assert record2.previous_record_id == record1.record_id
        assert record1.next_record_id == record2.record_id
    
    def test_link_next_record(self):
        """测试链接下一条记录"""
        record1 = ConversationRecord(
            sequence_number=1,
            user_input="你好",
            current_state="/",
            prompt="测试提示词1",
            agent_output="回复1"
        )
        
        record2 = ConversationRecord(
            sequence_number=2,
            user_input="没啥问题",
            current_state="1.用户发起闲聊",
            prompt="测试提示词2",
            agent_output="回复2"
        )
        
        record1.link_next(record2)
        
        assert record1.next_record_id == record2.record_id
        assert record2.previous_record_id == record1.record_id
    
    def test_json_serialization(self):
        """测试JSON序列化"""
        record = ConversationRecord(
            sequence_number=1,
            user_input="你好",
            current_state="/",
            prompt="测试提示词",
            agent_output="回复"
        )
        
        json_data = record.model_dump()
        
        assert "record_id" in json_data
        assert "sequence_number" in json_data
        assert "user_input" in json_data
        assert "current_state" in json_data
        assert "prompt" in json_data
        assert "agent_output" in json_data
        assert "created_at" in json_data
        assert "updated_at" in json_data


class TestRecordChain:
    """测试RecordChain实体"""
    
    def test_create_empty_chain(self):
        """测试创建空链条"""
        chain = RecordChain()
        
        assert isinstance(chain.chain_id, UUID)
        assert len(chain.records) == 0
        assert chain.get_chain_length() == 0
    
    def test_add_single_record(self):
        """测试添加单条记录"""
        chain = RecordChain()
        record = ConversationRecord(
            sequence_number=1,
            user_input="你好",
            current_state="/",
            prompt="测试提示词",
            agent_output="回复"
        )
        
        chain.add_record(record)
        
        assert len(chain.records) == 1
        assert chain.get_chain_length() == 1
        assert chain.records[0] == record
    
    def test_add_multiple_records(self):
        """测试添加多条记录"""
        chain = RecordChain()
        
        record1 = ConversationRecord(
            sequence_number=1,
            user_input="你好",
            current_state="/",
            prompt="测试提示词1",
            agent_output="回复1"
        )
        
        record2 = ConversationRecord(
            sequence_number=2,
            user_input="没啥问题",
            current_state="1.用户发起闲聊",
            prompt="测试提示词2",
            agent_output="回复2"
        )
        
        record3 = ConversationRecord(
            sequence_number=3,
            user_input="就想看下你们服务如何",
            current_state="1.1引导用户询问业务问题",
            prompt="测试提示词3",
            agent_output="回复3"
        )
        
        chain.add_record(record1)
        chain.add_record(record2)
        chain.add_record(record3)
        
        assert len(chain.records) == 3
        assert chain.get_chain_length() == 3
        
        # 验证链接关系
        assert record1.next_record_id == record2.record_id
        assert record2.previous_record_id == record1.record_id
        assert record2.next_record_id == record3.record_id
        assert record3.previous_record_id == record2.record_id
    
    def test_get_history_from_middle_record(self):
        """测试从中间记录获取历史"""
        chain = RecordChain()
        
        record1 = ConversationRecord(
            sequence_number=1,
            user_input="你好",
            current_state="/",
            prompt="测试提示词1",
            agent_output="回复1"
        )
        
        record2 = ConversationRecord(
            sequence_number=2,
            user_input="没啥问题",
            current_state="1.用户发起闲聊",
            prompt="测试提示词2",
            agent_output="回复2"
        )
        
        record3 = ConversationRecord(
            sequence_number=3,
            user_input="就想看下你们服务如何",
            current_state="1.1引导用户询问业务问题",
            prompt="测试提示词3",
            agent_output="回复3"
        )
        
        chain.add_record(record1)
        chain.add_record(record2)
        chain.add_record(record3)
        
        # 从record2获取历史
        history = chain.get_history_from(record2.record_id)
        
        assert len(history) == 2  # record1 和 record2
        assert history[0] == record1
        assert history[1] == record2
    
    def test_get_history_from_first_record(self):
        """测试从第一条记录获取历史"""
        chain = RecordChain()
        
        record1 = ConversationRecord(
            sequence_number=1,
            user_input="你好",
            current_state="/",
            prompt="测试提示词1",
            agent_output="回复1"
        )
        
        record2 = ConversationRecord(
            sequence_number=2,
            user_input="没啥问题",
            current_state="1.用户发起闲聊",
            prompt="测试提示词2",
            agent_output="回复2"
        )
        
        chain.add_record(record1)
        chain.add_record(record2)
        
        # 从record1获取历史
        history = chain.get_history_from(record1.record_id)
        
        assert len(history) == 1  # 只有record1
        assert history[0] == record1
    
    def test_get_full_chain(self):
        """测试获取完整链条"""
        chain = RecordChain()
        
        record1 = ConversationRecord(
            sequence_number=1,
            user_input="你好",
            current_state="/",
            prompt="测试提示词1",
            agent_output="回复1"
        )
        
        record2 = ConversationRecord(
            sequence_number=2,
            user_input="没啥问题",
            current_state="1.用户发起闲聊",
            prompt="测试提示词2",
            agent_output="回复2"
        )
        
        chain.add_record(record1)
        chain.add_record(record2)
        
        full_chain = chain.get_full_chain()
        
        assert len(full_chain) == 2
        assert full_chain[0] == record1
        assert full_chain[1] == record2
        
        # 确保返回的是副本
        full_chain.append(ConversationRecord(
            sequence_number=3,
            user_input="测试",
            current_state="测试",
            prompt="测试",
            agent_output="测试"
        ))
        assert len(chain.records) == 2  # 原链条不受影响


class TestImportResult:
    """测试ImportResult实体"""
    
    def test_successful_import(self):
        """测试成功导入"""
        result = ImportResult(
            success=True,
            total_records=10,
            imported_records=10,
            failed_records=0,
            error_messages=[],
            chain_id=uuid4()
        )
        
        assert result.success is True
        assert result.total_records == 10
        assert result.imported_records == 10
        assert result.failed_records == 0
        assert len(result.error_messages) == 0
        assert result.success_rate == 1.0
    
    def test_partial_import(self):
        """测试部分导入"""
        result = ImportResult(
            success=False,
            total_records=10,
            imported_records=7,
            failed_records=3,
            error_messages=["错误1", "错误2", "错误3"]
        )
        
        assert result.success is False
        assert result.total_records == 10
        assert result.imported_records == 7
        assert result.failed_records == 3
        assert len(result.error_messages) == 3
        assert result.success_rate == 0.7
    
    def test_failed_import(self):
        """测试导入失败"""
        result = ImportResult(
            success=False,
            total_records=5,
            imported_records=0,
            failed_records=5,
            error_messages=["连接失败"]
        )
        
        assert result.success is False
        assert result.total_records == 5
        assert result.imported_records == 0
        assert result.failed_records == 5
        assert result.success_rate == 0.0
    
    def test_empty_import(self):
        """测试空导入"""
        result = ImportResult(
            success=True,
            total_records=0,
            imported_records=0,
            failed_records=0,
            error_messages=[]
        )
        
        assert result.success is True
        assert result.total_records == 0
        assert result.imported_records == 0
        assert result.failed_records == 0
        assert result.success_rate == 0.0


class TestQueryResult:
    """测试QueryResult实体"""
    
    def test_create_query_result(self):
        """测试创建查询结果"""
        record = ConversationRecord(
            sequence_number=1,
            user_input="你好",
            current_state="/",
            prompt="测试提示词",
            agent_output="回复"
        )
        
        result = QueryResult(
            query_text="你好",
            results=[record],
            total_count=1
        )
        
        assert result.query_text == "你好"
        assert len(result.results) == 1
        assert result.results[0] == record
        assert result.total_count == 1
        assert isinstance(result.query_id, UUID)
        assert isinstance(result.query_time, datetime)
    
    def test_empty_query_result(self):
        """测试空查询结果"""
        result = QueryResult(
            query_text="不存在的查询",
            results=[],
            total_count=0
        )
        
        assert result.query_text == "不存在的查询"
        assert len(result.results) == 0
        assert result.total_count == 0