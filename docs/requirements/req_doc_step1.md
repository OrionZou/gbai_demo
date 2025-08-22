写一个ai工具管理的项目，要求项目具有以下功能：

我们计划写一个 AI 知识库的项目，要求项目架构经典的 DDD 四层架构（Domain, Application, Infrastructure, Interface）。


目前我明确了其中部分功能，要求仅完成以下功能，不进行以下功能以外的设计和规划。


1. 基于 Weaviate 设计一个 Vector DB Client 在 Infrastructure层, 该 Client 具有创建 collection、导入数据、查询等功能。
2. 基于 Neo4j 设计一个 Graph DB Client 在 Infrastructure层, 该 Client 具有创建 collection、导入数据、查询等功能。
3. 设计导入数据实体类，使用 pydantic 实现，参考oss'pa中的三个案例，每行表示一个条数据，可以链接上一条数据和下一条数据，可以不断追溯上一条数据到最开始构建 history。
4. 构建Weaviate 和 Neo4j 一键部署的 docker compose 镜像组件，挂载的数据库目录，分别在该镜像下的 weaviate_db_data 和 neo4j_db_data，这 2 个文件夹设置 gitignore。


使用 pydantic 实现，实现所有实体类。

首先根据功能需求 设计项目架构文档，要求明确 实体类定义、状态管理、时序调用。项目架构采用经典的 DDD 四层架构（Domain, Application, Infrastructure, Interface）实现，但是架构设计尽可能简洁，最小化文件数量创建。google 专业架构师的水平进行设计。

设计完成后，google 代码专家根据架构设计文档进行实现。
- python环境要求 3.12，使用 uv 管理 python环境，使用 poetry 管理 python 包依赖。
- 引入包时，使用绝对路径。

实现完成后 google， 测试专家对代码进元测试，测试覆盖率达到 100%，然后测试每个功能接口。


