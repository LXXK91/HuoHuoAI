<template>
  <view class="container" @touchstart="handleTouchStart" @touchend="handleTouchEnd">
    <!-- 对话状态显示 - 移动到右上方 -->
    <view class="status-text-top" :data-status="statusType">
      <text class="status-top">{{ statusText }}</text>
    </view>

    <!-- 顶部标题 -->
    <!-- <view class="header">
			<text class="header-title">藿藿语音助手</text>
		</view> -->

    <!-- 人物头像区域 -->
    <view class="avatar-section">
      <view class="avatar-container">
        <image class="avatar" :src="avatarUrl" mode="aspectFit"></image>
        <view class="status-indicator" :class="{ active: isListening, speaking: isSpeaking }"></view>
      </view>
      <!-- <text class="character-name">藿藿</text> -->
    </view>

    <!-- 对话内容区域 -->
    <view class="conversation-area">
      <view class="message-list">
        <!-- 只显示最新的用户消息和AI回复 -->
        <view v-if="currentUserMessage" class="message-item">
          <text class="message-time-top">{{ currentUserMessage.time }}</text>
          <view class="message user">
            <text class="message-text">{{ currentUserMessage.content }}</text>
          </view>
        </view>
        
        <view v-if="currentAiMessage" class="message-item">
          <text class="message-time-top">{{ currentAiMessage.time }}</text>
          <view class="message assistant">
            <text class="message-text">{{ currentAiMessage.content }}</text>
          </view>
        </view>
      </view>
    </view>

  </view>
</template>

<script>
export default {
  data() {
    return {
      avatarUrl: "http://localhost:5000/api/emotion/4.jpg", // 藿藿头像图片，默认为中性情绪
      defaultAvatarUrl: "http://localhost:5000/api/emotion/5.jpg", // 默认头像
      isListening: false, // 是否正在监听
      isSpeaking: false, // 是否正在说话
      isRecording: false, // 是否正在录音
      statusText: "正在连接藿藿...",
      messages: [], // 对话消息列表
      scrollTop: 0,
      // 录音相关
      mediaRecorder: null,
      audioChunks: [],
      audioContext: null,
      recorderManager: null, // App端录音管理器
      // WebSocket相关
      websocket: null,
      wsUrl: "ws://localhost:8765",
      isConnected: false,
      reconnectAttempts: 0,
      maxReconnectAttempts: 5,
      reconnectInterval: 3000,
      heartbeatTimer: null, // 心跳定时器
      // 临时语音消息ID，用于删除
      tempVoiceMessageId: null,
      innerAudioContext: null,
      // 语音活动检测相关
      audioContext: null,
      analyser: null,
      microphone: null,
      dataArray: null,
      silenceTimer: null,
      isVoiceActive: false,
      voiceThreshold: 40, // 声音阈值
      silenceThreshold: 3000, // 静音阈值（毫秒）
      isAutoListening: false, // 是否处于自动监听模式
      // 当前对话消息
      currentUserMessage: null,
      currentAiMessage: null,
      // App端录音管理
      currentRecorder: null,
      hasDetectedVoice: false, // App端声音检测标志
      voiceDetectionTimer: null, // 声音检测定时器
      recordingPhase: 'waiting' // 录音阶段：waiting, detecting, recording
    };
  },
  computed: {
    // 根据状态文本动态确定状态类型
    statusType() {
      const status = this.statusText.toLowerCase();
      if (status.includes('连接') || status.includes('正在连接') || status.includes('重连')) {
        return 'connecting';
      } else if (status.includes('成功') || status.includes('点击按钮') || status.includes('继续对话')) {
        return 'connected';
      } else if (status.includes('错误') || status.includes('失败') || status.includes('断开')) {
        return 'error';
      } else if (status.includes('处理') || status.includes('识别') || status.includes('生成') || status.includes('录音') || status.includes('思考') || status.includes('说话')) {
        return 'processing';
      }
      return 'default';
    }
  },
  onLoad() {
    // 初始化WebSocket连接
    this.initWebSocket();
    // 检查浏览器是否支持录音
    this.checkMediaSupport();
    // 自动开始监听
    this.$nextTick(() => {
      setTimeout(() => {
		  
        this.startAutoListening();
      }, 2000); // 延迟2秒开始监听
    });
	
  },
  onUnload() {
    // 页面卸载时清理资源
    this.cleanup();
  },
  onHide() {
    // 页面隐藏时清理资源
    this.cleanup();
  },
  methods: {
    // WebSocket相关方法
    initWebSocket() {
      try {
        this.statusText = "正在连接藿藿...";
        console.log(`尝试连接WebSocket: ${this.wsUrl}`);

        // #ifdef APP-PLUS
        // 在App中检查网络状态
        if (typeof plus !== "undefined") {
          const netType = plus.networkinfo.getCurrentType();
          console.log("当前网络类型:", netType);
          if (netType === plus.networkinfo.CONNECTION_NONE) {
            this.statusText = "网络未连接，请检查网络设置";
            uni.showToast({
              title: "网络未连接",
              icon: "none",
              duration: 3000,
            });
            return;
          }
        }

        // 使用uni-app的WebSocket API
        this.websocket = uni.connectSocket({
          url: this.wsUrl,
          complete: () => {},
        });
        // #endif

        // #ifdef H5
        // 在H5中使用原生WebSocket
        this.websocket = new WebSocket(this.wsUrl);
        // #endif

        // #ifdef APP-PLUS
        // App端事件监听
        uni.onSocketOpen(() => {
          console.log("WebSocket连接已建立");
          this.isConnected = true;
          this.reconnectAttempts = 0;
          this.statusText = "连接成功";

          // 发送心跳
          this.startHeartbeat();
        });

        uni.onSocketMessage((res) => {
          try {
            const data = JSON.parse(res.data);
            this.handleWebSocketMessage(data);
          } catch (error) {
            console.error("解析WebSocket消息失败:", error);
          }
        });

        uni.onSocketClose((res) => {
          console.log("WebSocket连接已关闭", res.code, res.reason);
          this.isConnected = false;
          this.statusText = "连接断开，正在尝试重连...";
          this.stopHeartbeat();
          this.attemptReconnect();
        });

        uni.onSocketError((res) => {
          console.error("WebSocket错误:", res);
          this.statusText = "连接错误，正在尝试重连...";
        });
        // #endif

        // #ifdef H5
        // H5端事件监听
        this.websocket.onopen = () => {
          console.log("WebSocket连接已建立");
          this.isConnected = true;
          this.reconnectAttempts = 0;
          this.statusText = "连接成功";

          // 发送心跳
          this.startHeartbeat();
        };

        this.websocket.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            this.handleWebSocketMessage(data);
          } catch (error) {
            console.error("解析WebSocket消息失败:", error);
          }
        };

        this.websocket.onclose = (event) => {
          console.log("WebSocket连接已关闭", event.code, event.reason);
          this.isConnected = false;
          this.statusText = "连接断开，正在尝试重连...";
          this.stopHeartbeat();
          this.attemptReconnect();
        };

        this.websocket.onerror = (error) => {
          console.error("WebSocket错误:", error);
          this.statusText = "连接错误，正在尝试重连...";
        };
        // #endif
      } catch (error) {
        console.error("创建WebSocket连接失败:", error);
        this.statusText = "无法连接到服务器";

        uni.showToast({
          title: "无法连接到服务器，请检查网络和服务器状态",
          icon: "none",
          duration: 5000,
        });
      }
    },

    // 心跳机制
    startHeartbeat() {
      this.stopHeartbeat(); // 先停止之前的心跳
      this.heartbeatTimer = setInterval(() => {
        // #ifdef APP-PLUS
        if (this.isConnected) {
          this.sendWebSocketMessage({ type: "ping" });
        }
        // #endif

        // #ifdef H5
        if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
          this.sendWebSocketMessage({ type: "ping" });
        }
        // #endif
      }, 30000); // 每30秒发送一次心跳
    },

    stopHeartbeat() {
      if (this.heartbeatTimer) {
        clearInterval(this.heartbeatTimer);
        this.heartbeatTimer = null;
      }
    },

    attemptReconnect() {
      if (this.reconnectAttempts < this.maxReconnectAttempts) {
        this.reconnectAttempts++;
        console.log(`尝试重连 (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);

        setTimeout(() => {
          this.initWebSocket();
        }, this.reconnectInterval);
      } else {
        this.statusText = "连接失败，请检查网络或服务器状态";

        uni.showToast({
          title: "连接失败，请检查网络",
          icon: "none",
          duration: 3000,
        });
      }
    },

    handleWebSocketMessage(data) {
      console.log("收到WebSocket消息:", data);

      switch (data.type) {
        case "welcome":
          this.setCurrentAiMessage(data.message);
          break;

        case "status":
          this.statusText = data.message;
          break;

        case "asr_result":
          // 显示语音识别结果作为用户消息
          if (data.message) {
            const text = data.message.replace('识别结果: "', "").replace('"', "");
            // 只有识别出内容时才显示
            if (text.trim()) {
              this.setCurrentUserMessage(text);
            } else {
              // 识别失败时清空当前消息，不显示任何内容
              this.clearCurrentMessages();
              this.statusText = "正在监听语音中...";
            }
          }
          break;

        case "assistant_reply":
          // 只有在有AI回复内容时才显示
          if (data.message && data.message.trim()) {
            // 显示用户消息（如果还没有显示）
            if (data.user_message && !this.currentUserMessage) {
              this.setCurrentUserMessage(data.user_message);
            }

            // 显示助手回复
            this.setCurrentAiMessage(data.message);
          } else {
            // 没有AI回复时，清空当前消息
            this.clearCurrentMessages();
            this.statusText = "正在监听语音中...";
          }

          // 更新头像情绪图片
          if (data.emotion_img) {
            this.avatarUrl = `http://localhost:5000${data.emotion_img}`;
            console.log(`更新头像为情绪值 ${data.emotion_value}: ${this.avatarUrl}`);
            
            // 3秒后恢复默认头像
            // setTimeout(() => {
            //   this.avatarUrl = this.defaultAvatarUrl;
            // }, 3000);
          }

          // 停止说话状态
          this.isSpeaking = false;
          this.statusText = "继续对话";

          // 播放语音（如果有）
          if (data.audio_url && data.message && data.message.trim()) {
            this.playAudio(`http://localhost:5000${data.audio_url}`);
          } else if (!data.message || !data.message.trim()) {
            // 没有AI回复时，直接重新开始监听
            setTimeout(() => {
              if (!this.isAutoListening) {
                this.startAutoListening();
              }
            }, 500);
          }
          break;

        case "error":
          this.statusText = "出现错误，请重试";
          this.setCurrentAiMessage(`错误: ${data.message}`);

          uni.showToast({
            title: data.message,
            icon: "none",
            duration: 3000,
          });
          break;

        case "pong":
          // 心跳响应
          break;

        default:
          console.warn("未知的消息类型:", data.type);
          break;
      }
    },

    sendWebSocketMessage(message) {
      // #ifdef APP-PLUS
      if (this.isConnected) {
        uni.sendSocketMessage({
          data: JSON.stringify(message),
          success: () => {
            // console.log('消息发送成功');
          },
          fail: (err) => {
            console.error("消息发送失败:", err);
          },
        });
        return true;
      } else {
        console.error("WebSocket连接未开放");
        uni.showToast({
          title: "WebSocket连接断开",
          icon: "none",
        });
        return false;
      }
      // #endif

      // #ifdef H5
      if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
        this.websocket.send(JSON.stringify(message));
        return true;
      } else {
        console.error("WebSocket连接未开放");
        uni.showToast({
          title: "WebSocket连接断开",
          icon: "none",
        });
        return false;
      }
      // #endif
    },

    // 检查媒体支持
    checkMediaSupport() {
      // #ifdef APP-PLUS
      // 在App中检查录音权限
      return true; // App中的权限由manifest.json配置
      // #endif

      // #ifdef H5
      // 在浏览器中检查API支持
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        uni.showToast({
          title: "你的浏览器不支持录音功能",
          icon: "none",
        });
        return false;
      }
      return true;
      // #endif
    },

    // 开始自动语音监听
    async startAutoListening() {
      if (!this.checkMediaSupport() || this.isAutoListening) {
        return;
      }
      
      try {
        this.isAutoListening = true;
        this.statusText = "正在监听语音中...";
        
        // #ifdef H5
        // 在浏览器中使用Web Audio API
        const stream = await navigator.mediaDevices.getUserMedia({
          audio: {
            sampleRate: 16000,
            channelCount: 1,
            volume: 1.0,
          },
        });
        
        // 创建音频上下文
        this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
        this.analyser = this.audioContext.createAnalyser();
        this.microphone = this.audioContext.createMediaStreamSource(stream);
        
        this.analyser.fftSize = 256;
        const bufferLength = this.analyser.frequencyBinCount;
        this.dataArray = new Uint8Array(bufferLength);
        
        this.microphone.connect(this.analyser);
        
        // 开始检测语音活动
        this.detectVoiceActivity();
        // #endif
        
        // #ifdef APP-PLUS
        // 在App中使用简化的监听模式，直接开始录音
        this.startAppAutoListening();
        // #endif
        
      } catch (error) {
        console.error("启动自动监听失败:", error);
        this.isAutoListening = false;
        uni.showToast({
          title: "无法访问麦克风",
          icon: "none",
        });
      }
    },
    
    // App端自动监听（使用录音管理器）
    startAppAutoListening() {
      console.log("App端开始自动监听");
      // 在App端直接开始一次长时间录音，通过静音检测来控制
      this.startAppContinuousRecording();
    },
    
    // App端持续录音模式
    startAppContinuousRecording() {
      if (!this.isAutoListening) {
        return;
      }
      
      console.log("开始App端持续录音");
      this.recordingPhase = 'detecting';
      const recorderManager = uni.getRecorderManager();
      this.currentRecorder = recorderManager;
      
      // 清理之前的事件监听器
      recorderManager.onStart(() => {
        console.log("App端检测录音开始");
        this.isListening = true;
        this.statusText = "正在监听语音中...";
        this.hasDetectedVoice = false;
        
        // 开始声音检测定时器 - 延长检测时间
        this.startVoiceDetectionTimer();
      });
      
      recorderManager.onStop((res) => {
        console.log("App端检测录音停止", res, "阶段:", this.recordingPhase);
        
        // 清理检测定时器
        this.clearVoiceDetectionTimer();
        
        if (this.recordingPhase === 'detecting') {
          // 检测阶段结束，检查是否检测到声音
          const fileSize = res.fileSize || 0;
          console.log("检测录音文件大小:", fileSize);
          
          if (fileSize > 3000) { // 提高文件大小阈值，说明可能有声音
            console.log("检测到可能的声音输入，开始正式录音");
            this.hasDetectedVoice = true;
            this.startAppFormalRecording();
          } else {
            console.log("未检测到声音，重新开始监听");
            this.statusText = "正在监听语音中...";
            this.isListening = false;
            // 重新开始监听
            setTimeout(() => {
              if (this.isAutoListening) {
                this.startAppContinuousRecording();
              }
            }, 500);
          }
        } else if (this.recordingPhase === 'recording') {
          // 正式录音结束
          this.isRecording = false;
          this.isListening = false;
          this.isVoiceActive = false;
          
          const fileSize = res.fileSize || 0;
          console.log("正式录音文件大小:", fileSize);
          
          if (fileSize > 2000) {
            this.statusText = "录音完成，正在处理...";
            this.processAppRecording(res.tempFilePath);
          } else {
            console.log("录音文件过小，重新开始监听");
            this.statusText = "正在监听语音中...";
            setTimeout(() => {
              if (this.isAutoListening) {
                this.startAppContinuousRecording();
              }
            }, 500);
          }
        }
      });
      
      recorderManager.onError((error) => {
        console.error("App端录音错误:", error);
        this.isRecording = false;
        this.isListening = false;
        this.isVoiceActive = false;
        this.clearVoiceDetectionTimer();
        
        // 错误后重新开始
        setTimeout(() => {
          if (this.isAutoListening) {
            this.startAppContinuousRecording();
          }
        }, 1000);
      });
      
      // 开始检测录音
      recorderManager.start({
        duration: 6000, // 6秒检测周期，给用户更多时间
        sampleRate: 16000,
        numberOfChannels: 1,
        encodeBitRate: 96000,
        format: "mp3",
      });
    },
    
    // 开始声音检测定时器
    startVoiceDetectionTimer() {
      this.clearVoiceDetectionTimer();
      
      // 3秒后如果没有切换到正式录音，则认为没有声音
      this.voiceDetectionTimer = setTimeout(() => {
        console.log("声音检测超时，停止当前录音");
        if (this.currentRecorder && this.recordingPhase === 'detecting') {
          this.currentRecorder.stop();
        }
      }, 5000); // 5秒检测超时
    },
    
    // 清理声音检测定时器
    clearVoiceDetectionTimer() {
      if (this.voiceDetectionTimer) {
        clearTimeout(this.voiceDetectionTimer);
        this.voiceDetectionTimer = null;
      }
    },
    
    // App端正式录音
    startAppFormalRecording() {
      console.log("开始App端正式录音");
      
      // 清理检测定时器
      this.clearVoiceDetectionTimer();
      
      // 等待一小段时间让检测录音完全停止
      setTimeout(() => {
        this.recordingPhase = 'recording';
        
        // 开始正式录音
        const formalRecorder = uni.getRecorderManager();
        this.currentRecorder = formalRecorder;
        
        formalRecorder.onStart(() => {
          console.log("正式录音开始");
          this.isRecording = true;
          this.isVoiceActive = true;
          this.statusText = "正在录音中，请说话...";
          
          // 设置静音检测定时器 - 延长静音检测时间
          this.setupAppSilenceTimer();
        });
        
        formalRecorder.onStop((res) => {
          console.log("正式录音结束", res);
          // 这个回调会在startAppContinuousRecording的onStop中处理
        });
        
        formalRecorder.onError((error) => {
          console.error("正式录音错误:", error);
          this.isRecording = false;
          this.isListening = false;
          this.isVoiceActive = false;
          this.recordingPhase = 'waiting';
          
          // 清除静音定时器
          if (this.silenceTimer) {
            clearTimeout(this.silenceTimer);
            this.silenceTimer = null;
          }
        });
        
        // 开始正式录音
        formalRecorder.start({
          duration: 60000, // 最长60秒
          sampleRate: 16000,
          numberOfChannels: 1,
          encodeBitRate: 96000,
          format: "mp3",
        });
      }, 300); // 延迟300ms确保检测录音已停止
    },
    
    // 设置App端静音检测定时器
    setupAppSilenceTimer() {
      // 清除之前的定时器
      if (this.silenceTimer) {
        clearTimeout(this.silenceTimer);
      }
      
      // 设置新的静音定时器 - 给用户更多时间说话
      this.silenceTimer = setTimeout(() => {
        console.log("检测到静音，停止录音");
        if (this.isRecording && this.currentRecorder && this.recordingPhase === 'recording') {
          this.currentRecorder.stop();
        }
      }, this.silenceThreshold + 2000); // 增加2秒缓冲时间
    },
    
    // 检测语音活动（仅H5）
    detectVoiceActivity() {
      // #ifdef H5
      if (!this.isAutoListening || !this.analyser) {
        return;
      }
      
      this.analyser.getByteFrequencyData(this.dataArray);
      
      // 计算音频强度
      let sum = 0;
      for (let i = 0; i < this.dataArray.length; i++) {
        sum += this.dataArray[i];
      }
      const average = sum / this.dataArray.length;
      
      // 检测是否超过阈值
      if (average > this.voiceThreshold) {
        if (!this.isVoiceActive && !this.isRecording && !this.isSpeaking) {
          // 开始录音
          this.isVoiceActive = true;
          this.startRecording();
        }
        
        // 清除静音计时器
        if (this.silenceTimer) {
          clearTimeout(this.silenceTimer);
          this.silenceTimer = null;
        }
      } else {
        // 如果正在录音且检测到静音
        if (this.isVoiceActive && this.isRecording && !this.silenceTimer) {
          this.silenceTimer = setTimeout(() => {
            // 静音超过阈值时间，停止录音
            this.isVoiceActive = false;
            this.stopRecording();
          }, this.silenceThreshold);
        }
      }
      
      // 继续检测
      if (this.isAutoListening) {
        requestAnimationFrame(() => this.detectVoiceActivity());
      }
      // #endif
    },
    
    // 停止自动监听
    stopAutoListening() {
      this.isAutoListening = false;
      
      if (this.silenceTimer) {
        clearTimeout(this.silenceTimer);
        this.silenceTimer = null;
      }
      
      // 清理声音检测定时器
      this.clearVoiceDetectionTimer();
      
      if (this.microphone) {
        this.microphone.disconnect();
        this.microphone = null;
      }
      
      if (this.audioContext) {
        this.audioContext.close();
        this.audioContext = null;
      }
      
      this.analyser = null;
      this.dataArray = null;
      this.recordingPhase = 'waiting';
    },
    
    // 切换语音对话状态（保留兼容性，但不再使用）
    toggleVoiceChat() {
      // 空实现，保持兼容性
    },

    // 开始录音
    async startRecording() {
      if (!this.checkMediaSupport()) {
        return;
      }

      try {
        // #ifdef APP-PLUS
        // 在App中使用uni-app的录音API
        this.startAppRecording();
        return;
        // #endif

        // #ifdef H5
        // 在浏览器中使用MediaRecorder API
        await this.startBrowserRecording();
        // #endif
      } catch (error) {
        console.error("开始录音失败:", error);
        uni.showToast({
          title: "无法访问麦克风，请检查权限设置",
          icon: "none",
          duration: 3000,
        });
      }
    },

    // App端录音
    startAppRecording() {
      // 使用uni-app的录音API
      const recorderManager = uni.getRecorderManager();

      recorderManager.onStart(() => {
        console.log("开始录音");
        this.isRecording = true;
        this.isListening = true;
        this.statusText = "正在录音中，请说话...";

        uni.showToast({
          title: "开始录音",
          icon: "none",
        });
      });

      recorderManager.onStop((res) => {
        console.log("录音结束", res);
        this.isRecording = false;
        this.isListening = false;
        this.statusText = "录音完成，正在处理...";

        // 处理录音文件
        this.processAppRecording(res.tempFilePath);
      });

      recorderManager.onError((error) => {
        console.error("录音错误:", error);
        this.isRecording = false;
        this.isListening = false;

        uni.showToast({
          title: "录音失败，请检查麦克风权限",
          icon: "none",
        });
      });

      // 开始录音
      recorderManager.start({
        duration: 60000, // 最长录音时间60秒
        sampleRate: 16000, // 采样率
        numberOfChannels: 1, // 声道数
        encodeBitRate: 96000, // 编码比特率
        format: "mp3", // 音频格式
      });

      this.recorderManager = recorderManager;
    },

    // 浏览器端录音
    async startBrowserRecording() {
      // 请求麦克风权限
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: 16000,
          channelCount: 1,
          volume: 1.0,
        },
      });

      // 创建 MediaRecorder
      this.mediaRecorder = new MediaRecorder(stream, {
        mimeType: "audio/webm;codecs=opus",
      });

      // 重置音频数据
      this.audioChunks = [];

      // 设置事件监听器
      this.mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          this.audioChunks.push(event.data);
        }
      };

      this.mediaRecorder.onstop = () => {
        this.processBrowserRecording();
        // 停止所有音频轨道
        stream.getTracks().forEach((track) => track.stop());
      };

      // 开始录音
      this.mediaRecorder.start();
      this.isRecording = true;
      this.isListening = true;
      this.statusText = "正在录音中，请说话...";

      uni.showToast({
        title: "开始录音",
        icon: "none",
      });
    },

    // 停止录音
    stopRecording() {
      // #ifdef APP-PLUS
      if (this.recorderManager) {
        this.recorderManager.stop();
        return;
      }
      // #endif

      // #ifdef H5
      if (this.mediaRecorder && this.mediaRecorder.state === "recording") {
        this.mediaRecorder.stop();
        this.isRecording = false;
        this.isListening = false;
        this.statusText = "录音完成，正在处理...";

        uni.showToast({
          title: "录音结束",
          icon: "none",
        });
      }
      // #endif
    },

    // 工具方法：读取录音文件为 Base64
    async readFileToBase64(filePath, callback) {
      // #ifdef MP-WEIXIN
      // 小程序
      const fs = uni.getFileSystemManager();
      fs.readFile({
        filePath,
        encoding: "base64",
        success: (res) => callback(null, res.data),
        fail: (err) => callback(err),
      });
      // #endif

      // #ifdef APP-PLUS
      // App 端
      plus.io.resolveLocalFileSystemURL(
        filePath,
        (entry) => {
          entry.file(
            (file) => {
              const reader = new plus.io.FileReader();
              reader.onloadend = (e) => {
                // e.target.result 是 data:audio/mp3;base64,xxxx 形式
                const base64 = e.target.result.split(",")[1];
                callback(null, base64);
              };
              reader.readAsDataURL(file);
            },
            (err) => callback(err)
          );
        },
        (err) => callback(err)
      );
      // #endif

      // #ifdef H5
      // H5 浏览器
      fetch(filePath)
        .then((res) => res.blob())
        .then((blob) => {
          const reader = new FileReader();
          reader.onloadend = () => {
            const base64 = reader.result.split(",")[1];
            callback(null, base64);
          };
          reader.readAsDataURL(blob);
        })
        .catch((err) => callback(err));
      // #endif
    },

    // 处理App录音结果
    async processAppRecording(filePath) {
      try {
        // 读取文件并转换为base64
        // const fileManager = uni.getFileSystemManager();
        // console.log(99, filePath);
        // console.log(88, fileManager);

        // const tempFilePath = res.tempFilePath;
        this.readFileToBase64(filePath, (err, base64) => {
          if (err) {
            console.error("读取录音文件失败:", err);
            return;
          }
          console.log("读取录音文件成功:");
          // 显示临时用户消息
          this.setCurrentUserMessage("发送了一条语音消息");
          
          // App端录音完成后重新开始监听
          // #ifdef APP-PLUS
          setTimeout(() => {
            if (this.isAutoListening && !this.isRecording && this.recordingPhase !== 'recording') {
              this.recordingPhase = 'waiting';
              this.startAppContinuousRecording();
            }
          }, 1000);
          // #endif

          // 发送到WebSocket服务器
          this.sendAudioBase64ToWebSocket(base64);
          // TODO: 这里可以把 base64 发送到 WebSocket 或后端
        });

        // fileManager({
        //   filePath: filePath,
        //   encoding: "base64",
        //   success: (res) => {
        //     console.log("读取录音文件成功", res);

        //     // 显示临时用户消息
        //     this.tempVoiceMessageId = this.addMessage("用户", `发送了一条语音消息`, "user");

        //     // 发送到WebSocket服务器
        //     this.sendAudioBase64ToWebSocket(res.data);
        //   },
        //   fail: (error) => {
        //     console.error("读取录音文件失败:", error);
        //     uni.showToast({
        //       title: "处理录音失败",
        //       icon: "none",
        //     });
        //   },
        // });
      } catch (error) {
        console.error("处理App录音失败:", error);
        uni.showToast({
          title: "处理录音失败",
          icon: "none",
        });
      }
    },

    // 处理浏览器录音结果
    async processBrowserRecording() {
      try {
        // 合并音频数据
        const audioBlob = new Blob(this.audioChunks, { type: "audio/webm" });

        if (audioBlob.size === 0) {
          uni.showToast({
            title: "录音数据为空",
            icon: "none",
          });
          return;
        }

        // 显示临时用户消息
        const duration = Math.round(audioBlob.size / 1000); // 估算时长
        this.setCurrentUserMessage(`发送了一条语音消息 (${duration}s)`);

        // 转换为base64并发送到WebSocket服务器
        await this.sendAudioToWebSocket(audioBlob);
      } catch (error) {
        console.error("处理浏览器录音失败:", error);
        uni.showToast({
          title: "处理录音失败",
          icon: "none",
        });
      }
    },

    // 发送base64音频到WebSocket
    async sendAudioBase64ToWebSocket(base64Audio) {
      try {
        this.statusText = "正在处理语音...";

        // 发送到WebSocket服务器
        const message = {
          type: "audio",
          audio: base64Audio,
        };

        const success = this.sendWebSocketMessage(message);

        if (success) {
          uni.showToast({
            title: "语音已发送",
            icon: "success",
          });
        } else {
          throw new Error("WebSocket连接不可用");
        }
      } catch (error) {
        console.error("发送base64音频失败:", error);

        this.statusText = "发送失败，请检查网络连接";

        uni.showToast({
          title: "发送失败，请检查网络",
          icon: "none",
          duration: 3000,
        });
      }
    },

    // 通过WebSocket发送音频
    async sendAudioToWebSocket(audioBlob) {
      try {
        this.statusText = "正在处理语音...";

        // 转换为ArrayBuffer
        const arrayBuffer = await audioBlob.arrayBuffer();

        // 转换为base64
        const uint8Array = new Uint8Array(arrayBuffer);
        let binary = "";
        for (let i = 0; i < uint8Array.length; i++) {
          binary += String.fromCharCode(uint8Array[i]);
        }
        const base64Audio = btoa(binary);

        // 发送到WebSocket服务器
        const message = {
          type: "audio",
          audio: base64Audio,
        };

        const success = this.sendWebSocketMessage(message);

        if (success) {
          uni.showToast({
            title: "语音已发送",
            icon: "success",
          });
        } else {
          throw new Error("WebSocket连接不可用");
        }
      } catch (error) {
        console.error("发送音频失败:", error);

        this.statusText = "发送失败，请检查网络连接";

        uni.showToast({
          title: "发送失败，请检查网络",
          icon: "none",
          duration: 3000,
        });
      }
    },

    // 播放音频文件
    playAudio(audioUrl) {
      try {
        console.log("开始播放音频:", audioUrl);

        // 创建音频对象
        if (this.innerAudioContext) {
          this.innerAudioContext.stop();
          this.innerAudioContext.destroy();
        }

        this.innerAudioContext = uni.createInnerAudioContext();
        this.innerAudioContext.autoplay = true;
        this.innerAudioContext.src = audioUrl; // 录音文件路径或 http(s) 网络地址

        // 设置音频事件监听器
        this.innerAudioContext.onloadstart = () => {
          console.log("音频开始加载");
          this.statusText = "藿藿的语音正在加载...";
        };

        this.innerAudioContext.oncanplay = () => {
          console.log("音频可以播放");
          this.statusText = "藿藿正在说话...";
          this.isSpeaking = true;
        };

        this.innerAudioContext.onplay = () => {
          console.log("音频开始播放");
          this.isSpeaking = true;
        };

        this.innerAudioContext.onended = () => {
          console.log("音频播放结束");
          this.isSpeaking = false;
          this.statusText = "正在监听语音中...";
          
          // AI语音播放完成后，重新开始监听
          setTimeout(() => {
            if (!this.isAutoListening) {
              this.startAutoListening();
            } else {
              // #ifdef APP-PLUS
              // App端需要重新开始录音循环
              if (this.recordingPhase !== 'recording') {
                this.recordingPhase = 'waiting';
                this.startAppContinuousRecording();
              }
              // #endif
            }
          }, 500);
        };

        this.innerAudioContext.onerror = (error) => {
          console.error("音频播放错误:", error);
          this.isSpeaking = false;
          this.statusText = "语音播放失败";

          uni.showToast({
            title: "语音播放失败",
            icon: "none",
          });
        };

        // 开始播放
        // this.innerAudioContext.play().catch((error) => {
        //   console.error("播放音频失败:", error);
        //   this.isSpeaking = false;
        //   this.statusText = "自动播放被阻止，请手动点击播放";

        //   uni.showToast({
        //     title: "请手动允许音频播放",
        //     icon: "none",
        //     duration: 3000,
        //   });
        // });
      } catch (error) {
        console.error("创建音频对象失败:", error);
        uni.showToast({
          title: "音频播放功能不可用",
          icon: "none",
        });
      }
    },

    // 设置当前用户消息
    setCurrentUserMessage(content) {
      const now = new Date();
      const time = `${now.getHours().toString().padStart(2, "0")}:${now.getMinutes().toString().padStart(2, "0")}`;
      
      this.currentUserMessage = {
        content,
        time,
        type: 'user'
      };
    },
    
    // 设置当前AI消息
    setCurrentAiMessage(content) {
      const now = new Date();
      const time = `${now.getHours().toString().padStart(2, "0")}:${now.getMinutes().toString().padStart(2, "0")}`;
      
      this.currentAiMessage = {
        content,
        time,
        type: 'assistant'
      };
    },
    
    // 清除当前对话
    clearCurrentMessages() {
      this.currentUserMessage = null;
      this.currentAiMessage = null;
    },

    // 清理资源
    cleanup() {
      // 停止心跳
      this.stopHeartbeat();
      
      // 停止自动监听
      this.stopAutoListening();

      // 关闭WebSocket连接
      // #ifdef APP-PLUS
      if (this.isConnected) {
        uni.closeSocket();
      }
      // #endif

      // #ifdef H5
      if (this.websocket) {
        this.websocket.close();
        this.websocket = null;
      }
      // #endif

      // 停止录音
      if (this.mediaRecorder && this.mediaRecorder.state !== "inactive") {
        this.mediaRecorder.stop();
      }

      // 停止App端录音
      if (this.recorderManager) {
        this.recorderManager.stop();
        this.recorderManager = null;
      }

      // 重置状态
      this.isConnected = false;
      this.isRecording = false;
      this.isListening = false;
    },
  },

  // 组件销毁时清理资源
  beforeDestroy() {
    this.cleanup();
  },
};
</script>

<style>
page {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  height: 100vh;
}

.container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  padding: 20rpx;
  box-sizing: border-box;
}

/* 右上角状态显示 */
.status-text-top {
  position: fixed;
  top: 120rpx;
  right: 1rpx;
  z-index: 1000;
  background: rgba(255, 255, 255, 0.95);
  padding: 16rpx 24rpx;
  border-radius: 20rpx;
  box-shadow: 0 4rpx 16rpx rgba(0, 0, 0, 0.1);
  backdrop-filter: blur(10rpx);
  max-width: 400rpx;
  transition: all 0.3s ease;
}

.status-top {
  font-size: 24rpx;
  color: #333333;
  font-weight: 500;
  text-align: center;
  display: block;
  line-height: 1.3;
  word-wrap: break-word;
  overflow-wrap: break-word;
}

/* 适配不同状态的颜色 */
.status-text-top[data-status="connecting"] {
  background: rgba(255, 193, 7, 0.9);
  border-left: 4rpx solid #ffc107;
}

.status-text-top[data-status="connected"] {
  background: rgba(40, 167, 69, 0.9);
  border-left: 4rpx solid #28a745;
}

.status-text-top[data-status="error"] {
  background: rgba(220, 53, 69, 0.9);
  border-left: 4rpx solid #dc3545;
}

.status-text-top[data-status="processing"] {
  background: rgba(23, 162, 184, 0.9);
  border-left: 4rpx solid #17a2b8;
}

.status-text-top[data-status="connecting"] .status-top,
.status-text-top[data-status="connected"] .status-top,
.status-text-top[data-status="error"] .status-top,
.status-text-top[data-status="processing"] .status-top {
  color: #ffffff;
  font-weight: 600;
}

/* 默认状态动画 */
.status-text-top[data-status="processing"] {
  animation: pulse-status 2s infinite;
}

@keyframes pulse-status {
  0% {
    transform: scale(1);
    opacity: 0.9;
  }
  50% {
    transform: scale(1.02);
    opacity: 1;
  }
  100% {
    transform: scale(1);
    opacity: 0.9;
  }
}

/* 顶部标题 */
.header {
  text-align: center;
  padding: 40rpx 0 20rpx;
}

.header-title {
  font-size: 48rpx;
  font-weight: bold;
  color: #ffffff;
  text-shadow: 0 2rpx 4rpx rgba(0, 0, 0, 0.3);
}

/* 人物头像区域 */
.avatar-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 50rpx 0;
}

.avatar-container {
  position: relative;
  width: 480rpx;
  height: 480rpx;
  margin-bottom: 20rpx;
}

.avatar {
  width: 100%;
  height: 100%;
  border-radius: 50%;
  border: 6rpx solid #ffffff;
  box-shadow: 0 8rpx 32rpx rgba(0, 0, 0, 0.2);
  background: #f0f0f0;
}

.status-indicator {
  position: absolute;
  bottom: 6rpx;
  right: 6rpx;
  width: 30rpx;
  height: 30rpx;
  border-radius: 50%;
  background: #cccccc;
  border: 4rpx solid #ffffff;
  transition: all 0.3s ease;
}

.status-indicator.active {
  background: #4cd964;
  animation: pulse 2s infinite;
}

.status-indicator.speaking {
  background: #ff3b30;
  animation: speaking 0.5s infinite alternate;
}

@keyframes pulse {
  0% {
    transform: scale(1);
    opacity: 1;
  }
  50% {
    transform: scale(1.2);
    opacity: 0.7;
  }
  100% {
    transform: scale(1);
    opacity: 1;
  }
}

@keyframes speaking {
  0% {
    transform: scale(1);
  }
  100% {
    transform: scale(1.3);
  }
}

.character-name {
  font-size: 36rpx;
  font-weight: bold;
  color: #ffffff;
  text-shadow: 0 2rpx 4rpx rgba(0, 0, 0, 0.3);
}

/* 对话区域 */
.conversation-area {
  
  margin: 20rpx 0;
  /* background: rgba(255, 255, 255, 0.95); */
  border-radius: 20rpx;
  overflow: hidden;
}

.message-list {
  height: 100%;
  padding: 20rpx;
  box-sizing: border-box;
}

.message-item {
  margin-bottom: 20rpx;
}

.message-time-top {
  font-size: 22rpx;
  color: #666666;
  text-align: center;
  display: block;
  margin-bottom: 8rpx;
  opacity: 0.8;
}

.message {
  max-width: 80%;
  padding: 20rpx;
  border-radius: 16rpx;
  position: relative;
}

.message.user {
  background: #007aff;
  margin-left: auto;
  border-bottom-right-radius: 4rpx;
}

.message.user .message-text {
  color: #ffffff;
}

.message.assistant {
  background: #f0f0f0;
  margin-right: auto;
  border-bottom-left-radius: 4rpx;
}

.message.assistant .message-text {
  color: #333333;
}

.message.error {
  background: #ffebee;
  margin-right: auto;
  border-left: 4rpx solid #f44336;
  border-bottom-left-radius: 4rpx;
}

.message.error .message-text {
  color: #d32f2f;
}

.message-text {
  font-size: 30rpx;
  line-height: 1.4;
  display: block;
}

</style>
