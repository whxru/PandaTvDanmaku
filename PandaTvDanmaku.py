# -*- coding: UTF-8 -*-

import requests
import logging
import websocket
import time
import math
import json
import execjs
import argparse
import binascii
from threading import Thread


class PandaTvDanmaku:
    """爬取熊猫TV直播间的弹幕

    接收所有类型的弹幕消息(在变量danmaku_str中)，但仅提取普通的聊天弹幕（type=1）放到buffer中.
    普通的弹幕格式如下:


    Attributes:
        __room_id: 房间号.
        __data: 房间信息（包括弹幕服务器地址）.
        __ws: WebSocket对象.
        __done: 状态标志.
        __buffer: 存放包含弹幕信息的JSON对象的缓冲区.
    """
    def __init__(self, room_id):
        self.__room_id = room_id
        self.__data = None
        self.__ws = None
        self.__done = False
        self.__buffer = []
        Thread(target=self.__init_connection, name='Danmaku').start()

    def get_buffer(self):
        """获取buffer"""
        return self.__buffer

    def stop(self):
        """关闭连接"""
        self.__done = True
        self.__ws.close()

    def __init_connection(self,):
        """建立和弹幕服务器的连接"""

        # 获取弹幕服务器地址
        room_id = self.__room_id
        req = requests.get('https://riven.panda.tv/chatroom/getinfo', {
            'roomid': room_id,
            'app': 1,
            'protocol': 'ws',
            '_caller': 'panda-pc_web',
            '_': math.floor(time.time())
        }, verify=False)
        response = json.loads(req.text)
        self.__data = response['data']

        # 初始化WebSocket连接
        # ws_url = list(filter(lambda i: '8080' in i, response['data']['chat_addr_list']))[0]
        ws_url = response['data']['chat_addr_list'][0]
        websocket.enableTrace(True)
        ws = websocket.WebSocketApp('wss://' + ws_url)
        ws.on_open = self.__maintain_ws
        ws.on_message = self._on_message
        self.__ws = ws
        ws.run_forever(origin='https://www.panda.tv')

    def __maintain_ws(self, ws):
        """通过心跳包维持和弹幕服务器的WebSocket连接"""

        # 心跳初始化
        user_msg = 'u:{}@{}\n' \
                   'ts:{}\n' \
                   'sign:{}\n' \
                   'authtype:{}\n' \
                   'plat:jssdk_pc_web\n' \
                   'version:0.5.9\n' \
                   'pdft:\n' \
                   'network:unknown\n' \
                   'compress:zlib'.format(self.__data['rid'], self.__data['appid'], self.__data['ts'],
                                          self.__data['sign'], self.__data['authType'])
        header = bytes.fromhex('00060002') + len(user_msg).to_bytes(2, byteorder='big')
        content = bytes(user_msg, encoding='utf-8')
        self.__ws.send(header+content, opcode=websocket.ABNF.OPCODE_BINARY)

        # 定时发送心跳包
        heartbeats = Thread(target=self._heartbeats, name="Send-Heartbeats")
        heartbeats.start()

    def _heartbeats(self):
        """定时向弹幕服务器发送心跳包"""

        while not self.__done:
            time.sleep(30)
            heartbeat = bytes.fromhex("00060000")
            self.__ws.send(heartbeat, opcode=websocket.ABNF.OPCODE_BINARY)

    def _on_message(self, ws, message):
        """处理弹幕服务器送来的数据"""

        if len(message) < 5:
            return

        op = int.from_bytes(message[2:4], byteorder='big')
        if op == 3:
            # 从压缩后的JS代码中提取出的解压字节流的过程
            parse_msg = execjs.compile(
                """
                function parseMsg(msg) {
                    const ByteBuffer = require('bytebuffer');
                    const pako = require('pako');
                    var buf = ByteBuffer.fromBase64(msg);
                    buf.offset = 10 + buf.readShort(4);
                    var l = pako.inflate(new Uint8Array(buf.toArrayBuffer()));
                    var new_buf = new ByteBuffer()
                    new_buf.append(l).flip()
                    return new_buf.toBase64();
                }
                """
            )
            # 使用JS代码解压缩弹幕服务器传来的字节流
            danmaku_base64 = parse_msg.call("parseMsg", str(binascii.b2a_base64(message, newline=False))[2:-1])
            danmaku_str = str(binascii.a2b_base64(danmaku_base64)[16:].decode('utf-8', 'ignore')).strip()
            # 提取普通的消息弹幕
            try:
                normal_danmaku = "\"type\":\"1\""
                if normal_danmaku in danmaku_str:
                    p1 = danmaku_str.find('{' + normal_danmaku)
                    p2 = danmaku_str.rfind('{' + normal_danmaku)
                    if p1 == p2:
                        self.__buffer.append(json.loads(danmaku_str))
                    else:
                        p1_end = danmaku_str[p1:p2].rfind('}') + 1
                        danmaku1 = json.loads(danmaku_str[p1:p1_end])
                        danmaku2 = json.loads(danmaku_str[p2:])
                        self.__buffer.append(danmaku1)
                        self.__buffer.append(danmaku2)
            except json.JSONDecodeError:
                pass


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('room_id', type=int, help='ID of room')
    args = parser.parse_args()
    danmaku = PandaTvDanmaku(args.room_id)
    buf = danmaku.get_buffer()
    while True:
        try:
            if len(buf) > 0:
                msg = buf.pop(0)
                print('@%s: %s' % (msg['data']['from']['nickName'], msg['data']['content']))
        except KeyboardInterrupt:
            danmaku.stop()
            break
