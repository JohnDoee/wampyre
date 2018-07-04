WAMPyre
=======

.. image:: https://travis-ci.org/JohnDoee/wampyre.svg?branch=master
   :target: https://travis-ci.org/JohnDoee/wampyre

WAMPyre is a Python WAMP router with a bit of a pluggable architecture.

The goal is a basic router that allows for embedding into all-in-one applications.
For every other situation, crossbar (or another implementation) is the correct choice.

It also includes a transport for Autobahn so you don't need to do that over TCP.

Who should use this
-------------------

Probably only me, the only use-case is where you need a Python router and cannot use Crossbar,
i.e. embeddable with more premissive license.

How to use
----------

Use with Django Channels, add the following to routing.py:

.. code-block:: Python

    from wampyre.transports.django import WAMPRouter

    application = ProtocolTypeRouter({
        "websocket": URLRouter([
            path("router/", WAMPRouter),
        ]),
    })

This way you can use authentication the same way you do with other Django Channels Websocket projects.

There is also a built-in transport for Autobahn that makes it possible to interact with the Router without
creating an actual TCP connection.

.. code-block:: Python

    from autobahn.twisted.wamp import ApplicationSession
    from wampyre.transports.autowamp import ApplicationRunner
    from twisted.internet.defer import inlineCallbacks

    class Component(ApplicationSession):
        """
        An application component that publishes an event every second.
        """

        @inlineCallbacks
        def onJoin(self, details):
            print("session attached")
            def ping():
                return 'Pong!'
            yield self.register(ping, u'com.arguments.ping')

    ApplicationRunner('crossbardemo', ).run(Component)

This can be put in any file, just make sure it's loaded when Django Channels is initiated.

License
-------

MIT