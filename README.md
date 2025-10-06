由于第一次使用GitHub平台，也是第一次开源项目
我也只能算个小白
下面我只说一下需要安装的环境和依赖什么的
如有遗漏请见谅，有遗漏的话欢迎补充

所需依赖：requirements.txt文件和package.json文件里

#藿藿语音聊天机器人

基于vue3+uni-app+Python Django的全栈语音聊天应用

##功能特性
-🎤  实时语音对话
-🤖 人工智能智能回复
-📱 多端支持(H5/微信小程序/App)
-🎵  语音合成与识别

##技术栈
###前端
-Vue3
-uni-app
-Vite

###后端
-Python Django
-Django REST框架
-WebSocket

##环境要求
-Node.js16+
-Python3.8+
-HBuilderX(可选，用于开发)

##快速开始

###前端设置
```猛击
# 安装依赖
npm安装

#开发模式(H5)
npm运行dev:h5

# 构建生产版本
npm运行内部版本：H5

# 微信小程序开发
npm运行设备：mp-weixin


后端设置
# 创建虚拟环境
Python-m venv venv
源venv/bin/activate#Linux/Mac
venv\脚本\activate#Windows

#安装python依赖
PIP安装-r要求.文本

# 配置环境变量
CP.env.example.env
#编辑.env文件，配置数据库和API密钥

# 数据库迁移
Python manage.py migrate
Python manage.py runserver

项目结构
huo-voice-chat/
├--前端/#uni-app前端项目
│├--页数/#页面文件
│├--静态/#静态资源
│├--组件/#组件
│├--包.json#前端依赖
│└--manifest.json#应用配置
├--后端/#Django后端项目
│   ├── requirements.txt     # Python 依赖
│   └── manage.py           # Django 管理脚本
└── README.md

最后，直接在源码里搜索localhost,将其全部替换成你电脑的IP
将源码里you api替换成你火山引擎的api就可以了
最后在火山引擎开通字节跳动大模型，声音复刻模型等，源码里注释有所需的模型，我这里就不一样写出来了（因为懒）

开启电脑手机游览器的录音权限:
修改 Chrome 标志（Flags）
在 Chrome 浏览器地址栏输入 chrome://flags/ 并回车，进入 Chrome 实验性功能页面。
在搜索框中输入 “insecure origins treated as secure” 。
在搜索结果中找到 Insecure origins treated as secure 选项，点击下拉菜单，选择 Enabled 。
在下方出现的 Secure origins list 输入框中，输入你要允许使用录音权限的 HTTP 网站地址，格式为 http://你需要将其替换为你实际的网站地址:5173，多个地址用逗号分隔。
点击页面底部的 Relaunch Now 按钮，重启 Chrome 浏览器，设置生效。
Edge 浏览器
Edge 浏览器基于 Chromium 内核，和 Chrome 有一些相似之处，设置方式如下：

在地址栏输入 edge://flags/ 并回车，进入 Edge 的实验性功能页面。
在搜索框中输入 “insecure origins treated as secure” 。
找到 Insecure origins treated as secure 选项，点击下拉菜单，选择 Enabled 。
在下方出现的 Secure origins list 输入框中，输入你要允许使用录音权限的 HTTP 网站地址，格式为 http://你的网站地址 ，多个地址用逗号分隔。
点击页面底部的 Restart 按钮，重启 Edge 浏览器，设置即可生效。

此版本可能会出现一些小bug，小白不建议使用
