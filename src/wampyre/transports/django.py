from channels.generic.websocket import JsonWebsocketConsumer

from .base import TransportBase


class WAMPRouter(JsonWebsocketConsumer):
    guard = None
    realm_authenticator = None
    user = None

    def __init__(self, *args, **kwargs):
        self.realm_authenticator = kwargs.pop("realm_authenticator", None)
        self.guard = kwargs.pop("guard", None)

        super().__init__(*args, **kwargs)
        self.transport = DjangoWebsocketTransport(self)

    def connect(self):
        self.user = self.scope.get("user")
        self.accept("wamp.2.json")

    def receive_json(self, content):
        if not isinstance(content, list):
            pass  # TODO: some error?

        self.transport.receive(*content)

    def realm_allowed(self, realm):
        if self.realm_authenticator:
            return self.realm_authenticator(self.user, realm)
        else:
            return True

    def disconnect(self, code):
        self.transport.session_lost()


class DjangoWebsocketTransport(TransportBase):
    def __init__(self, consumer):
        super().__init__()
        self.consumer = consumer

    def send(self, opcode, *args):
        self.consumer.send_json([opcode] + list(args))

    def realm_allowed(self, realm):
        if self.consumer.realm_authenticator:
            self.consumer.realm_allowed(realm)
        return True

    def close_session(self):
        self.consumer.close()

    def method_uri_allowed(self, method, uri):
        if self.consumer.guard:
            return self.consumer.guard(self.consumer.user, method, uri)
        else:
            return True
