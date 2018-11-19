#!/bin/env Python3
from twisted.internet import protocol, reactor, task
from twisted.internet.protocol import connectionDone
from twisted.python import log

from queue import Queue

import json
import os
import base64

from functools import partial

__version__ = "0.1"


def parse_msg0(msg):
    _, _color = msg.split(';')
    _joining = _[4:].strip()
    _color = _color.split('=')[1]
    return _joining, _color


def parse_msg1(msg, server, *args):
    if ';' in msg:
        cmd_chain = []
        for request in msg.split(';'):
            a, b = request.split(' ')
            if a.upper() in server.bypass.keys():
                cmd_chain.append(partial(server.bypass[a.upper()], args))
                return 'PARTIAL', cmd_chain
    try:
        a, *b = msg.split(' ')
        b = msg[len(a)+1:]
    except Exception as e:
        print(e)
        return
    return a, b


class RelayChannel(object):

    def __init__(self, name=None, creator="", description="", upstream=None):
        assert name is not None
        self.name = name
        self.creator = creator
        self.description = description
        self.users = dict()
        self.q = Queue()  # incoming request Q
        self.upstream = upstream  # main Q
        task.LoopingCall(self.__check_queue, ()).start(.1)

    def __user_list(self):
        r = map(lambda _: (_, self.users[_]['color']), self.users.keys())
        return Base64RelayChat.encode64(json.dumps({'name': '_chat_users', 'space': '_cmd_', 'msg': list(r)}))

    def __check_queue(self, *args, **kwargs):
        while not self.q.empty():
            todo = self.q.get()
            _job = todo[0]
            try:
                foo = {'say': self.__broadcast,
                       'join': self.__add_user}[_job]
                foo(*todo[1:])
            except KeyError as e:
                print("FOO UNKNOWN.. send upstream?")
                self.upstream.put(todo)
                pass
            except Exception as e:
                raise e
        # CHANNEL TRAFFIC

    def __add_user(self, name, transport, color=''):
        if name not in self.users.keys():
            self.users[name] = {'transport': transport, 'color': color}
            for user in self.users:
                self.users[user]['transport'].write(self.__user_list())  # update user list
            return True
        print('{} already in list')
        return False

    def __broadcast(self, name, transport, msg):
        if name not in self.users.keys():
            if [True for match in ['JOIN', ';', 'COLOR'] if match in msg]:
                _joining, _color = parse_msg0(msg)
                try:
                    assert _joining == self.name
                    self.__add_user(name, transport, color=_color)
                    return True
                except AssertionError:
                    print('Q upstream')
                    self.upstream.put(('join', name, transport, _joining, _color))
                    return True
            transport.write(Base64RelayChat._error_msg('JOIN CHANNEL before posting'))
            return
        if self.users[name]['transport'] != transport:
            transport.write(Base64RelayChat._error_msg('ERROR.001'))
            return
        # Check for escape seq ... hash at less "#@<"
        if msg.startswith("#@<"):
            a, b = parse_msg1(msg[3:], self, )
            try:
                self.q.put((a, name, transport, b))
            except Exception as e:
                print(e)
                return False
            return True
        broadcast = Base64RelayChat.encode64(
            json.dumps(dict(name=name, msg=msg, space=self.name, color=self.users[name]['color'])))
        for u in [_ for _ in self.users if _ != name]:
            try:
                self.users[u]['transport'].write(broadcast)
            except Exception as e:
                print('error sending msg to user: ', u)
        return True


class Base64RelayChat(protocol.Protocol):
    channel_list = dict(lobby=RelayChannel(name="lobby", creator="system", description="welcome"))
    user_list = dict()
    pid = os.getpid()

    def __init__(self, *args, **kwargs):
        super(Base64RelayChat, self).__init__(*args, **kwargs)
        self.q = Queue()
        self.bypass = {'JOIN': lambda *x: self.user_join(*x),
                       'SAY': lambda *x: self.user_say(*x),
                       'CODE': lambda *x: self.user_code(*x),
                       'PART': lambda *x: self.user_part(*x),
                       'PARTIAL': lambda *x: self.__partial(*x),
                       'QUIT': lambda *x: self.user_quit(*x),
                       'CONFIG': lambda *x: self.user_config(*x)}
        hyperspace = RelayChannel(name='_cmd_', creator='system', description="", upstream=self.q)
        hyperspace.say = lambda *x: self.__user_cmd(*x)
        self.channel_list['_cmd_'] = hyperspace
        task.LoopingCall(self.__upstream, ()).start(.1)
        # print('connecting to {}'.format(self.pid))

    def __upstream(self, *args, **kwargs):
        while not self.q.empty():
            todo = self.q.get()
            _job = todo[0].upper()
            try:
                self.bypass[_job](*todo[1:])
            except KeyError as e:
                print("UNKNOWN foo")
            except Exception as e:
                raise e

    def makeConnection(self, transport):
        super(Base64RelayChat, self).makeConnection(transport)
        self.transport.write('SUP\n'.encode('utf-8'))

    def dataReceived(self, data):
        # expects base64 encoded JSON
        try:
            _obj = json.loads(self.decode64(data))
            _name = _obj['name'].strip()  # esc CR
            _msg = _obj['msg']
        except KeyError as e:
            print("missing name &/or msg")
            return
        except Exception as e:
            print(e)  # cannot decode?
            return
        try:
            _space = _obj['space']
        except KeyError as e:
            _space = 'lobby'
        if _space == '_cmd_' and _msg.upper().startswith('PART'):
            self.q.put(('PART', _name, self.transport, _msg[4:].strip()))
            return
        try:
            self.channel_list[_space].q.put(('say', _name, self.transport, _msg))
        except Exception as e:
            print(e)

    def connectionLost(self, reason=connectionDone):
        _lost = []
        for u in self.user_list.keys():
            for chan in self.user_list[u]['channels']:
                for _name in self.channel_list[chan].users:
                    _tp = self.channel_list[chan].users[_name]['transport']
                    if _tp.disconnected and _name not in _lost:
                        _lost.append(_name)  # queue 1 time only
                        print("{} lost connection".format(_name))
                        self.q.put(('PART', _name, _tp, chan))
        print('cleaned up {}'.format(_lost))

    def user_join(self, name, transport, chan, color=None):
        if chan.startswith('_'):
            # reserved for internal use
            return False

        if chan not in self.channel_list.keys():
            transport.write(self._error_msg('_ERROR.002\n'))  # unknown channel
            return False

        if (name in self.channel_list[chan].users.keys()) or (name in self.user_list):
            transport.write(self._error_msg('_ERROR.001'))  # name is taken
            return False

        print("{} JOINS {}".format(name, chan))
        self.user_list[name] = {'channels': [chan], 'color': color}
        self.channel_list[chan].q.put(('join', name, transport, self.user_list[name]['color']))
        return True

    def user_part(self, name, transport, chan):
        print("{} parts {}".format(name, chan))
        if (name in self.channel_list[chan].users.keys()) and \
                (self.channel_list[chan].users[name]['transport'] != transport):
            print("DUPLICATE {} QUIT".format(name))
            return False
        del self.channel_list[chan].users[name]  # remove user from channel
        del self.user_list[name]['channels'][self.user_list[name]['channels'].index(chan)]  # remove channel from user
        for user in self.channel_list[chan].users:
            self.channel_list[chan].users[user]['transport'].write(self.__enc_user_list(chan))  # update active users
        if len(self.user_list[name]['channels']) == 0:
            transport.loseConnection()
            del self.user_list[name]  # remove from list of active users
        return True

    def user_quit(self, name, transport):
        _out = '{} QUITS'.format(name)
        try:
            for c in self.user_list[name]['channels']:
                self.user_part(name, transport, c)
        except KeyError as e:
            print(e)

    def __user_cmd(self, name, transport, msg):
        name = name.strip()  # no trailing \n

        if msg.upper() == 'QUIT':
            self.user_quit(name, transport)
            return True

        if ';' in msg:
            cmd_chain = []
            for request in msg.split(';'):
                a, b = request.split(' ')
                if a.upper() in self.bypass.keys():
                    cmd_chain.append(partial(self.bypass[a.upper()], (name, transport, b)))
            self.q.put(('PARTIAL', name, transport, cmd_chain))
            return True

        a, b = msg.split(' ')

        available = [x for x in self.bypass.keys() if x != '_cmd']  # no recursion at this level

        if a.upper() in available:
            if a.upper() == 'PART':
                self.user_part(name, transport, b)
                return
            self.bypass[a.upper()](name, transport, b)
        return True

    def __partial(self, name, transport, cmds):
        for f in cmds:
            print(f)
            f()

    def __enc_user_list(self, chan):
        r = map(lambda _: (_, self.channel_list[chan].users[_]['color']), self.channel_list[chan].users.keys())
        return self.encode64(json.dumps({'name': '_chat_users', 'space': '_cmd_', 'msg': list(r)}))

    @staticmethod
    def encode64(plain_text):
        return base64.b64encode(plain_text.encode())

    @staticmethod
    def decode64(b64_text):
        return base64.b64decode(b64_text).decode()

    @staticmethod
    def _error_msg(txt):
        return Base64RelayChat.encode64(json.dumps(dict(space='_ERROR', name='_ERROR', msg='{}'.format(txt))))


class Base64RelayChatFactory(protocol.Factory):
    def buildProtocol(self, addr):
        return Base64RelayChat()


if __name__ == "__main__":
    import argparse
    import sys

    log.startLogging(sys.stdout)
    _factory = Base64RelayChatFactory()
    parser = argparse.ArgumentParser()
    parser.add_argument("PORT")
    args = parser.parse_args()
    _port = int(args.PORT)

    print('[simple.object.relay.Protocol.{}]'.format(__version__))
    print('[process ID : {}]\n[listening on port {}]\n'.format(os.getpid(), _port))
    try:
        reactor.listenTCP(_port, _factory)
        reactor.run()
        print('[exit]')
        exit(0)
    except Exception as e:
        raise e
