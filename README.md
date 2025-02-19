# LLM Web API

[![](https://img.shields.io/github/license/adryfish/llm-web-api.svg)](LICENSE)
![](https://img.shields.io/github/stars/adryfish/llm-web-api.svg)
![](https://img.shields.io/github/forks/adryfish/llm-web-api.svg)

[中文文档](README-ZH.md)

ChatGPT Web Page to API interface. 

## Features
  - Bypass `Cloudflare` challenge
  - Login mode: no-login, email, google login
  - High-speed streaming output
  - Model switching, Dynamically display supported models
  - Conversation support
  - TTS support

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
      # OPENAI_LOGIN_TYPE: ""     # Login Type,nologin or email or google
      # OPENAI_LOGIN_EMAIL: ""    # Login email
      # OPENAI_LOGIN_PASSWORD: "" # Login password
    restart: unless-stopped
```

### Environment

All environment variables are optional. 

| Variable              | Description                              | Default  |
|-----------------------|------------------------------------------|--------|
| PROXY_SERVER          | Proxy server address	                   | None     |
| DATA_DIR              | Data storage directory	                 | ./data   |
| OPENAI_LOGIN_TYPE     | ChatGPT login type: `nologin`, `email`, `google`  | nologin |
| OPENAI_LOGIN_EMAIL    | Email account for email login           | None     |
| OPENAI_LOGIN_PASSWORD | Password for email login                | None     |
| OPENAI_LOGIN_APP_PASSWORD | App password for email verification  | None     |
| GOOGLE_LOGIN_EMAIL    | Google login email                      | None     |
| GOOGLE_LOGIN_PASSWORD | Google login password                   | None     |
| GOOGLE_LOGIN_OTP_SECRET | Google login 2FA secret               | None     |
| GOOGLE_LOGIN_RECOVERY_EMAIL | Google login recovery email       | None     |


## How it works

The system uses `Playwright` to control a fingerprint browser, simulating user operations to send requests to the OpenAI website and converting the responses into API interfaces.

## API

Currently supports the OpenAI-compatible /v1/chat/completions API, which can be accessed using OpenAI or other compatible clients.

### Chat completion

Chat completion API，compatible with OpenAI [Chat Completions API](https://platform.openai.com/docs/api-reference/chat)。

**POST /v1/chat/completions**

**Request：**
```jsonc
{
    "model": "gpt-4o",
    "messages": [
        {
            "role": "user",
            "content": "Hello"
        }
    ],
    // Optional: If using SSE stream, set to true, default is false
    "stream": false
    // Optional: If enabled, the response will include meta information(message_id and conversation id)
    // If both parent_message_id and conversation_id are provided, the request will continue within the existing conversation context.
    // If they are not set, the request will be treated as a new conversation.
    // "meta": {
    //   "enable": true,
    //   "parent_message_id": "5363437e-b364-4b72-b3d6-415deeed11ab", # Optional
    //   "conversation_id": "6774f183-f70c-800b-9965-6c110d3a3485"    # Optional 
    // }
}
```

**Response：**
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
    "meta": {
        "message_id": "dffd63ef-63ac-4d40-b6de-e33ec40de9e2",
        "conversation_id": "6774f183-f70c-800b-9965-6c110d3a3485"
    }
}
```

### Audio Create Speech

Audio Speech API, compatible with OpenAI's [Audio Speech API](https://platform.openai.com/docs/api-reference/audio). It allows users to generate speech from text input.

**POST /v1/audio/speech**

**Request:**
```jsonc
{
    "input": "Hello, how are you?",
    "voice": "cove"
    "model": "tts-1",
    // Optional: specify response format, default is "aac"
    "response_format": "mp3",
}
```

**Response:**

If successful, the API returns an audio file in the requested format.


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

## Similar Projects
  - chat2api: https://github.com/lanqian528/chat2api

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=adryfish/llm-web-api&type=Date)](https://star-history.com/#adryfish/llm-web-api&Date)