## v1.0.2

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
