"""
测试情绪值功能
"""
from character_config import parse_emotion_from_reply, EMOTION_SCALE

def test_emotion_parsing():
    """测试情绪值解析功能"""
    print("----- 情绪值解析测试 -----")
    
    test_cases = [
        "你好呀~ 我是藿藿！😊 [情绪:4]",
        "抱歉，我有点害怕... [情绪:2]", 
        "太好了！我们一起加油吧！💪 [情绪:5]",
        "这是一个没有情绪标记的回复",
        "哇！这真是太棒了！！！ [情绪:6]",
        "我感觉有点紧张... [情绪:1]"
    ]
    
    for i, test_reply in enumerate(test_cases, 1):
        print(f"\n测试 {i}: {test_reply}")
        clean_reply, emotion_value = parse_emotion_from_reply(test_reply)
        emotion_desc = EMOTION_SCALE.get(emotion_value, "未知情绪")
        print(f"清理后回复: {clean_reply}")
        print(f"情绪值: {emotion_value} ({emotion_desc})")

if __name__ == "__main__":
    test_emotion_parsing()