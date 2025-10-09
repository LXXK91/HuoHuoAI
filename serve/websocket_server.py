import asyncio
import websockets
import json
import base64
import os
import uuid
import logging
import threading
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from http.server import HTTPServer, SimpleHTTPRequestHandler
import socketserver
from urllib.parse import urlparse

# 导入现有模块
try:
    from sauc_websocket_demo import AsrWsClient
except ImportError:
    print("无法导入语音识别模块，请确保sauc_websocket_demo.py文件存在")
    AsrWsClient = None

try:
    from chart import get_ai_response
except ImportError:
    print("无法导入AI对话模块，请确保chart.py文件存在")
    get_ai_response = None

try:
    from tts_service import generate_speech
except ImportError:
    print("无法导入TTS服务模块，请确保tts_service.py文件存在")
    generate_speech = None

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('websocket_server.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 配置
UPLOAD_FOLDER = 'uploads/audio'
REPLY_AUDIO_FOLDER = 'reply_video'
EMOTION_IMG_FOLDER = 'emotion_img'  # 情绪图片文件夹
ASR_URL = "wss://openspeech.bytedance.com/api/v3/sauc/bigmodel_nostream"
ASR_SEGMENT_DURATION = 200

# 确保目录存在
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(REPLY_AUDIO_FOLDER, exist_ok=True)
os.makedirs(EMOTION_IMG_FOLDER, exist_ok=True)

# 连接管理
connected_clients = set()
executor = ThreadPoolExecutor(max_workers=4)

class AudioFileHandler(SimpleHTTPRequestHandler):
    """处理音频文件访问的HTTP处理器"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=os.getcwd(), **kwargs)
    
    def do_GET(self):
        parsed_path = urlparse(self.path)
        
        if parsed_path.path.startswith('/api/audio/'):
            # 提取文件名
            filename = parsed_path.path.split('/')[-1]
            file_path = os.path.join(REPLY_AUDIO_FOLDER, filename)
            
            if os.path.exists(file_path):
                # 设置CORS头
                self.send_response(200)
                self.send_header('Content-Type', 'audio/mpeg')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type')
                self.end_headers()
                
                # 发送文件内容
                with open(file_path, 'rb') as f:
                    self.wfile.write(f.read())
            else:
                self.send_error(404, "Audio file not found")
                
        elif parsed_path.path.startswith('/api/emotion/'):
            # 提取情绪图片文件名
            filename = parsed_path.path.split('/')[-1]
            file_path = os.path.join(EMOTION_IMG_FOLDER, filename)
            
            if os.path.exists(file_path):
                # 设置CORS头
                self.send_response(200)
                self.send_header('Content-Type', 'image/jpeg')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type')
                self.end_headers()
                
                # 发送文件内容
                with open(file_path, 'rb') as f:
                    self.wfile.write(f.read())
            else:
                self.send_error(404, "Emotion image not found")
        else:
            self.send_error(404, "Not found")

def start_http_server():
    """启动HTTP服务器提供音频文件访问"""
    try:
        httpd = HTTPServer(('localhost', 5000), AudioFileHandler)
        logger.info("HTTP服务器已启动，监听 localhost:5000")
        httpd.serve_forever()
    except Exception as e:
        logger.error(f"HTTP服务器启动失败: {str(e)}")

async def run_asr_async(file_path: str) -> dict:
    """异步运行ASR处理"""
    try:
        if AsrWsClient is None:
            return {'success': False, 'error': '语音识别服务不可用'}
        
        logger.info(f"开始ASR处理: {file_path}")
        
        async with AsrWsClient(ASR_URL, ASR_SEGMENT_DURATION) as client:
            responses = []
            async for response in client.execute(file_path):
                responses.append(response.to_dict())
                logger.info(f"ASR响应: {response.to_dict()}")
            
            # 提取识别结果
            recognized_text = ""
            for resp in responses:
                if resp.get('payload_msg') and resp['payload_msg'].get('result'):
                    result = resp['payload_msg']['result']
                    if result.get('text'):
                        recognized_text += result['text']
            
            return {
                'success': True,
                'recognized_text': recognized_text.strip(),
                'raw_responses': responses
            }
            
    except Exception as e:
        logger.error(f"ASR处理失败: {str(e)}")
        return {'success': False, 'error': str(e)}

async def run_ai_response_async(text: str) -> dict:
    """异步运行AI对话"""
    try:
        if get_ai_response is None:
            return {'success': False, 'error': 'AI对话服务不可用'}
        
        logger.info(f"开始AI对话: {text}")
        
        # 在线程池中运行同步函数
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(executor, get_ai_response, text)
        
        logger.info(f"AI对话结果类型: {type(result)}, 内容: {result}")
        
        # 确保返回的是字典
        if isinstance(result, dict):
            return result
        else:
            logger.error(f"AI对话返回类型错误: {type(result)}")
            return {'success': False, 'error': f'AI对话返回类型错误: {type(result)}'}
        
    except Exception as e:
        logger.error(f"AI对话失败: {str(e)}", exc_info=True)
        return {'success': False, 'error': str(e)}

async def run_tts_async(text: str) -> dict:
    """异步运行TTS处理"""
    try:
        if generate_speech is None:
            return {'success': False, 'error': 'TTS服务不可用'}
        
        logger.info(f"开始TTS处理: {text}")
        
        # 直接调用异步TTS函数
        result = await generate_speech(text)
        
        logger.info(f"TTS结果类型: {type(result)}, 内容: {result}")
        
        # 确保返回的是字典
        if isinstance(result, dict):
            return result
        else:
            logger.error(f"TTS返回类型错误: {type(result)}")
            return {'success': False, 'error': f'TTS返回类型错误: {type(result)}'}
        
    except Exception as e:
        logger.error(f"TTS处理失败: {str(e)}", exc_info=True)
        return {'success': False, 'error': str(e)}

def get_emotion_image_url(emotion_value: int) -> str:
    """
    根据情绪值获取对应的图片URL
    
    Args:
        emotion_value (int): 情绪值 (1-6)
    
    Returns:
        str: 图片URL
    """
    # 确保情绪值在有效范围内
    if emotion_value < 1 or emotion_value > 6:
        emotion_value = 3  # 默认为中性情绪
    
    filename = f"{emotion_value}.jpg"
    return f"/api/emotion/{filename}"

def run_tts_in_thread(text: str, result_container: dict):
    """在线程中运行TTS处理"""
    try:
        if generate_speech is None:
            result_container.update({'success': False, 'error': 'TTS服务不可用'})
            return
            
        result = generate_speech(text)
        result_container.update(result)
    except Exception as e:
        logger.error(f"线程TTS处理失败: {str(e)}")
        result_container.update({'success': False, 'error': str(e)})

async def save_audio_file(audio_data: bytes, file_extension: str = 'webm') -> str:
    """保存音频文件并返回文件路径"""
    try:
        # 生成唯一文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        filename = f"voice_{timestamp}_{unique_id}.{file_extension}"
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        
        # 保存文件
        with open(file_path, 'wb') as f:
            f.write(audio_data)
        
        logger.info(f"音频文件保存成功: {file_path}")
        return file_path
        
    except Exception as e:
        logger.error(f"保存音频文件失败: {str(e)}")
        raise

async def process_voice_message(websocket, audio_data: bytes) -> dict:
    """处理语音消息的完整流程"""
    try:
        # 发送状态更新
        await websocket.send(json.dumps({
            'type': 'status',
            'message': '正在保存音频文件...'
        }))
        
        # 1. 保存音频文件
        file_path = await save_audio_file(audio_data)
        
        # 发送状态更新
        await websocket.send(json.dumps({
            'type': 'status',
            'message': '正在进行语音识别...'
        }))
        
        # 2. 进行语音识别
        asr_result = await run_asr_async(file_path)
        
        if not asr_result['success']:
            return {
                'type': 'error',
                'message': f"语音识别失败: {asr_result['error']}"
            }
        
        recognized_text = asr_result['recognized_text']
        
        # 发送语音识别结果
        await websocket.send(json.dumps({
            'type': 'asr_result',
            'message': f'识别结果: "{recognized_text}"'
        }))
        
        if not recognized_text.strip():
            return {
                'type': 'assistant_reply',
                'message': '抱歉，我没有听清楚您说的话，请重新录音。',
                'audio_url': None
            }
        
        # 发送状态更新
        await websocket.send(json.dumps({
            'type': 'status',
            'message': 'AI正在思考回复...'
        }))
        
        # 3. 调用AI模型
        ai_result = await run_ai_response_async(recognized_text)
        
        # 安全地检查ai_result并提取情绪值
        if isinstance(ai_result, dict) and ai_result.get('success'):
            ai_reply = ai_result.get('ai_reply', '抱歉，我现在没有回复。')
            emotion_value = ai_result.get('emotion_value', 3)  # 默认为中性情绪
        else:
            ai_reply = '抱歉，我现在有点问题，请稍后再试。'
            emotion_value = 2  # 错误情况下设置为消极情绪
        
        # 发送状态更新
        await websocket.send(json.dumps({
            'type': 'status',
            'message': '正在生成语音回复...'
        }))
        
        # 4. 生成TTS语音
        audio_url = None
        try:
            tts_result = await run_tts_async(ai_reply)
            if isinstance(tts_result, dict) and tts_result.get('success'):
                audio_filename = tts_result.get('filename')
                if audio_filename:
                    audio_url = f"/api/audio/{audio_filename}"
        except Exception as tts_error:
            logger.error(f"TTS处理失败: {str(tts_error)}")
        
        # 返回最终结果
        return {
            'type': 'assistant_reply',
            'message': ai_reply,
            'emotion_value': emotion_value,
            'emotion_img': get_emotion_image_url(emotion_value),
            'audio_url': audio_url,
            'user_message': recognized_text
        }
        
    except Exception as e:
        logger.error(f"处理语音消息失败: {str(e)}")
        return {
            'type': 'error',
            'message': f'处理失败: {str(e)}'
        }

async def handle_client(websocket, path):
    """处理WebSocket客户端连接"""
    client_id = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
    logger.info(f"客户端连接: {client_id}")
    
    connected_clients.add(websocket)
    
    try:
        # 发送欢迎消息
        welcome_message = {
            'type': 'welcome',
            'message': '你好，我叫藿藿，是新上任的十王司判官，请多多指教！'
        }
        await websocket.send(json.dumps(welcome_message))
        
        async for message in websocket:
            try:
                data = json.loads(message)
                message_type = data.get('type')
                
                if message_type == 'audio':
                    # 处理音频消息
                    audio_base64 = data.get('audio')
                    if audio_base64:
                        # 解码base64音频数据
                        audio_data = base64.b64decode(audio_base64)
                        
                        logger.info(f"收到音频数据，大小: {len(audio_data)} bytes")
                        
                        # 处理语音消息
                        result = await process_voice_message(websocket, audio_data)
                        
                        # 发送处理结果
                        await websocket.send(json.dumps(result))
                    else:
                        await websocket.send(json.dumps({
                            'type': 'error',
                            'message': '无效的音频数据'
                        }))
                
                elif message_type == 'text':
                    # 处理文本消息
                    text_content = data.get('message')
                    if text_content:
                        logger.info(f"收到文本消息: {text_content}")
                        
                        # 发送状态更新
                        await websocket.send(json.dumps({
                            'type': 'status',
                            'message': 'AI正在思考回复...'
                        }))
                        
                        # 调用AI模型
                        ai_result = await run_ai_response_async(text_content)
                        
                        # 安全地检查ai_result并提取情绪值
                        if isinstance(ai_result, dict) and ai_result.get('success'):
                            ai_reply = ai_result.get('ai_reply', '抱歉，我现在没有回复。')
                            emotion_value = ai_result.get('emotion_value', 3)  # 默认为中性情绪
                        else:
                            ai_reply = '抱歉，我现在有点问题，请稍后再试。'
                            emotion_value = 2  # 错误情况下设置为消极情绪
                        
                        # 生成TTS语音
                        audio_url = None
                        try:
                            tts_result = await run_tts_async(ai_reply)
                            if isinstance(tts_result, dict) and tts_result.get('success'):
                                audio_filename = tts_result.get('filename')
                                if audio_filename:
                                    audio_url = f"/api/audio/{audio_filename}"
                        except Exception as tts_error:
                            logger.error(f"TTS处理失败: {str(tts_error)}")
                        
                        # 发送回复
                        await websocket.send(json.dumps({
                            'type': 'assistant_reply',
                            'message': ai_reply,
                            'emotion_value': emotion_value,
                            'emotion_img': get_emotion_image_url(emotion_value),
                            'audio_url': audio_url,
                            'user_message': text_content
                        }))
                    else:
                        await websocket.send(json.dumps({
                            'type': 'error',
                            'message': '无效的文本消息'
                        }))
                
                elif message_type == 'ping':
                    # 心跳检测
                    await websocket.send(json.dumps({
                        'type': 'pong',
                        'timestamp': time.time()
                    }))
                
                else:
                    await websocket.send(json.dumps({
                        'type': 'error',
                        'message': f'未知的消息类型: {message_type}'
                    }))
                    
            except json.JSONDecodeError:
                await websocket.send(json.dumps({
                    'type': 'error',
                    'message': '无效的JSON格式'
                }))
            except Exception as e:
                logger.error(f"处理消息失败: {str(e)}")
                await websocket.send(json.dumps({
                    'type': 'error',
                    'message': f'服务器内部错误: {str(e)}'
                }))
                
    except websockets.exceptions.ConnectionClosed:
        logger.info(f"客户端断开连接: {client_id}")
    except Exception as e:
        logger.error(f"WebSocket处理错误: {str(e)}")
    finally:
        connected_clients.discard(websocket)
        logger.info(f"清理客户端连接: {client_id}")

async def start_server():
    """启动WebSocket服务器"""
    host = "localhost"
    port = 8765
    
    logger.info(f"启动WebSocket服务器在 ws://{host}:{port}")
    
    server = await websockets.serve(
        handle_client,
        host,
        port,
        ping_interval=30,  # 30秒ping间隔
        ping_timeout=10,   # 10秒ping超时
        max_size=16 * 1024 * 1024,  # 16MB最大消息大小
        compression=None   # 禁用压缩以提高性能
    )
    
    logger.info(f"WebSocket服务器已启动，监听 {host}:{port}")
    logger.info("等待客户端连接...")
    
    return server

if __name__ == "__main__":
    try:
        # 在后台线程中启动HTTP服务器
        http_thread = threading.Thread(target=start_http_server, daemon=True)
        http_thread.start()
        logger.info("HTTP服务器线程已启动")
        
        # 启动WebSocket服务器
        loop = asyncio.get_event_loop()
        server = loop.run_until_complete(start_server())
        
        logger.info("服务器正在运行，按Ctrl+C停止")
        logger.info("WebSocket地址: ws://localhost:8765")
        logger.info("音频文件HTTP服务: http://localhost:5000")
        logger.info("情绪图片HTTP服务: http://localhost:5000/api/emotion/")
        
        # 保持服务器运行
        loop.run_forever()
        
    except KeyboardInterrupt:
        logger.info("收到中断信号，正在关闭服务器...")
    except Exception as e:
        logger.error(f"服务器启动失败: {str(e)}")
    finally:
        # 清理资源
        executor.shutdown(wait=True)
        logger.info("服务器已关闭")