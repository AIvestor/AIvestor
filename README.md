# ![AIvestor Banner](https://pbs.twimg.com/profile_banners/1874873527028826112/1735839875/1500x500)

[![AIvestor CI](https://github.com/freqtrade/freqtrade/workflows/Freqtrade%20CI/badge.svg)](https://github.com/freqtrade/freqtrade/actions/)
[![DOI](https://joss.theoj.org/papers/10.21105/joss.04864/status.svg)](https://doi.org/10.21105/joss.04864)
[![Coverage Status](https://coveralls.io/repos/github/freqtrade/freqtrade/badge.svg?branch=develop&service=github)](https://coveralls.io/github/freqtrade/freqtrade?branch=develop)
[![Documentation](https://readthedocs.org/projects/freqtrade/badge/)](https://aivestor.cx)
[![Maintainability](https://api.codeclimate.com/v1/badges/5737e6d668200b7518ff/maintainability)](https://codeclimate.com/github/freqtrade/freqtrade/maintainability)

AIvestor is a free and open-source platform for building AI-driven hedge fund strategies. It supports all major exchanges and can be controlled via Telegram or webUI. AIvestor offers advanced tools such as backtesting, real-time performance tracking, and strategy optimization using machine learning.

## Follow Us
- Website: [AIvestor.cx](https://aivestor.cx)
- Twitter: [@AIvestordotcx](https://x.com/AIvestordotcx)

![AIvestor Screenshot](https://raw.githubusercontent.com/freqtrade/freqtrade/develop/docs/assets/freqtrade-screenshot.png)

## Disclaimer

This software is for educational purposes only. Do not risk money you cannot afford to lose. USE THE SOFTWARE AT YOUR OWN RISK. THE AUTHORS AND AFFILIATES ASSUME NO RESPONSIBILITY FOR YOUR TRADING RESULTS.

Always start by running the bot in Dry-run mode and understand how it works before engaging real funds. Coding and Python knowledge is strongly recommended. Review the source code to fully understand the mechanism of the bot.

---

## Supported Exchange Marketplaces

Please read the [exchange-specific notes](docs/exchanges.md) to learn about special configurations needed for each exchange.

- [X] Binance
- [X] Bitmart
- [X] BingX
- [X] Bybit
- [X] Gate.io
- [X] HTX
- [X] Hyperliquid (A decentralized exchange, or DEX)
- [X] Kraken
- [X] OKX
- [X] MyOKX
- [ ] Potentially many others via [CCXT](https://github.com/ccxt/ccxt).

### Supported Futures Exchanges (Experimental)

- [X] Binance
- [X] Gate.io
- [X] Hyperliquid
- [X] OKX
- [X] Bybit

---

## Features

- [X] **Python 3.10+ Support**: Compatible with major operating systems.
- [X] **Dry-run**: Test strategies without financial risk.
- [X] **Backtesting**: Simulate buy/sell strategies.
- [X] **Machine Learning Optimization**: Enhance strategies using real exchange data.
- [X] **Adaptive Modeling**: Use FreqAI for self-training market strategies. [Learn more](https://aivestor.cx/freqai/)
- [X] **Edge Position Sizing**: Calculate optimal stop-loss and position size for specific markets. [Learn more](https://aivestor.cx/edge/)
- [X] **Whitelist/Blacklist Cryptocurrencies**: Manage trading preferences dynamically.
- [X] **Builtin WebUI**: Easy management via a web interface.
- [X] **Telegram Integration**: Manage bots through Telegram commands.
- [X] **Profit/Loss Reports**: Display results in fiat currency.

---

## Quick Start

Follow the [Docker Quickstart Guide](https://aivestor.cx/docker_quickstart/) for an easy setup.

For alternative methods, refer to the [Installation Guide](https://aivestor.cx/installation/).

---

## Bot Commands

### Basic Usage

```bash
usage: aivestor [-h] [-V] {trade,create-userdir,new-config,...}

positional arguments:
  {trade,create-userdir,new-config,...}

options:
  -h, --help            Show help message and exit.
  -V, --version         Show program version and exit.
```

### Telegram Commands

Control the bot via Telegram:

- `/start`: Start trading.
- `/stop`: Stop trading.
- `/status`: View trade status.
- `/profit`: View cumulative profit.
- `/forceexit`: Exit a trade instantly.

Full command list available [here](https://aivestor.cx/telegram-usage/).

---

## Support

- **Discord**: Join our [Discord community](https://discord.gg/p7nuUNVfP7) to discuss strategies, share ideas, or get help.
- **Bugs/Issues**: Report issues via our [GitHub tracker](https://github.com/freqtrade/freqtrade/issues).
- **Feature Requests**: Suggest enhancements [here](https://github.com/freqtrade/freqtrade/labels/enhancement).
- **Contribute**: View our [Contributing Guide](https://github.com/freqtrade/freqtrade/blob/develop/CONTRIBUTING.md).

---

## Requirements

### Hardware
- **Minimal Requirements**: 2GB RAM, 1GB disk space, 2 vCPUs.

### Software
- **Python >= 3.10**
- **pip**
- **git**
- **TA-Lib**
- **virtualenv** (Recommended)
- **Docker** (Recommended)
