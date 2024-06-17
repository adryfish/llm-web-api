## v1.1.2

`2024-06-17`

## Feature
  - Debug增强: 多打印debug日志，出错自动截图保存

## Enhancement
  - 更新Dockerfile

## v1.1.0

`2024-06-16`

## Feature
  - 支持监听Websocket
  - 使用Javascript Fetch API发送conversation请求
  - 动态显示支持模型。(解释: 免费用户如果gpt-4o额度使用完，再发送gpt-4o请求则报不支持的模型错误，限制到期后可再发送)

## Removed
  - httpx发送conversation请求(python库请求可能会被指纹识别)

## v1.0.5

`2024-06-04`

## Enhancement
  - 更新Dockerfile

## Feature
  - 多轮对话


## v1.0.4

`2024-06-03`

## Enhancement
  - 登录增强: 某些客户端打开首页后会弹出一个登录的dialog


## v1.0.3

`2024-05-27`

## Feature
  - Docker compose支持
  - 支持多种聊天服务

## BugFix
  - 修复消息结尾错误
  - 修复HEADLESS不存在程序报错


## v1.0.2

`2024-05-26`

## Enhancement
  - Cloudflare bypass异常处理
  - 登录账户和未登录账户用不同的conversation url请求

## BugFix
  - HEADLESS默认值应为False


## v1.0.1

`2024-05-25`

## Enhancement
  - 优化create_conversation和change_model逻辑
  - 使用锁避免并发问题
  - Playwright移除stealth脚本

## BugFix
  - 2024-04-25发现,访问chatgpt.com首页后会直接进入登录页面,OpenAILogin兼容这种情况

## Feature
  - 新增Docker支持
  - 新增无GUI Linux支持


## v1.0.0

`2024-05-21`

## Feature
  - 支持Cloudflare 5s盾破解
  - 支持免登录使用(支持gpt3.5模型)
  - 支持邮箱自动登录(支持gpt3.5, gpt-4o, gpt-4模型)
  - 支持登录失效后自动重新登录
  - 支持高速流式输出
  - 支持模型切换
