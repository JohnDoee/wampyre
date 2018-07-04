import pytest

from ..opcodes import OP
from ..pattern import Pattern
from ..realm import realm_manager
from ..session import STATE_CLOSED, STATE_UNAUTHENTICATED
from ..transports.base import TransportBase


def transport_base():
    class TestTransportBase(TransportBase):
        def __init__(self):
            self._sends = []
            self._closed = False
            self._last_id = 0

            super().__init__()

        def send(self, opcode, *args):
            self._sends.append((opcode, args))

        def realm_allowed(self, realm):
            return 'realm_deny' not in realm

        def close_session(self):
            self._closed = True

        def set_state(self, state):
            self.session.state = state

        def get_reply(self):
            return self._sends.pop()

        def is_empty(self):
            return not self._sends

        def generate_id(self):
            self._last_id += 1
            return self._last_id

        def connect(self, realm):
            self.receive(OP.HELLO, realm, {})
            return self.get_reply()

        def disconnect(self):
            self.session.close_session()

    return TestTransportBase()


@pytest.fixture
def transport():
    yield transport_base()
    realm_manager.realms = {}


@pytest.fixture
def transport2():
    yield transport_base()
    realm_manager.realms = {}


@pytest.fixture
def transport3():
    yield transport_base()
    realm_manager.realms = {}


def test_hello_goodbye(transport):
    transport.receive(OP.HELLO, 'a.realm', {})
    opcode, args = transport.get_reply()
    assert opcode == OP.WELCOME
    assert Pattern('id', 'dict')(*args)

    transport.receive(OP.GOODBYE, {}, 'wamp.close.goodbye_and_out')
    opcode, args = transport.get_reply()
    assert opcode == OP.GOODBYE
    assert Pattern('dict', 'uri!')(*args)


def test_subscribe_unsubscribe(transport, transport2, transport3):
    transport.connect('a.realm')
    transport2.connect('a.realm')
    transport3.connect('a.realm')

    transport.receive(OP.PUBLISH, transport.generate_id(), {}, 'a.topic', ['a'], {'b': 'c'})
    assert transport.is_empty()
    assert transport2.is_empty()
    assert transport3.is_empty()

    transport2.receive(OP.SUBSCRIBE, transport2.generate_id(), {}, 'a.topic')
    opcode, args = transport2.get_reply()
    assert opcode == OP.SUBSCRIBED
    assert Pattern('id', 'id')(*args)
    assert transport2._last_id == args[0]
    transport2_a_topic_subscription_id = args[1]

    transport.receive(OP.PUBLISH, transport.generate_id(), {}, 'a.topic', ['a'], {'b': 'c'})
    opcode, args = transport2.get_reply()
    assert opcode == OP.EVENT
    assert Pattern('id', 'id', 'dict', 'list', 'dict')(*args)
    assert args[0] == transport2_a_topic_subscription_id
    assert args[3] == ['a']
    assert args[4] == {'b': 'c'}

    assert transport.is_empty()
    assert transport2.is_empty()
    assert transport3.is_empty()

    transport3.receive(OP.SUBSCRIBE, transport3.generate_id(), {}, 'a.topic')
    opcode, args = transport3.get_reply()
    assert opcode == OP.SUBSCRIBED
    transport3_a_topic_subscription_id = args[1]

    transport2.receive(OP.PUBLISH, transport2.generate_id(), {}, 'a.topic', ['b'], {'c': 'd'})
    opcode, args = transport2.get_reply()
    assert opcode == OP.EVENT
    assert Pattern('id', 'id', 'dict', 'list', 'dict')(*args)
    assert args[0] == transport2_a_topic_subscription_id
    assert args[3] == ['b']
    assert args[4] == {'c': 'd'}

    opcode, args = transport3.get_reply()
    assert opcode == OP.EVENT
    assert Pattern('id', 'id', 'dict', 'list', 'dict')(*args)
    assert args[0] == transport3_a_topic_subscription_id
    assert args[3] == ['b']
    assert args[4] == {'c': 'd'}

    assert transport.is_empty()
    assert transport2.is_empty()
    assert transport3.is_empty()

    transport2.receive(OP.UNSUBSCRIBE, transport2.generate_id(), transport2_a_topic_subscription_id)
    opcode, args = transport2.get_reply()
    assert opcode == OP.UNSUBSCRIBED
    assert Pattern('id')(*args)
    assert transport2._last_id == args[0]

    transport2.receive(OP.PUBLISH, transport2.generate_id(), {}, 'a.topic', ['b'], {'c': 'd'})
    opcode, args = transport3.get_reply()
    assert transport.is_empty()
    assert transport2.is_empty()
    assert transport3.is_empty()

    transport3.receive(OP.UNSUBSCRIBE, transport3.generate_id(), transport3_a_topic_subscription_id)
    opcode, args = transport3.get_reply()
    assert opcode == OP.UNSUBSCRIBED
    assert Pattern('id')(*args)
    assert transport3._last_id == args[0]

    transport2.receive(OP.PUBLISH, transport2.generate_id(), {}, 'a.topic', ['b'], {'c': 'd'})
    assert transport.is_empty()
    assert transport2.is_empty()
    assert transport3.is_empty()

    transport3.receive(OP.SUBSCRIBE, transport3.generate_id(), {}, 'a.topic')
    opcode, args = transport3.get_reply()
    assert opcode == OP.SUBSCRIBED
    transport3_a_topic_subscription_id = args[1]

    transport.receive(OP.PUBLISH, transport.generate_id(), {'acknowledge': True}, 'a.topic', ['b'])
    opcode, args = transport.get_reply()
    assert opcode == OP.PUBLISHED
    assert Pattern('id', 'id')(*args)
    assert transport._last_id == args[0]

    opcode, args = transport3.get_reply()
    assert opcode == OP.EVENT
    assert Pattern('id', 'id', 'dict', 'list')(*args)
    assert args[0] == transport3_a_topic_subscription_id
    assert args[3] == ['b']

    assert transport.is_empty()
    assert transport2.is_empty()
    assert transport3.is_empty()


def test_register_call_yield(transport, transport2, transport3):
    transport.connect('a.realm')
    transport2.connect('a.realm')
    transport3.connect('a.realm')

    transport.receive(OP.REGISTER, transport.generate_id(), {}, 'a.procedure')
    opcode, args = transport.get_reply()
    assert opcode == OP.REGISTERED
    assert Pattern('id', 'id')(*args)
    assert transport._last_id == args[0]
    assert transport.is_empty()
    transport_register_id = args[1]

    transport3.receive(OP.REGISTER, transport.generate_id(), {}, 'a.procedure.2')
    opcode, args = transport3.get_reply()

    transport2.receive(OP.CALL, transport2.generate_id(), {}, 'a.procedure', ['a'], {'b': 'c'})
    assert transport2.is_empty()

    opcode, args = transport.get_reply()
    assert opcode == OP.INVOCATION
    assert Pattern('id', 'id', 'dict', 'list', 'dict')(*args)
    assert transport.is_empty()
    assert args[1] == transport_register_id
    assert args[3] == ['a']
    assert args[4] == {'b': 'c'}

    transport.receive(OP.YIELD, args[0], {}, ['c'], {'d': 'e'})
    assert transport.is_empty()
    assert transport3.is_empty()
    opcode, args = transport2.get_reply()
    assert opcode == OP.RESULT
    assert transport2._last_id == args[0]
    assert args[2] == ['c']
    assert args[3] == {'d': 'e'}

    assert transport.is_empty()
    assert transport2.is_empty()
    assert transport3.is_empty()


def test_inter_realm_communication(transport, transport2):
    transport.connect('a.realm')
    transport2.connect('another.realm')

    transport2.receive(OP.SUBSCRIBE, transport2.generate_id(), {}, 'a.topic')
    opcode, args = transport2.get_reply()

    transport.receive(OP.PUBLISH, transport.generate_id(), {}, 'a.topic', ['a'], {'b': 'c'})

    assert transport.is_empty()
    assert transport2.is_empty()


def test_failed_register_unregister(transport, transport2):
    transport.connect('a.realm')
    transport2.connect('a.realm')

    transport.receive(OP.REGISTER, transport.generate_id(), {}, 'a.procedure')
    opcode, args = transport.get_reply()
    assert opcode == OP.REGISTERED
    assert Pattern('id', 'id')(*args)
    assert transport._last_id == args[0]
    assert transport.is_empty()
    transport_register_id = args[1]

    transport.receive(OP.REGISTER, transport.generate_id(), {}, 'a.procedure')
    opcode, args = transport.get_reply()
    assert opcode == OP.ERROR
    assert Pattern('opcode', 'id', 'dict', 'uri!')(*args)
    assert args[0] == OP.REGISTER
    assert args[3] == 'wamp.error.procedure_already_exists'
    assert transport.is_empty()

    transport2.receive(OP.REGISTER, transport2.generate_id(), {}, 'a.procedure')
    opcode, args = transport2.get_reply()
    assert opcode == OP.ERROR
    assert Pattern('opcode', 'id', 'dict', 'uri!')(*args)
    assert args[0] == OP.REGISTER
    assert args[3] == 'wamp.error.procedure_already_exists'
    assert transport2.is_empty()

    transport2.receive(OP.UNREGISTER, transport2.generate_id(), transport_register_id)
    opcode, args = transport2.get_reply()
    assert opcode == OP.ERROR
    assert Pattern('opcode', 'id', 'dict', 'uri!')(*args)
    assert args[0] == OP.UNREGISTER
    assert args[3] == 'wamp.error.no_such_registration'
    assert transport2.is_empty()

    transport.receive(OP.UNREGISTER, transport.generate_id(), transport_register_id)
    opcode, args = transport.get_reply()
    assert opcode == OP.UNREGISTERED
    assert Pattern('id')(*args)
    assert args[0] == transport._last_id
    assert transport.is_empty()

    transport.receive(OP.UNREGISTER, transport.generate_id(), transport_register_id)
    opcode, args = transport.get_reply()
    assert opcode == OP.ERROR
    assert Pattern('opcode', 'id', 'dict', 'uri!')(*args)
    assert args[0] == OP.UNREGISTER
    assert args[3] == 'wamp.error.no_such_registration'
    assert transport.is_empty()


def test_failed_mixed_unsubscribe(transport, transport2):
    transport.connect('a.realm')
    transport2.connect('a.realm')

    transport.receive(OP.SUBSCRIBE, transport.generate_id(), {}, 'a.topic')
    opcode, args = transport.get_reply()
    transport_a_topic_subscription_id = args[1]

    transport2.receive(OP.UNSUBSCRIBE, transport2.generate_id(), transport_a_topic_subscription_id)
    opcode, args = transport2.get_reply()
    assert opcode == OP.ERROR
    assert Pattern('opcode', 'id', 'dict', 'uri!')(*args)
    assert args[0] == OP.UNSUBSCRIBE
    assert args[3] == 'wamp.error.no_such_subscription'
    assert transport2.is_empty()

    transport.receive(OP.UNSUBSCRIBE, transport.generate_id(), transport_a_topic_subscription_id)
    opcode, args = transport.get_reply()
    assert opcode == OP.UNSUBSCRIBED
    assert Pattern('id')(*args)
    assert transport.is_empty()

    transport.receive(OP.UNSUBSCRIBE, transport.generate_id(), transport_a_topic_subscription_id)
    opcode, args = transport.get_reply()
    assert opcode == OP.ERROR
    assert Pattern('opcode', 'id', 'dict', 'uri!')(*args)
    assert args[0] == OP.UNSUBSCRIBE
    assert args[3] == 'wamp.error.no_such_subscription'
    assert transport.is_empty()


def test_call_invocation_error(transport, transport2):
    transport.connect('a.realm')
    transport2.connect('a.realm')

    transport.receive(OP.REGISTER, transport.generate_id(), {}, 'a.procedure')
    opcode, args = transport.get_reply()

    transport2.receive(OP.CALL, transport2.generate_id(), {}, 'a.procedure', ['a'], {'b': 'c'})
    opcode, args = transport.get_reply()

    transport.receive(OP.ERROR, OP.INVOCATION, args[0], {}, 'a.procedure.error.no_happy_time', ['a'], {'b': 'c'})

    opcode, args = transport2.get_reply()
    assert opcode == OP.ERROR
    assert Pattern('opcode', 'id', 'dict', 'uri', 'list', 'dict')(*args)
    assert args[0] == OP.CALL
    assert args[1] == transport2._last_id
    assert args[3] == 'a.procedure.error.no_happy_time'
    assert transport2.is_empty()


def test_call_unknown(transport):
    transport.connect('a.realm')
    transport.receive(OP.CALL, transport.generate_id(), {}, 'a.procedure', ['a'], {'b': 'c'})
    opcode, args = transport.get_reply()
    assert opcode == OP.ERROR
    assert Pattern('opcode', 'id', 'dict', 'uri!')(*args)
    assert args[0] == OP.CALL
    assert args[1] == transport._last_id
    assert args[3] == 'wamp.error.no_such_procedure'
    assert transport.is_empty()


def test_call_connection_lost(transport, transport2):
    transport.connect('a.realm')
    transport2.connect('a.realm')

    transport.receive(OP.REGISTER, transport.generate_id(), {}, 'a.procedure')
    opcode, args = transport.get_reply()

    transport2.receive(OP.CALL, transport2.generate_id(), {}, 'a.procedure', ['a'], {'b': 'c'})

    transport.disconnect()

    opcode, args = transport2.get_reply()
    assert opcode == OP.ERROR
    assert Pattern('opcode', 'id', 'dict', 'uri!')(*args)
    assert args[0] == OP.CALL
    assert args[1] == transport._last_id
    assert args[3] == 'wamp.error.callee_lost'
    assert transport2.is_empty()


def test_connection_lost_unregister_disable_calls(transport, transport2):
    transport.connect('a.realm')
    transport2.connect('a.realm')

    transport2.receive(OP.REGISTER, transport2.generate_id(), {}, 'a.procedure')
    opcode, args = transport2.get_reply()

    transport2.receive(OP.SUBSCRIBE, transport2.generate_id(), {}, 'a.topic')
    opcode, args = transport2.get_reply()

    transport2.disconnect()

    transport.receive(OP.CALL, transport.generate_id(), {}, 'a.procedure', ['a'], {'b': 'c'})
    opcode, args = transport.get_reply()
    assert opcode == OP.ERROR
    assert Pattern('opcode', 'id', 'dict', 'uri!')(*args)
    assert args[0] == OP.CALL
    assert args[1] == transport._last_id
    assert args[3] == 'wamp.error.no_such_procedure'
    assert transport.is_empty()

    transport.receive(OP.PUBLISH, transport.generate_id(), {}, 'a.topic', ['b'], {'c': 'd'})


def test_invalid_opcodes_syntaxes(transport):
    assert transport.session.state == STATE_UNAUTHENTICATED
    transport.connect('a.realm')

    transport.receive(OP.REGISTER, transport.generate_id(), 'a.bogus.procedure')
    opcode, args = transport.get_reply()
    assert opcode == OP.ABORT
    assert Pattern('dict', 'uri!')(*args)
    assert args[1] == 'wamp.error.protocol_violation'
    assert transport.is_empty()
    assert transport.session.state == STATE_CLOSED

    transport.connect('a.realm')

    transport.receive(500000, transport.generate_id(), 'a.bogus.procedure')
    opcode, args = transport.get_reply()
    assert opcode == OP.ABORT
    assert Pattern('dict', 'uri!')(*args)
    assert args[1] == 'wamp.error.protocol_violation'
    assert transport.is_empty()
    assert transport.session.state == STATE_CLOSED

    transport.connect('a.realm')
    transport.receive(OP.HELLO, 'a.realm', {})
    opcode, args = transport.get_reply()
    assert opcode == OP.ABORT
    assert Pattern('dict', 'uri!')(*args)
    assert args[1] == 'wamp.error.protocol_violation'
    assert transport.is_empty()
    assert transport.session.state == STATE_CLOSED


def test_inaccessible_realm(transport):
    opcode, args = transport.connect('a.realm_deny')
    assert opcode == OP.ABORT
    assert Pattern('dict', 'uri!')(*args)
    assert args[1] == 'wamp.error.no_such_realm'
    assert transport.is_empty()
    assert transport.session.state == STATE_CLOSED
