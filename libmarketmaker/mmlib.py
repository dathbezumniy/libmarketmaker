import ujson
import requests
from pprint import pprint
import builtins
import functools
from itertools import count
from electrums import all_tickers, utxo_link, eth_link
from requests.exceptions import RequestException



DEFAULT_HTTP_TIMEOUT = 120
DEFAULT_RPC_PORT = 7783
DEFAULT_RPC_HOST = "127.0.0.1"



class MMProxy():
    _ids = count(0)

    def __init__(self,
                 userpass="testuser",
                 rpcport=DEFAULT_RPC_PORT,
                 rpchost=DEFAULT_RPC_HOST,
                 timeout=DEFAULT_HTTP_TIMEOUT):
        self.timeout = timeout
        self.userpass = userpass
        self.rpcport = rpcport
        self.rpchost = rpchost


    def __getattr__(self, request):
        _id = next(self._ids)

        def call(**params):
            if 'batch' not in request:
                post_val = {
                    'jsonrpc': '2.0',
                    'userpass': self.userpass,
                    'method': request,
                    'id': _id
                }
                for param, value in params.items():
                    post_val.update({param: value})
            else:
                post_val = []
                for key in params:
                    post_dict = {
                        'jsonrpc': '2.0',
                        'userpass': self.userpass,
                        'method': params.get(key).get('method'),
                        'id': _id
                    }
                    for param, value in params.get(key).items():
                        post_dict.update({param: value})
                    post_val.append(post_dict)

            url = 'http://{}:{}'.format(self.rpchost, self.rpcport)
            post_data = ujson.dumps(post_val)

            try:
                resp = requests.post(url, data=post_data, timeout=self.timeout).json()
            except ValueError:
                resp = str(requests.post(url, data=post_data, timeout=self.timeout).content)
            return resp

        return call



class Parser:
    def __init__(self, all_tickers=all_tickers, utxo_link=utxo_link, eth_link=eth_link):
        self.all_tickers = all_tickers
        self.utxo_link = utxo_link
        self.eth_link = eth_link
        self.repo_links = self.combine_electrums_repo_links()
        self.electrums = self.gather_electrumx_links_into_dict(self.repo_links)
        self.available_coins = list(self.electrums.keys())


    def combine_electrums_repo_links(self):
        repo_links = {}
        for ticker in self.all_tickers:
            if 'ETH' in ticker:
                repo_links[ticker] = "{}{}".format(self.eth_link, ticker)
            else:
                repo_links[ticker] = "{}{}".format(self.utxo_link, ticker)
        return repo_links


    def gather_electrumx_links_into_dict(self, electrum_links):
        output = {}
        print("Getting electrums from official coins repo --> https://github.com/KomodoPlatform/coins")
        for coin, link in electrum_links.items():
            print("{} --> {}".format(coin, link))
            try:
                r = requests.get(link).json()
            except RequestException as e:
                logging.error(e)
            urls = []
            if 'rpc_nodes' in r:
                for url in r['rpc_nodes']:
                    try:
                        if url['protocol']:
                            continue
                    except KeyError:
                        url['protocol'] = "TCP"
                    url.pop('contact', None)
                    urls.append(url)
            else:
                for url in r:
                    try:
                        if url['protocol']:
                            continue
                    except KeyError:
                        url['protocol'] = "TCP"
                    url.pop('contact', None)
                    urls.append(url)
            output[coin] = urls
        return output





class MarketMaker:
    def __init__(self, userpass="testuser"):
        self.parser = Parser()
        self.electrums = self.parser.electrums
        self.available_coins = self.parser.available_coins
        
        self.userpass = userpass
        self.proxy = MMProxy(self.userpass)
        


    ###! Wallet API
    def wallet(self):
        enabled_coins = self.get_enabled_coins()

        print('Enabled coins {}, total: {}'.format(enabled_coins, len(enabled_coins)))
        print('Balances/Addresses: ')
        for coin in enabled_coins:
            print(self.proxy.my_balance(coin=coin))

    
    def my_balance(self, coin: str):
        return self.proxy.my_balance(coin=coin)


    def electrum(self, coin: str):
        return pprint(self.proxy.electrum(coin=coin,
                                          servers=self.electrums[coin],
                                          tx_history=True,
                                          mm2='1'))


    def electrum_batch(self, coins: list):
        for coin in coins:
            self.electrum(coin)


    def enable(self, coin: str):
        return pprint(self.proxy.enable(coin=coin,
                                        urls=self.electrums[coin],
                                        tx_history=True,
                                        mm2='1'))


    def enable_erc20(self, coin: str):
        swap_contract_address = "0x8500AFc0bc5214728082163326C2FF0C73f4a871"
        eth_nodes = [ url['url'] for url in self.electrums[coin] ]
        return pprint(self.proxy.enable(coin=coin,
                                        urls=eth_nodes,
                                        swap_contract_address=swap_contract_address,
                                        tx_history=True,
                                        mm2='1'))


    def enable_batch(self, coins: list):
        for coin in coins:
            self.enable(coin)


    def kmd_rewards_info(self):
        return pprint(self.proxy.kmd_rewards_info())


    def withdraw(self, coin: str, to: str, amount: str):
        print("This method generates !!!a raw transaction!!! which should then be broadcasted using send_raw_transaction method in order to reach the mempool")
        return pprint(self.proxy.withdraw(coin=coin, to=to, amount=amount))


    def withdraw_max(self, coin: str, to: str, max=True):
        print("This method generates !!!a raw transaction!!! which should then be broadcasted using send_raw_transaction in order to reach the mempool")
        return pprint(self.proxy.withdraw(coin=coin, to=to, max=max))


    def send_raw_transaction(self, coin: str, tx_hex:str):
        return self.proxy.send_raw_transaction(coin=coin, tx_hex=tx_hex)


    def combined_send(self, coin: str, to: str, amount: str):
        tx_hex = self.proxy.withdraw(coin=coin, to=to, amount=amount)
        
        print("Broadcasting... : {}".format(tx_hex))
        return self.proxy.send_raw_transaction(coin=coin, tx_hex=tx_hex)
    

    def combined_send_max(self, coin: str, to: str, max=True):
        response = self.proxy.withdraw(coin=coin, to=to, max=max)
        try:
            tx_hex = response['tx_hex']
        except KeyError:
            return response
            
        print("Broadcasting... : {}".format(tx_hex))
        return self.proxy.send_raw_transaction(coin=coin, tx_hex=tx_hex)


    def disable_coin(self, coin: str):
        return pprint(self.proxy.disable_coin(coin=coin))

    
    def disable_batch(self, coins: list):
        for coin in coins:
            self.disable_coin(coin)

    
    def disable_all(self):
        for coin in self.available_coins:
            self.disable_coin(coin)


    def get_enabled_coins(self):
        return [ coin['ticker']
                 for coin
                 in self.proxy.get_enabled_coins()['result'] ]



    def my_tx_history(self, coin: str, limit=5, max=False):
        return pprint(self.proxy.my_tx_history(coin=coin,
                                               limit=limit,
                                               max=max)['result'])


    def validateaddress(self, coin: str, address: str):
        return self.proxy.validateaddress(coin=coin, address=address)['result']

    
    def show_priv_key(self, coin: str):
        return self.proxy.show_priv_key(coin=coin)['result']







    ###! Trading API
    def setprice(self, base: str, rel:str, volume: float, price: float):
        return pprint(self.proxy.setprice(base=base, rel=rel, volume=volume, price=price)['result'])
    
    
    def setprice_max(self, base: str, rel:str, price: float, max=True):
        return pprint(self.proxy.setprice(base=base, rel=rel, max=max, price=price)['result'])



    def buy(self, base: str, rel: str, volume: float, price: float):
        return pprint(self.proxy.buy(base=base, rel=rel, volume=volume, price=price)['result'])
    

    def sell(self, base: str, rel: str, volume: float, price: float):
        return pprint(self.proxy.sell(base=base, rel=rel, volume=volume, price=price)['result'])



    def max_taker_vol(self, coin: str):
        return self.proxy.max_taker_vol(coin=coin)


    def my_orders(self):
        return pprint(self.proxy.my_orders()['result'])


    def order_status(self, uuid: str):
        return pprint(self.proxy.order_status(uuid=uuid)['result'])

    
    def my_recent_swaps(self, limit=10):
        return pprint(self.proxy.my_recent_swaps(limit=limit)['result'])

    
    def my_swap_status(self, uuid: str):
        return pprint(self.proxy.my_swap_status(uuid=uuid))


    def set_required_confirmations(self, coin: str, confirmations: int):
        return pprint(self.proxy.set_required_confirmations(coin=coin, confirmations=confirmations))


    def set_requires_notarization(self, coin: str, requires: bool):
        return pprint(self.proxy.set_requires_notarization(coin=coin, requires_notarization=requires))



    def orderbook(self, base: str, rel: str):
        return pprint(self.proxy.orderbook(base=base, rel=rel))


    def cancel_all_orders(self):
        return pprint(self.proxy.cancel_all_orders(cancel_by={"type": "All"})['result'])


    def cancel_all_orders_by_pair(self, base: str, rel: str):
        return pprint(self.proxy.cancel_all_orders(cancel_by= {
                                                                "type": "Pair",
                                                                "data": {
                                                                            "base": base,
                                                                            "rel" : rel
                                                                        }
                                                              })['result'])


    def cancel_all_orders_by_coin(self, coin: str):
        return pprint(self.proxy.cancel_all_orders(cancel_by= {
                                                                "type": "Coin",
                                                                "data": {
                                                                            "ticker": coin
                                                                        }
                                                              })['result'])
    

    def cancel_order_by_uuid(self, uuid: str):
        return pprint(self.proxy.cancel_order(uuid=uuid))








    ###! Utilities
    def list_banned_pubkeys(self):
        return pprint(self.proxy.list_banned_pubkeys()['result'])
    

    def unban_pubkeys(self, pubkeys: list):
        by = {"type":"Few","data": pubkeys}
        return pprint(self.proxy.unban_pubkeys(unban_by=by))


    def unban_all_pubkeys(self):
        by = {"type":"All"}
        return pprint(self.proxy.unban_pubkeys(unban_by=by)['result'])


    def version(self):
        return pprint(self.proxy.version())


    def help(self):
        return pprint(self.proxy.help())


    def stop(self):
        return pprint(self.proxy.stop()['result'])





