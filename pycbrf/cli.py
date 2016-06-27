import argparse

from pycbrf import VERSION


def main():

    from operator import attrgetter
    from .toolbox import ExchangeRates

    arg_parser = argparse.ArgumentParser(prog='pycbrf', description='Tools to query Bank of Russia')
    arg_parser.add_argument('--version', action='version', version='.'.join(map(str, VERSION)))

    subparsers = arg_parser.add_subparsers(dest='subparsers')
    subcommand_parser = subparsers.add_parser('rates', help='Prints out exchange rates')

    subcommand_parser.add_argument('-c', help='Currency to get info (e.g. USD, 840)', default=None)
    subcommand_parser.add_argument('-d', help='Date to get rate for (e.g. 20016-06-27)', default=None)

    parsed_args = arg_parser.parse_args()
    parsed_args = vars(parsed_args)
    subparsed_args = parsed_args['subparsers']

    if subparsed_args == 'rates':
        date = parsed_args['d']
        currency = parsed_args['c']

        def print_rate(rate):
            print('[%s] %s - %s' % (rate.code, rate.name, rate.rate))

        rates = ExchangeRates(on_date=date, locale_en=True)

        print(rates.date_received.strftime('%Y-%m-%d'))
        print('=' * 10)

        if currency:
            rate = rates[currency]
            if rate:
                print_rate(rate)
            else:
                print('No data for %s' % currency)
        else:
            for rate in sorted(rates.rates, key=attrgetter('code')):
                print_rate(rate)
