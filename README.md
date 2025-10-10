> **作者的话**
> 
> 大家好！这是我第一次使用 GitHub 平台，也是我的第一个开源项目，所以还算是个小白。
> 下面我将介绍项目所需的环境和依赖。如有遗漏，敬请见谅，也欢迎大家补充！

所需依赖已在 `requirements.txt` 和 `package.json` 文件中列出。

# 藿藿语音聊天机器人

基于vue3+uni-app+Python Django的全栈语音聊天应用

## ✨ 功能特性
- 🎤 实时语音对话
- 🤖 AI 智能回复
- 📱 多端支持 (H5 / 微信小程序 / App)
- 🎵 语音合成与识别

## 🛠️ 技术栈

### 前端
- Vue3
- uni-app
- Vite

### 后端
- Python 3.8+
- Django
- Django REST Framework
- WebSocket

## ⚙️ 环境要求
- Node.js 16+
- Python 3.8+
- HBuilderX (可选，用于 App 或小程序开发)

## 🚀 快速开始

### 1. 前端设置

```bash
# 克隆项目
git clone https://github.com/your-username/huo-voice-chat.git
cd huo-voice-chat/frontend/

# 安装依赖
npm install

# 开发模式 (H5)
npm run dev:h5

# 构建生产版本 (H5)
npm run build:h5

# 微信小程序开发
npm run dev:mp-weixin
```

### 2. 后端设置

```bash
# 进入后端目录
cd ../backend/

# 创建并激活虚拟环境
# Linux/Mac
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate

# 安装Python依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
```
> **注意**: 请编辑 `.env` 文件，配置你的数据库和火山引擎 API 密钥。

```bash
# 数据库迁移
python manage.py migrate

# 启动后端服务
python manage.py runserver
```

### 3. 重要配置

> 1.  在项目源码中全局搜索 `localhost`，并将其全部替换成你电脑的局域网 IP 地址。
> 2.  在源码中搜索 `your_api`，将其替换成你自己的火山引擎 API 信息。
> 3.  请前往火山引擎平台开通所需服务，例如：字节跳动大模型、声音复刻等。源码注释中已列出所需的具体模型。

### 4. (H5) 开启浏览器录音权限

为了在 `http://` (非 `https`) 协议的 H5 页面上进行测试，你需要为浏览器设置白名单。

**Chrome 浏览器**
1.  在地址栏输入 `chrome://flags/#unsafely-treat-insecure-origin-as-secure` 并回车。
2.  将 `Insecure origins treated as secure` 选项设置为 `Enabled`。
3.  在下方出现的输入框中，填入你的 H5 服务地址，例如 `http://<你的IP地址>:5173`。多个地址用逗号分隔。
4.  点击 `Relaunch` 重启浏览器。

**Edge 浏览器**
1.  在地址栏输入 `edge://flags/#unsafely-treat-insecure-origin-as-secure` 并回车。
2.  将 `Insecure origins treated as secure` 选项设置为 `Enabled`。
3.  在下方出现的输入框中，填入你的 H5 服务地址，例如 `http://<你的IP地址>:5173`。多个地址用逗号分隔。
4.  点击 `Restart` 重启浏览器。

## 📂 项目结构
```
huo-voice-chat/
├── frontend/         # uni-app 前端项目
│   ├── src/
│   ├── package.json
│   └── ...
├── backend/          # Django 后端项目
│   ├── requirements.txt
│   ├── manage.py
│   └── ...
└── README.md
```

---

> **⚠️ 警告**
> 
> 此版本可能存在一些小 Bug，不建议编程新手直接使用。
