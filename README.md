# LLM Web API

[![](https://img.shields.io/github/license/adryfish/llm-web-api.svg)](LICENSE)
![](https://img.shields.io/github/stars/adryfish/llm-web-api.svg)
![](https://img.shields.io/github/forks/adryfish/llm-web-api.svg)

[中文文档](README-ZH.md)

ChatGPT Web Page to API interface. 

## Features
  - Bypass `Cloudflare` challenge
  - Use without login (supports gpt3.5 model)
  - Auto-login with email account (supports gpt3.5, gpt-4o, gpt-4 models)
  - Auto re-login after session expiration
  - High-speed streaming output
  - Model switching
  - Multi-turn conversations
  - Dynamically display supported models
  - Support for both event-stream and websocket responses

Compatible with the `ChatGPT` API.


## Usage

### Docker
#### Run with Docker

```shell
docker run --name llm-web-api --rm -it -p 5000:5000 adryfish/llm-web-api
```

#### Docker compose

See detailed configuration below for environment variables.

```yml
version: '3.8'
services:
  llm-web-api:
    image: adryfish/llm-web-api
    container_name: llm-web-api
    ports:
      - "5000:5000"
    volumes:
      # Browser data. Configure if you want to retain browser login information.
      - ./browser_data:/app/browser_data
    environment:
      # PROXY_SERVER: ""          # Proxy server address
      # USER_AGENT: ""            # Browser User-Agent
      # OPENAI_LOGIN_TYPE: ""     # Login Type,nologin or email
      # OPENAI_LOGIN_EMAIL: ""    # Login email
      # OPENAI_LOGIN_PASSWORD: "" # Login password
    restart: unless-stopped
```

### Local
#### Create and activate python venv

```shell   
cd llm-web-api

# create python venv
# Note: Python version must be above 3.10
python -m venv venv

# macos & linux activate virtual environment
source venv/bin/activate

# windows activate virtual environment
venv\Scripts\activate
```

#### Install dependencies

```shell
pip3 install -r requirements.txt
```

#### Install Chrome web browser

```shell
# Currently only supports Chrome browser
playwright install chrome
```

#### Install xvfb (Optional)
```shell
# For no GUI Linux, install xvfb
sudo apt-get install xvfb
```

#### Set environment variables

```shell
# Set environment variables as needed
cp .env.example .env
```

#### Start FastAPI server

```shell
python main.py
```

### Environment

| variable              | description                              | default  |
|-----------------------|------------------------------------------|--------|
| PROXY_SERVER          | Proxy server address	                   | None     |
| USER_AGENT            | User-Agent                               | Browser default     |
| BROWSER_DATA          | Browser data storage directory	       | ./browser_data   |
| OPENAI_LOGIN_TYPE     | ChatGPT login type, nologin or email     | nologin|
| OPENAI_LOGIN_EMAIL    | Email account for email login type	   | None     |
| OPENAI_LOGIN_PASSWORD | Password for email login type	           | None     |


## API

Currently supports the OpenAI-compatible /v1/chat/completions API, which can be accessed using OpenAI or other compatible clients.

### Chat completion

Chat completion API，compatible with Openai [chat-completions-api](https://platform.openai.com/docs/guides/text-generation/chat-completions-api)。

**POST /v1/chat/completions**

Request：
```json
{
    // If you are no-login user, use gpt-3.5-turbo for the model name.
    // If you are a free user, use gpt-3.5-turbo or gpt-4o for the model name.
    // If you are a subscribed user, use gpt-3.5-turbo, gpt-4o, or gpt-4 for the model name.
    "model": "gpt-4o",
    "messages": [
        {
            "role": "user",
            "content": "Hello"
        }
    ],
    // If using SSE stream, set to true, default is false
    "stream": false
}
```

Response：
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

## Examples
### Using OpenAI Official Library
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

## Notes

### Nginx config

If you are using Nginx as a reverse proxy for llm-web-api, add the following configuration to optimize the streaming output and improve the user experience.

```nginx
# Disable proxy buffering. When set to off, Nginx sends client requests to the backend server immediately and sends responses back to the client immediately.
proxy_buffering off;

# Enable chunked transfer encoding. This allows the server to send data in chunks for dynamically generated content without knowing the size of the content in advance.
chunked_transfer_encoding on;

# Enable TCP_NOPUSH, which tells Nginx to send data as efficiently as possible before sending data packets to the client. This is often used with sendfile to improve network efficiency.
tcp_nopush on;

# Enable TCP_NODELAY, which tells Nginx not to delay sending data and to send small data packets immediately. In some cases, this can reduce network latency.
tcp_nodelay on;

# Set the keepalive timeout, here set to 120 seconds. If there is no further communication between the client and the server within this period, the connection will be closed.
keepalive_timeout 120;
```

### Token
Since inference is not performed on the llm-web-api side, token statistics will be returned as fixed number!!!!!

## Buy Me a Coffee
If this project is helpful to you, why not buy the author a cup of coffee 
![wechat.jpg](static/image/wechat.jpg)

## Disclaimer

**This project is for learning and research purposes only and is not intended for commercial use. You should be aware that using this project may violate related user agreements and understand the associated risks. We are not responsible for any losses resulting from the use of this project.**

## Reference
  - MediaCrawler: https://github.com/NanmiCoder/MediaCrawler
  - Bypass Cloudflare: https://github.com/sarperavci/CloudflareBypassForScraping
  - ChatGPT Reverse Engine: https://github.com/PawanOsman/ChatGPT

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=adryfish/llm-web-api&type=Date)](https://star-history.com/#adryfish/llm-web-api&Date)