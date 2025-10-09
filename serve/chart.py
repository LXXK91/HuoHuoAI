import os
import logging
from volcenginesdkarkruntime import Ark
from character_config import get_system_prompt, CHARACTER_INFO, SCENARIO_RESPONSES, parse_emotion_from_reply

# 配置日志
logger = logging.getLogger(__name__)

# 初始化Ark客户端
client = Ark(
    base_url="https://ark.cn-beijing.volces.com/api/v3",
    api_key="your_api",
)

def get_ai_response(user_message: str, system_prompt: str = None) -> dict:
    """
    调用豆包AI模型获取回复
    
    Args:
        user_message (str): 用户消息内容
        system_prompt (str): 系统提示词，如果不提供则使用藿藿的默认角色设定
    
    Returns:
        dict: 包含成功状态和AI回复的字典
    """
    try:
        # 使用角色配置文件中的系统提示词
        if system_prompt is None:
            system_prompt = get_system_prompt()
        
        logger.info(f"调用AI模型，用户消息: {user_message}")
        logger.info(f"使用角色: {CHARACTER_INFO['name']} ({CHARACTER_INFO['identity']})")
        
        # 调用豆包AI模型
        completion = client.chat.completions.create(
            model="doubao-1-5-pro-32k-250115",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
        )
        
        ai_reply = completion.choices[0].message.content
        logger.info(f"AI原始回复: {ai_reply}")
        
        # 解析情绪值
        clean_reply, emotion_value = parse_emotion_from_reply(ai_reply)
        logger.info(f"AI清理后回复: {clean_reply}")
        logger.info(f"情绪值: {emotion_value}")
        
        return {
            'success': True,
            'ai_reply': clean_reply,
            'emotion_value': emotion_value,
            'model': 'doubao-1-5-pro-32k-250115',
            'character': CHARACTER_INFO['name']
        }
        
    except Exception as e:
        logger.error(f"调用AI模型失败: {str(e)}")
        # 使用角色配置中的默认错误回复
        default_error_reply = SCENARIO_RESPONSES.get('apology', ['抱歉，我现在有点忙，请稍后再试~'])[0]
        return {
            'success': False,
            'error': str(e),
            'ai_reply': default_error_reply,
            'emotion_value': 2,  # 错误时设置为消极/担心情绪
            'character': CHARACTER_INFO['name']
        }

def test_ai_chat():
    """测试AI对话功能"""
    print(f"----- {CHARACTER_INFO['name']}AI对话测试 -----")
    print(f"角色信息: {CHARACTER_INFO['identity']}, {CHARACTER_INFO['species']}")
    print(f"组织: {CHARACTER_INFO['organization']}")
    print()
    
    test_messages = [
        "你好藿藿",
        "今天天气怎么样？",
        "给我讲个笑话",
        "我想听音乐",
        "我有点害怕"
    ]
    
    for msg in test_messages:
        print(f"\n用户: {msg}")
        result = get_ai_response(msg)
        if result['success']:
            print(f"{result['character']}: {result['ai_reply']}")
            print(f"情绪值: {result['emotion_value']} (桥链到静态情绪映射)")
        else:
            print(f"错误: {result['error']}")
            print(f"{result['character']}: {result['ai_reply']}")
            print(f"情绪值: {result['emotion_value']} (错误情况下的默认值)")

if __name__ == "__main__":
    test_ai_chat()