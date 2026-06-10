# 🎨 Graphical AI Toolchain / 图形AI工具链

<p align="center">
  <a href="#-design-philosophy--设计理念">
    <img src="https://img.shields.io/badge/English-Click_to_Switch-blue?style=for-the-badge&logo=github" alt="Switch to English">
  </a>
  &nbsp;&nbsp;
  <a href="#-设计理念">
    <img src="https://img.shields.io/badge/中文-点击切换-red?style=for-the-badge&logo=github" alt="切换到中文">
  </a>
</p>

---

## 🇬🇧 English

### 🧠 Design Philosophy
1. **Accessible to Everyone**: Keep the system as simple as possible and use straightforward language for development, making it ideal for teaching and secondary development.
2. **Small-Parameter & Privacy Friendly**: It's normal for large models to get things done, but making a 1/10th parameter model do the same is challenging. Small models often suffer from context forgetting and hallucinations caused by excessive prompts. Moreover, everyone has secrets; the network is never entirely risk-free.
3. **Extensibility**: The code is designed with numerous hooks:
   - **Message Tree Manager**: Handles message concatenation and the recycling of session/message IDs.
   - **Guardrails**: Error logging + error message dropping.
   - **Router Manager**: Distributes messages downstream. Currently based on keyword matching at the beginning of code blocks, but you can plug in your own routing models here.
   - **JSON Protocol**: Supports strings, Python lists/dicts, and binary byte streams. Specific templates are maintained in the maintenance classes.
   - **UI_Canvas.py**: Manages the UI interface, allowing you to add custom nodes and reuse JSON protocol wrapper classes.
4. **Pseudo-Decentralization**: Balances centralized communication management with decentralized plugin autonomy. Plugins have an independent `_plugin_public.py` to manage session IDs and parse protocol packets, letting plugins focus purely on business logic. Plugin development templates (e.g., connecting to Ollama or local weights) are provided.
5. **Plugin Proactivity**: Plugins can proactively output content without being explicitly called. These outputs are tagged for session management and downstream transmission, making it easy to integrate random number generators to solve threshold issues caused by missing or insufficient AI training data.

### 🚀 Quick Start
1. **Prerequisites**: Install [Ollama](https://ollama.com/) and [Python 3.11.8](https://www.python.org/downloads/release/python-3118/).
2. **Choose Your Model**: Download a model via Ollama. Open `plugins/Ollama_model.py` and change the model name variable (refer to the comments in the file).
3. **Setup Environment**: Run the auto-setup script based on your OS:
   - Windows: `auto_setup_WINDOWS_CMD.bat`
   - Linux: `auto_setup_Linux.sh`
4. **Download Default Model**: Start Ollama. If on Windows, click the model icon in the bottom right of the dialog and download `Qwen3-vl:4B` (required for the default plugin demo).
5. **Launch**: Double-click the startup file:
   - Windows: `main_run_WINDOWS_CMD.bat`
   - Linux: `main_run_Linux.sh`
6. **Explore**: You should now see the UI. The project is a bit older, so feel free to explore its features based on the design philosophy above!

### ⚠️ Known Issues
1. In massive cyclic multi-agent workflows, session IDs might struggle to manage highly proactive agents.
2. Fault handling only has hooks without timeout settings yet. (Awaiting future expansion as I'm currently preparing for college entrance exams!)

### 💬 A Note from the Author
I am a 17-year-old high school student, not a professional programmer. This system inevitably has flaws. I warmly welcome fellow enthusiasts to discuss solutions! While I couldn't make this project perfect, I hope for sincere and friendly exchanges.

The framework was co-developed by a human and AI. I handled the design, validation, router, message tree manager, and guardrails. Due to limited experience, details like text validation, fault tolerance, and multi-layer error handling are weak. This is merely a Minimum Viable Product (MVP) for learning.

Thank you for viewing this project. Your support is my greatest motivation!

---

## 🇨🇳 设计理念

1. **面向大众**: 尽可能让这个系统变得简洁，使用更简单的语言开发，用于教学或者二次开发。
2. **小参数友好，私密性能**: 用大参数的模型完成一件事情很正常，但如何让一个 1/10 参数的模型完成同样的事情是一件有难度的事。小参数模型的上下文遗忘、提示词过多造成的幻觉都会影响最终结果。而且每一个企业个人都有一些不能告诉别人的秘密，网络永远存在风险。
3. **可扩展性**: 在代码中留下了很多钩子:
   - **消息树管理器**: 负责消息的拼接，会话标识、消息标识的回收。
   - **护栏处理**: 错误记录 + 错误信息丢弃。
   - **路由管理器**: 消息的向下分发。目前是基于代码块中的首位关键词匹配分发，你也可以在这里接入你自己的路由模型。
   - **JSON协议**: 协议本身支持字符串、Python列表/字典、二进制字节流等传输模式，具体模板在维护类中。
   - **界面_画布.py**: UI界面的管理，可以添加新的自定义节点，复用JSON协议包装类。
4. **伪去中心化**: 兼顾中心化的交流管理能力，以及去中心化的插件自治优势。插件端有独立的 `_插件公用.py`，负责管理会话标识、协议包解析，让插件端可以专注于业务逻辑。提供了插件开发模板（对接 Ollama、对接本地权重等）。
5. **插件主动性**: 某一插件可以在没有被任何调用的情况下主动输出内容，并被打上标识进行会话管理及向下传输。这使得它可以对接随机数生成器，用于解决 AI 原有数据里不存在某内容，或者对某内容覆盖程度不够导致的阈限问题。

### 🚀 运行流程
1. **环境准备**: 你需要拥有 [Ollama](https://ollama.com/) 和 [Python 3.11.8](https://www.python.org/downloads/release/python-3118/)，安装引导里已经为你提供了目标网址。
2. **选择模型**: 在 Ollama 下载一个你喜欢的模型，并在 `插件/Ollama_model.py` 修改模型名变量（详细参照文件里的注释）。
3. **配置环境**: 根据你的操作系统运行自动配置脚本：
   - Windows: `自动配置环境_WINDOWS_CMD.bat`
   - Linux: `自动配置环境_Linux.sh`
4. **下载默认模型**: 打开 Ollama 软件。如果是 Windows，点击对话框右下角的小栏目，选择并下载 `Qwen3-vl:4B`（默认插件演示所需）。
5. **正式启动**: 双击启动文件：
   - Windows: `正式启动_WINDOEWS_CMD.bat`
   - Linux: `main_run_Linux.sh`
6. **开始探索**: 不出意外现在你应该成功看见了页面。接下来的就交给你自己去探索了！

### ⚠️ 潜在问题
1. 在庞大的环状多智能体协作流程中，会话标识几乎无法撑住针对庞大的主动性智能体进行管理。
2. 故障处理仅预留了钩子并没有做任何超时设置，这些功能等待后期拓展（因为我个人能力有限，且马上高考了 🎓）。

### 💬 结语
本人并不是专业的程序员，只有 17 岁，并且在上高中，所以该系统免不了会有一些问题。我很欢迎任何去探讨这些问题解决方法的同好！虽然无法让该作品达到完美是我的问题，但我依然希望我们可以进行真挚且友好的交流。

系统框架由人与 AI 协作开发。本人负责设计、验证、路由器、消息树管理器、护栏等的具体设计与实现。由于开发经验不足，在文本校验、容错冗余、多层故障处理等细节上显得非常薄弱。该系统仅仅只是一个最小可行验证（MVP）以及主要用于学习。

感谢每一个观看到该项目的人，你的支持是我最大的动力，谢谢！

---
<p align="center">
  <a href="#">⬆️ Back to Top / 回到顶部</a>
</p>

# github简介:
A lightweight multi-agent collaboration system for learning. Built entirely in Python with a built-in vector DB and CMD executor. Features one-click setup and launch scripts, plugin support, and offline capability. Highly optimized for small local models (e.g., 30B).