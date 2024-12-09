# LLM Web API

[![](https://img.shields.io/github/license/adryfish/llm-web-api.svg)](LICENSE)
![](https://img.shields.io/github/stars/adryfish/llm-web-api.svg)
![](https://img.shields.io/github/forks/adryfish/llm-web-api.svg)

[中文文档](README-ZH.md)

ChatGPT Web Page to API interface. 

## Features
  - Bypass `Cloudflare` challenge
  - Login mode: no-login or email
  - High-speed streaming output
  - Model switching
  - Dynamically display supported models

Compatible with the `ChatGPT` API.


## Usage

### Run with Docker

```shell
docker run --name llm-web-api --rm -it -p 5000:5000 adryfish/llm-web-api
```

### Docker compose

See detailed configuration below for environment variables.

```yml
services:
  llm-web-api:
    image: adryfish/llm-web-api
    container_name: llm-web-api
    ports:
      - "5000:5000"
    volumes:
      # Browser data. Configure if you want to retain browser login information.
      - ./data:/app/data
    environment:
      # PROXY_SERVER: ""          # Proxy server address
      # OPENAI_LOGIN_TYPE: ""     # Login Type,nologin or email
      # OPENAI_LOGIN_EMAIL: ""    # Login email
      # OPENAI_LOGIN_PASSWORD: "" # Login password
    restart: unless-stopped
```

### Environment

All environment variables are optional. 

| variable              | description                              | default  |
|-----------------------|------------------------------------------|--------|
| PROXY_SERVER          | Proxy server address	                   | None     |
| DATA_DIR              | Data storage directory	                 | ./browser_data   |
| OPENAI_LOGIN_TYPE     | ChatGPT login type, nologin or email     | nologin|
| OPENAI_LOGIN_EMAIL    | Email account for email login type	     | None     |
| OPENAI_LOGIN_PASSWORD | Password for email login type	           | None     |

## Principle

The system uses `Playwright` to control a fingerprint browser, simulating user operations to send requests to the OpenAI website and converting the responses into API interfaces.

## API

Currently supports the OpenAI-compatible /v1/chat/completions API, which can be accessed using OpenAI or other compatible clients.

### Chat completion

Chat completion API，compatible with Openai [chat-completions-api](https://platform.openai.com/docs/api-reference/chat)。

**POST /v1/chat/completions**

Request：
```json
{
    // If you are no-login user, use gpt-3.5-turbo or gpt-4o-mini 
    // If you are a free user, use gpt-3.5-turbo, gpt-4o-mini or gpt-4o 
    // If you are a subscribed user, use gpt-3.5-turbo, gpt-4o-mini, gpt-4o, or gpt-4 for the model name.
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
    }
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

## Disclaimer

This document outlines the terms and conditions under which the Project (hereinafter referred to as "the Project") is provided. By accessing or using the Project, you acknowledge that you have read, understood, and agreed to the terms of this disclaimer.

1. **No Warranties**  
   The Project is provided "as is" without any warranties, express or implied, including but not limited to warranties of merchantability, fitness for a particular purpose, legality, or non-infringement. We do not guarantee the Project's reliability, accuracy, or suitability for any specific purpose.

2. **Limitation of Liability**  
   Under no circumstances shall the developer or contributors of the Project be held liable for any direct, indirect, incidental, consequential, or special damages arising from or related to the use or inability to use the Project. This includes, but is not limited to, loss of data, revenue, or business opportunities.

3. **User Responsibility**  
   Users are solely responsible for ensuring their compliance with all applicable laws and regulations when using the Project. Any misuse, unauthorized actions, or illegal activities conducted with or through the Project are entirely at the user's own risk and responsibility.

4. **Third-Party Content**  
   The Project may contain links to or resources from third-party websites or services. These are provided for convenience only, and we make no representations or warranties regarding their content, accuracy, or functionality. We disclaim any liability for any issues arising from the use of such third-party content.

5. **Acceptance of Terms**  
   By continuing to use the Project, you agree to the terms outlined in this disclaimer. If you do not agree with any part of this disclaimer, you must immediately discontinue the use of the Project.

6. **Modifications to the Disclaimer**  
   We reserve the right to modify or update this disclaimer at any time without prior notice. It is the user's responsibility to review the disclaimer periodically for any changes.

If you have any concerns or questions regarding this disclaimer, please contact us before using the Project.


## Similar Projects
  - chat2api: https://github.com/lanqian528/chat2api

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=adryfish/llm-web-api&type=Date)](https://star-history.com/#adryfish/llm-web-api&Date)