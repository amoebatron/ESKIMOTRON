import io, sys, time, datetime, urllib2, json, winsound, titles
from poloniex import Poloniex
from bittrex import BittrexAPI

from ConfigParser import SafeConfigParser
import smtplib
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText

version = 0.7
# Get tradin configuration from trading.cfg

pairs = SafeConfigParser(allow_no_value=True)
pairs_location = 'trading.cfg'
loadedPairs = pairs.read([pairs_location])

# Get API configuration from default.cfg

config = SafeConfigParser()
config_location = 'default.cfg'
loadedFiles = config.read([config_location])
polo_key = config.get("POLONIEX","apikey")
polo_secret = config.get("POLONIEX","secret")
trex_key = config.get("BITTREX","apikey")
trex_secret = config.get("BITTREX","secret")

e_email = config.get("EMAILSERVER","email")
e_gmail = config.get("EMAILSERVER","gmail")
e_gpass = config.get("EMAILSERVER","gpass")

# initiate bots
polobot = Poloniex(polo_key, polo_secret)
trexbot = BittrexAPI(trex_key,trex_secret)

def alt_name_parser(name):
    namelist = name.split("/")
    code = str(namelist[0])
    return code.upper()

def core_name_parser(name):
    namelist = name.split("/")
    code = str(namelist[1])
    return code.upper()

def polo_pair_parser(name):
    namelist = name.split("/")
    codelist = ["NULL","NIL"]
    codelist[0] = namelist[1]
    codelist[1] = namelist[0]
    code = "_".join(codelist)
    return code

def trex_pair_parser(name):
    namelist = name.split("/")
    codelist = ["NULL","NIL"]
    codelist[0] = namelist[1]
    codelist[1] = namelist[0]
    code = "-".join(codelist)
    return code

def stamp_pair_parser(name):
    namelist = name.split("/")
    codelist = ["NULL","NIL"]
    codelist[0] = namelist[1]
    codelist[1] = namelist[0]
    code = "-".join(codelist)
    return code

def polo_validate():
    pairs_list = pairs.options("POLONIEX")
    num = len(pairs_list)
    ticker = polobot.returnTicker()
    new_list = []
    for i in range (0,num-1):
        try:
            pair_name = (str(pairs_list[i])).upper()
            pair_code = polo_pair_parser(pair_name)
            pair_ticker = ticker[pair_code]
            new_list.append(pair_name)
        except (KeyError, IndexError):
            pass
    return new_list

def trex_validate(): #need to fix this
    pairs_list = pairs.options("BITTREX")
    num = len(pairs_list)
    ticker = trexbot.getticker("BTC-AEON")
    new_list = []
    for i in range (0,num-1):
        try:
            pair_name = (str(pairs_list[i])).upper()
            pair_code = trex_pair_parser(pair_name)
            pair_ticker = ticker[pair_code]
            new_list.append(pair_name)
        except (KeyError, IndexError):
            pass
    return new_list

# see how far we have to go into the order book to fill the order

def get_buy_price(pair_name,core_unit_volume,exchange): 

    if exchange == "Poloniex":

        pair_code = polo_pair_parser(pair_name)
        while True:
            try:
                order_book = polobot.returnOrderBook(pair_code)
                break
            except:
                time.sleep(5)
        
        asks = order_book["asks"]
        core_ask_volume = 0.0
        for i, val in enumerate(asks):
            core_ask_volume += (float(val[0]) * val[1])
            if core_ask_volume >= core_unit_volume:
                return float(val[0])

    elif exchange == "Bittrex":

        pair_code = trex_pair_parser(pair_name)
        order_book = trexbot.getorderbook(pair_code,'sell',10)
        asks = order_book["result"]
        core_ask_volume = 0.0
        i = 0
        while True:
            vol_tuplex = asks[i]
            volume = float(vol_tuplex["Quantity"])
            price = float(vol_tuplex["Rate"])
            core_ask_volume += volume
            if core_ask_volume >= core_unit_volume:
                return float(price)
            i += 1

    else:
        
        print "Unknown error."


def get_sell_price(pair_name,alt_unit_amount,exchange):

    if exchange == "Poloniex":
    
        pair_code = polo_pair_parser(pair_name)
        while True:
            try:
                order_book = polobot.returnOrderBook(pair_code)
                break
            except:
                time.sleep(5)
                    
        bids = order_book["bids"]
        alt_ask_volume = 0.0
        for i, val in enumerate(bids):
            alt_ask_volume += (val[1])     
            if alt_ask_volume >= alt_unit_amount:
                return float(val[0])
            
    elif exchange == "Bittrex":

        pair_code = trex_pair_parser(pair_name)
        order_book = trexbot.getorderbook(pair_code,'buy',10)
        bids = order_book["result"]
        alt_ask_volume = 0.0
        i = 0
        while True:
            vol_tuplex = bids[i]
            volume = float(vol_tuplex["Quantity"])
            price = float(vol_tuplex["Rate"])
            alt_ask_volume += volume
            if alt_ask_volume >= alt_unit_amount:
                return float(price)
            i += 1
    else:
        print "Unknown error."

# new variables

poloniexPairs = polo_validate()
bittrexPairs = pairs.options("BITTREX")
enabled = True
emailer = False
body = ""

# old variables
report = "Nothing to report."
fromaddr = e_gmail
toaddr = e_email

def email_report(body,alt,exchange,trade_type,i):
    msg = MIMEMultipart()
    msg['From'] = fromaddr
    msg['To'] = toaddr
    msg['Subject'] = str(alt)+" "+(str(exchange).upper())+" "+(str(trade_type).upper())+" REPORT ["+str(i)+"]"
    msg.attach(MIMEText(body, 'plain'))
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(fromaddr, e_gpass)
    text = msg.as_string()
    server.sendmail(fromaddr, toaddr, text)
    server.quit()

def report(text):
    global body
    print text
##    if text == "":
##        text = "\n"
    body += text+"\n"
    
def program_timecycle(pair_name,trade_type,exchange,total,duration,frequency,threshold): ### migrate Trex routines

    global enabled
    global body
    exchange_error = False
    numTrades = 0
    header = pair_header(pair_name,exchange)
    pair_code = header[0]
    alt = header[1]
    core = header[2]
    altbal = header[3]
    corebal = header[4]
    last_price = header[5]

    i = 0
    core_total_so_far = 0.0
    alt_total_so_far = 0.0
    countingTime = 0.0
    targetTime = time.time()
    targetTime += (duration * 3600)
    
    
    if trade_type == "Buy":
        print ""
        titles.print_line()
        wait = False
        while True:
            startTime = time.time()
            extra = 0.00000001
            
            core_total = total
            if (not duration == 0 and not frequency == 0):
                core_unit_volume = (core_total/(duration*3600/frequency))+extra
                buy_price = get_buy_price(pair_name,core_unit_volume,exchange) #REQUIRED polo specific needs to change
                alt_unit_amount = core_unit_volume/buy_price
            else:
                core_unit_volume = core_total
                buy_price = get_buy_price(pair_name,core_unit_volume,exchange)
                alt_unit_amount = core_unit_volume/buy_price
            if buy_price <= threshold:
                wait = False
                i += 1
                if enabled:

                    if exchange == "Poloniex":
                        
                        exchange_response = polobot.buy(pair_code, buy_price, alt_unit_amount, 1)
                        for key in exchange_response:
                            value = exchange_response[key]
                            if key == "error":
                                exchange_error = True
                        if exchange_error:
                            print ""
                            print "Exchange Error: " + value
                            print ""
                            titles.print_line()
                            winsound.Beep(800,800)
                            break
                        else:
                            orderNumber = exchange_response['orderNumber']
                            try:
                                amountUnfilled = exchange_response['amountUnfilled']
                            except:
                                amountUnfilled = "No information currently available."
                            resultingTrades = exchange_response['resultingTrades']
                            numTrades = len(resultingTrades)
                            for n, order in enumerate(resultingTrades):
                                tradeID = order['tradeID']
                                tradeAM = float(order['amount'])
                                tradeRT = float(order['rate'])
                                tradeBT = float(order['total'])
                                alt_total_so_far += tradeAM
                                core_unit_amount = tradeBT
                                core_total_so_far += core_unit_amount

                    elif exchange == "Bittrex":
                        exchange_response = trexbot.buylimit(pair_code, alt_unit_amount,buy_price)
                        if not exchange_response['success']:
                            print ""
                            print "Exchange Error: " + str(exchange_response['message'])
                            print ""
                            titles.print_line()
                            winsound.Beep(800,800)
                            break
                        else:
                            #print str(exchange_response)
                            result = exchange_response['result']
                            uuid = result['uuid']
                            orderdetails = trexbot.getorder(uuid)
                            details = orderdetails['result']
                            #print str(details)
                            try:
                                amountUnfilled = details['QuantityRemaining']
                            except:
                                amountUnfilled = "No information currently available."
                            orderNumber = details['OrderUuid']
                            tradeID = "n/a"
                            tradeAM = float(details['Quantity'])
                            tradeRT = float(details['PricePerUnit'])
                            tradeBT = (float(details['Quantity']))*(float(details['PricePerUnit']))
                            alt_total_so_far += tradeAM
                            core_unit_amount = tradeBT
                            core_total_so_far += core_unit_amount

                            ##resultingTrades = exchange_response['resultingTrades']

                            ##numTrades = len(resultingTrades)
                            ##for n, order in enumerate(resultingTrades):
                            ##    tradeID = order['tradeID']
                            ##    tradeAM = float(order['amount'])
                            ##    tradeRT = float(order['rate'])
                            ##    tradeBT = float(order['total'])
                            ##    alt_total_so_far += tradeAM
                            ##    core_unit_amount = tradeBT
                            ##    core_total_so_far += core_unit_amount
                            
##                        for key in exchange_response:
##                            value = exchange_response[key]
##                            if key == "error":
##                                exchange_error = True
##                        if exchange_error:
##                            print ""
##                            print "Exchange Error: " + value
##                            print ""
##                            titles.print_line()
##                            winsound.Beep(800,800)
##                            break
##                        else:
##                            pass

                else:
                    core_total_so_far += core_unit_volume # possibly optional
                    alt_unit_amount = core_unit_volume/buy_price
                    alt_total_so_far += alt_unit_amount
                    exchange_response = "*** SIMULATION ONLY ***"
                    orderNumber = "*** SIMULATION ONLY ***"
                    numTrades = "n/a"
                    amountUnfilled = "n/a"
                    
                # buy-trade done. now let's print the report:-
                
                header = pair_header(pair_name,exchange)
                altbal = header[3]
                corebal = header[4]
                last_price = header[5]

                now = ('{:%H:%M %a %d %B %Y}'.format(datetime.datetime.now()))
                
                alt_projection = ((float(core_total)-core_total_so_far) / float(buy_price)) + alt_total_so_far
                eta = targetTime - time.time()         
                days = (eta / 60 / 60 / 24)
                hours = (eta / 60 / 60)
                minutes = (eta / 60)
                if eta <= 0:
                    eta = 0
                body = ""
                report("")
                report("["+str(i)+"] "+str(trade_type).upper()+" REPORT @ "+str(exchange).upper()+" "+str(pair_name)+" ("+str(now)+")")
                report("")
                report("[Threshold: "+str(format(float(threshold), '.8f'))+"] [Frequency: "+str(frequency)+" seconds] [Duration: "+str(duration)+" hours] [Batch: "+str(core_total)+" "+str(core)+"]")
                report("")
                report("Buy Price: "+str(format(float(buy_price), '.8f')))
                report("Unit Amount: "+str(format(float(alt_unit_amount), '.8f'))+ " " + str(alt))
                report("")
                report("Order Number: "+str(orderNumber))
                report("")
                if enabled:
##                    for y, order in enumerate(resultingTrades):
##                                    tradeID = order['tradeID']
##                                    tradeAM = float(order['amount'])
##                                    tradeRT = float(order['rate'])
##                                    tradeBT = float(order['total'])
                    report("ID: "+str(tradeID)+" --- Price: "+str(tradeRT)+" --- Amount: "+str(tradeAM)+" --- Total BTC: "+str(format(float(tradeBT), '.8f')))
                    report("")   
                report("Last Price: "+str(format(float(last_price), '.8f')))
                report(str(alt)+" Balance: "+str(format(float(altbal), '.8f'))+" "+str(alt))
                report(str(core)+" Balance: "+str(format(float(corebal), '.8f'))+" "+str(core))
                report("")
                report("Total "+str(alt)+" Bought: "+ str(format(float(alt_total_so_far), '.8f'))+" "+str(alt)+" (of "+str(format(float(alt_projection), '.8f'))+" "+str(alt)+")")
                report("Total "+str(core)+" Spent: "+str(format(float(core_total_so_far), '.8f'))+" "+str(core)+" (of "+str(format(float(core_total), '.8f'))+" "+str(core)+")")
                report("")
                if days > 1:
                    report("Completion ETA: " +str(int(days)) + " days")
                elif hours > 1:
                    report("Completion ETA: " +str(int(hours)) + " hours")
                elif minutes > 1:
                    report("Completion ETA: " +str(int(minutes)) + " minutes")
                else:
                    report("Completion ETA: " +str(int(eta)) + " seconds")
                report("")
                titles.print_line()
                if emailer:
                    email_report(body,alt,exchange,trade_type,i)

                if core_total_so_far >= core_total or frequency == 0 or duration ==0:
                    print ""
                    print "Complete."
                    print ""
                    titles.print_line()
                    winsound.Beep(1600,1200)
                    pair(pair_name,exchange)

            else:
                if not wait:
                    now = ('{:%H:%M %a %d %B %Y}'.format(datetime.datetime.now()))
                    print ""
                    print "WAITING TO "+str(trade_type).upper()+"... ("+str(now)+")"
                    print ""
                    print "[Threshold: "+str(format(float(threshold), '.8f'))+"] [Frequency: "+str(frequency)+" seconds] [Duration: "+str(duration)+" hours] [Batch: "+str(core_total)+" "+str(core)+"]"
                    print ""
                    titles.print_line()
                    wait = True
            endTime = time.time()
            elapsedTime = endTime - startTime
            sleepTime = frequency - elapsedTime
  
            if sleepTime < 0.0:
                sleepTime = 0.0
            countingTime += frequency
            time.sleep(sleepTime)
   
    elif trade_type == "Sell":
        print ""
        titles.print_line()
        wait = False
        while True:
            startTime = time.time()         
            extra = 0.00000001

            alt_total = total

            if (not duration == 0 and not frequency == 0):
                alt_unit_amount = (alt_total/(duration*3600/frequency))+extra
                sell_price = get_sell_price(pair_name,alt_unit_amount,exchange)
            else:
                alt_unit_amount = alt_total
                sell_price = get_sell_price(pair_name,alt_unit_amount,exchange)

            if sell_price >= threshold:
                
                wait = False
                i += 1
                if enabled:

                    if exchange == "Poloniex":
                        
                        exchange_response = polobot.sell(pair_code, sell_price, alt_unit_amount)
                        for key in exchange_response:
                            value = exchange_response[key]
                            if key == "error":
                                exchange_error = True
                        if exchange_error:
                            print ""
                            print "Exchange Error: " + value
                            print ""
                            titles.print_line()
                            winsound.Beep(800,800)
                            break
                        else:
                            orderNumber = exchange_response['orderNumber']
                            try:
                                amountUnfilled = exchange_response['amountUnfilled']
                            except:
                                amountUnfilled = "No information currently available."
                            resultingTrades = exchange_response['resultingTrades']
                            numTrades = len(resultingTrades)
                            for n, order in enumerate(resultingTrades):
                                tradeID = order['tradeID']
                                tradeAM = float(order['amount'])
                                tradeRT = float(order['rate'])
                                tradeBT = float(order['total'])
                                alt_total_so_far += tradeAM
                                core_unit_amount = tradeBT
                                core_total_so_far += core_unit_amount
                                

                    elif exchange == "Bittrex":
                        exchange_response = trexbot.selllimit(pair_code, alt_unit_amount,sell_price)
                        if not exchange_response['success']:
                            print ""
                            print "Exchange Error: " + str(exchange_response['message'])
                            print ""
                            titles.print_line()
                            winsound.Beep(800,800)
                            break
                        else:
                            #print str(exchange_response)
                            result = exchange_response['result']
                            uuid = result['uuid']
                            orderdetails = trexbot.getorder(uuid)
                            details = orderdetails['result']
                            #print str(details)
                            try:
                                amountUnfilled = details['QuantityRemaining']
                            except:
                                amountUnfilled = "No information currently available."
                            orderNumber = details['OrderUuid']
                            tradeID = "n/a"
                            tradeAM = float(details['Quantity'])
                            tradeRT = float(details['PricePerUnit'])
                            tradeBT = (float(details['Quantity']))*(float(details['PricePerUnit']))
                            alt_total_so_far += tradeAM
                            core_unit_amount = tradeBT
                            core_total_so_far += core_unit_amount

                        
                else:
                    alt_total_so_far += alt_unit_amount
                    core_unit_amount = alt_unit_amount * sell_price
                    core_total_so_far += core_unit_amount
                    exchange_response = "*** SIMULATION ONLY ***"
                    orderNumber = "*** SIMULATION ONLY ***"
                    numTrades = "n/a"
                    amountUnfilled = "n/a"
                    

                now = ('{:%H:%M %a %d %B %Y}'.format(datetime.datetime.now()))    

                header = pair_header(pair_name,exchange)
                altbal = header[3]
                corebal = header[4]
                last_price = header[5]

                core_projection = ((float(alt_total)-alt_total_so_far) * float(sell_price)) + core_total_so_far
                eta = (targetTime - time.time())        
                days = (eta / 60 / 60 / 24)
                hours = (eta / 60 / 60)
                minutes = (eta / 60)
                if eta <= 0:
                    eta = 0
                body = ""
                report("")
                report("["+str(i)+"] "+str(trade_type).upper()+" REPORT @ "+str(exchange).upper()+" "+str(pair_name)+" ("+str(now)+")")
                report("")
                report("[Threshold: "+str(format(float(threshold), '.8f'))+"] [Frequency: "+str(frequency)+" seconds] [Duration: "+str(duration)+" hours] [Batch: "+str(alt_total)+" "+str(alt)+"]")
                report("")
                report("Sell Price: "+str(format(float(sell_price), '.8f')))
                report("Unit Amount: "+str(format(float(alt_unit_amount), '.8f'))+ " " + str(alt))  
                report("")
                report("Order Number: "+str(orderNumber))
                report("")
                if enabled:
##                    for y, order in enumerate(resultingTrades):
##                                    tradeID = order['tradeID']
##                                    tradeAM = float(order['amount'])
##                                    tradeRT = float(order['rate'])
##                                    tradeBT = float(order['total'])
                    report("ID: "+str(tradeID)+" --- Price: "+str(tradeRT)+" --- Amount: "+str(tradeAM)+" --- Total BTC: "+str(format(float(tradeBT), '.8f')))
                    report("")
                ##print "Amount Unfilled: "+str(amountUnfilled)
                report("Last Price: "+str(format(float(last_price), '.8f')))
                report(str(alt)+" Balance: "+str(format(float(altbal), '.8f'))+" "+str(alt))
                report(str(core)+" Balance: "+str(format(float(corebal), '.8f'))+" "+str(core))
                report("")
                report("Total "+str(alt)+" Sold: "+str(format(float(alt_total_so_far), '.8f'))+" "+str(alt)+" (of "+str(format(float(alt_total), '.8f'))+" "+str(alt)+")")
                
                report("Total "+str(core)+" Acquired: "+ str(format(float(core_total_so_far), '.8f'))+" "+str(core)+" (of "+str(format(float(core_projection), '.8f'))+" "+str(core)+")")
                report("")
                if days > 1:
                    report("Completion ETA: " +str(int(days)) + " days")
                elif hours > 1:
                    report("Completion ETA: " +str(int(hours)) + " hours")
                elif minutes > 1:
                    report("Completion ETA: " +str(int(minutes)) + " minutes")
                else:
                    report("Completion ETA: " +str(int(eta)) + " seconds")
                report("")
                titles.print_line()
                if emailer:
                    email_report(body,alt,exchange,trade_type,i)   

                if alt_total_so_far >= alt_total or frequency == 0 or duration ==0:
                    print ""
                    print "Complete."
                    print ""
                    titles.print_line()
                    winsound.Beep(1600,1200)
                    pair(pair_name,exchange)
            else:
                if not wait:
                    now = ('{:%H:%M %a %d %B %Y}'.format(datetime.datetime.now()))
                    print ""
                    print "WAITING TO "+str(trade_type).upper()+"... ("+str(now)+")"
                    print ""
                    print "[Threshold: "+str(format(float(threshold), '.8f'))+"] [Frequency: "+str(frequency)+" seconds] [Duration: "+str(duration)+" hours] [Batch: "+str(alt_total)+" "+str(alt)+"]"
                    print ""
                    titles.print_line()
                    wait = True
            endTime = time.time()
            elapsedTime = endTime - startTime
            sleepTime = frequency - elapsedTime
            countingTime += frequency
            if sleepTime < 0.0:
                sleepTime = 0.0
    
            time.sleep(sleepTime)    
        
    else:
        print "Trade type error."

def timecycle(pair_name,trade_type,exchange,zone):
  
    header = pair_header(pair_name,exchange)
    pair_code = header[0]
    alt = header[1]
    core = header[2]
    altbal = header[3]
    corebal = header[4]
    last_price = header[5]
    
    print ""
    print "ESKIMOTRON ("+str(exchange)+" >> "+str(pair_name)+" >> "+str(trade_type)+" "+str(alt)+")"
    print ""
    print "Last Price: "+ str(last_price)
    print alt + " Balance: "+str(altbal)
    print core + " Balance: "+str(corebal)
    print ""
    if trade_type == "Buy":
        i = 0
        while i == 0:
            try:
                total = float(raw_input("Enter total amount of "+core+" to spend: "))
                if total == 0:
                    print ""
                    print "Cancelled."
                    pair(pair_name,exchange)
                else:
                    i += 1
            except ValueError:
                print "Invalid entry!"
                
    elif trade_type == "Sell":
        i = 0
        while i == 0:
            try:
                total = float(raw_input("Enter total amount of "+alt+" to sell: "))
                if total == 0:
                    print ""
                    print "Cancelled."
                    pair(pair_name,exchange)
                else:
                    i += 1
            except ValueError:
                print "Invalid entry!"
    else:
        print "error!"
    if zone:
        i = 0
        while i == 0:
            try:
                if trade_type == "Buy":
                    threshold = float(raw_input("Price threshold to "+str(trade_type).lower()+" under: "))
                elif trade_type == "Sell":
                    threshold = float(raw_input("Price threshold to "+str(trade_type).lower()+" over: "))
                i += 1
            except ValueError:
                print "Invalid entry!"
    else:
        if trade_type == "Buy":
            threshold = 99999999.0
        elif trade_type == "Sell":
            threshold = 0.0

        
    i = 0
    while i == 0:
        try:
            duration = float(raw_input("Enter duration in hours: "))
            i += 1
        except ValueError:
            print "Invalid entry!"
    i = 0
    while i == 0:
        try:
            frequency = float(raw_input("Enter frequency in seconds: "))
            i += 1
        except ValueError:
            print "Invalid entry!"
  
    print ""
    confirm = raw_input("Start program (Y/N): ")
    if confirm.upper() == "Y":
        print ""
        print "Starting program..."
        program_timecycle(pair_name,trade_type,exchange,total,duration,frequency,threshold)
    else:
        print ""
        print "Cancelled."
        pair(pair_name,exchange)
    pair(pair_name,exchange)

def pair_header(pair_name,exchange):

    alt = alt_name_parser(pair_name)
    core = core_name_parser(pair_name)

    if exchange == "Poloniex":
        
        pair_code = polo_pair_parser(pair_name)    
        ticker = polobot.returnTicker()
        pair_ticker = ticker[pair_code]
        balances = polobot.returnBalances()
        try:
            altbal = balances[alt]
        except KeyError:
            print ""
            titles.print_line()
            print ""
            print "Exchange Error: INVALID API KEY/SECRET"
            print ""
            titles.print_line()
            winsound.Beep(800,800)
            return("ERROR","KEY")
            
        corebal = balances[core]
        last_price = pair_ticker["last"]
        
        
    elif exchange == "Bittrex":
        
        pair_code = trex_pair_parser(pair_name)    
        ticker = trexbot.getticker(pair_code)    
        pair_ticker = ticker["result"]
        altbal_string = trexbot.getbalance(alt)
        corebal_string = trexbot.getbalance(core)
        altbal_res = altbal_string["result"]
        corebal_res = corebal_string["result"]
        try:
            altbal = altbal_res["Balance"]
        except TypeError:
            print ""
            titles.print_line()
            print ""
            print "Exchange Error: INVALID API KEY/SECRET"
            print ""
            titles.print_line()
            winsound.Beep(800,800)
            return("ERROR","KEY")
        corebal = corebal_res["Balance"]
        last_price = format(pair_ticker["Last"], '.8f')

    else:
        print "Error! Exchange not recognised."

    return (pair_code,alt,core,altbal,corebal,last_price)

def pair(pair_name,exchange):

    header = pair_header(pair_name,exchange)
    if header[0] == "ERROR":
        pairs_list_menu(exchange)
    pair_code = header[0]
    alt = header[1]
    core = header[2]
    altbal = header[3]
    corebal = header[4]
    last_price = header[5]

    print ""
    print "ESKIMOTRON ("+str(exchange)+" >> "+str(pair_name)+")"
    print ""
    print "Last Price: "+ str(last_price)
    print alt + " Balance: "+str(altbal)
    print core + " Balance: "+str(corebal)
    print ""
    print "1. Buy "+alt
    print "2. Sell "+alt
    print "0. Back"
    print ""
    result = menu_input()
    if result == 1:
        zone = True
        timecycle(pair_name,"Buy",exchange,zone)
    elif result == 2:
        zone = True
        timecycle(pair_name,"Sell",exchange,zone)
    elif result == 0:
        pairs_list_menu(exchange)
    else:
        pair(pair_name,exchange)


def pairs_list_menu(exchange):
    print ""
    print "ESKIMOTRON ("+str(exchange)+")"
    print ""
    if exchange == "Poloniex":
        
        pairsNum = len(poloniexPairs)
        backNum = pairsNum + 1
        ticker = polobot.returnTicker()
        g = 0
        for i in range (1,pairsNum+1):
            try:
                pair_name = (str(poloniexPairs[i-1])).upper()
                pair_code = polo_pair_parser(pair_name)
                pair_ticker = ticker[pair_code]
                last_price = format(float(pair_ticker["last"]), '.8f')
                print str(i-g)+". "+ pair_name + " ("+str(last_price)+")"
            except (KeyError, IndexError):
                backNum -= 1
                g += 1
    elif exchange == "Bittrex":

        pairsNum = len(bittrexPairs)
        backNum = pairsNum + 1
        g = 0
        for i in range (1,pairsNum+1):
            try:
                pair_name = (str(bittrexPairs[i-1])).upper()
                pair_code = trex_pair_parser(pair_name)
                ticker_result = trexbot.getticker(pair_code)
                pair_ticker = ticker_result["result"]
                last_price = format(pair_ticker["Last"], '.8f')
                print str(i-g)+". "+ pair_name + " ("+str(last_price)+")"
            except (KeyError, IndexError):
                backNum -= 1
                g += 1

    elif exchange == "Bitstamp":

        pairsNum = len(bitstampPairs)
        backNum = pairsNum + 1
        g = 0
        last_price = "????"
        for i in range (1,pairsNum+1):
            try:
                pair_name = (str(bitstampPairs[i-1])).upper()
                print str(i-g)+". "+ pair_name + " ("+str(last_price)+")"
            except (KeyError, IndexError):
                backNum -= 1
                g += 1
                
              
    print "0. Back"
    print ""
    result = menu_input()
    if result == 9999 or result > pairsNum or result < 0:
        pairs_list_menu(exchange)
    elif result == 0:
        main()
    else:
        if exchange == "Poloniex":
            selection = poloniexPairs[result-1]
        elif exchange == "Bittrex":
            selection = (bittrexPairs[result-1]).upper()
            
        pair(selection,exchange)

def settings_menu():
    global enabled
    global emailer
    print ""
    print "ESKIMOTRON (Settings)"
    print ""
    if enabled:
        print "1. Trade API (Enabled)"
    elif not enabled:
        print "1. Trade API (Disabled)"
    if emailer:
        print "2. Email Notifications (Enabled: "+str(e_email)+")"
    elif not emailer:
        print "2. Email Notifications (Disabled)"
    print "3. About Eskimotron"
    print "0. Back"
    print ""
    result = menu_input()
    if result == 1:
        if enabled:
            enabled = False
            settings_menu()
        elif not enabled:
            enabled = True
            settings_menu()
    elif result == 2:
        if emailer:
            emailer = False
            settings_menu()
        elif not emailer:
            emailer = True
            settings_menu()
    elif result == 3:
        titles.eskimo_title()
        print "Version "+str(version)+" 2016"
        print "by amoebatron (amoebatron@tutanota.com)"
        settings_menu()
    elif result == 0:
        main()
    else:
        settings_menu()
     
def main():
    print ""
    print "ESKIMOTRON (Main)"
    print ""
    print "1. Poloniex"
    print "2. Bittrex"
    print "3. Settings"
    print "4. Quit"
    print ""
    result = menu_input()
    if result == 1:
        pairs_list_menu("Poloniex")
    elif result == 2:
        pairs_list_menu("Bittrex")
    elif result == 3:
        settings_menu()
    elif result == 4:
        print "Goodbye Mr. Bond."
        sys.exit()
    else:
        main()
            
def menu_input():                
    try:
        i = int(raw_input(">"))
        return i
    except ValueError:
        i = 9999
        return i

def cls(): print "\n" * 100
    
cls()
titles.eskimo_title()
main()

