from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import uuid
import logging
import asyncio
import subprocess
import sys
from datetime import datetime
from threading import Thread

# 导入语音识别模块
try:
    from sauc_websocket_demo import AsrWsClient
except ImportError:
    logger.warning("无法导入语音识别模块，请确保sauc_websocket_demo.py文件存在")
    AsrWsClient = None

# 导入AI对话模块
try:
    from chart import get_ai_response
except ImportError:
    logger.warning("无法导入AI对话模块，请确保chart.py文件存在")
    get_ai_response = None

# 导入TTS服务模块
try:
    from tts_service import generate_speech
except ImportError:
    logger.warning("无法导入TTS服务模块，请确保tts_service.py文件存在")
    generate_speech = None

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # 允许跨域请求

# 配置上传文件夹
UPLOAD_FOLDER = 'uploads/audio'
REPLY_AUDIO_FOLDER = 'reply_video'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
if not os.path.exists(REPLY_AUDIO_FOLDER):
    os.makedirs(REPLY_AUDIO_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 限制文件大小为16MB

# ASR配置
ASR_URL = "wss://openspeech.bytedance.com/api/v3/sauc/bigmodel_nostream"
ASR_SEGMENT_DURATION = 200

async def process_audio_with_asr(file_path: str) -> dict:
    """使用ASR处理音频文件"""
    try:
        if AsrWsClient is None:
            logger.warning("语音识别服务不可用")
            return {'success': False, 'error': '语音识别服务不可用'}
        
        logger.info(f"开始处理音频文件: {file_path}")
        
        # 创建ASR客户端
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

def run_asr_in_thread(file_path: str, result_container: dict):
    """在线程中运行ASR处理"""
    try:
        # 在新的事件循环中运行ASR
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(process_audio_with_asr(file_path))
        result_container.update(result)
        loop.close()
    except Exception as e:
        logger.error(f"线程ASR处理失败: {str(e)}")
        result_container.update({'success': False, 'error': str(e)})

def process_voice_to_ai_reply(file_path: str) -> dict:
    """
    完整的语音处理流程：语音识别 -> AI对话 -> TTS语音合成 -> 返回结果
    
    Args:
        file_path (str): 音频文件路径
    
    Returns:
        dict: 包含语音识别结果、AI回复和TTS语音文件的字典
    """
    result = {
        'asr_success': False,
        'ai_success': False,
        'tts_success': False,
        'recognized_text': '',
        'ai_reply': '',
        'tts_file': None,
        'error': None
    }
    
    # 步骤1：进行语音识别
    if AsrWsClient is not None:
        try:
            logger.info(f"开始语音识别: {file_path}")
            
            asr_container = {}
            asr_thread = Thread(target=run_asr_in_thread, args=(file_path, asr_container))
            asr_thread.daemon = True
            asr_thread.start()
            asr_thread.join(timeout=30)  # 最多等待30秒
            
            if asr_container and asr_container.get('success'):
                result['asr_success'] = True
                result['recognized_text'] = asr_container.get('recognized_text', '')
                logger.info(f"语音识别成功: {result['recognized_text']}")
            else:
                result['error'] = asr_container.get('error', '语音识别超时或失败')
                logger.warning(f"语音识别失败: {result['error']}")
                
        except Exception as e:
            result['error'] = f'语音识别异常: {str(e)}'
            logger.error(result['error'])
    else:
        result['error'] = '语音识别服务不可用'
    
    # 步骤2：如果语音识别成功，调用AI模型
    if result['asr_success'] and result['recognized_text'].strip():
        if get_ai_response is not None:
            try:
                logger.info(f"调用AI模型，输入: {result['recognized_text']}")
                
                ai_result = get_ai_response(result['recognized_text'])
                
                if ai_result['success']:
                    result['ai_success'] = True
                    result['ai_reply'] = ai_result['ai_reply']
                    logger.info(f"AI回复成功: {result['ai_reply']}")
                else:
                    result['ai_reply'] = ai_result.get('ai_reply', '抱歉，我现在有点问题，请稍后再试~')
                    logger.warning(f"AI回复失败: {ai_result.get('error', '未知错误')}")
                    
            except Exception as e:
                result['ai_reply'] = '抱歉，我现在有点忙，请稍后再试~'
                logger.error(f"AI对话异常: {str(e)}")
        else:
            result['ai_reply'] = '抱歉，AI对话服务不可用。'
            logger.warning("AI对话服务不可用")
    else:
        # 语音识别失败或识别结果为空时，不提供AI回复
        logger.info("语音识别失败或结果为空，跳过AI回复和TTS处理")
        result['ai_reply'] = ''  # 设置为空字符串，表示不需要AI回复
        return result  # 直接返回，不进行TTS处理
    
    # 步骤3：将AI回复转换为语音（TTS）
    if result['ai_reply'] and generate_speech is not None:
        try:
            logger.info(f"开始TTS转换: {result['ai_reply']}")
            
            # 在线程中执行TTS处理
            tts_container = {}
            tts_thread = Thread(target=run_tts_in_thread, args=(result['ai_reply'], tts_container))
            tts_thread.daemon = True
            tts_thread.start()
            tts_thread.join(timeout=20)  # 最多等待20秒
            
            if tts_container and tts_container.get('success'):
                result['tts_success'] = True
                result['tts_file'] = tts_container
                logger.info(f"TTS转换成功: {tts_container.get('filename')}")
            else:
                logger.warning(f"TTS转换失败: {tts_container.get('error', 'TTS超时')}")
                
        except Exception as e:
            logger.error(f"TTS处理异常: {str(e)}")
    else:
        if generate_speech is None:
            logger.warning("TTS服务不可用")
    
    return result

def run_tts_in_thread(text: str, result_container: dict):
    """在线程中运行TTS处理"""
    try:
        # 在新的事件循环中运行TTS
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(generate_speech(text))
        result_container.update(result)
        loop.close()
    except Exception as e:
        logger.error(f"线程TTS处理失败: {str(e)}")
        result_container.update({'success': False, 'error': str(e)})

@app.route('/api/upload_audio', methods=['POST'])
def upload_audio():
    """接收并保存音频文件，然后进行语音识别和AI对话"""
    try:
        if 'audio' not in request.files:
            return jsonify({'error': '没有音频文件'}), 400
        
        audio_file = request.files['audio']
        
        if audio_file.filename == '':
            return jsonify({'error': '没有选择文件'}), 400
        
        # 生成唯一文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_id = str(uuid.uuid4())[:8]
        filename = f"voice_{timestamp}_{unique_id}.mp3"
        
        # 保存文件
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        audio_file.save(file_path)
        
        # 记录文件信息
        file_size = os.path.getsize(file_path)
        logger.info(f"音频文件已保存: {filename}, 大小: {file_size} bytes")
        
        # 进行完整的语音处理流程（语音识别 + AI对话）
        voice_result = process_voice_to_ai_reply(file_path)
        
        # 构建返回结果
        response_data = {
            'success': True,
            'message': '音频上传成功',
            'filename': filename,
            'file_path': file_path,
            'file_size': file_size,
            'asr_result': {
                'success': voice_result['asr_success'],
                'recognized_text': voice_result['recognized_text'],
                'error': voice_result['error'] if not voice_result['asr_success'] else None
            },
            'ai_result': {
                'success': voice_result['ai_success'],
                'ai_reply': voice_result['ai_reply']
            },
            'tts_result': {
                'success': voice_result['tts_success'],
                'tts_file': voice_result['tts_file'] if voice_result['tts_success'] else None
            }
        }
        
        logger.info(f"处理结果 - 识别: {voice_result['recognized_text']}, AI回复: {voice_result['ai_reply']}")
        
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"上传音频文件时发生错误: {str(e)}")
        return jsonify({'error': f'上传失败: {str(e)}'}), 500

@app.route('/api/audio_files', methods=['GET'])
def list_audio_files():
    """获取已上传的音频文件列表"""
    try:
        files = []
        upload_dir = app.config['UPLOAD_FOLDER']
        
        if os.path.exists(upload_dir):
            for filename in os.listdir(upload_dir):
                if filename.endswith('.mp3'):
                    file_path = os.path.join(upload_dir, filename)
                    file_stat = os.stat(file_path)
                    files.append({
                        'filename': filename,
                        'size': file_stat.st_size,
                        'created_time': datetime.fromtimestamp(file_stat.st_ctime).strftime('%Y-%m-%d %H:%M:%S')
                    })
        
        return jsonify({
            'success': True,
            'files': files,
            'total': len(files)
        }), 200
        
    except Exception as e:
        logger.error(f"获取文件列表时发生错误: {str(e)}")
        return jsonify({'error': f'获取文件列表失败: {str(e)}'}), 500

@app.route('/api/recognize_audio', methods=['POST'])
def recognize_audio():
    """手动进行语音识别和AI对话"""
    try:
        data = request.get_json()
        if not data or 'filename' not in data:
            return jsonify({'error': '缺少文件名参数'}), 400
        
        filename = data['filename']
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        if not os.path.exists(file_path):
            return jsonify({'error': f'文件不存在: {filename}'}), 404
        
        logger.info(f"手动进行语音处理: {file_path}")
        
        # 进行完整的语音处理流程
        voice_result = process_voice_to_ai_reply(file_path)
        
        # 构建返回结果
        response_data = {
            'success': True,
            'filename': filename,
            'asr_result': {
                'success': voice_result['asr_success'],
                'recognized_text': voice_result['recognized_text'],
                'error': voice_result['error'] if not voice_result['asr_success'] else None
            },
            'ai_result': {
                'success': voice_result['ai_success'],
                'ai_reply': voice_result['ai_reply']
            },
            'tts_result': {
                'success': voice_result['tts_success'],
                'tts_file': voice_result['tts_file'] if voice_result['tts_success'] else None
            }
        }
        
        logger.info(f"手动处理结果 - 识别: {voice_result['recognized_text']}, AI回复: {voice_result['ai_reply']}")
        
        return jsonify(response_data), 200
            
    except Exception as e:
        logger.error(f"语音处理失败: {str(e)}")
        return jsonify({'error': f'语音处理失败: {str(e)}'}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return jsonify({
        'status': 'healthy',
        'message': '藿藿语音服务运行正常',
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }), 200

@app.route('/api/audio/<path:filename>', methods=['GET'])
def serve_audio_file(filename):
    """提供音频文件访问服务"""
    try:
        # 检查文件是否在reply_video目录中
        if os.path.exists(os.path.join(REPLY_AUDIO_FOLDER, filename)):
            return send_from_directory(REPLY_AUDIO_FOLDER, filename, as_attachment=False)
        # 检查文件是否在uploads/audio目录中
        elif os.path.exists(os.path.join(UPLOAD_FOLDER, filename)):
            return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=False)
        else:
            return jsonify({'error': '文件不存在'}), 404
    except Exception as e:
        logger.error(f"提供音频文件时发生错误: {str(e)}")
        return jsonify({'error': f'文件访问失败: {str(e)}'}), 500

if __name__ == '__main__':
    print(" 藿藿语音服务启动中...")
    print(f" 音频文件保存目录: {UPLOAD_FOLDER}")
    print(" 服务地址: http://19localhost000")
    print(" API接口:")
    print("   POST /api/upload_audio    - 上传音频文件（ASR+AI+TTS完整流程）")
    print("   POST /api/recognize_audio - 手动进行语音处理（ASR+AI+TTS）")
    print("   GET  /api/audio_files     - 获取音频文件列表")
    print("   GET  /api/audio/<filename> - 访问音频文件")
    print("   GET  /api/health          - 健康检查")
    
    # 检查服务状态
    print("\n 服务状态检查:")
    if AsrWsClient is None:
        print("   ⚠️  语音识别: 服务不可用")
    else:
        print("   ✅ 语音识别: 服务已加载")
        
    if get_ai_response is None:
        print("   ⚠️  AI对话: 服务不可用")
    else:
        print("   ✅ AI对话: 服务已加载")
        
    if generate_speech is None:
        print("   ⚠️  TTS语音合成: 服务不可用")
    else:
        print("   ✅ TTS语音合成: 服务已加载")
    
    print("\n 服务启动中...")
    app.run(debug=True, host='0.0.0.0', port=5000)