#!/bin/env Python
from kivy.app import App
from kivy.support import install_twisted_reactor
from kivy.properties import StringProperty
# from kivy.core.window import Window
from kivy.uix.button import Button
from kivy.lang import Builder
from kivy.clock import Clock
install_twisted_reactor()

from twisted.internet import reactor, protocol

import json
import base64
from random import choice

colors = ['E4572E', '17BEBB', 'FFC914', '76B041', 'C6C4C4', 'C0392B', '8E44AD', '7F8C8D']
Builder.load_string("""
#:import Clipboard kivy.core.clipboard.Clipboard
#:set bkg_color (.16862745098039217, .16862745098039217, .16862745098039217, 1)
#:set foreground_clr (0.6784313725490196, 0.6784313725490196, 0.6784313725490196, 1)

<ChatMessage>:
    markup: 1
    background_color: bkg_color
    foreground_color: foreground_clr
    text_size: (self.width, None)
    halign: 'left'
    valign: 'top'
    size_hint: 1, None
    height: self.texture_size[1]
    on_release: Clipboard.copy(self.plaintext)
""")


class ChatMessage(Button):
    message = StringProperty()
    plaintext = StringProperty()


class ChatClient(protocol.Protocol):
    color = None
    _version = "0.1"

    def connectionMade(self):
        self.color = choice(colors)
        self.factory.app.on_connect(self.transport)
        self.factory.app.color = self.color

    def dataReceived(self, data):
        txt = data.decode()
        if txt.startswith('SUP'):
            print('[HANDSHAKE]')
            self.factory.app.on_login()
            return
        self.factory.app.on_message(data)


class ChatClientFactory(protocol.ClientFactory):
    protocol = ChatClient

    def __init__(self, app):
        self.app = app

    def clientConnectionFailed(self, connector, reason):
        super(ChatClientFactory, self).clientConnectionFailed(connector, reason)
        print("CONNECTION FAILURE : {}:".format(reason))

    def clientConnectionLost(self, connector, reason):
        super(ChatClientFactory, self).clientConnectionLost(connector, reason)
        print(reason.value)


class Client(App):
    nick = StringProperty()
    chat_users = StringProperty()
    chat_ip = StringProperty()
    chat_port = int
    pks = None
    transport = None
    color = None

    def __init__(self, **kwargs):
        super(Client, self).__init__()
        self.chat_ip = kwargs.get('host_ip')
        self.chat_port = kwargs.get('host_port')
        self.nick = kwargs.get('client_nick')
        # resizing window crashes application.. why?
        # self._keyboard = Window.request_keyboard((), self, 'text')
        # self._keyboard.bind(on_key_down=self.on_keyboard)
        Clock.schedule_once(self.connect, 0)

    def on_keyboard(self, keyboard, keycode, text, modifiers):
        if keycode[0] == 13 and len(self.root.ids.message.text) > 0:
            if self.root.current == "login":
                return True
            self.send_msg()
            self.root.ids.message.focus = True
        return True

    def connect(self, *args, **kwargs):
        host = self.root.ids.server.text
        self.nick = self.root.ids.nickname.text  # only redundant on 1st run
        reactor.connectTCP(host, self.chat_port, ChatClientFactory(self))

    def disconnect(self, *args):
        print('disconnected')
        if self.transport:
            self.transport.write(
                self.encode64(
                    json.dumps(
                        {'name': self.nick,
                         'space': '_cmd_',
                         'msg': 'PART {}'.format(self.root.current)}
                    )
                )
            )
        self.root.ids.chat_logs.clear_widgets()  # clear messages
        self.chat_users = ''  # clear user-list
        self.root.current = 'login'  # back to login screen

    def on_connect(self, transport):
        print("CONNECTED")
        self.transport = transport
        self.root.current = 'lobby'

    def on_login(self, *args):
        out1 = json.dumps({'name': self.nick,
                           'space': '_cmd_',
                           'msg': 'JOIN {};CONFIG COLOR={}'.format(
                               self.root.current, self.color)})
        self.transport.write(self.encode64(out1))

    def send_msg(self):
        msg = self.root.ids.message.text
        out = self.encode64(json.dumps({'name': self.nick,
                                        'space': self.root.current,
                                        'msg': '{}'.format(msg)}))
        self.transport.write(out)
        chat_msg = ChatMessage(text='[b][{}][/b] : {}\n'.format(self.nick, msg),
                               plaintext="{}: {}".format(self.nick, msg),
                               message=msg)
        self.root.ids.chat_logs.add_widget(chat_msg)
        self.root.ids.message.text = ''
        self.root.ids.chat_view.scroll_to(chat_msg)

    def system_msg(self, decoded):
        if decoded['name'] == '_chat_users':
            self.chat_users = '\n'.join(['[b][color={}]{}[/color][/b]'.format(_[1], _[0]) for _ in decoded['msg']])
            return True
        if '_ERROR' in decoded['space']:
            if '001' in decoded['msg']:
                print('NICKNAME TAKEN, PLEASE CHOOSE ANOTHER')
                self.root.current = 'login'  # back to login screen
                self.transport.loseConnection()
            elif '002' in decoded['msg']:
                print("UNKNOWN CHANNEL, CHECK SETTINGS")
        else:
            print('UNHANDLED MSG FROM SYSTEM', decoded)
        return True

    def on_message(self, b64text):
        try:
            decoded = json.loads(self.decode64(b64text))
            if 'PING' in decoded.keys():
                print('PONG')
                self.transport.write(self.encode64(
                    json.dumps(dict(space="_cmd_", PONG=decoded['PING'],
                                    name=self.nick, msg="PING", chan=self.root.current))))
                return
        except Exception as e:
            print("ERROR DECODING INCOMING MESSAGE")
            raise e
        if decoded['name'].startswith('_'):
            self.system_msg(decoded)  # handle system msg
            return
        _color = decoded['color'].strip()
        _name = decoded['name'].strip()
        if 'color' in decoded.keys():
            _ = '[b][color={}]{}:[/color][/b] {}'.format(_color, _name, decoded['msg'])
        else:
            _ = '{}: {}'.format(_name, decoded['msg'])
        chat_msg = ChatMessage(text='{}\n'.format(_))
        self.root.ids.chat_logs.add_widget(chat_msg)
        self.root.ids.message.text = ''
        self.root.ids.chat_view.scroll_to(chat_msg)  # auto-scroll

    def on_stop(self):
        self.disconnect()
        return True

    @staticmethod
    def encode64(plain_text):
        return base64.b64encode(plain_text.encode())

    @staticmethod
    def decode64(b64_text):
        return base64.b64decode(b64_text).decode()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("IP", default="127.0.0.1")
    parser.add_argument("PORT", type=int, default=8123)
    parser.add_argument("USERNAME", type=str, default="user")
    args = parser.parse_args()
    _ip, _port, _name = args.IP, args.PORT, args.USERNAME
    Client(host_ip=_ip, host_port=_port, client_nick=_name).run()
