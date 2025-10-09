#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
语音识别功能测试脚本
用于测试上传的音频文件是否能够正确执行语音识别
"""

import requests
import json
import os
from pathlib import Path

def test_upload_and_recognize():
    """测试音频上传和完整处理功能"""
    
    # 服务器地址
    server_url = "http://localhost:5000"
    
    # 检查音频文件目录
    audio_dir = Path("uploads/audio")
    if not audio_dir.exists():
        print("❌ 音频文件目录不存在，请先上传一些音频文件")
        return
    
    # 获取音频文件列表
    try:
        response = requests.get(f"{server_url}/api/audio_files")
        if response.status_code == 200:
            files_data = response.json()
            if files_data['total'] == 0:
                print("❌ 没有找到音频文件，请先上传一些音频文件")
                return
            
            print(f" 找到 {files_data['total']} 个音频文件:")
            for i, file_info in enumerate(files_data['files']):
                print(f"   {i+1}. {file_info['filename']} ({file_info['size']} bytes)")
            
            # 测试第一个文件
            test_filename = files_data['files'][0]['filename']
            print(f"\n 测试完整语音处理流程: {test_filename}")
            
            # 调用完整处理API
            recognize_response = requests.post(
                f"{server_url}/api/recognize_audio",
                json={'filename': test_filename}
            )
            
            if recognize_response.status_code == 200:
                result = recognize_response.json()
                print("✅ 语音处理成功!")
                print(f" 完整结果: {json.dumps(result, indent=2, ensure_ascii=False)}")
                
                # 解析结果
                if result.get('asr_result', {}).get('success'):
                    recognized_text = result['asr_result']['recognized_text']
                    print(f"\n️ 语音识别结果: \"{recognized_text}\"")
                else:
                    print(f"\n⚠️ 语音识别失败: {result.get('asr_result', {}).get('error', '未知错误')}")
                
                if result.get('ai_result', {}).get('ai_reply'):
                    ai_reply = result['ai_result']['ai_reply']
                    print(f" 藿藿AI回复: \"{ai_reply}\"")
                else:
                    print("⚠️ AI回复不可用")
                    
            else:
                print(f"❌ 语音处理失败: {recognize_response.text}")
                
        else:
            print(f"❌ 获取文件列表失败: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到服务器，请确保服务器正在运行 (python voice_server.py)")
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {str(e)}")

def test_health_check():
    """测试服务器健康状态"""
    try:
        response = requests.get("http://localhost:5000/api/health")
        if response.status_code == 200:
            print("✅ 服务器运行正常")
            print(f" 服务器状态: {response.json()}")
            return True
        else:
            print(f"❌ 服务器状态异常: {response.text}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到服务器")
        return False

if __name__ == "__main__":
    print(" 藿藿语音识别功能测试")
    print("=" * 50)
    
    # 检查服务器状态
    if test_health_check():
        print("\n" + "=" * 50)
        # 测试语音识别
        test_upload_and_recognize()
    
    print("\n" + "=" * 50)
    print(" 测试完成")