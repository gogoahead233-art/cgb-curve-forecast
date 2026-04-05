# 开发计划 (PLAN.md)

逐 Task 推进，每个 Task 完成后测试验证再进下一个。

---

## Task 1.1: 项目初始化

创建目录结构、requirements.txt、config.py、state.py、.env.example、.gitignore

### requirements.txt
```
langchain>=0.3
langgraph>=0.2
langchain-anthropic>=0.3
WindPy
akshare>=1.18
tavily-python>=0.5
pandas>=2.0
numpy>=1.24
python-dotenv>=1.0
```

### config.py
```python
import os
from dotenv import load_dotenv
load_dotenv()

# LLM
BASE_URL = os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
AGENT_MODEL = "claude-sonnet-4-20250514"
CHIEF_MODEL = "claude-sonnet-4-20250514"

# 数据源: "wind" 或 "akshare"
DATA_SOURCE = os.getenv("DATA_SOURCE", "wind")

# Wind 回溯深度
MACRO_LOOKBACK_MONTHS = 24
YIELD_LOOKBACK_YEARS = 1  # 用1年而非3年，减少结构性下移干扰
FUTURES_LOOKBACK_DAYS = 60
FUNDING_LOOKBACK_DAYS = 60

# Tavily
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
```

### state.py
```python
from typing import TypedDict, Annotated, Optional
from langgraph.graph import add_messages

class AgentOutput(TypedDict):
    signal: str       # "bullish" | "bearish" | "none"
    reasoning: str    # 分析推理过程
    data_summary: str # 关键数据摘要

class MarketAgentOutput(AgentOutput):
    curve_shape: str  # "bull_flat" | "bull_steep" | "bear_flat" | "bear_steep" | "range_bound"

class RateAnalysisState(TypedDict):
    messages: Annotated[list, add_messages]
    query: str
    agent_a_output: Optional[AgentOutput]
    agent_b_output: Optional[AgentOutput]
    agent_c_output: Optional[MarketAgentOutput]
    agent_d_output: Optional[AgentOutput]
    agent_e_output: Optional[AgentOutput]
    chief_conclusion: Optional[str]
    confidence: Optional[str]       # "high" | "medium" | "low" | "insufficient"
    investment_advice: Optional[str]
```

### 验收标准
- [ ] 目录结构完整（agents/, tools/, prompts/, tests/, docs/）
- [ ] `pip install -r requirements.txt` 无报错
- [ ] `from state import RateAnalysisState` 可导入
- [ ] `from config import *` 可导入
- [ ] .env.example 包含 ANTHROPIC_API_KEY 和 TAVILY_API_KEY 和 DATA_SOURCE
- [ ] .gitignore 包含 .env, __pycache__, *.pyc

---

## Task 1.2: Wind 数据工具 (tools/wind_tools.py)

6 个 @tool 函数，每个返回格式化文本字符串供 LLM 阅读。

### get_macro_data(lookback_months: int = 24) -> str
- w.edb: M0000612(CPI), M0017126(PMI), M5525755(社融), M0001385(M2)
- 返回各指标最新值 + 近3/6/12月趋势方向
- 用线性回归斜率判断方向: 正=上升, 负=下降, 接近0=平稳

### get_yield_curve(lookback_years: int = 1) -> str
- w.edb: S0059744(1Y), S0059749(10Y), S0059751(30Y)
- 返回当前值 + 近1年百分位（仅位置参考）
- 计算 10Y-1Y 期限利差和 30Y-10Y 超长利差

### get_funding_data(lookback_days: int = 60) -> str
- w.edb: M0041653(DR007), M0062063(逆回购投放), M0062065(逆回购到期)
- 返回 DR007 最新值+20日均值 + 净投放 + vs政策利率偏离

### get_futures_data(lookback_days: int = 60) -> str
- w.wsd: T.CFE, TL.CFE 的 close,volume,oi
- 返回最新价格/量/仓 + 近60日数据供技术指标计算

### get_stock_index(lookback_days: int = 20) -> str
- w.wsd: 000001.SH 的 close
- 返回最新值 + 近20日涨跌幅

### get_us_treasury() -> str
- w.edb: G0000891
- 返回美债10Y最新值 + 中美利差

### 验收标准
- [ ] 每个函数独立运行返回格式化文本
- [ ] Wind 连接管理正常 (w.start/w.stop)
- [ ] 异常处理: Wind 未连接时给出清晰错误提示

---

## Task 1.3: AKShare 备用工具 (tools/akshare_tools.py)

与 wind_tools 相同的 6 个函数接口，用 AKShare 实现。
- bond_china_yield() 取收益率（含30Y）
- macro_china_cpi_yearly / pmi_yearly / m2_yearly 取宏观
- futures_main_sina("T0"/"TL0") 取期货
- stock_zh_index_daily("sh000001") 取上证
- bond_zh_us_rate() 取中美收益率
- 社融无稳定接口，返回"需通过搜索获取"

### 验收标准
- [ ] config.DATA_SOURCE="akshare" 时所有函数正常
- [ ] 与 wind_tools 返回格式一致

---

## Task 1.4: 计算工具 (tools/calc_tools.py)

### calc_curve_shape(yield_1y, yield_10y, yield_30y) -> str
输入近30日序列。计算:
- 10Y-1Y 和 30Y-10Y 利差及变化方向
- 1Y/10Y 近30日变动幅度(bp)
- 形态: 都下行+长端快=牛平, 都下行+短端快=牛陡, 都上行+长端快=熊陡, 都上行+短端快=熊平
- 变动小于3bp视为震荡

### calc_tech_signals(close, volume, oi) -> str
输入T合约近60日数据。计算:
- MA5/MA20 及交叉状态
- MACD (EMA12,EMA26,DEA=9) 金叉/死叉/柱体方向
- 量价: 价格方向×volume变化×oi变化 → 判断

### calc_trend_direction(series, periods=[3,6,12]) -> str
输入月度序列。用线性回归判断各period趋势方向。

### 验收标准
- [ ] 用真实数据测试，输出描述合理
- [ ] 边界情况: 数据不足时不报错

---

## Task 1.5: 搜索工具 (tools/search_tools.py)

封装 Tavily。5 个函数:
- search_policy_news() — 央行操作/货政
- search_bond_supply() — 债券供给计划
- search_external_events() — 美联储/地缘
- search_allocation_dynamics() — 资产荒/理财/配置
- search_policy_shock() — 监管表态/政治局会议

每个函数搜索2-3个关键词，返回最相关3-5条摘要。
无重大事件时返回"近期无重大相关信息"。

### 验收标准
- [ ] 有 Tavily key 时正常返回中文摘要
- [ ] 无 key 时优雅降级（返回提示信息）

---

## Task 2.1: Agent A — 宏观周期 (agents/macro_agent.py)

ReAct Agent，工具: get_macro_data, calc_trend_direction

完整 Prompt 和信号规范见 docs/DESIGN.md 第3节"Agent A"部分。
- 用"货币+信用"四象限判断周期
- 关注边际变化方向，不看绝对水平
- 不用均值回归
- 输出 AgentOutput 格式的 JSON

### 验收标准
- [ ] 拉取真实数据后输出合理的 signal + reasoning

---

## Task 2.2: Agent B — 资金供需 (agents/funding_agent.py)

ReAct Agent，工具: get_funding_data, get_yield_curve, search_policy_news, search_bond_supply

完整 Prompt 和信号规范见 docs/DESIGN.md 第3节"Agent B"部分。
- 两个维度: 当前资金面 + 政策预期
- 货政报告定调是"已知的未来"
- 收益率位置仅作参考

### 验收标准
- [ ] 整合数值数据和搜索结果输出合理判断

---

## Task 2.3: Agent C — 市场信号 (agents/market_agent.py)

ReAct Agent，工具: get_futures_data, calc_tech_signals, calc_curve_shape

完整 Prompt 和信号规范见 docs/DESIGN.md 第3节"Agent C"部分。
- 期货价格上涨=收益率下行=看多（注意方向反转）
- 量价组合判断趋势可信度
- 曲线形态判定
- 窄幅震荡/均线粘合=无信号
- 输出 MarketAgentOutput（含 curve_shape）

### 验收标准
- [ ] 输出包含方向信号+曲线形态

---

## Task 2.4: Agent D — 大类资产配置 (agents/allocation_agent.py)

ReAct Agent，工具: get_stock_index, search_allocation_dynamics

完整 Prompt 和信号规范见 docs/DESIGN.md 第3节"Agent D"部分。
- 判断资产荒 vs 负债荒
- 股市极端行情才有信号，日常波动=无信号
- 经常输出"none"是正常的
- 不要强行给信号

### 验收标准
- [ ] 股市平稳时输出 none，极端行情时输出方向

---

## Task 2.5: Agent E — 外部环境 (agents/external_agent.py)

ReAct Agent，工具: get_us_treasury, search_external_events, search_policy_shock

完整 Prompt 和信号规范见 docs/DESIGN.md 第3节"Agent E"部分。
- 低频高冲击，大部分时间无信号
- 中美利差倒挂是常态，只有大幅变化才是信号
- 国内监管/政策突发表态也归这里
- 无重大事件=none

### 验收标准
- [ ] 无事件时输出 none

---

## Task 3.1: 首席分析师 (agents/chief_agent.py)

不是 ReAct Agent，不调用工具。纯 LLM 推理节点。

完整 Prompt、判断规则和示例见 docs/DESIGN.md 第3节"首席分析师"和第6节"一致性判断示例"。
1. 过滤 signal="none" 的维度
2. 一致性判断:
   - 全同向 → 高确信，给方向+投资建议
   - 大部分同向 → 中确信，给方向+条件+风险
   - 严重分裂 → 低确信，不给方向，说"震荡/不确定"
   - ≤1个有效信号 → 信息不足
3. 逐步推理输出

输出格式:
```
【确信度】高/中/低/信号不足
【结论】一句话
【推理过程】逐步展开
【曲线形态】形态+预判
【投资建议】久期+期限+条件
【关键风险/等待变量】
```

### 验收标准
- [ ] 模拟5种信号组合，首席输出合理

---

## Task 3.2: LangGraph Graph (graph.py)

5 个 Agent 从 START 并行 → 全部完成后进入 chief → END

### 验收标准
- [ ] graph.compile() 无报错
- [ ] 完整运行 START→5 Agents→chief→END

---

## Task 3.3: 主入口 (main.py)

```python
def run_analysis(query="分析当前利率债市场，预测收益率方向和曲线形态"):
    result = app.invoke({"query": query, "messages": []})
    print(result["chief_conclusion"])
```

### 验收标准
- [ ] `python main.py` 输出完整分析

---

## Task 3.4: Prompt 调优

用真实数据跑3-5次，检查:
- Agent 是否正确输出三态信号
- 首席是否正确处理矛盾/无信号
- 推理链是否清晰
- 投资建议是否具体可操作

---

## Task 3.5: 测试

- tests/test_calc_tools.py — 计算函数单元测试
- tests/test_agents.py — 单 Agent 测试
- tests/test_graph.py — 端到端测试
