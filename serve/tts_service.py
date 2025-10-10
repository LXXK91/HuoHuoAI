#coding=utf-8

'''
TTS (Text-to-Speech) 服务模块
用于将文字转换为语音

requires Python 3.6 or later
pip install asyncio
pip install websockets
'''

import asyncio
import websockets
import uuid
import json
import gzip
import copy
import os
import logging
from datetime import datetime

# 配置日志
logger = logging.getLogger(__name__)

MESSAGE_TYPES = {11: "audio-only server response", 12: "frontend server response", 15: "error message from server"}
MESSAGE_TYPE_SPECIFIC_FLAGS = {0: "no sequence number", 1: "sequence number > 0",
                               2: "last message from server (seq < 0)", 3: "sequence number < 0"}
MESSAGE_SERIALIZATION_METHODS = {0: "no serialization", 1: "JSON", 15: "custom type"}
MESSAGE_COMPRESSIONS = {0: "no compression", 1: "gzip", 15: "custom compression method"}

# TTS服务配置
TTS_CONFIG = {
    "appid": "9270317800",
    "token": "x7msp2jKLy0bGXy6pEksMDy97CB_vWvT",
    "cluster": "volcano_icl",
    "voice_type": "S_jhlSRP7D1",  # 可以配置不同的声音类型
    "host": "openspeech.bytedance.com",
}

# 创建reply_video目录
REPLY_AUDIO_DIR = 'reply_video'
if not os.path.exists(REPLY_AUDIO_DIR):
    os.makedirs(REPLY_AUDIO_DIR)

# 默认请求头
default_header = bytearray(b'\x11\x10\x11\x00')

def create_tts_request(text: str, voice_type: str = None, speed_ratio: float = 1.0) -> dict:
    """
    创建TTS请求对象
    
    Args:
        text (str): 要转换为语音的文字
        voice_type (str): 声音类型，默认使用配置中的声音
        speed_ratio (float): 语速比例，默认1.0
    
    Returns:
        dict: TTS请求配置
    """
    if voice_type is None:
        voice_type = TTS_CONFIG["voice_type"]
    
    return {
        "app": {
            "appid": TTS_CONFIG["appid"],
            "token": "access_token",
            "cluster": TTS_CONFIG["cluster"]
        },
        "user": {
            "uid": "huohuo_tts_user"
        },
        "audio": {
            "voice_type": voice_type,
            "encoding": "mp3",
            "speed_ratio": speed_ratio,
            "volume_ratio": 1.0,
            "pitch_ratio": 1.0,
        },
        "request": {
            "reqid": str(uuid.uuid4()),
            "text": text,
            "text_type": "plain",
            "operation": "submit"
        }
    }

def parse_tts_response(res, file):
    """解析TTS响应并写入文件"""
    try:
        protocol_version = res[0] >> 4
        header_size = res[0] & 0x0f
        message_type = res[1] >> 4
        message_type_specific_flags = res[1] & 0x0f
        serialization_method = res[2] >> 4
        message_compression = res[2] & 0x0f
        reserved = res[3]
        header_extensions = res[4:header_size*4]
        payload = res[header_size*4:]
        
        if message_type == 0xb:  # audio-only server response
            if message_type_specific_flags == 0:  # no sequence number as ACK
                return False
            else:
                sequence_number = int.from_bytes(payload[:4], "big", signed=True)
                payload_size = int.from_bytes(payload[4:8], "big", signed=False)
                payload = payload[8:]
                
            file.write(payload)
            if sequence_number < 0:
                return True
            else:
                return False
        elif message_type == 0xf:  # error response
            code = int.from_bytes(payload[:4], "big", signed=False)
            msg_size = int.from_bytes(payload[4:8], "big", signed=False)
            error_msg = payload[8:]
            if message_compression == 1:
                error_msg = gzip.decompress(error_msg)
            error_msg = str(error_msg, "utf-8")
            logger.error(f"TTS错误 - 代码: {code}, 消息: {error_msg}")
            return True
        elif message_type == 0xc:  # frontend server response
            msg_size = int.from_bytes(payload[:4], "big", signed=False)
            payload = payload[4:]
            if message_compression == 1:
                payload = gzip.decompress(payload)
            logger.info(f"TTS前端消息: {payload}")
        else:
            logger.warning("未定义的消息类型!")
            return True
    except Exception as e:
        logger.error(f"解析TTS响应失败: {str(e)}")
        return True

async def generate_speech(text: str, voice_type: str = None, speed_ratio: float = 1.0) -> dict:
    """
    将文字转换为语音文件
    
    Args:
        text (str): 要转换的文字
        voice_type (str): 声音类型
        speed_ratio (float): 语速比例
    
    Returns:
        dict: 包含成功状态和文件信息的字典
    """
    try:
        logger.info(f"开始TTS转换: {text}")
        
        # 生成唯一文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_id = str(uuid.uuid4())[:8]
        filename = f"reply_{timestamp}_{unique_id}.mp3"
        file_path = os.path.join(REPLY_AUDIO_DIR, filename)
        
        # 创建TTS请求
        request_config = create_tts_request(text, voice_type, speed_ratio)
        
        # 准备请求数据
        payload_bytes = str.encode(json.dumps(request_config))
        payload_bytes = gzip.compress(payload_bytes)
        full_client_request = bytearray(default_header)
        full_client_request.extend((len(payload_bytes)).to_bytes(4, 'big'))
        full_client_request.extend(payload_bytes)
        
        # 连接TTS服务
        api_url = f"wss://{TTS_CONFIG['host']}/api/v1/tts/ws_binary"
        header = {"Authorization": f"Bearer; {TTS_CONFIG['token']}"}
        
        file_to_save = open(file_path, "wb")
        
        async with websockets.connect(api_url, extra_headers=header, ping_interval=None) as ws:
            await ws.send(full_client_request)
            while True:
                res = await ws.recv()
                done = parse_tts_response(res, file_to_save)
                if done:
                    file_to_save.close()
                    break
        
        # 检查文件是否成功生成
        if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
            file_size = os.path.getsize(file_path)
            logger.info(f"TTS转换成功: {filename}, 大小: {file_size} bytes")
            
            return {
                'success': True,
                'filename': filename,
                'file_path': file_path,
                'file_size': file_size,
                'text': text
            }
        else:
            logger.error("TTS文件生成失败或文件为空")
            return {
                'success': False,
                'error': 'TTS文件生成失败或文件为空'
            }
            
    except Exception as e:
        logger.error(f"TTS转换失败: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }

def test_tts():
    """测试TTS功能"""
    async def run_test():
        test_text = "你好，我是藿藿！这是一个测试语音。"
        result = await generate_speech(test_text)
        print(f"TTS测试结果: {json.dumps(result, indent=2, ensure_ascii=False)}")
    
    asyncio.run(run_test())

if __name__ == '__main__':
    test_tts()