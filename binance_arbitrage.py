import sys
from collections import defaultdict

#simulation variables
simulation = True	#True if you want to simulate, False if you want to connect to Binance API 
simlength = 10000     #number of data files to use for simulation. Simulation time is simlength * interval between data files, usually 1 second. Set to None to process all files in folder
simulation_data_directory = 'C:/Users/rishi\Documents\Scripts\Arb\BinanceScraping/1 Second Pitch (2)'
plot_data = True

#Parameters
trade_duration_required = 10			#time an arb value must stay over a certain threshold to be executed
trade_relaxation_threshold = 1.000		#amount an arb value must stay over throughout the required duration to be executed
trade_fraction = 1.0					#what % of total amount should be traded at a given step. This will be useful/dynamic for step sizes, right now just default to 1


#cryptos of interest are considered as viable for trading

cryptosofinterest = ['USDT', 'XMR', 'NEO', 'XRP', 'XZC', 'POA', 'DLT', 'OAX', 'AST', 'MCO', 'TRX', 'ICN', 'OMG', 'BCC', 'WTC', 'MOD', 'QSP', 'BNB', 'NEB', 'GXS', 'MAN', 'XEM', 'DGD', 'ADA', 'GVT', 'ARN', 'REQ', 'AIO', 'OST', 'TRI', 'APP', 'XVG', 'IOT', 'NUL', 'MTH', 'MTL', 'ENJ', 'VIA', 'IOS', 'SUB', 'ARK', 'POW', 'INS', 'LUN', 'CHA', 'AEB', 'RDN', 'BCD', 'BQX', 'WAV', 'PPT', 'MDA', 'LTC', 'WAB', 'POE', 'LEN', 'TNT', 'ZRX', 'ZIL', 'BAT', 'KMD', 'EOS', 'ADX', 'BRD', 'RLC', 'LSK', 'WAN', 'ENG', 'EVX', 'DNT', 'ICX', 'QTU', 'CMT', 'RCN', 'ETH', 'STEEM', 'STR', 'ELF', 'SNM', 'VEN', 'NAN', 'BNT', 'BTC', 'CND', 'BCP', 'NCA', 'KNC', 'AMB', 'ETC', 'SNG', 'FUE', 'WIN', 'TNB', 'AEE', 'BLZ', 'ZEC', 'BTS', 'GTO', 'EDO', 'CTR', 'CDT', 'NAV', 'VIB', 'RPX', 'XLM', 'LIN', 'ONT', 'GAS', 'DAS', 'BTG', 'SNT', 'PIV', 'LRC', 'HSR', 'STO', 'YOY', 'SAL', 'FUN']
# cryptosofinterest = ['USDT', 'BTC', 'ETH', 'DASH', 'XRP', 'LTC']
oktohold = ['USDT']		#coins that you are ok holding a balance of in between trades

#load historical binance ticker data files (from https://www.binance.com/api/v3/ticker/bookTicker) from a specified directory. assumes files are in order.
def simulation_init(simulation_data_directory, simlength = None):
	import json
	import os
	simdata = []	#initialize simulation data output list

	filenames = os.listdir(simulation_data_directory)	#get all files in simulation_data_directory

	# if simlength = True or simlength > number of files, load all files in directory. Otherwise, load number of files specified by simlength
	if simlength == None:				
		simlength = len(filenames)
	else:
		simlength = min(simlength, len(filenames))

	#load all 
	for index, filename in enumerate(filenames[0:simlength]):	
			sys.stdout.write('Loading Data: %i / %i\r' % (index+1, simlength))
			sys.stdout.flush()
			with open(simulation_data_directory + '/' + filename) as jsonfile: 
				simdata.append(json.load(jsonfile))
	
	print('Data Initialization Complete')
	return simdata

#reads ticker data file (https://www.binance.com/api/v3/ticker/bookTicker). Returns a list of all trading pairs in format price_matrix[coin to sell][coin to buy] = cost.
#
# example: I want to buy 12 BTC worth of ETH. Ignoring trading fees, the amount of ETH I can afford = 12 * pricematrix['BTC']['ETH'] 
def get_prices(ticker_data, cryptosofinterest):

	#given a ticker and list of valid symbols, this function figures out which symbol is first and which is second.
	#example: ETHBTC, will return coin1 = ETH, coin2 = BTC, True. Useful for assigning bid/ask prices accordingly
	# returns , , False if no match is found
	def find_match(ticker_symbol, cryptosofinterest):
		ticker_symbol_length = len(ticker_symbol)

		for coin1_index, coin1 in enumerate(cryptosofinterest):
			coin1_symbol_length = len(coin1)
			if coin1 == ticker_symbol[:coin1_symbol_length]:
				for coin2 in cryptosofinterest[coin1_index:]:
					if coin2 == ticker_symbol[coin1_symbol_length:]:
						return coin1, coin2, True

			if coin1 == ticker_symbol[ticker_symbol_length-coin1_symbol_length:]:
				for coin2 in cryptosofinterest[coin1_index:]:
					if coin2 == ticker_symbol[:ticker_symbol_length - coin1_symbol_length]:
						return coin2, coin1, True

		return(0, 0, False)	

	price_matrix = defaultdict(dict)		#initialize price list

	for ticker in ticker_data:					#for each ticker in the binance data
		m , n, found = find_match(ticker['symbol'], cryptosofinterest)		#try to break the ticker into its constituent symbols
		if found:												#if we found the symbols
			price_matrix[m][n] = float(ticker['bidPrice'])		#assign the appropriate cost of going from a->b or b->a 
			price_matrix[n][m] = 1/float(ticker['askPrice'])

	return price_matrix

#brute force search through up to 5 trades. Will only start/end trades in cryptos listed in oktohold (usually just set to USDT)
#trading fees are considered, and a minimum threshold arbitrage ratio can be specified to filter results below a certain level
#
#returns a high-to-low ordered list of potential arbitrage sequences in the format [predicted arbitrage ratio, [list of crypto trading path]] 
def look_for_arbs(price_matrix, cryptosofinterest,  oktohold, arb_threshold, trading_fee):
	arbs_found = []	#initialize list for arb opportunities


	for starting_coin in oktohold:										#starting coin has to be from oktohold 
		for coin_a, pair_a in price_matrix[starting_coin].items():		#for each trading pair available to our starting_coin
			arb_ratio_a = pair_a * (1-trading_fee)						#calculate the hypothetical balance for starting_coin->coin_a

			for coin_b, pair_b in price_matrix[coin_a].items():			#for each trading pair available to coin_a
				arb_ratio_b = arb_ratio_a * pair_b * (1-trading_fee)	#calculate the hypothetical balance for starting_coin->coin_a->coin_b

				for coin_c, pair_c in price_matrix[coin_b].items():		#etc etc
					arb_ratio_c = arb_ratio_b * pair_c * (1-trading_fee)

					if (arb_ratio_c >= arb_threshold) and (coin_c in oktohold):	#at this point, we may hypothetically have made it back to an oktohold coin without a reduntant path
						trading_path = [starting_coin, coin_a, coin_b, coin_c]	#if a path has a desirable arb ratio and ends in an oktohold coin, add the path to the list
						arbs_found.append([arb_ratio_c, trading_path])

					for coin_d, pair_d in price_matrix[coin_c].items():				#etc etc
						arb_ratio_d = arb_ratio_c * pair_d * (1-trading_fee)

						if (arb_ratio_d >= arb_threshold) and (coin_d in oktohold):
							trading_path = [starting_coin, coin_a, coin_b, coin_c, coin_d]
							arbs_found.append([arb_ratio_d, trading_path])

						for coin_e, pair_e in price_matrix[coin_d].items():
							arb_ratio_e = arb_ratio_d * pair_e * (1-trading_fee)

							if (arb_ratio_e >= arb_threshold) and (coin_e in oktohold):
								trading_path = [starting_coin, coin_a, coin_b, coin_c, coin_d, coin_e]
								arbs_found.append([arb_ratio_e, trading_path])

							# for coin_f, pair_f in price_matrix[coin_e].items():								#can keep going, but this layer really brings things to a crawl. also wtf to execute this in real life haha
							# 	arb_ratio_f = arb_ratio_e * pair_f * (1-trading_fee)
							#
							# 	if (arb_ratio_f >= arb_threshold) and (coin_f in oktohold):
							# 		trading_path = ['USDT', coin_a, coin_b, coin_c, coin_d, coin_e, coin_f]
							# 		arbs_found.append([arb_ratio_f, trading_path])		

	arbs_found.sort(reverse = True)
	return(arbs_found)				

#given a price matrix, trading path, and trading fee, this function will calculate the arbitrage ratio. Useful for checking up on paths of interest
def get_arb_status(price_matrix, trading_path, trading_fee):
	arb_status = 1

	for index, trade in enumerate(trading_path[:-1]):
		arb_status *= price_matrix[trading_path[index]][trading_path[index+1]] * (1-trading_fee)

	return(arb_status) 

# will print out a price matrix to console in human-legible form
def print_matrix(price_matrix):
	for key, value in price_matrix.items():
		printstr = key + ': 	'
		for key2, val2 in value.items():
			printstr += str(price_matrix[key][key2])[0:5] + ' ' + key2 + ', '
		print(printstr[:-2])

# will print out current balance to console in human-legible form
def print_balance(balance_dict):
	printstr = "Current Balance: 	"
	for currency, balance in balance_dict.items():
		if balance > 0:
			printstr += currency + ": " + str(balance)[0:6] + "	"

	print(printstr)

# loops through binance historical ticker data and pretends to trade assuming each trade takes 1 second to execute
# completely ignores step sizes and order size, assumes that entire trade at any increment can be executed at bid/ask price
def simulate_market_monitor(simulation_data_directory, simlength, cryptosofinterest):
	simdata = simulation_init(simulation_data_directory, simlength)	#load historical data
	balance = {'USDT': 1.0}	#assume you start with 1 USDT.
	USDTbalance = []		#used to track USDT balance over time. only used for graphing at the end

	trading_fee = 0.0005	#assume BNB for now
	arb_threshold = 1.000	#look for any positive arbitrage paths

	arbs_checking = []		#array of opportunities that have been spotted, and are to be monitored before deciding whether to execute
	tradeinprogress = False	#indicates whether to look for arbitrages (False), or execute a trade (True)

	for tickerindex, ticker in enumerate(simdata):
		sys.stdout.write('Checking for opportunities: %i / %i\r' % (tickerindex+1, simlength))		#Print progress to console
		sys.stdout.flush()
		price_matrix = get_prices(ticker, cryptosofinterest)	#get price matrix for current dataset
		# print_matrix(price_matrix)

		if not tradeinprogress:																						#if we aren't trading 
			opportunities = look_for_arbs(price_matrix, cryptosofinterest, oktohold, arb_threshold, trading_fee)	#Look for any arbitrage opportunities in this given timepoint
			for arb in opportunities:																				#check all the opportunities found in this timepoint
				if not any(arb[1] in monitored_arbs for monitored_arbs in arbs_checking):							# if this trading path isnt already being considered
					arbs_checking.append([0, arb[1]])																# add it to the list [opportunity lifetime, [trading path]]

			# if(len(arbs_checking)>0):
				# print('\n-----Potential Trades-----')

			for arb in arbs_checking:																				#for all paths being considered 
				arbstatus = get_arb_status(price_matrix, arb[1], trading_fee)										#get the current value of this path
				if arbstatus >= trade_relaxation_threshold:															#if its still valuable enough to be of interest
					arb[0] += 1																						#increment its lifetime
					# print(arb, arbstatus)
					if arb[0] >= trade_duration_required:															#if its been around long enough that we think it will stick around
						printstring = ''	
						approved_trade_path = arb[1]																#set up for executing a trade
						tradeinprogress = True
						trade_step = 0

						print('\nTrade Opportunity: ', arb[1])
						arbs_checking = []
						break
				else:
					arbs_checking.remove(arb)																		#if it is no longer valuable enough, remove it from the list

		if tradeinprogress:																							#if a trade has been approved, we will iterate through the trading path at a rate of one trade per timepoint (1s)
			inputcoin = approved_trade_path[trade_step]																#get the symbols of coins involved in current trading step
			outputcoin = approved_trade_path[trade_step+1]															
			inputbalance = balance.get(inputcoin, None)																#get our current balance of coins involved in current trading step
			outputbalance = balance.get(outputcoin, None)

			if outputbalance == None:																				#if the coin we are buying doesn't exist in our balance sheet, add an entry for it
				balance[outputcoin] = inputbalance * trade_fraction * price_matrix[inputcoin][outputcoin] * (1-trading_fee)
			else:																									#otherwise just adjust the balance accordingly
				balance[outputcoin] += inputbalance * trade_fraction * price_matrix[inputcoin][outputcoin] * (1-trading_fee)
			
			balance[inputcoin] = inputbalance * (1-trade_fraction)													#reduce the outgoing balance accordingly

			trade_step +=1																							#increment so we execute the next trading step on next iteration
			print_balance(balance)							

			if trade_step == len(approved_trade_path)-1:															#once we reach the last step, flag the trade as complete
				tradeinprogress = False


		if plot_data:																								#if we're plotting, record the USDT balance for each datapoint. Need to do some stupid to keep the graph from going to 0 during trades
			if balance['USDT'] == 0:
				USDTbalance.append(USDTbalance[tickerindex-1])
			else:
				USDTbalance.append(balance['USDT'])

	if plot_data:
		import matplotlib.pyplot as plt
		import numpy as np

		x = np.linspace(1,simlength, simlength)
		fig = plt.figure()

		plt.plot(x, USDTbalance)
		plt.plot(x, x/x, dashes=[5, 5])
		plt.show()


	print('-------Final Results--------')
	print_balance(balance)



# def market_monitor():

simulate_market_monitor(simulation_data_directory, simlength, cryptosofinterest)								#run the script