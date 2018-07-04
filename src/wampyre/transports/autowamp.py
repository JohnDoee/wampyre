import txaio

from autobahn.wamp.interfaces import ITransport, ISerializer, IObjectSerializer
from autobahn.wamp.serializer import Serializer
from autobahn.wamp.types import ComponentConfig

from twisted.internet import reactor

from .base import TransportBase


class ApplicationRunner(object):
    log = txaio.make_logger()

    def __init__(self, realm=None, extra=None):
        self.realm = realm
        self.extra = extra or dict()

    def run(self, make):
        if callable(make):
            def create():
                cfg = ComponentConfig(self.realm, self.extra)
                try:
                    session = make(cfg)
                except Exception:
                    self.log.failure('ApplicationSession could not be instantiated: {log_failure.value}')
                    raise
                else:
                    return session
        else:
            create = make

        # Setup all the plumbing
        session = create()
        protocol = WampLocalProtocol(session)
        transport = AutobahnTransport(protocol)
        protocol._transport = transport

        # Trigger a start
        protocol.onOpen()


class WampLocalProtocol:
    log = txaio.make_logger()

    _session = None
    _transport = None

    def __init__(self, session):
        self._session = session
        self._serializer = PythonSerializer(PythonObjectSerializer())

    def onOpen(self):
        self._session.onOpen(self)

    def send(self, message):
        print('d', message, message.marshal())
        reactor.callInThread(self._transport.receive, *message.marshal())

    def isOpen():
        return True

    def close(self):
        pass

    def abort(self):
        pass

    def onMessage(self, payload):
        for msg in self._serializer.unserialize(payload):
            reactor.callFromThread(self._session.onMessage, msg)

ITransport.register(WampLocalProtocol)


class AutobahnTransport(TransportBase):
    def __init__(self, protocol):
        super().__init__()
        self.protocol = protocol

    def send(self, opcode, *args):
        self.protocol.onMessage([opcode] + list(args))

    def realm_allowed(self, realm):
        return True

    def close_session(self):
        pass # TODO


class PythonObjectSerializer:
    NAME = 'python'

    def serialize(self, obj):
        return obj

    def unserialize(self, payload):
        return [payload]

IObjectSerializer.register(PythonObjectSerializer)


class PythonSerializer(Serializer):
    SERIALIZER_ID = 'python'

ISerializer.register(PythonSerializer)
