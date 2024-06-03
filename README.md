# LLM Web API

[![](https://img.shields.io/github/license/adryfish/llm-web-api.svg)](LICENSE)
![](https://img.shields.io/github/stars/adryfish/llm-web-api.svg)
![](https://img.shields.io/github/forks/adryfish/llm-web-api.svg)

使用`Playwright`将网页版ChatGPT转换成`FastAPI`接口

## 功能列表
 - Cloudflare 5s盾破解
 - 免登录使用(支持gpt3.5模型)
 - 邮箱帐号自动登录(支持gpt3.5, gpt-4o, gpt-4模型)
 - 登录失效后自动重新登录
 - 高速流式输出
 - 模型切换
 - 多轮对话

与ChatGPT接口完全兼容。

## 原理
利用[DrissionPage](https://github.com/g1879/DrissionPage)模拟浏览器登录破解cloudflare 5s盾，成功后将cookie注入[Playwright](https://playwright.dev/)控制的浏览器中。通过模拟用户操作获取请求参数，使用httpx发送获取流式请求响应。
通过使用此方式，免去了复现核心加密JS代码，逆向难度大大降低。

## 使用方法

### 使用Docker
#### 使用Docker运行

```shell
docker run --name llm-web-api --rm -it 5000:5000 adryfish/llm-web-api
```

#### 使用Docker compose

详细配置见下方环境变量

```yml
version: '3.8'
services:
  llm-web-api:
    image: adryfish/llm-web-api
    container_name: llm-web-api
    ports:
      - "5000:5000"
    volumes:
      # 浏览器数据，如何要保留浏览器登录信息，需要配置
      - ./browser_data:/app/browser_data
    environment:
      # PROXY_SERVER: ""          # 代理服务器地址
      # USER_AGENT: ""            # 浏览器User-Agent
      # OPENAI_LOGIN_TYPE: ""     # 登录类型,nologin or email
      # OPENAI_LOGIN_EMAIL: ""    # 登录邮箱
      # OPENAI_LOGIN_PASSWORD: "" # 登录密码
    restart: unless-stopped
```

### 本地安装
#### 创建并激活 python 虚拟环境

```shell   
# 进入项目根目录
cd llm-web-api

# 创建虚拟环境
# 注意python 版本需要3.10以上
python -m venv venv

# macos & linux 激活虚拟环境
source venv/bin/activate

# windows 激活虚拟环境
venv\Scripts\activate
```

#### 安装依赖库

```shell
pip3 install -r requirements.txt
```

#### 安装 playwright浏览器驱动

```shell
# 暂时只支持Chrome浏览器
playwright install chrome
```

#### 安装xvfb(可选)
```shell
# 对于无图形界面的Linux，需要安装xvfb
sudo apt-get install xvfb
```

#### 设置环境变量

```shell
# 根据需求设置环境变量
cp .env.example .env
```

#### 启动FastAPI服务器
```shell
python main.py
```

### 环境变量

| 变量名             | 描述                                       | 默认值  |
|---------------------|--------------------------------------------|--------|
| PROXY_SERVER        | 代理服务器地址                             | None     |
| HEADLESS            | 是否使用无头模式(不推荐开启)               | False   |
| USER_AGENT          | 浏览器的 User-Agent                        | 浏览器默认     |
| BROWSER_DATA            | 浏览器数据存放目录               | 当前目录/browser_data   |
| OPENAI_LOGIN_TYPE   | ChatGPT 的登录类型, nologin 或者 email    | nologin|
| OPENAI_LOGIN_EMAIL  | 对于 email 登录方式，提供 email 帐号       | None     |
| OPENAI_LOGIN_PASSWORD | 对于 email 登录方式，提供密码            | None     |


## 接口列表

目前支持与openai兼容的 `/v1/chat/completions` 接口，可自行使用与openai或其他兼容的客户端接入接口

### 对话补全

对话补全接口，与openai的 [chat-completions-api](https://platform.openai.com/docs/guides/text-generation/chat-completions-api) 兼容。

**POST /v1/chat/completions**

请求数据：
```json
{
    // 如何你是免费或者未登录用户，模型是gpt-3.5-turbo
    // 如果你是订阅用户,模型名称填写gpt-4o, gpt-4, gpt-3.5-turbo
    "model": "gpt-4o",
    "messages": [
        {
            "role": "user",
            "content": "Hello"
        }
    ],
    // 如果使用SSE流请设置为true，默认false
    "stream": false
}
```

响应数据：
```json
{
    "id": "chatcmpl-ZklDQbSRpTI5gzb8zzctb6fB3YDW",
    "model": "gpt-4o",
    "object": "chat.completion",
    "choices": [
        {
            "message": {
                "role": "assistant",
                "content": "Hi there! How can I assist you today?"
            },
            "index": 0,
            "finish_reason": "stop"
        }
    ],
    "usage": {
        "prompt_tokens": 1,
        "completion_tokens": 1,
        "total_tokens": 2
    },
    "created": 1716305953
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
    model="gpt-3.5-turbo",
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
  model: 'gpt-3.5-turbo',
});

console.log(chatCompletion.choices[0].message.content);
```

## 注意事项

### Nginx反代优化

如果您正在使用Nginx反向代理llm-web-api，请添加以下配置项优化流的输出效果，优化体验感。

```nginx
# 关闭代理缓冲。当设置为off时，Nginx会立即将客户端请求发送到后端服务器，并立即将从后端服务器接收到的响应发送回客户端。
proxy_buffering off;
# 启用分块传输编码。分块传输编码允许服务器为动态生成的内容分块发送数据，而不需要预先知道内容的大小。
chunked_transfer_encoding on;
# 开启TCP_NOPUSH，这告诉Nginx在数据包发送到客户端之前，尽可能地发送数据。这通常在sendfile使用时配合使用，可以提高网络效率。
tcp_nopush on;
# 开启TCP_NODELAY，这告诉Nginx不延迟发送数据，立即发送小数据包。在某些情况下，这可以减少网络的延迟。
tcp_nodelay on;
# 设置保持连接的超时时间，这里设置为120秒。如果在这段时间内，客户端和服务器之间没有进一步的通信，连接将被关闭。
keepalive_timeout 120;
```

### Token统计
由于推理侧不在llm-web-api，因此token不可统计，将以固定数字返回!!!!!

## 打赏
免费开源不易，如果项目帮到你了，可以给我打赏哦，您的支持就是我最大的动力！
<div style="display: flex;justify-content: space-between;width: 100%">
    <p><img alt="打赏-微信" src="static/images/wechat_pay.jpg" style="width: 200px;height: 100%" ></p>
    <p><img alt="打赏-支付宝" src="static/images/alipay.jpg"   style="width: 200px;height: 100%" ></p>
</div>

## 参考
  - 社媒爬虫 [MediaCrawler](https://github.com/NanmiCoder/MediaCrawler)
  - cloudflare破解 [CloudflareBypassForScraping](CloudflareBypassForScraping)
  - ChatGPT逆向接口服务 [ChatGPT](https://github.com/PawanOsman/ChatGPT)

## 免责声明

**网页API是不稳定的，建议前往官方 https://openai.com/ 付费使用API，避免封禁的风险。**

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=adryfish/llm-web-api&type=Date)](https://star-history.com/#adryfish/llm-web-api&Date)
