import sys
from collections import defaultdict

#simulation variables
simulation = True	#True if you want to simulate, False if you want to connect to Binance API 
simlength = None     #number of data files to use for simulation. Simulation time is simlength * interval between data files, usually 1 second
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

	# price_matrix = [[0 for x in range(len(cryptosofinterest))] for y in range(len(cryptosofinterest))] #intialize price matrix to zeros
	price_matrix = defaultdict(dict)

	for ticker in ticker_data:
		m , n, found = find_match(ticker['symbol'], cryptosofinterest)
		if found:
			price_matrix[m][n] = float(ticker['bidPrice'])
			price_matrix[n][m] = 1/float(ticker['askPrice'])

	return price_matrix

def look_for_arbs(price_matrix, cryptosofinterest,  oktohold, arb_threshold, trading_fee):
	arbs_found = []	#initialize list for arb opportunities


	for starting_coin in oktohold:
		for coin_a, pair_a in price_matrix[starting_coin].items():
			arb_ratio_a = pair_a * (1-trading_fee)

			for coin_b, pair_b in price_matrix[coin_a].items():
				arb_ratio_b = arb_ratio_a * pair_b * (1-trading_fee)

				for coin_c, pair_c in price_matrix[coin_b].items():
					arb_ratio_c = arb_ratio_b * pair_c * (1-trading_fee)

					if (arb_ratio_c >= arb_threshold) and (coin_c in oktohold):
						trading_path = [starting_coin, coin_a, coin_b, coin_c]
						arbs_found.append([arb_ratio_c, trading_path])

					for coin_d, pair_d in price_matrix[coin_c].items():
						arb_ratio_d = arb_ratio_c * pair_d * (1-trading_fee)

						if (arb_ratio_d >= arb_threshold) and (coin_d in oktohold):
							trading_path = [starting_coin, coin_a, coin_b, coin_c, coin_d]
							arbs_found.append([arb_ratio_d, trading_path])

						for coin_e, pair_e in price_matrix[coin_d].items():
							arb_ratio_e = arb_ratio_d * pair_e * (1-trading_fee)

							if (arb_ratio_e >= arb_threshold) and (coin_e in oktohold):
								trading_path = [starting_coin, coin_a, coin_b, coin_c, coin_d, coin_e]
								arbs_found.append([arb_ratio_e, trading_path])

							# for coin_f, pair_f in price_matrix[coin_e].items():
							# 	arb_ratio_f = arb_ratio_e * pair_f * (1-trading_fee)
							#
							# 	if (arb_ratio_f >= arb_threshold) and (coin_f in oktohold):
							# 		trading_path = ['USDT', coin_a, coin_b, coin_c, coin_d, coin_e, coin_f]
							# 		arbs_found.append([arb_ratio_f, trading_path])		

	arbs_found.sort(reverse = True)
	return(arbs_found)				

def get_arb_status(price_matrix, trading_path, trading_fee):
	arb_status = 1

	for index, trade in enumerate(trading_path[:-1]):
		arb_status *= price_matrix[trading_path[index]][trading_path[index+1]] * (1-trading_fee)

	return(arb_status) 

def print_matrix(price_matrix):
	for key, value in price_matrix.items():
		printstr = key + ': 	'
		for key2, val2 in value.items():
			printstr += str(price_matrix[key][key2])[0:5] + ' ' + key2 + ', '
		print(printstr[:-2])

def print_balance(balance_dict):
	printstr = "Current Balance: 	"
	for currency, balance in balance_dict.items():
		if balance > 0:
			printstr += currency + ": " + str(balance)[0:6] + "	"

	print(printstr)

def simulate_market_monitor(simulation_data_directory, simlength, cryptosofinterest):
	simdata = simulation_init(simulation_data_directory, simlength)
	balance = {'USDT': 1.0}
	USDTbalance = []

	trading_fee = 0.0005	#assume BNB for now
	arb_threshold = 1.000	#look for any positive arbitrage paths

	arbs_checking = []		#array of opportunities that have been spotted, and are to be monitored before deciding whether to execute
	tradeinprogress = False

	for tickerindex, ticker in enumerate(simdata):
		sys.stdout.write('Checking for opportunities: %i / %i\r' % (tickerindex+1, simlength))
		sys.stdout.flush()
		price_matrix = get_prices(ticker, cryptosofinterest)
		# print_matrix(price_matrix)
		opportunities = look_for_arbs(price_matrix, cryptosofinterest, oktohold, arb_threshold, trading_fee)

		if not tradeinprogress:
			for arb in opportunities:
				if not any(arb[1] in monitored_arbs for monitored_arbs in arbs_checking):
					arbs_checking.append([0, arb[1]])

			# if(len(arbs_checking)>0):
				# print('\n-----Potential Trades-----')

			for arb in arbs_checking:
				arbstatus = get_arb_status(price_matrix, arb[1], trading_fee)
				if arbstatus >= trade_relaxation_threshold:
					arb[0] += 1
					# print(arb, arbstatus)
					if arb[0] >= trade_duration_required:
						printstring = ''
						approved_trade_path = arb[1]
						tradeinprogress = True
						trade_step = 0

						print('\nTrade Opportunity: ', arb[1])
						arbs_checking = []
						break
				else:
					arbs_checking.remove(arb)

		if tradeinprogress:
			inputcoin = approved_trade_path[trade_step]
			outputcoin = approved_trade_path[trade_step+1]
			inputbalance = balance.get(inputcoin, None)
			outputbalance = balance.get(outputcoin, None)

			if outputbalance == None:
				balance[outputcoin] = inputbalance * trade_fraction * price_matrix[inputcoin][outputcoin] * (1-trading_fee)
			else:
				balance[outputcoin] += inputbalance * trade_fraction * price_matrix[inputcoin][outputcoin] * (1-trading_fee)
			
			balance[inputcoin] = inputbalance * (1-trade_fraction)

			trade_step +=1
			print_balance(balance)

			if trade_step == len(approved_trade_path)-1:
				tradeinprogress = False


		if plot_data:
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

simulate_market_monitor(simulation_data_directory, simlength, cryptosofinterest)