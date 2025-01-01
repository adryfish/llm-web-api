# LLM Web API

[![](https://img.shields.io/github/license/adryfish/llm-web-api.svg)](LICENSE)
![](https://img.shields.io/github/stars/adryfish/llm-web-api.svg)
![](https://img.shields.io/github/forks/adryfish/llm-web-api.svg)

使用`Playwright`将网页版ChatGPT转换成`API`接口

## 功能列表
 - 通过`Cloudflare`验证破解
 - 登录模式支持免登录,邮箱登录和Google登录
 - 高速流式输出
 - 模型切换,动态显示支持模型
 - 对话支持

与ChatGPT接口完全兼容。

## 使用方法

### 使用Docker运行

```shell
docker run --name llm-web-api --rm -it -p 5000:5000 adryfish/llm-web-api
```

### 使用Docker compose

详细配置见下方环境变量

```yml
services:
  llm-web-api:
    image: adryfish/llm-web-api
    container_name: llm-web-api
    ports:
      - "5000:5000"
    volumes:
      # 浏览器数据，如何要保留浏览器登录信息，需要配置
      - ./data:/app/data
    environment:
      # PROXY_SERVER: ""          # 代理服务器地址
      # OPENAI_LOGIN_TYPE: ""     # 登录类型,nologin or email
      # OPENAI_LOGIN_EMAIL: ""    # 登录邮箱
      # OPENAI_LOGIN_PASSWORD: "" # 登录密码
    restart: unless-stopped
```

### 环境变量

所有的环境变量均为可选。

| 变量名                 | 描述                                    | 默认值  |
|-----------------------|----------------------------------------|--------|
| PROXY_SERVER          | 代理服务器地址                            | None     |
| DATA_DIR              | 数据存放目录                         | 当前目录/data   |
| OPENAI_LOGIN_TYPE     | ChatGPT 的登录类型, nologin, email, google    | nologin|
| OPENAI_LOGIN_EMAIL    | 对于 email 登录方式，提供 email 帐号        | None     |
| OPENAI_LOGIN_PASSWORD | 对于 email 登录方式，提供密码               | None     |
| GOOGLE_LOGIN_EMAIL    | google登录邮箱 | None      |
| GOOGLE_LOGIN_PASSWORD    | google登录邮箱密码 | None      |
| GOOGLE_LOGIN_OTP_SECRET    | google登录二次认证secret  | None      |
| GOOGLE_LOGIN_RECOVERY_EMAIL    | google登录恢复邮箱  | None      |
| ENABLE_REQUEST_METADATA       | 请求支持meta数据                         | False   |


## 原理
使用`Playwright`控制指纹浏览器，模拟用户操作，发送请求到OpenAI网页， 将响应转换成API接口。

## 接口列表

目前支持与openai兼容的 `/v1/chat/completions` 接口，可自行使用与openai或其他兼容的客户端接入接口

### 对话补全

对话补全接口，与openai的 [chat-completions-api](https://platform.openai.com/docs/api-reference/chat) 兼容。

**POST /v1/chat/completions**

请求数据：
```jsonc
{
    "model": "gpt-4o",
    "messages": [
        {
            "role": "user",
            "content": "Hello"
        }
    ],
    // 可选: 如果使用SSE流请设置为true，默认false
    "stream": false
    // 可选,需要设置ENABLE_REQUEST_METADATA=True
    // 对话上下文信息
    // "meta": {
    //   "parent_message_id": "5363437e-b364-4b72-b3d6-415deeed11ab",
    //   "conversation_id": "6774f183-f70c-800b-9965-6c110d3a3485"
    // }
}
```

响应数据：
```jsonc
{
    "id": "chatcmpl-fZc6l869OzRu8rp7X8Dhj0COfTsR6",
    "object": "chat.completion",
    "created": 1733726226,
    "model": "gpt-4o",
    "choices": [
        {
            "index": 0,
            "message": {
                "role": "assistant",
                "content": "Hi there! How can I assist you today? 😊"
            },
            "logprobs": null,
            "finish_reason": "stop"
        }
    ],
    "usage": {
        "prompt_tokens": 1,
        "completion_tokens": 11,
        "total_tokens": 12
    },
    // 如何没有设置ENABLE_REQUEST_METADATA=True，则不会有meta数据返回
    "meta": {
        "message_id": "dffd63ef-63ac-4d40-b6de-e33ec40de9e2",
        "conversation_id": "6774f183-f70c-800b-9965-6c110d3a3485"
    }
}
```

## 用例
### 使用Python OpenAI官方库
#### Python
```python
import openai

openai.api_key = 'anything'
openai.base_url = "http://localhost:5000/v1/"

completion = openai.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "user", "content": "Hello"},
    ],
)

print(completion.choices[0].message.content)
```

#### Node.js

```javascript
import OpenAI from 'openai';

const openai = new OpenAI({
	apiKey: "anything",
	baseURL: "http://localhost:5000/v1/",
});

const chatCompletion = await openai.chat.completions.create({
  messages: [{ role: 'user', content: 'Echo Hello' }],
  model: 'gpt-4o-mini',
});

console.log(chatCompletion.choices[0].message.content);
```



## 免责声明

本项目（以下简称“项目”）为公开分享的工具，旨在为用户提供便利和功能支持。使用本项目的所有风险由用户自行承担。

1. 本项目由开发者个人维护，不提供任何形式的保证，包括但不限于适销性、特定用途适用性、合法性或非侵权性的保证。

2. 使用本项目过程中产生的任何直接或间接后果，包括但不限于数据丢失、财产损失、业务中断或其他损害，开发者概不负责。

3. 用户应在遵守适用法律法规的前提下使用本项目，因用户不当使用或非法使用导致的后果与开发者无关。

4. 本项目中的内容可能包含第三方资源或链接，开发者对其内容的准确性、可靠性或合法性不作任何保证，也不对其造成的任何后果负责。

5. 用户在使用本项目的同时，视为已完全理解并接受上述声明内容。

若有任何疑问，请勿使用本项目。


## 同类项目 
  - chat2api: https://github.com/lanqian528/chat2api

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=adryfish/llm-web-api&type=Date)](https://star-history.com/#adryfish/llm-web-api&Date)
