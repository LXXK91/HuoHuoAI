## 腾讯小程序实时语音识别， app使用语音文件识别

## [官方文档](https://cloud.tencent.com/document/product/1093/48982)
  

* 微信小程序： 支持实时音频识别
* App：录音后通过后台Api进行语音文件识别。

为省事样式直接使用的color ui 的样式 ， 适合引入了ColorUi的项目使用。


```vue
<template>
	<view>
		<button @click="open">打开</button>
		<lyuan-tx-asr
			ref="asr"
			:uploadMethod="uploadFile" 
			@change="asrChange"		
				@fileChange="fileChange"
			appId=""
			secretId=""
			secretKey=""
		></lyuan-tx-asr>
	</view>
</template>

<script>
export default {
	data() {
		return {};
	},

	methods: {
		open: function() {
			this.$refs.asr.show();
		},
		asrChange: function(res) {
			console.log('语音识别确认结果：' + res);
		},
		fileChange: function({file,content}) {
			console.log('录音文件', file);
		},
		uploadFile: function(tempFilePath) {
			return new Promise((resolve, reject) => {
				//调用你的接口把音频文件转为文字
				this.$minApi
					.upload('txasr/SentenceRecognition', null, tempFilePath)
					.then(res => {
						if (res.code == 1) {
							resolve(res.data.Result);
						} else {
							reject(e);
						}
					})
					.catch(e => {
						reject(e);
					});
			});
		}
	}
};
</script>

<style lang="scss"></style>


```


.net core 使用腾讯sdk语音转文字参考
```csharp
 using (var ms = new MemoryStream())
{
    var file = Request.Form.Files[0];
    file.CopyTo(ms);
    var bytes = ms.ToArray();
    Credential cred = new Credential
    {
        SecretId = "",
        SecretKey = ""
    };
    ClientProfile clientProfile = new ClientProfile();
    HttpProfile httpProfile = new HttpProfile {Endpoint = ("asr.tencentcloudapi.com")};
    clientProfile.HttpProfile = httpProfile;
    AsrClient client = new AsrClient(cred, "", clientProfile);
    SentenceRecognitionRequest req = new SentenceRecognitionRequest();
    req.ProjectId = 0;
    req.SubServiceType = 2;
    req.EngSerViceType = "16k_zh";
    req.SourceType = 1;
    req.VoiceFormat = "mp3";
    req.UsrAudioKey = Guid.NewGuid().ToString();
    req.Data = Convert.ToBase64String(bytes);
    req.DataLen = bytes.Length;
    SentenceRecognitionResponse resp = client.SentenceRecognitionSync(req);
    return resp;
}
```