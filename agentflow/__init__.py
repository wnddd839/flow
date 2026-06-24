"""AgentFlow / Flow — 本地 AI 编程工作流 CLI（离线、无 API）。

## 从哪里读起

1. ``cli.main``     — 带参数子命令（``flow init``、``flow handoff`` …）
2. ``repl.run_repl`` — 无参数时进入交互工作台（``flow``）
3. ``core``         — 初始化、扫描、路由推荐、doctor 等纯逻辑

## 模块分工（按层）

**入口层**

- ``cli``   — argparse 解析 + ``COMMANDS`` 分发表
- ``repl``  — Rich 终端 UI + ``/`` 斜杠命令（文件较大，按 ``# -- 章节 --`` 跳转）

**项目工作流（读写当前目录 ``.agentflow/``）**

- ``core``        — ``init_project``、``scan_project``、``recommend_route``、``doctor_project``
- ``quick_setup`` — 勾选 agent 后一步完成 init（``flow setup`` / 裸 ``flow init``）
- ``templates``   — 生成 constitution、skills、薄入口等**文件内容**（字符串模板）
- ``state``       — ``.agentflow/state.yaml`` 读写
- ``changes``     — ``.agentflow/changes/<id>/`` 轻量变更记录
- ``context``     — 生成 ``FLOW_CONTEXT.md`` 交接快照
- ``repair``      — 按 doctor 结果补缺失文件（不覆盖已有内容）

**用户级配置（读写 ``~/.agentflow/``）**

- ``editors``  — 启用哪些 AI 工具；配置在 ``editors.yaml``（**全局**，影响所有项目）
- ``skills``   — 全局 skill 安装/同步；配置在 ``config.yaml``、``skills.lock.yaml``
- ``projects`` — 已注册项目列表；用于 ``sync-all`` 批量刷新

**辅助**

- ``clipboard``   — handoff/context 输出后 best-effort 复制剪贴板
- ``diagnostics`` — PATH 上 AI 工具探测 + doctor 汇总展示

## 数据流简图

::

    用户 → cli / repl
              ↓
         core / quick_setup / skills / editors …
              ↓
         templates（内容）→ 写入磁盘
              ↓
    项目 .agentflow/  +  用户 ~/.agentflow/

## 注意

- 请阅读 ``agentflow/`` 下的**源码**；``build/lib/`` 是构建缓存，可能过期，已在 ``.gitignore`` 中忽略。
"""

__version__ = "0.3.1"
