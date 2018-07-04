import logging

from .opcodes import OP
from .pattern import Pattern
from .realm import realm_manager
from .utils import generate_id

STATE_UNAUTHENTICATED = 0
STATE_AUTHENTICATING = 1
STATE_AUTHENTICATED = 2
STATE_CLOSED = 3

logger = logging.getLogger(__name__)


class Session:
    state = STATE_UNAUTHENTICATED

    supported_roles = None
    agent = None
    realm = None

    def __init__(self, transport):
        self.last_id = 0
        self.transport = transport

        self.command_registry = {
            OP.HELLO: (
                self.handle_hello,
                Pattern('uri', 'dict'),
                STATE_UNAUTHENTICATED,
            ),
            OP.ABORT: (
                self.handle_abort,
                Pattern('dict', 'uri'),
                STATE_AUTHENTICATED,
            ),
            OP.GOODBYE: (
                self.handle_goodbye,
                Pattern('dict', 'uri!'),
                STATE_AUTHENTICATED,
            ),

            OP.ERROR: (
                self.handle_error,
                Pattern('opcode', 'id', 'dict', 'uri!', 'list?', 'dict?'),
                STATE_AUTHENTICATED,
            ),

            OP.PUBLISH: (
                self.handle_publish,
                Pattern('id', 'dict', 'uri', 'list?', 'dict?'),
                STATE_AUTHENTICATED,
            ),

            OP.SUBSCRIBE: (
                self.handle_subscribe,
                Pattern('id', 'dict', 'uri', 'list?', 'dict?'),
                STATE_AUTHENTICATED,
            ),
            OP.UNSUBSCRIBE: (
                self.handle_unsubscribe,
                Pattern('id', 'id'),
                STATE_AUTHENTICATED,
            ),

            OP.CALL: (
                self.handle_call,
                Pattern('id', 'dict', 'uri', 'list?', 'dict?'),
                STATE_AUTHENTICATED,
            ),
            OP.REGISTER: (
                self.handle_register,
                Pattern('id', 'dict', 'uri'),
                STATE_AUTHENTICATED,
            ),
            OP.UNREGISTER: (
                self.handle_unregister,
                Pattern('id', 'id'),
                STATE_AUTHENTICATED,
            ),
            OP.YIELD: (
                self.handle_yield,
                Pattern('id', 'dict', 'list?', 'dict?'),
                STATE_AUTHENTICATED,
            ),
        }

    def handle_command(self, opcode, *args):
        logger.debug('Handling opcode:%s with args:%r' % (opcode, args, ))
        if opcode not in self.command_registry:
            self.send(OP.ABORT, {'message': 'Invalid opcode'}, 'wamp.error.protocol_violation')
            self.close_session()
            return

        func, pattern, allowed_state = self.command_registry[opcode]
        if self.state != allowed_state:
            self.send(OP.ABORT, {'message': 'Tried to execute command in wrong state'}, 'wamp.error.protocol_violation')
            self.close_session()
            return

        if not pattern(*args):
            self.send(OP.ABORT, {'message': 'Command syntax does not match any allowed syntaxes'}, 'wamp.error.protocol_violation')
            self.close_session()
            return

        try:
            func(*args)
        except:
            logger.exception('Failed to execute command %r with args %r' % (func, args, ))
            self.send(OP.ABORT, {'message': 'Failed to execute command'}, 'wamp.error.protocol_violation')
            self.close_session()
            return

    def handle_hello(self, realm, details):
        if not self.transport.realm_allowed(realm):
            self.send(OP.ABORT, {'message': 'You do not have access to this realm.'}, 'wamp.error.no_such_realm')
            self.close_session()
            return

        self.supported_roles = details.get('roles')
        self.agent = details.get('agent')

        self.realm = realm_manager.get_realm(realm)
        if not self.realm:
            self.send(OP.ABORT, {'message': 'The realm does not exist.'}, 'wamp.error.no_such_realm')
            self.close_session()
            return

        self.realm.session_joined(self)

        self.state = STATE_AUTHENTICATED
        self.send(OP.WELCOME, generate_id(), {
            'roles':{
                'broker': {},
                'dealer': {},
            }
        })

    def handle_abort(self, details, reason):
        logger.info('Client aborted our session with reason:%s and details:%r' % (reason, details, ))
        self.close_session()

    def handle_goodbye(self, details, reason):
        self.send(OP.GOODBYE, {}, 'wamp.close.goodbye_and_out')
        self.close_session()

    def handle_error(self, opcode, request_id, details, error, args=None, kwargs=None):
        if opcode == OP.INVOCATION:
            self.realm.error_invocation(self, request_id, details, error, args, kwargs)
        else:
            logger.warning('Unhandled error for opcode:%s' % (opcode, ))

    ### Broker functionality ###
    def handle_publish(self, request_id, options, topic, args=None, kwargs=None):
        publish_id = self.realm.publish(self, options, topic, args, kwargs)
        if publish_id:
            self.send(OP.PUBLISHED, request_id, publish_id)

    def handle_subscribe(self, request_id, options, topic):
        subscription_id = self.realm.subscribe(self, options, topic)
        self.send(OP.SUBSCRIBED, request_id, subscription_id)

    def handle_unsubscribe(self, request_id, subscription_id):
        if self.realm.unsubscribe(self, subscription_id):
            self.send(OP.UNSUBSCRIBED, request_id)
        else:
            self.send(OP.ERROR, OP.UNSUBSCRIBE, request_id, {}, 'wamp.error.no_such_subscription')

    ### Dealer functionality ###
    def handle_call(self, request_id, options, procedure, args=None, kwargs=None):
        if not self.realm.call(self, request_id, procedure, args, kwargs):
            self.send(OP.ERROR, OP.CALL, request_id, {}, 'wamp.error.no_such_procedure')

    def handle_register(self, request_id, options, procedure):
        registration_id = self.realm.register(self, procedure)
        if registration_id:
            self.send(OP.REGISTERED, request_id, registration_id)
        else:
            self.send(OP.ERROR, OP.REGISTER, request_id, {}, 'wamp.error.procedure_already_exists')

    def handle_unregister(self, request_id, registration_id):
        if self.realm.unregister(self, registration_id):
            self.send(OP.UNREGISTERED, request_id)
        else:
            self.send(OP.ERROR, OP.UNREGISTER, request_id, {}, 'wamp.error.no_such_registration')

    def handle_yield(self, request_id, options, args=None, kwargs=None):
        self.realm.yield_(self, request_id, args, kwargs)

    def close_session(self):
        self.state = STATE_CLOSED
        self.transport.close_session()
        if self.realm:
            self.realm.session_lost(self)

    def send(self, opcode, *args):
        logger.debug('Sending response opcode:%s, args:%r' % (opcode, args, ))
        self.transport.send(opcode, *args)

    def generate_id(self):
        self.last_id += 1
        return self.last_id
