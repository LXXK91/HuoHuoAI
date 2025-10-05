由于第一次使用GitHub平台，也是第一次开源项目
我也只能算个小白
下面我只说一下需要安装的环境和依赖什么的
如有遗漏请见谅，有遗漏的话欢迎补充
# 藿藿语音聊天机器人

基于 Vue3 + uni-app + Python Django 的全栈语音聊天应用

## 功能特性
- 🎤 实时语音对话
- 🤖 AI 智能回复
- 📱 多端支持 (H5/微信小程序/App)
- 🎵 语音合成与识别

## 技术栈
### 前端
- Vue 3
- uni-app
- Vite

### 后端
- Python Django
- Django REST Framework
- WebSocket

## 环境要求
- Node.js 16+
- Python 3.8+
- HBuilderX (可选，用于开发)

## 快速开始

### 前端设置
```bash
# 安装依赖
npm install

# 开发模式 (H5)
npm run dev:h5

# 构建生产版本
npm run build:h5

# 微信小程序开发
npm run dev:mp-weixin
这个版本一般都是运行在本地web端

后端设置
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# 安装Python依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，配置数据库和API密钥

# 数据库迁移
python manage.py migrate
python manage.py runserver

项目结构
huohuo-voice-chat/
├── frontend/                 # uni-app 前端项目
│   ├── pages/               # 页面文件
│   ├── static/              # 静态资源
│   ├── components/          # 组件
│   ├── package.json         # 前端依赖
│   └── manifest.json        # 应用配置
├── backend/                 # Django 后端项目
│   ├── requirements.txt     # Python 依赖
│   └── manage.py           # Django 管理脚本
└── README.md

最后，直接在源码里搜索localhost,将其全部替换成你电脑的IP
然后将you api替换成你火山引擎的api就可以了
最后在火山引擎开通这些模型doubao1.6flash,声音复刻模型并训练好，字节跳动大模型，语音场景大模型，语音合成大模型等，源码里注释有所需的模型，我这里就不一样写出来了（因为懒）
