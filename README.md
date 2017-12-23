# PandaTvDanmaku

爬取熊猫tv直播间弹幕消息。

## 使用方法

1. 安装Python依赖模块：`PyExecJS` `requests` `websocket-client` （均可用pip安装）
2. 安装Node.js依赖模块：`Pako` `bytebuffer`

### 直接运行

```
py danmaku.py <room_id>
```

通过`Ctrl`+`C` 终止运行。

### 作为模块导入

```python
import PandaTvDanmaku

# 初始化对象
room_id = 56666
danmaku = PandaTvDanmaku(room_id)

# 获取弹幕信息
while True:
  if len(buf) > 0:
  	msg = buf.pop(0)
  	print('@%s: %s' % (msg['data']['from']['nickName'], msg['data']['content']))

# 终止连接
danmaku.stop()
```

## 弹幕格式

```json
{
  "type": "1",
  "time": 1514007624,
  "data": {
    "from": {
      "identity": "30",
      "nickName": "就是来随便看一看",
      "badge": "",
      "rid": "101260884",
      "medal": {
                "level": 4,
                "medal": "苜宝宝",
                "active": 1,
                "type": 4
               },
      "group": {
                "groupid": 101320,
                "sp_name": "河科大"
               },
      "msgcolor": "",
      "level": "6",
      "sp_identity": "30",
      "__plat": "",
      "userName": ""
    },
    "to": {
      "toroom": "404055"
    },
    "content": "上把也是这个圈"
  }
}
```

## 说明

1. 接收并解压所有类型的弹幕消息(结果在函数`_on_message` 的变量`danmaku_str`中)，但仅提取普通的聊天弹幕（type=1），有需要解析其他弹幕消息的请对该变量进行处理。
2. 通过Wireshark和Fiddler抓包容易分析出通过GET请求获取弹幕服务器地址的过程，但在和弹幕服务器建立WebSocket连接以后，由于送至服务器的数据和传回的弹幕消息均为二进制码，故难直接通过抓包分析通讯过程。此时可打开任意直播页面，找到主页面引用的JS文件，搜索关键字'websocket'可以找到建立连接、发心跳包、解压弹幕消息的过程（在同一个类中）。
3. 目前解压消息的过程未能用Python语言复原，故使用`PyExecJS` 执行JS函数，由于bytes无法直接传入，故需解码为字符串再传入，因为bytes经过了zlib压缩故不能使用utf-8解码，具体过程参见源码。
4. 由于直播平台本身会不断更新客户端和服务器的交互方式，故爬取弹幕的方式也应该随之变化，此项目在你发现时可能已失时效，但希望上述说明能对你有所帮助。



