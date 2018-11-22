#!/bin/env python3
from twisted.internet import protocol, reactor, task
from twisted.internet.protocol import connectionDone
from zope.interface import provider
from twisted.logger import ILogObserver, formatEvent, jsonFileLogObserver, Logger, globalLogPublisher
from functools import partial
from queue import Queue
from sys import argv
import json
import os
import base64
import io
__version__ = "0.1"


@provider(ILogObserver)
def simpleObserver(event):
    print(formatEvent(event))


log = Logger(observer=jsonFileLogObserver(io.open("log.json", "a")), namespace="lanChat")
globalLogPublisher.addObserver(simpleObserver)


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
        log.info(e)
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
                log.info("FOO UNKNOWN.. send upstream?")
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
        log.info('{} already in list')
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
                    log.info('*upstream Q')
                    self.upstream.put(('join', name, transport, _joining, _color))
                    return True
            _bits = Base64RelayChat._error_msg('JOIN CHANNEL before posting')
            transport.write(_bits, [], 200, "SUP")
            return
        if self.users[name]['transport'] != transport:
            _bits = Base64RelayChat._error_msg('ERROR.001')
            transport.write(_bits, [], 200, "SUP")
            return
        # Check for escape seq ... hash at less "#@<"
        if msg.startswith("#@<"):
            a, b = parse_msg1(msg[3:], self)
            try:
                self.q.put((a, name, transport, b))
            except Exception as e:
                log.info(e)
                return False
            return True
        broadcast = Base64RelayChat.encode64(
            json.dumps(dict(name=name, msg=msg, space=self.name, color=self.users[name]['color'])))
        for u in [_ for _ in self.users if _ != name]:
            try:
                self.users[u]['transport'].write(broadcast)
            except Exception as e:
                log.info('error sending msg to user: ', u)
        return True


class Base64RelayChat(protocol.Protocol):
    channel_list = dict(
        lobby=RelayChannel(name="lobby", creator="system", description="Welcome")
    )  # must declare channels here or clients are blind to each other
    user_list = dict()
    pid = os.getpid()

    def __init__(self, *args, **kwargs):
        super(Base64RelayChat, self).__init__(*args, **kwargs)
        self.q = Queue()
        self.channel_list['lobby'].upstream = self.q
        self.bypass = {'JOIN': lambda *x: self.user_join(*x),
                       'SAY': lambda *x: self.user_say(*x),
                       'CODE': lambda *x: self.user_code(*x),
                       'PART': lambda *x: self.user_part(*x),
                       'PARTIAL': lambda *x: self.__partial(*x),
                       'QUIT': lambda *x: self.user_quit(*x),
                       'CONFIG': lambda *x: self.user_config(*x)}
        hyperspace = RelayChannel(name='_cmd_', creator='system',
                                  description="", upstream=self.q)
        hyperspace.say = lambda *x: self.__user_cmd(*x)
        self.greetings = 'TWFuIGlzIGRpc3Rpbmd1aXNoZWQsIG5vdCBvbmx5IGJ5IGhpcyBy' \
                         'ZWFzb24sIGJ1dCBieSB0aGlzIHNpbmd1bGFyIHBhc3Npb24gZnJv' \
                         'bSBvdGhlciBhbmltYWxzLCB3aGljaCBpcyBhIGx1c3Qgb2YgdGh' \
                         'lIG1pbmQsIHRoYXQgYnkgYSBwZXJzZXZlcmFuY2Ugb2YgZGVsaW' \
                         'dodCBpbiB0aGUgY29udGludWVkIGFuZCBpbmRlZmF0aWdhYmxlI' \
                         'GdlbmVyYXRpb24gb2Yga25vd2xlZGdlLCBleGNlZWRzIHRoZSBz' \
                         'aG9ydCB2ZWhlbWVuY2Ugb2YgYW55IGNhcm5hbCBwbGVhc3VyZS4='
        self.channel_list['_cmd_'] = hyperspace
        task.LoopingCall(self.__upstream, ()).start(.1)

    def __upstream(self, *args, **kwargs):
        while not self.q.empty():
            todo = self.q.get()
            _job = todo[0].upper()
            try:
                self.bypass[_job](*todo[1:])
            except KeyError as e:
                log.info("UNKNOWN foo")
            except Exception as e:
                raise e

    def makeConnection(self, transport):
        super(Base64RelayChat, self).makeConnection(transport)
        _ = base64.test()
        self.transport.write(self.greetings.encode())

    def dataReceived(self, data):
        # expects base64 encoded JSON
        try:
            _obj = json.loads(self.decode64(data))
            _name = _obj['name'].strip()
            _msg = _obj['msg']
        except KeyError as e:
            log.info("missing name &/or msg")
            return
        except Exception as e:
            log.info("EXCEPTION")
            log.info(e)  # cannot decode?
            return
        try:
            _space = _obj['space']
        except KeyError as e:
            _space = 'lobby'
        if _space.lower() == '_cmd_' and _msg.upper().startswith('PART'):
            self.q.put(('PART', _name, self.transport, _msg[4:].strip()))
            return
        try:
            self.channel_list[_space].q.put(('say', _name, self.transport, _msg))
        except Exception as e:
            log.info("EXCEPTION")
            log.info(e)

    def connectionLost(self, reason=connectionDone):
        _lost = []
        for u in self.user_list.keys():
            for chan in self.user_list[u]['channels']:
                for _name in self.channel_list[chan].users:
                    _tp = self.channel_list[chan].users[_name]['transport']
                    if _tp.disconnected and _name not in _lost:
                        _lost.append(_name)  # queue 1 time only
                        log.info("{} lost connection".format(_name))
                        self.q.put(('PART', _name, _tp, chan))
        log.info('cleaned up {}'.format(_lost))

    def user_code(self, name, transport, B64text):
        log.info("USER [{}] ENTERED CODE".format(name))
        try:
            ufo = json.loads(self.decode64(B64text))
            log.info("{} sent {}".format(name, type(ufo)))
            space = ufo['space']
            msg = ufo['msg']
            if '_cmd_' in space.lower():
                self.__user_cmd(name, transport, msg)
                return True
            if space in self.bypass.keys():
                self.bypass[space](name, transport, msg)
                return True
            log.info("??? ", ufo)
        except Exception as e:
            log.info("EXCEPTION")
            log.info(e)
        return False

    def user_join(self, name, transport, chan, color=None):
        if chan.startswith('_'):
            # reserved for internal use
            err = "One Does Not Simply Walk into {}".format(chan)
            transport.write(self._error_msg(err))
            log.info(err)
            return False

        if chan not in self.channel_list.keys():
            transport.write(self._error_msg('_ERROR.002\n'))  # unknown channel
            return False

        if (name in self.channel_list[chan].users.keys()) or (name in self.user_list):
            transport.write(self._error_msg('_ERROR.001'))   # name is taken
            return False

        log.info("{} JOINS {}".format(name, chan))
        self.user_list[name] = {'channels': [chan], 'color': color}
        self.channel_list[chan].q.put(('join', name, transport, self.user_list[name]['color']))
        return True

    def user_part(self, name, transport, chan):
        log.info("{} parts {}".format(name, chan))
        if (name in self.channel_list[chan].users.keys()) and \
                (self.channel_list[chan].users[name]['transport'] != transport):
            log.info("DUPLICATE {} QUIT".format(name))
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
            log.info(e)

    def __user_cmd(self, name, transport, msg):
        name = name.strip()
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
            log.info(f)
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
    _factory = Base64RelayChatFactory()
    _port = int(argv[1])
    x = "[simple.object.relay.Protocol.{}]".format(__version__)
    y = "[process ID : {}]\n[listening on port {}]\n".format(os.getpid(), _port)
    log.info(x)
    print(x)
    log.info(y)
    print(y)
    try:
        reactor.listenTCP(_port, _factory)
        reactor.run()
        log.info("[exit]")
        exit(0)
    except Exception as e:
        raise e
