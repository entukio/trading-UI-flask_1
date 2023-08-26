from flask import Flask, render_template, request, url_for, flash, redirect
from binance.client import Client
import datetime
import _thread
import time

#Binance config

apikey = 'key'
apise = 'secret'

client = Client(apikey,apise)


app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret_key'

#Logic

waiting = []
active = []
complete = []
btc_price = {'price':'0','time':'0'}

def getBtcPrice():
    global btc_price
    btc = client.futures_symbol_ticker(symbol='BTCBUSD')
    btc_price['price'] = btc['price']
    btc_price['time'] = (datetime.datetime.fromtimestamp(btc['time'] / 1000)).strftime('%d-%m-%y %H:%M')


def WaitingtoActive():
    global waiting
    global active
    open = False
    for i in waiting:
        print(i['side'])
        if btc_price['price'] != '0':
            if i['side'] == 'long':
                if  float(i['price']) >= float(btc_price['price']):
                    #OpenLong
                    print('long',i['price'])
                    active.append(i)
                    waiting.remove(i)
                    open = True

            if i['side'] == 'short':
                if float(btc_price['price']) >= float(i['price']):
                    #Openshort
                    print('short',i['price'])
                    active.append(i)
                    waiting.remove(i)
                    open = True
    return open
        

def ActivetoComplete():
    global active
    global complete
    closed = False
    for i in active:
        if btc_price['price'] != '0':
            if i['side'] == 'long':
                if  float(i['stop']) >= float(btc_price['price']):
                    #closeLongSL
                    print('long',i['price'],'closed at: ',btc_price['price'])
                    complete.append(i)
                    active.remove(i)
                    closed = True

                elif  float(i['profit']) <= float(btc_price['price']):
                    #closeLongTP
                    print('long',i['price'],'closed at: ',btc_price['price'])
                    complete.append(i)
                    active.remove(i)
                    closed = True

            elif i['side'] == 'short':

                if  float(i['stop']) <= float(btc_price['price']):
                    #closeShortSL
                    print('short',i['price'],'closed at: ',btc_price['price'])
                    complete.append(i)
                    active.remove(i)
                    closed = True

                elif  float(i['profit']) >= float(btc_price['price']):
                    #closeShortTP
                    print('short',i['price'],'closed at: ',btc_price['price'])
                    complete.append(i)
                    active.remove(i)
                    closed = True
    return closed


def background():
    global btc_price
    while True:
        getBtcPrice()
        print('done BTC price',btc_price['time'])
        if WaitingtoActive() or ActivetoComplete():
            time.sleep(3)
            print('sleep 3, trade detected')
        else:
            print('no trade detected, 20s waiting')
            time.sleep(20)
        
    
def returnTrade(side,price,sl,tp):
    stop = 0.0
    profit = 0.0
    sl = float(sl)
    tp = float(tp)
    side = side
    price = float(price)
    if side == 'long':
        stop = price - (price * (sl / 1000))
        profit = price + (price * (sl / 1000)) * tp
    elif side == 'short':
        stop = price + (price * (sl / 1000))
        profit = price - (price * (sl / 1000)) * tp
    return side,price,stop,profit

def createWaiting(side,price,pair,size,leverage,gridperc,sl,tp,comment):

    order1 = float(price)
    order2 =float(price) * (float(gridperc)/1000 + 1)
    order3 =float(price) / (float(gridperc)/1000 + 1)

    price_arr = [order1,order2,order3]

    for orderprice in price_arr:

        side1,price1,stop,profit = returnTrade(side,orderprice,sl,tp)
        obj = {
            'side':side1,
            'price': price1,
            'pair': pair,
            'size': size,
            'leverage': leverage,
            'stop':stop,
            'profit': profit,
            'comment':comment,
            'grid%': gridperc,
            'sl%': sl,
            'tp%': tp
        }

        waiting.append(obj)

   

    return waiting[0],waiting[1],waiting[2]


#Flask App

@app.route('/', methods = ['GET'])
def index():
    try:
        return render_template('index.html',waiting=waiting,active=active,complete=complete,btc_price=btc_price)
    except:
        print('error')

@app.route('/new_game', methods = ['POST'])
def new_game():
    price = request.form.get('price')
    side = request.form.get('side')
    pair = request.form.get('pair')
    size = request.form.get('size')
    leverage = request.form.get('leverage')
    gridperc = request.form.get('grid%')
    sl = request.form.get('SL')
    tp = request.form.get('TP')
    comment = request.form.get('comment')

    o1,o2,o3 = createWaiting(side,price,pair,size,leverage,gridperc,sl,tp,comment)

    print(o1,o2,o3)

    return render_template('index.html',waiting=waiting,active=active,complete=complete,btc_price=btc_price)

@app.route('/cancel_waiting_order',methods = ['POST'])
def cancel_waiting_order():
    input1 = request.form.get('orderID_internal').replace("'","").replace(" ","").replace("(","").replace(")","").split(',')
    
    for i in waiting:
        print(i['price'],input1[1])
        if i['side'] == input1[0] and float(i['price']) == float(input1[1]) and i['pair'] == input1[2]:
            print('matched',i['price'])
            waiting.remove(i)

    return render_template('index.html',waiting=waiting,active=active,complete=complete,btc_price=btc_price)


_thread.start_new_thread(background, ())

app.run(debug=True)

