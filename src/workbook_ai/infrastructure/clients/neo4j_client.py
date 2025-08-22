"""
Neo4j图数据库客户端
Infrastructure层 - 实现图数据库的核心功能
"""

import logging
from typing import List, Dict, Any, Optional

try:
    from neo4j import GraphDatabase, Driver, Session
    from neo4j.exceptions import Neo4jError
except ImportError:
    # 在没有安装neo4j时提供占位符
    GraphDatabase = None
    Driver = None
    Session = None
    Neo4jError = Exception

from workbook_ai.domain.entities import ImportResult


logger = logging.getLogger(__name__)


class Neo4jClient:
    """Neo4j图数据库客户端"""
    
    def __init__(
        self, 
        uri: str = "bolt://localhost:7687", 
        user: str = "neo4j", 
        password: str = "password"
    ):
        """
        初始化Neo4j客户端
        
        Args:
            uri: Neo4j服务器地址
            user: 用户名
            password: 密码
        """
        self.uri = uri
        self.user = user
        self.password = password
        self.driver: Optional[Driver] = None
        self._connect()
    
    def _connect(self) -> None:
        """连接到Neo4j服务器"""
        if GraphDatabase is None:
            logger.error("neo4j驱动未安装，请运行: pip install neo4j")
            return
            
        try:
            self.driver = GraphDatabase.driver(
                self.uri, 
                auth=(self.user, self.password)
            )
            # 测试连接
            with self.driver.session() as session:
                session.run("RETURN 1")
            logger.info(f"成功连接到Neo4j服务器: {self.uri}")
        except Exception as e:
            logger.error(f"连接Neo4j服务器失败: {e}")
            self.driver = None
    
    def create_collection(self, collection_name: str) -> bool:
        """
        创建collection（在Neo4j中相当于创建节点标签和约束）
        
        Args:
            collection_name: 集合名称（节点标签）
            
        Returns:
            bool: 创建是否成功
        """
        if not self.driver:
            logger.error("Neo4j客户端未连接")
            return False
        
        try:
            with self.driver.session() as session:
                # 创建唯一性约束
                constraint_query = f"""
                CREATE CONSTRAINT {collection_name}_id_unique 
                IF NOT EXISTS 
                FOR (n:{collection_name}) 
                REQUIRE n.recordId IS UNIQUE
                """
                session.run(constraint_query)
                
                # 创建索引以提高查询性能
                index_query = f"""
                CREATE INDEX {collection_name}_sequence_idx 
                IF NOT EXISTS 
                FOR (n:{collection_name}) 
                ON (n.sequenceNumber)
                """
                session.run(index_query)
                
                logger.info(f"成功创建collection: {collection_name}")
                return True
                
        except Neo4jError as e:
            logger.error(f"创建collection失败: {e}")
            return False
    
    def import_data(
        self, 
        nodes: List[Dict[str, Any]], 
        relationships: List[Dict[str, Any]]
    ) -> ImportResult:
        """
        导入节点和关系数据
        
        Args:
            nodes: 节点数据列表
            relationships: 关系数据列表
            
        Returns:
            ImportResult: 导入结果
        """
        if not self.driver:
            logger.error("Neo4j客户端未连接")
            return ImportResult(
                success=False,
                total_records=len(nodes) + len(relationships),
                imported_records=0,
                failed_records=len(nodes) + len(relationships),
                error_messages=["Neo4j客户端未连接"]
            )
        
        total_records = len(nodes) + len(relationships)
        imported_records = 0
        failed_records = 0
        error_messages = []
        
        try:
            with self.driver.session() as session:
                # 导入节点
                for node in nodes:
                    try:
                        label = node.pop('label', 'ConversationRecord')
                        node_query = f"""
                        MERGE (n:{label} {{recordId: $recordId}})
                        SET n += $properties
                        """
                        session.run(
                            node_query, 
                            recordId=node.get('recordId'),
                            properties=node
                        )
                        imported_records += 1
                        
                    except Exception as e:
                        failed_records += 1
                        error_msg = f"导入节点失败: {e}"
                        error_messages.append(error_msg)
                        logger.error(error_msg)
                
                # 导入关系
                for rel in relationships:
                    try:
                        rel_query = """
                        MATCH (a {recordId: $from_id})
                        MATCH (b {recordId: $to_id})
                        MERGE (a)-[r:NEXT_RECORD]->(b)
                        SET r += $properties
                        """
                        session.run(
                            rel_query,
                            from_id=rel.get('from_id'),
                            to_id=rel.get('to_id'),
                            properties=rel.get('properties', {})
                        )
                        imported_records += 1
                        
                    except Exception as e:
                        failed_records += 1
                        error_msg = f"导入关系失败: {e}"
                        error_messages.append(error_msg)
                        logger.error(error_msg)
            
            logger.info(
                f"数据导入完成: 总数={total_records}, "
                f"成功={imported_records}, 失败={failed_records}"
            )
            
        except Neo4jError as e:
            error_msg = f"批量导入失败: {e}"
            error_messages.append(error_msg)
            logger.error(error_msg)
            failed_records = total_records
            imported_records = 0
        
        return ImportResult(
            success=failed_records == 0,
            total_records=total_records,
            imported_records=imported_records,
            failed_records=failed_records,
            error_messages=error_messages
        )
    
    def query(
        self, 
        cypher_query: str, 
        parameters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        执行Cypher查询
        
        Args:
            cypher_query: Cypher查询语句
            parameters: 查询参数
            
        Returns:
            List[Dict[str, Any]]: 查询结果
        """
        if not self.driver:
            logger.error("Neo4j客户端未连接")
            return []
        
        if parameters is None:
            parameters = {}
        
        try:
            with self.driver.session() as session:
                result = session.run(cypher_query, parameters)
                return [record.data() for record in result]
                
        except Neo4jError as e:
            logger.error(f"查询失败: {e}")
            return []
    
    def get_conversation_chain(self, record_id: str) -> List[Dict[str, Any]]:
        """
        获取对话链条
        
        Args:
            record_id: 记录ID
            
        Returns:
            List[Dict[str, Any]]: 链条中的所有记录
        """
        query = """
        MATCH path = (start:ConversationRecord {recordId: $record_id})
                    -[:NEXT_RECORD*0..]->(end:ConversationRecord)
        WHERE NOT (end)-[:NEXT_RECORD]->()
        WITH start, end, path
        MATCH chain = (first:ConversationRecord)-[:NEXT_RECORD*0..]->(end)
        WHERE NOT (first)<-[:NEXT_RECORD]-()
        AND first IN nodes(path)
        RETURN [node in nodes(chain) | node] as chain_nodes
        ORDER BY length(chain) DESC
        LIMIT 1
        """
        
        result = self.query(query, {"record_id": record_id})
        if result and result[0].get('chain_nodes'):
            return [dict(node) for node in result[0]['chain_nodes']]
        return []
    
    def get_state_transitions(self) -> List[Dict[str, Any]]:
        """
        获取状态转换统计
        
        Returns:
            List[Dict[str, Any]]: 状态转换信息
        """
        query = """
        MATCH (a:ConversationRecord)-[:NEXT_RECORD]->(b:ConversationRecord)
        WHERE a.currentState IS NOT NULL AND b.currentState IS NOT NULL
        RETURN a.currentState as from_state, 
               b.currentState as to_state, 
               count(*) as transition_count
        ORDER BY transition_count DESC
        """
        
        return self.query(query)
    
    def delete_collection(self, collection_name: str) -> bool:
        """
        删除collection（删除所有指定标签的节点）
        
        Args:
            collection_name: 集合名称
            
        Returns:
            bool: 删除是否成功
        """
        if not self.driver:
            logger.error("Neo4j客户端未连接")
            return False
        
        try:
            with self.driver.session() as session:
                # 删除节点和关系
                delete_query = f"MATCH (n:{collection_name}) DETACH DELETE n"
                session.run(delete_query)
                
                # 删除约束
                try:
                    constraint_query = f"""
                    DROP CONSTRAINT {collection_name}_id_unique IF EXISTS
                    """
                    session.run(constraint_query)
                except Neo4jError:
                    pass  # 约束可能不存在
                
                # 删除索引
                try:
                    index_query = f"""
                    DROP INDEX {collection_name}_sequence_idx IF EXISTS
                    """
                    session.run(index_query)
                except Neo4jError:
                    pass  # 索引可能不存在
                
                logger.info(f"成功删除collection: {collection_name}")
                return True
                
        except Neo4jError as e:
            logger.error(f"删除collection失败: {e}")
            return False
    
    def close(self) -> None:
        """关闭连接"""
        if self.driver:
            self.driver.close()
            self.driver = None
            logger.info("Neo4j连接已关闭")