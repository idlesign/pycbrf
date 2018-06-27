from operator import attrgetter

import click

from pycbrf import VERSION_STR, ExchangeRates


@click.group()
@click.version_option(version=VERSION_STR)
def entry_point():
    """Tools to query Bank of Russia."""


@entry_point.command()
@click.option('-c', '--currency', help='Currency to get info (e.g. USD, 840)')
@click.option('-d', '--date', help='Date to get rate for (e.g. 20016-06-27)')
def rates(currency, date):
    """Prints out exchange rates."""

    def print_rate(rate):
        click.secho('[%s] %s - %s' % (rate.code, rate.name, rate.rate))

    rates = ExchangeRates(on_date=date, locale_en=True)

    click.secho(rates.date_received.strftime('%Y-%m-%d'))
    click.secho('=' * 10)

    if currency:
        rate = rates[currency]
        if rate:
            print_rate(rate)
        else:
            click.secho('No data for %s' % currency)
    else:
        for rate in sorted(rates.rates, key=attrgetter('code')):
            print_rate(rate)


def main():
    entry_point(obj={})


if __name__ == '__main__':
    main()
