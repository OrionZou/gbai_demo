根据以下信息设计对话列表实体类。

\begin{case_lib} 
案例库即案例列表，每个元素是 一个列表是指多轮对话，列表的每个元素表示每轮对话，形式为 ospa。

\begin{case}{案例id，自动生成}
以下是多轮对话案例的描述 \\

\begin{turn}
一轮对话
\content[o, obs] 写观测信息
\begin{tags}[s，写记忆状态名称，可以理解为章节名称，以及其中相关标签] 
  \pair{标签维度}{标签名称}
\end{tags}
\begin{dict}[p，写记忆状态的关联信息，可以理解章节关联的多个 node]
   内容% \begin{node}[chapter]{章节名称} \end{node}
\end{dict}
\content[a, answer] 写回复
\end{turn}


\begin{turn}
  asda
  \content[obs] 写观测信息
  \begin{tags}[维修 L6汽车的轮胎] 
    \pair{标签维度}{标签名称}
  \end{tags}
  \begin{dict}[p，写记忆状态的关联信息，可以理解章节关联的多个 node]
    \item[名称] 内容% \begin{node}[chapter]{章节名称} \end{node}
  \end{dict}
  \content[answer] 写回复
\end{turn}

\end{case_lib}


根据以下信息设计动作类。


\begin{action_lib} % 动作列表，每个元素是 一个 dict。
动作列表即动作库，类似于工具库，可以通过 tool celling 或 structured output 等方式生成调用参数，通过工具调用模块进行调用。 \\

\begin{dict}[使用dict环境，写action名称]
  \item[动作名称] 写动作名称% 也可以是 \begin{dict} \end{dict}
  \item[动作描述] 写动作描述
  \item[动作参数] 写动作参数，是dict环境嵌套的\begin{dict}[dict名称(action名称)] asda \end{dict}
\end{dict}
\end{action_lib}