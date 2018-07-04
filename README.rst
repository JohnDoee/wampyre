WAMPyre
=======

WAMPyre is a Python WAMP router with a bit of a pluggable architecture.

The goal is a basic router that allows for embedding into all-in-one applications.
For every other situation, crossbar (or another implementation) is the correct choice.

It also includes a transport for Autobahn so you don't need to do that over TCP.

Who should use this
-------------------

Probably only me, the only use-case is where you need a Python router and cannot use Crossbar,
i.e. embeddable with more premissive license.

License
-------

MIT