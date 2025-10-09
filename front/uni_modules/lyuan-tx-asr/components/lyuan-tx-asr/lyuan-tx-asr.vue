<template>
	<view class="asr-container flex flex-direction " v-show="isShow" :class="isAnimation ? 'animation-slide-bottom' : 'animation-slide-bottom-hidden'">
		<view class="flex1" :style="'background-color: rgba(0,0,0,' + opacity + ');'"></view>
		<view class="bg-white shadow shadow-warp radius padding-bottom shadow-blur">
			<view class="cu-bar">
				<view class="action"><button class="cu-btn" @click="cancel">取消</button></view>
				<view class="content"></view>
				<view class="action"><button class="cu-btn bg-main" @click="ok">确定</button></view>
			</view>

			<view class="padding">
				<view class=" bg-gray padding border">{{ content }}</view>
			</view>
			<view class="flex  align-center justify-center">
				<view v-if="status" class="flex1 margin-lr asr-playing"></view>
				<view class=" flex justify-center flex-direction align-center">
					<view
						style="border: 2px solid #007AFF;"
						class="cu-avatar xl round bg-white   "
						:class="status ? 'startBtn' : ''"
						@touchstart="ontouchstart"
						@touchend="ontouchend"
					>
						<view :class="status ? 'cuIcon-stop text-blue' : 'cuIcon-playfill text-blue'"></view>
					</view>
					<view class=" text-gray padding">
						<text v-if="status == 0">长按开始</text>
						<text v-else-if="status == 1">引擎初始化</text>
						<text v-else-if="status == 2">语音识别启动中</text>
						<text v-else-if="status == 3">正在识别 {{ durationClock }}</text>
					</view>
				</view>
				<view v-if="status" class="flex1 margin-lr asr-playing" style=""></view>
			</view>
		</view>
	</view>
</template>

<script>
import asrauthentication from './asrauthentication.js';
export default {
	name: 'lyuan-tx-asr',
	props: {
		secretKey: { type: String },
		secretId: { type: String },
		appId: { type: Number | String },
		uploadFile: { type: Function },
		opacity: { type: Number, default: 0.4 }
	},
	data() {
		return {
			socket: null,
			recorder: null,
			status: 0,
			timer: null,
			content: '',
			message: '',
			duration: 0,
			durationTimer: null,
			isShow: false,
			isAnimation: false
		};
	},
	computed: {
		durationClock: function() {
			let minute = Math.floor(this.duration / 60);
			if (minute < 10) minute = '0' + minute.toString();
			let seconds = this.duration % 60;
			if (seconds < 10) seconds = '0' + seconds.toString();
			return minute + ':' + seconds;
		}
	},
	methods: {
		show: function() {
			if (!this.appId || !this.secretId || !this.secretKey) {
				uni.showToast({
					icon: 'none',
					title: '缺少腾讯配置参数'
				});
				return;
			}

			// #ifdef H5
			uni.showToast({
				icon: 'none',
				title: '暂不支持H5平台'
			});
			return;
			// #endif
			this.status = 0;
			this.content = '';
			this.isShow = true;
			this.isAnimation = true;
		},
		hide: function() {
			this.stop();
			this.isAnimation = false;
			setTimeout(() => {
				this.isShow = false;
			}, 500);
		},
		ok: function() {
			this.$emit('change', this.content);
			this.hide();
		},
		cancel: function() {
			this.hide();
		},
		ontouchstart(e) {
			console.log('touch start');
			if (this.timer) clearTimeout(this.timer);
			this.timer = setTimeout(() => {
				this.start();
				this.timer = null;
			}, 600);
		},
		ontouchend(e) {
			console.log('touch end');
			if (this.timer) {
				console.log('清除定时器');
				clearTimeout(this.timer);
				this.timer = null;
			}
			this.stop();
		},
		getUrl: function() {
			const timestamp = parseInt(new Date().getTime() / 1000) - 1;
			const params = {
				secretid: this.secretId,
				timestamp: timestamp,
				expired: timestamp + 60 * 60,
				nonce: timestamp,
				engine_model_type: '16k_zh',
				voice_id: timestamp.toString(),
				voice_format: 8
			};
			const url =
				'asr.cloud.tencent.com/asr/v2/' +
				this.appId +
				'?' +
				Object.keys(params)
					.sort(function(a, b) {
						return a.localeCompare(b);
					})
					.map(key => {
						return encodeURIComponent(key) + '=' + encodeURIComponent(params[key]);
					})
					.join('&');
			const signature = asrauthentication.signCallback(url, this.secretKey);
			return url + '&signature=' + signature;
		},
		startTimer: function() {
			this.duration = 0;
			this.durationTimer = setInterval(() => {
				this.duration += 1;
			}, 1000);
		},
		stopTimer: function() {
			if (this.durationTimer) {
				clearInterval(this.durationTimer);
				this.durationTimer = null;
			}
		},
		start: function() {
			// #ifdef APP-PLUS
			this.startRecorder();
			// #endif
			// #ifdef MP-WEIXIN
			this.startConnect();
			// #endif
		},
		stop: function() {
			// #ifdef APP-PLUS
			this.stopRecorder();
			// #endif
			// #ifdef MP-WEIXIN
			this.stopConnect();
			// #endif
		},
		startConnect: function() {
			this.status = 1;

			const socket = (this.socket = uni.connectSocket({
				url: 'wss://' + this.getUrl(),
				success: data => {
					console.log('socket connect result ', data);
				},
				fail: e => {
					this.loading(JSON.stringify(e));
				}
			}));

			socket.onOpen(() => {
				console.log('socket open');
			});
			socket.onMessage(({ data }) => {
				console.log('socket message', data);
				if (typeof data === 'string') data = JSON.parse(data);
				if (data.code == 0 && data.result) {
					if (data.result.voice_text_str) {
						console.log('识别成功：' + data.result.voice_text_str);
						this.content = data.result.voice_text_str;
					}
				} else if (data.code == 0) {
					this.status = 2;
					this.startRecorder();
				} else {
					this.loading(data.message);
				}
			});
			socket.onClose(e => {
				console.log('socket close');
				this.stopRecorder();
				this.socket = null;
			});
			socket.onError(e => {
				console.log('socket error', e);
				this.stopRecorder();
				this.socket = null;
			});
		},
		stopConnect: function() {
			if (this.socket) {
				this.socket.close();
			}
		},
		startRecorder: function() {
			if (this.recorder == null) {
				const recorder = (this.recorder = uni.getRecorderManager());
				recorder.onFrameRecorded(({ isLastFrame, frameBuffer }) => {
					if (this.socket) {
						this.socket.send({
							data: frameBuffer
						});
						if (isLastFrame) {
							this.socket.send({
								data: JSON.stringify({
									type: 'end'
								})
							});
						}
					}
				});
				recorder.onError(({ errMsg }) => {
					console.log('recorder error', errMsg);
					if (errMsg != "operateRecorder:fail:audio is stop, don't stop record again") {
						this.loading('启动失败：' + errMsg);
						this.stopConnect();
					}
				});
				recorder.onStart(() => {
					console.log('recorder start');
					//this.loading('正在识别');
					this.status = 3;
					this.startTimer();
				});
				recorder.onStop(({ tempFilePath }) => {
					console.log('recorder stop', tempFilePath);

					// #ifdef APP-PLUS
					if (this.uploadFile)
						this.uploadFile(tempFilePath)
							.then(res => {
								this.content = res;
								this.$emit('fileChange', { file: tempFilePath, content: res });
							})
							.catch(e => {
								console.log(e);
							});

					// #endif
					// #ifdef MP-WEIXIN
					this.$emit('fileChange', { file: tempFilePath, content: this.content });
					// #endif
				});
				recorder.onPause(e => {
					console.log('recorder pause');
				});
			}

			this.recorder.start({
				duration: 60 * 1000,
				format: 'mp3',
				frameSize: 1.25,
				sampleRate: 16000,
				numberOfChannels: 1
			});
		},
		stopRecorder: function() {
			this.stopTimer();

			if (this.status != 0) {
				this.status = 0;
			}

			if (this.recorder) {
				this.recorder.stop();
			}
		},
		loading(title) {
			uni.showToast({
				icon: 'none',
				title: title
			});
		}
	}
};
</script>

<style lang="scss">
.asr-container {
	height: calc(100vh - var(--window-top));
	width: 750rpx;
	position: fixed;
	bottom: 0;
}

.asr-playing {
	background: url(data:image/gif;base64,R0lGODlhDgAOAIABACWbJP///yH/C05FVFNDQVBFMi4wAwEAAAAh/wtYTVAgRGF0YVhNUDw/eHBhY2tldCBiZWdpbj0i77u/IiBpZD0iVzVNME1wQ2VoaUh6cmVTek5UY3prYzlkIj8+IDx4OnhtcG1ldGEgeG1sbnM6eD0iYWRvYmU6bnM6bWV0YS8iIHg6eG1wdGs9IkFkb2JlIFhNUCBDb3JlIDUuNS1jMDE0IDc5LjE1MTQ4MSwgMjAxMy8wMy8xMy0xMjowOToxNSAgICAgICAgIj4gPHJkZjpSREYgeG1sbnM6cmRmPSJodHRwOi8vd3d3LnczLm9yZy8xOTk5LzAyLzIyLXJkZi1zeW50YXgtbnMjIj4gPHJkZjpEZXNjcmlwdGlvbiByZGY6YWJvdXQ9IiIgeG1sbnM6eG1wPSJodHRwOi8vbnMuYWRvYmUuY29tL3hhcC8xLjAvIiB4bWxuczp4bXBNTT0iaHR0cDovL25zLmFkb2JlLmNvbS94YXAvMS4wL21tLyIgeG1sbnM6c3RSZWY9Imh0dHA6Ly9ucy5hZG9iZS5jb20veGFwLzEuMC9zVHlwZS9SZXNvdXJjZVJlZiMiIHhtcDpDcmVhdG9yVG9vbD0iQWRvYmUgUGhvdG9zaG9wIENDIChXaW5kb3dzKSIgeG1wTU06SW5zdGFuY2VJRD0ieG1wLmlpZDpFNjUzM0MxOTMxMEQxMUU2OEUwRkQ0NTk5RTVERjg2OCIgeG1wTU06RG9jdW1lbnRJRD0ieG1wLmRpZDpFNjUzM0MxQTMxMEQxMUU2OEUwRkQ0NTk5RTVERjg2OCI+IDx4bXBNTTpEZXJpdmVkRnJvbSBzdFJlZjppbnN0YW5jZUlEPSJ4bXAuaWlkOkU2NTMzQzE3MzEwRDExRTY4RTBGRDQ1OTlFNURGODY4IiBzdFJlZjpkb2N1bWVudElEPSJ4bXAuZGlkOkU2NTMzQzE4MzEwRDExRTY4RTBGRDQ1OTlFNURGODY4Ii8+IDwvcmRmOkRlc2NyaXB0aW9uPiA8L3JkZjpSREY+IDwveDp4bXBtZXRhPiA8P3hwYWNrZXQgZW5kPSJyIj8+Af/+/fz7+vn49/b19PPy8fDv7u3s6+rp6Ofm5eTj4uHg397d3Nva2djX1tXU09LR0M/OzczLysnIx8bFxMPCwcC/vr28u7q5uLe2tbSzsrGwr66trKuqqainpqWko6KhoJ+enZybmpmYl5aVlJOSkZCPjo2Mi4qJiIeGhYSDgoGAf359fHt6eXh3dnV0c3JxcG9ubWxramloZ2ZlZGNiYWBfXl1cW1pZWFdWVVRTUlFQT05NTEtKSUhHRkVEQ0JBQD8+PTw7Ojk4NzY1NDMyMTAvLi0sKyopKCcmJSQjIiEgHx4dHBsaGRgXFhUUExIREA8ODQwLCgkIBwYFBAMCAQAAIfkECSgAAQAsAAAAAA4ADgAAAh6Mj6mrAIwcPJLJuu6zDwesfZ0ziiZZhuiZkiyrtgUAIfkECSgAAQAsAAAAAA4ADgAAAh6Mj6nL7QjAiocqGyjO0ujugR8kSmN0mmrKcez3qgUAIfkEBSgAAQAsAAAAAA4ADgAAAh2Mj6nL7Q8VAHAua3CmWgcLTtz4jWGJiuSppitQAAA7)
		repeat-x;
	height: 60rpx;
	background-size: contain;
}

.startBtn {
	transition: all 0.3s;
	cursor: pointer;

	&:hover {
		filter: contrast(1.1);
	}

	&:active {
		filter: contrast(0.9);
	}

	&::before,
	&::after {
		content: '';
		position: absolute;
		top: -10px;
		left: -10px;
		right: -10px;
		bottom: -10px;
		border: 2px solid #007aff;
		transition: all 0.5s;
		animation: clippath 3s infinite linear;
		border-radius: 10px;
	}

	&::after {
		animation: clippath 3s infinite -1.5s linear;
	}
}

@keyframes clippath {
	0%,
	100% {
		clip-path: inset(0 0 98% 0);
	}

	25% {
		clip-path: inset(0 98% 0 0);
	}

	50% {
		clip-path: inset(98% 0 0 0);
	}

	75% {
		clip-path: inset(0 0 0 98%);
	}
}
</style>
