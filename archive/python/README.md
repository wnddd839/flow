# Python 版（已归档）

v0.5.0 及更早版本的 Flow CLI 由 Python 实现，已于 **v0.6.0** 起由 TypeScript 重写并作为主线维护。

## 为何归档

- npm 分发（`npx @wnddd8339/flow`）无需 Python 运行时
- 与前端/Node 生态仓库的安装方式一致
- 功能已完整迁移至 `src/`（init / check / editors / tools / instructions）

## 如需查阅旧实现

```bash
cd archive/python
python -m pip install -e ".[dev]"
python -m pytest -q
```

**请勿在新项目中使用此目录**；仅作历史参考。
