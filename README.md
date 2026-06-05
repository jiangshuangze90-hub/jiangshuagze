# 四川蒲江育苗基地

四川蒲江育苗基地，自产自销。

## 供应品类

- 茶苗
- 茶叶树
- 茶树老桩
- 茶树盆栽
- 景观茶树
- 绿化茶树
- 工程茶苗

## 服务优势

- 货源稳定
- 苗质好
- 成活率高
- 全国物流发货
- 支持实地看苗
- 支持批量采购

## 批发合作

联系电话：13982177413
## work

## Codex 接入 DeepSeek

本仓库提供一套本地 DeepSeek 适配配置，用于把 DeepSeek 模型放进 Codex 的模型下拉列表，并通过本地桥接服务正常调用 DeepSeek 官方 Chat Completions API。

### 文件说明

- `codex-deepseek/model-catalog.json`：Codex 模型目录，声明 `DeepSeek Chat` 和 `DeepSeek Reasoner` 两个可见模型选项。
- `scripts/install_deepseek_codex.py`：安装脚本，会把 DeepSeek provider 和模型目录写入 `~/.codex/config.toml`。
- `scripts/deepseek_codex_bridge.py`：本地 Responses API 桥接服务，把 Codex 的 `/v1/responses` 请求转换成 DeepSeek `/chat/completions` 请求。

### 使用步骤

1. 准备 DeepSeek API Key：

   ```bash
   export DEEPSEEK_API_KEY="你的 DeepSeek API Key"
   ```

2. 安装 Codex 配置：

   ```bash
   python3 scripts/install_deepseek_codex.py
   ```

   如需直接把 DeepSeek 设为默认模型：

   ```bash
   python3 scripts/install_deepseek_codex.py --set-default
   ```

3. 启动本地桥接服务：

   ```bash
   python3 scripts/deepseek_codex_bridge.py
   ```

4. 重启 Codex，在模型下拉框中选择 `DeepSeek Chat` 或 `DeepSeek Reasoner`。也可以直接用命令行指定：

   ```bash
   codex -c model_provider=deepseek -c model=deepseek-chat
   ```

### 注意事项

- Codex 自定义 provider 当前按 Responses API 调用；DeepSeek 官方接口是 Chat Completions 格式，所以需要保持 `scripts/deepseek_codex_bridge.py` 运行。
- `DeepSeek Chat` 更适合需要工具调用的代码修改流程；`DeepSeek Reasoner` 更适合分析和推理。
- 如果 Codex 桌面端没有立即刷新下拉选项，请完全退出并重启 Codex；配置文件只会在启动时加载。
