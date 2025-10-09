"""
测试情绪图片功能
"""
import requests
import time

def test_emotion_images():
    """测试情绪图片HTTP访问"""
    print("----- 情绪图片访问测试 -----")
    
    base_url = "http://localhost:5000/api/emotion/"
    
    for emotion_value in range(1, 7):
        image_url = f"{base_url}{emotion_value}.jpg"
        print(f"\n测试情绪值 {emotion_value}: {image_url}")
        
        try:
            response = requests.get(image_url, timeout=5)
            if response.status_code == 200:
                print(f"✅ 成功访问，文件大小: {len(response.content)} bytes")
            else:
                print(f"❌ 访问失败，状态码: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"❌ 请求异常: {str(e)}")
        
        time.sleep(0.5)  # 避免请求过快

if __name__ == "__main__":
    print("请确保WebSocket服务器已启动 (python websocket_server.py)")
    print("等待5秒后开始测试...")
    time.sleep(5)
    test_emotion_images()