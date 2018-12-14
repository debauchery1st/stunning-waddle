#!/usr/bin/env python
from platform import python_version
from kivy.app import App
from kivy.uix.textinput import TextInput
from kivy.support import install_twisted_reactor
from kivy.properties import StringProperty
from kivy.uix.button import Button
from kivy.clock import Clock
from kivy.utils import platform
install_twisted_reactor()

from twisted.internet import reactor, protocol

import json
import base64
import socket
from random import choice


def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(('8.8.8.8', 0))
    s.setblocking(False)
    local_ip_address = s.getsockname()[0]
    s.close()
    del s
    return local_ip_address


if platform == 'android':
    if int(python_version()[0]) < 3:
        from _droid import *
    else:
        from ._droid import *

colors = ['E4572E', '17BEBB', 'FFC914', '76B041', 'C6C4C4', 'C0392B', '8E44AD', '7F8C8D']
GREETINGS = 'TWFuIGlzIGRpc3Rpbmd1aXNoZWQsIG5vdCBvbmx5IGJ5IGhpcyBy' \
            'ZWFzb24sIGJ1dCBieSB0aGlzIHNpbmd1bGFyIHBhc3Npb24gZnJv' \
            'bSBvdGhlciBhbmltYWxzLCB3aGljaCBpcyBhIGx1c3Qgb2YgdGh' \
            'lIG1pbmQsIHRoYXQgYnkgYSBwZXJzZXZlcmFuY2Ugb2YgZGVsaW' \
            'dodCBpbiB0aGUgY29udGludWVkIGFuZCBpbmRlZmF0aWdhYmxlI' \
            'GdlbmVyYXRpb24gb2Yga25vd2xlZGdlLCBleGNlZWRzIHRoZSBz' \
            'aG9ydCB2ZWhlbWVuY2Ugb2YgYW55IGNhcm5hbCBwbGVhc3VyZS4='

__version__ = "0.2.1"


class Receivable(object):
    name, space, msg = '', 'lobby', ''  # isolate incoming to lobby by default

    def __init__(self, data):
        self.color = ''
        self._incoming = data
        try:
            _o = json.loads(base64.b64decode(data).decode())
            for _ in _o.keys():
                self.__setattr__(_, _o[_])
        except Exception as err:
            self._incoming = err
            pass

    def mark_up(self):
        return '\n [b][color={}]{}:[/color][/b] {}\n'.format(self.color, self.name, self.msg)

    def plain_text(self):
        return self.msg.__str__() if '://' in self.msg else '{}: {}'.format(self.name, self.msg)

    def outgoing(self):
        result = dict()
        exportable = [_ for _ in self.__dict__.keys() if not _.startswith('_')]
        for k in exportable:
            result[k] = self.__getattribute__(k)
        return base64.b64encode(json.dumps(result).encode())


class Sendable(Receivable):

    def __init__(self, **kwargs):
        super(Sendable, self).__init__(None)
        for _ in kwargs.keys():
            self.__setattr__(_, kwargs[_])


class ChatMessage(Button):
    message = StringProperty()
    plaintext = StringProperty()


class ChatInput(TextInput):

    def on_parent(self, widget, parent):
        self.focus = True

    def on_text_validate(self):
        # called after pressing [Enter]
        app = App.get_running_app()
        if app.root.current != 'login':
            app.send_msg()
        Clock.schedule_once(app.refocus_input, 0)  # refocus on the text box


class ChatClient(protocol.Protocol):
    color = None
    _version = "0.1"

    def connectionMade(self):
        self.color = choice(colors)
        self.factory.app.on_connect(self.transport)
        self.factory.app.color = self.color

    def dataReceived(self, data):
        txt = data.decode()
        if txt == GREETINGS:
            print('[HANDSHAKE]')
            self.factory.app.on_login()
            return
        self.factory.app.on_message(data)


class ChatClientFactory(protocol.ClientFactory):
    protocol = ChatClient

    def __init__(self, app):
        self.app = app

    def clientConnectionFailed(self, connector, reason):
        print("CONNECTION FAILURE : {}:".format(reason))

    def clientConnectionLost(self, connector, reason):
        print(reason.value)


class Client(App):
    icon = StringProperty('data/icon.png')
    nick = StringProperty()
    chat_users = StringProperty()
    chat_ip = StringProperty()
    pks = None
    transport = None
    color = None

    def __init__(self, **kwargs):
        super(Client, self).__init__()
        # if file_uri is not None:
        #     print('started with android INTENT')
        self.chat_ip = kwargs.get('host_ip')
        self.nick = kwargs.get('client_nick')
        Clock.schedule_once(self.connect, 0)

    def refocus_input(self, delta):
        # called from ChatInput(TextInput)
        self.root.ids.message.focus = True

    def connect(self, *args, **kwargs):
        host = self.root.ids.server_ip.kv_text
        chat_port = int(self.root.ids.server_port.kv_text)
        self.nick = self.root.ids.nick_name.kv_text  # only redundant on 1st run
        try:
            assert chat_port > 0
        except Exception as e:
            print(e)
            return
        reactor.connectTCP(host, chat_port, ChatClientFactory(self))

    def disconnect(self, *args):
        print('disconnected')
        _ = Sendable(name=self.nick, space='_cmd_', msg='PART {}'.format(self.root.current)).outgoing()
        self.transport.write(_)
        self.root.ids.chat_logs.clear_widgets()  # clear messages
        self.chat_users = ''  # clear user-list
        self.root.current = 'login'  # back to login screen

    def on_connect(self, transport):
        print("CONNECTED")
        self.transport = transport
        self.root.current = 'lobby'
        self.vibrate()

    def on_login(self, *args):
        _ = Sendable(name=self.nick, space='_cmd_', msg='JOIN {};CONFIG COLOR={}'.format(self.root.current, self.color))
        self.transport.write(_.outgoing())

    def send_msg(self):
        _ = Sendable(name=self.nick, space=self.root.current, msg=self.root.ids.message.text)
        self.transport.write(_.outgoing())
        chat_msg = ChatMessage(text=_.mark_up(), plaintext=_.plain_text(), message=_.msg)
        self.root.ids.chat_logs.add_widget(chat_msg)
        self.root.ids.message.text = ''
        self.root.ids.chat_view.scroll_to(chat_msg)

    def system_msg(self, decoded):
        if decoded.name == '_chat_users':
            self.chat_users = '\n'.join(['[b][color={}]{}[/color][/b]'.format(_[1], _[0]) for _ in decoded.msg])
            return True
        if '_ERROR' in decoded.space:
            if '001' in decoded.msg:
                print('NICKNAME TAKEN, PLEASE CHOOSE ANOTHER')
                self.root.current = 'login'  # back to login screen
                self.transport.loseConnection()
            elif '002' in decoded.msg:
                print("UNKNOWN CHANNEL, CHECK SETTINGS")
        else:
            print('UNHANDLED MSG FROM SYSTEM', decoded)
        return True

    def on_message(self, b64text):
        item = Receivable(b64text)
        if 'PING' in item.__dict__.keys():
            print('PONG')
            self.transport.write('PONG')
            return
        if item.name.startswith('_'):
            self.system_msg(item)  # handle system msg
            return
        chat_msg = ChatMessage(text=item.mark_up(), plaintext=item.plain_text(), message=item.msg)
        self.root.ids.chat_logs.add_widget(chat_msg)
        self.root.ids.message.text = ''
        self.root.ids.chat_view.scroll_to(chat_msg)  # auto-scroll

    def on_stop(self):
        self.disconnect()
        return True

    def vibrate(self):
        print('vibrate')
        if platform == 'android':
            vibrate(234)


if __name__ == "__main__":
    file_uri = None
    nick = str(platform)
    Client(host_ip=get_local_ip(), client_nick=nick, file_uri=file_uri).run()
