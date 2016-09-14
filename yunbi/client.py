import urllib.request    
#导入 urllib模块的request模块（urllib的request模块可以非常方便地抓取URL内容，也就是发送一个GET请求到指定的页面，然后返回HTTP的响应：）
import urllib.error
#导入 urllib模块的error模块（异常处理）
import urllib.parse
#导入 urllib模块的parse模块（pass）
import urllib
#导入 urllib模块
import json
#导入 json模块
import time
#导入 time模块
import hmac
#导入 hmac模块 （Python中的用于加密的函数，验证数字签名用）
import hashlib
#导入 hashlib模块（Python的hashlib提供了常见的摘要算法，如MD5，SHA1等等）Python中的用于加密的函数


BASE_URL = 'https://yunbi.com/'  #云币地址

API_BASE_PATH = '/api/v2'        #云币api路径
API_PATH_DICT = {                #定义data 字典类型
    # GET
    'members': '%s/members/me.json',      #用户名 （字符串类型）
    'markets': '%s/markets.json',         #市场名称（字符串类型）

    #market code required in url as {market}.json
    'tickers' : '%s/tickers/%%s.json',    #市场价格信息（买入价，卖出价，最高价，最低价，最后成交价，成交量）
    #market required in url query string as '?market={market}'
    'orders': '%s/orders.json',        #你的订单信息（特定市场中的订单信息）

    #order id required in url query string as '?id={id}'
    'order': '%s/order.json',           #你的订单信息（特定id的订单信息）

    #market required in url query string as '?market={market}'
    'order_book': '%s/order_book.json',   #当前市场的挂单信息

    #market required in url query string as '?market={market}'
    'trades': '%s/trades.json',    #获得最近的订单撮合后形成的交易信息

    #market required in url query string as '?market={market}'
    'my_trades': '%s/trades/my.json',     #获取订单撮合后形成的交易信息
    #Get OHLC(k line) of specific market
    'k': '%s/k.json',                #获取特定市场的k线信息
    #clear orders in all markets---Cancel all my orders
    'clear': '%s/orders/clear.json',     #在特定市场中所有取消订单

    #delete a specific order
    'delete_order': '%s/order/delete.json',       #取消一个特定的订单

    #TODO multi orders API
    'multi_orders': '%s/orders/multi.json',   #创建多个销售/购买订单
}

class Client():     #创建一个客户端的类

    def __init__(self, access_key=None, secret_key=None):
        if access_key and secret_key:
            self.auth = Auth(access_key, secret_key)
        else:
            print("provide key please")

    def getBalance(self):
        result = self.get('members', sigrequest=True)
        balance = {}
        for record in result["accounts"]:
            balance[record["currency"]] = float(record["balance"])
            balance[record["currency"]+"_locked"] = float(record["locked"])
        return balance

    def getTickers(self,market='btscny'):
        ticker = self.get('tickers', {'market': market})["ticker"]
        result = {"vol": float(ticker["vol"]), "buy": float(ticker["buy"]),
                  "last": float(ticker["last"]),
                  "sell": float(ticker["sell"])}
        return result

    def getOpenOrders(self,market='btscny'):
        orders = self.get('orders', {'market': market}, True)
        openorders=[]
        for order in orders:
            openorders.append({"amount": float(order["volume"]), "type": order["side"], "price": float(order["price"]),"id": order["id"],})
        return openorders

    def getOrderBook(self,market='btscny'):
        orderbooks = self.get('order_book', {'market': market}, True)
        if orderbooks["asks"][0]["id"] == 202429485 and orderbooks["asks"][0]["price"] == "0.0326":#just fix the bug
            orderbooks["asks"].pop(0)
        asks = []
        for record in orderbooks["asks"]:
            asks.append([float(record['price']), float(record['volume'])])

        bids = []
        for record in orderbooks["bids"]:
            bids.append([float(record['price']), float(record['volume'])])
        return {"bids": bids, "asks": asks}

    def getMyTradeList(self,market='btscny'):
        return self.get('trades', {'market': market}, True)

    def submitOrder(self,params):
        return self.client.yunbiClient.post('orders', params)

    def get_api_path(self,name):
        path_pattern = API_PATH_DICT[name]
        return path_pattern % API_BASE_PATH

    def get(self, name, params=None, sigrequest=False):
        verb = "GET"
        path =self.get_api_path(name)
        if "%s" in path:
            path = path % params["market"]
        if  sigrequest:
            signature, query = self.auth.sign_params(verb, path, params)
            query = self.auth.urlencode(query)
            url = "%s%s?%s&signature=%s" % (BASE_URL, path, query, signature)
        else:
            url = "%s%s?" % (BASE_URL, path)
        resp = urllib.request.urlopen(url,timeout=5)
        data = resp.readlines()
        resp.close()
        if len(data):
            return json.loads(data[0].decode('utf-8'))


    def post(self, name, params=None):
        verb = "POST"
        path = self.get_api_path(name)
        print (params)
        signature, data = self.auth.sign_params(verb, path, params)
        url = "%s%s" % (BASE_URL, path)
        data.update({"signature":signature})
        data = urllib.parse.urlencode(data)
        data = data.encode('utf-8')
        resp = urllib.request.urlopen(url, data,timeout=5)
        data = resp.readlines()
        resp.close()
        if len(data):
            return json.loads(data[0].decode('utf-8'))

#--------------------------------------------------------------------------------------

class Auth():
    def __init__(self, access_key, secret_key):
        self.access_key = access_key
        self.secret_key = secret_key

    def urlencode(self, params):
        keys = params.keys()
        keys = sorted(keys)
        query = ''
        for key in keys:
            value = params[key]
            if key != "orders":
               query = "%s&%s=%s" % (query, key, value) if len(query) else "%s=%s" % (key, value)
            else:
                #this ugly code is for multi orders API, there should be an elegant way to do this
                d = {key: params[key]}
                for v in value:
                    ks = v.keys()
                    ks = sorted(ks)
                    for k in ks:
                        item = "orders[][%s]=%s" % (k, v[k])
                        query = "%s&%s" % (query, item) if len(query) else "%s" % item
        return query

    def sign(self, verb, path, params=None):
        query = self.urlencode(params)
        msg = ("|".join([verb, path, query])).encode('utf-8')
        signature = hmac.new(self.secret_key.encode('utf-8'), msg=msg, digestmod=hashlib.sha256).hexdigest()

        return signature

    def sign_params(self, verb, path, params=None):
        if not params:
            params = {}
        params.update({'tonce': int(1000*time.time()), 'access_key': self.access_key})
        signature = self.sign(verb, path, params)

        return signature, params
