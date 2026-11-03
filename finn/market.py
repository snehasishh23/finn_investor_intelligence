"""Daily bars only. Latest completed session compared with the preceding 20 sessions."""
import hashlib
import math
from datetime import datetime, time
from zoneinfo import ZoneInfo
import yfinance as yf
from . import cache

PORTFOLIO = 'RELIANCE TCS HDFCBANK INFY ICICIBANK SUNPHARMA TATAMOTORS ITC LT BHARTIARTL ASIANPAINT TITAN DIXON ETERNAL KPITTECH PERSISTENT'.split()


def summarize(ticker, frame, now=None):
    frame = frame.dropna(subset=['Close', 'Volume'])
    now = now or datetime.now(ZoneInfo('Asia/Kolkata'))
    # Yahoo may return an in-progress daily candle. Wait until after the close.
    if len(frame) and frame.index[-1].date() == now.date() and now.time() < time(15, 45):
        frame = frame.iloc[:-1]
    if len(frame) < 21:
        return None
    price, previous = float(frame.Close.iloc[-1]), float(frame.Close.iloc[-2])
    baseline = float(frame.Volume.iloc[-21:-1].mean())
    volume = float(frame.Volume.iloc[-1])
    if previous <= 0 or baseline <= 0 or volume < 0 or not all(map(math.isfinite, [price, previous, baseline, volume])):
        return None
    return {'t': ticker, 'px': round(price, 2), 'ch': round((price / previous - 1) * 100, 2),
            'vol': round(volume / baseline, 2), 'as_of': str(frame.index[-1].date())}


def eod(tickers=None):
    tickers = tickers or PORTFOLIO
    key = 'eod:v2:' + hashlib.sha256(','.join(tickers).encode()).hexdigest()
    cached = cache.get(key, 1800)
    if cached is not None:
        return cached
    frame = yf.download([t + '.NS' for t in tickers], period='3mo', group_by='ticker',
                        progress=False, threads=True, auto_adjust=True, timeout=12)
    out = []
    for ticker in tickers:
        try:
            data = frame[ticker + '.NS'] if frame.columns.nlevels > 1 else frame
            row = summarize(ticker, data)
            if row:
                out.append(row)
        except (KeyError, ValueError, IndexError):
            continue
    return cache.put(key, out) if out else out
