# 微信公众号文章 HTML 结构参考

## 链接格式

### 短链接（推荐）
```
https://mp.weixin.qq.com/s/xxxxxxxxxxxxx
```
可直接访问，不容易触发验证码。

### 长链接
```
https://mp.weixin.qq.com/s?__biz=xxx&mid=xxx&idx=xxx&sn=xxx
```
可能触发验证码/访问验证。

## 关键 HTML 元素

### 元数据（`<head>` 中）
```html
<meta property="og:title" content="文章标题" />
<meta property="og:article:author" content="作者名称" />
<meta property="og:description" content="文章摘要..." />
<meta property="og:url" content="https://mp.weixin.qq.com/s/..." />
<meta property="og:image" content="https://mmbiz.qpic.cn/..." />
<meta property="weixin:account" content="公众号ID" />
```

### 正文区域
文章正文位于：
```html
<div id="js_content" class="rich_media_content">
  <!-- 文章内容 -->
</div>
```
备用选择器：`<div class="rich_media_content">`

### 图片
微信图片使用 `data-src` 而非 `src`：
```html
<img data-src="https://mmbiz.qpic.cn/..." data-type="jpeg" data-w="1080" />
```
图片 CDN 域名：`mmbiz.qpic.cn` 或 `mmbiz.qlogo.cn`

格式参数：`wx_fmt=png|gif|jpeg|jpg`

### Script 变量
`<script>` 标签中嵌入的关键元数据：
```javascript
var msg_title = "文章标题";
var msg_author = "作者";
var create_time = "1234567890";
var nickname = "公众号名称";
var __biz = "base64编码的biz_id";
var mid = "123456";
var idx = "1";
var sn = "哈希字符串";
```

## 常见问题

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| 验证码页面 | 反爬检测 | 使用短链接格式 |
| 正文区域为空 | JS渲染内容 | 使用移动端 User-Agent |
| `环境异常` 页面 | IP/UA 被拦截 | 重试或使用 Cookie |
| 图片缺失 | 防盗链保护 | 设置 `Referer: https://mp.weixin.qq.com/` |
| `data-src` 为空 | 懒加载机制 | 优先检查 `data-src` 再检查 `src` 属性 |

## 必需的 HTTP 请求头

```
User-Agent: Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.42(0x18002a2a) NetType/WIFI Language/zh_CN
Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8
Accept-Language: zh-CN,zh;q=0.9,en;q=0.8
Referer: https://mp.weixin.qq.com/
```

使用微信移动端 User-Agent 是绕过访问限制的关键。
