#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
WebSocket服务器测试脚本
用于测试藿藿语音助手的WebSocket连接和基本功能
"""

import asyncio
import websockets
import json
import base64
import os
import sys

async def test_websocket_connection():
    """测试WebSocket连接"""
    uri = "ws://localhost:8765"
    
    try:
        print(" 正在连接WebSocket服务器...")
        async with websockets.connect(uri) as websocket:
            print("✅ WebSocket连接成功！")
            
            # 等待欢迎消息
            welcome_msg = await websocket.recv()
            welcome_data = json.loads(welcome_msg)
            print(f" 收到欢迎消息: {welcome_data}")
            
            # 测试文本消息
            print("\n 测试文本消息...")
            text_message = {
                "type": "text",
                "message": "你好藿藿，这是一个测试消息"
            }
            
            await websocket.send(json.dumps(text_message))
            print(" 已发送文本消息")
            
            # 接收响应
            timeout_count = 0
            while timeout_count < 10:  # 最多等待10个消息
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    data = json.loads(response)
                    print(f" 收到响应: {data}")
                    
                    if data.get('type') == 'assistant_reply':
                        print("✅ 文本消息测试完成！")
                        break
                        
                except asyncio.TimeoutError:
                    timeout_count += 1
                    print(f"⏰ 等待响应超时 ({timeout_count}/10)")
                    continue
            
            # 测试心跳
            print("\n 测试心跳消息...")
            ping_message = {"type": "ping"}
            await websocket.send(json.dumps(ping_message))
            
            pong_response = await websocket.recv()
            pong_data = json.loads(pong_response)
            if pong_data.get('type') == 'pong':
                print("✅ 心跳测试成功！")
            else:
                print(f"❌ 心跳测试失败: {pong_data}")
            
    except websockets.exceptions.ConnectionRefused:
        print("❌ 连接被拒绝，请确保WebSocket服务器正在运行")
        return False
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        return False
    
    return True

async def test_audio_message():
    """测试音频消息（使用模拟数据）"""
    uri = "ws://localhost:8765"
    
    try:
        print("\n 测试音频消息...")
        async with websockets.connect(uri) as websocket:
            # 跳过欢迎消息
            await websocket.recv()
            
            # 创建一个小的测试音频数据（实际上是空数据，仅用于测试协议）
            test_audio_data = b"fake_audio_data_for_testing"
            audio_base64 = base64.b64encode(test_audio_data).decode('utf-8')
            
            audio_message = {
                "type": "audio",
                "audio": audio_base64
            }
            
            await websocket.send(json.dumps(audio_message))
            print(" 已发送音频消息")
            
            # 接收响应
            timeout_count = 0
            while timeout_count < 15:  # 音频处理可能需要更长时间
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    data = json.loads(response)
                    print(f" 收到响应: {data}")
                    
                    if data.get('type') == 'error':
                        print("⚠️ 音频处理出现预期错误（测试数据无效）")
                        break
                    elif data.get('type') == 'assistant_reply':
                        print("✅ 音频消息测试完成！")
                        break
                        
                except asyncio.TimeoutError:
                    timeout_count += 1
                    print(f"⏰ 等待响应超时 ({timeout_count}/15)")
                    continue
            
    except Exception as e:
        print(f"❌ 音频测试失败: {str(e)}")
        return False
    
    return True

def check_dependencies():
    """检查依赖文件是否存在"""
    print(" 检查依赖文件...")
    
    required_files = [
        "websocket_server.py",
        "sauc_websocket_demo.py", 
        "chart.py",
        "tts_service.py"
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
        else:
            print(f"✅ {file}")
    
    if missing_files:
        print(f"❌ 缺少文件: {missing_files}")
        return False
    
    return True

async def main():
    """主测试函数"""
    print(" 藿藿WebSocket服务器测试")
    print("=" * 50)
    
    # 检查依赖
    if not check_dependencies():
        print("\n❌ 依赖检查失败，请确保所有必要文件存在")
        return
    
    # 测试WebSocket连接和文本消息
    success = await test_websocket_connection()
    if not success:
        print("\n❌ 基础连接测试失败")
        return
    
    # 测试音频消息
    await test_audio_message()
    
    print("\n 测试完成！")
    print("\n 提示:")
    print("   - 如果看到连接错误，请先启动WebSocket服务器")
    print("   - 运行命令: python websocket_server.py")
    print("   - 或使用脚本: ./start_websocket_server.bat")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⏹️ 测试已取消")
    except Exception as e:
        print(f"\n❌ 测试过程中出现错误: {str(e)}")