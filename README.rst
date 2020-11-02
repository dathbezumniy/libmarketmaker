libmarketmaker
==============

Python3 library to proxy marketmaker2 remote calls.

This lib is intended to be used in python-based applications and python-REPL.

API reference:
https://developers.atomicdex.io/basic-docs/atomicdex/atomicdex-api.html

Variants:
---------

``mm2_rpclib_req`` based on requests library
https://requests.kennethreitz.org/en/master/

Deps:

::

   pip install requests ujson



Usage example:
~~~~~~~~~~~~~~

.. code:: python

       from mm2rpclib_req import MMProxy
       
       host = {
           'userpass': 'testuser',
           'rpchost': '127.0.0.1',
           'rpcport': 7783
       }
       proxy = MMProxy(host)
       
       proxy.version()


RPC params should be passed as \**kwargs:

``shell script     curl --url "http://127.0.0.1:7783" --data "{\"userpass\":\"$userpass\",\"method\":\"orderbook\",\"base\":\"KMD\",\"rel\":\"BTC\"}``

Will be:

.. code:: python

       proxy.orderbook(base='KMD', rel='BTC')

All RPC methods will return dictionary with server’s response, errors
are returned as is:

.. code:: python

       coin = 'KMD'  # str
       electrum_url = "example.domain.net:0000"  # domain:port
       r = proxy.electrum(coin=coin, servers=[{'url': electrum_url, 'protocol': 'TCP'}], mm2='1')
       print(r)
       print(type(r))
       r = proxy.electrum(coin=coin, servers=[{'url': electrum_url, 'protocol': 'TCP'}], mm2='1')


.. code:: text

       {'address': '0000000000000000000000000000000000', 'balance': '0', 'coin': 'KMD',
        'locked_by_swaps': '0', 'required_confirmations': 1, 'result': 'success'}
       <class 'dict'>
       {'error': 'rpc:339] lp_commands:85] lp_coins:643] Coin KMD already initialized'}
       <class 'dict'>


Batch requests:
~~~~~~~~~~~~~~~

Batch requests should be passed as dictionary via batch() method.

Example to batch 10 identical setprice calls:

.. code:: python

       req = {
           "method": "setprice", "base": base, "rel": rel, "price": price, "volume": volume, "cancel_previous": False
       }
       rec_d = {}
       for i in range(10):
           rec_d.update({str(i): req})
       res = proxy.batch(**rec_d)