from automation.weekly_report import calculate_metrics


def test_calculate_metrics_empty():
    metrics = calculate_metrics([])
    assert metrics["total_trades"] == 0
    assert metrics["winning_trades"] == 0
    assert metrics["losing_trades"] == 0
    assert metrics["win_rate_pct"] == 0.0
    assert metrics["total_profit_usdt"] == 0.0
    assert metrics["total_profit_pct"] == 0.0
    assert metrics["best_trade_pair"] == "N/A"
    assert metrics["worst_trade_pair"] == "N/A"
    assert metrics["total_fees_usdt"] == 0.0
    assert metrics["fees_as_pct_of_profit"] == 0.0
    assert metrics["by_strategy"] == {}


def test_calculate_metrics_single_trade():
    trades = [
        {
            "pair": "BTC/USDT",
            "profit_ratio": 0.05,
            "profit_abs": 10.0,
            "fee_open": 0.5,
            "fee_close": 0.5,
            "strategy": "ScalpV1",
        }
    ]
    metrics = calculate_metrics(trades)

    assert metrics["total_trades"] == 1
    assert metrics["winning_trades"] == 1
    assert metrics["losing_trades"] == 0
    assert metrics["win_rate_pct"] == 100.0
    assert metrics["total_profit_usdt"] == 10.0
    assert metrics["total_profit_pct"] == 5.0
    assert metrics["best_trade_usdt"] == 10.0
    assert metrics["worst_trade_usdt"] == 10.0
    assert metrics["best_trade_pair"] == "BTC/USDT"
    assert metrics["worst_trade_pair"] == "BTC/USDT"
    assert metrics["total_fees_usdt"] == 1.0
    assert metrics["fees_as_pct_of_profit"] == 10.0  # 1.0 / 10.0 * 100

    assert "ScalpV1" in metrics["by_strategy"]
    assert metrics["by_strategy"]["ScalpV1"]["trades"] == 1
    assert metrics["by_strategy"]["ScalpV1"]["wins"] == 1
    assert metrics["by_strategy"]["ScalpV1"]["profit"] == 10.0
    assert metrics["by_strategy"]["ScalpV1"]["win_rate"] == 100.0


def test_calculate_metrics_multiple_trades():
    trades = [
        {
            "pair": "BTC/USDT",
            "profit_ratio": 0.05,
            "profit_abs": 10.0,
            "fee_open": 0.5,
            "fee_close": 0.5,
            "strategy": "ScalpV1",
        },
        {
            "pair": "ETH/USDT",
            "profit_ratio": -0.02,
            "profit_abs": -4.0,
            "fee_open": 0.2,
            "fee_close": 0.2,
            "strategy": "MeanReversionV1",
        },
        {
            "pair": "SOL/USDT",
            "profit_ratio": 0.08,
            "profit_abs": 16.0,
            "fee_open": 0.8,
            "fee_close": 0.8,
            "strategy": "ScalpV1",
        },
    ]
    metrics = calculate_metrics(trades)

    assert metrics["total_trades"] == 3
    assert metrics["winning_trades"] == 2
    assert metrics["losing_trades"] == 1
    assert metrics["win_rate_pct"] == round((2 / 3) * 100, 1)  # 66.7
    assert metrics["total_profit_usdt"] == 22.0  # 10 - 4 + 16
    assert metrics["total_profit_pct"] == 11.0  # (0.05 - 0.02 + 0.08) * 100
    assert metrics["avg_profit_per_trade_usdt"] == round(22.0 / 3, 2)
    assert metrics["best_trade_pair"] == "SOL/USDT"
    assert metrics["worst_trade_pair"] == "ETH/USDT"
    assert metrics["best_trade_usdt"] == 16.0
    assert metrics["worst_trade_usdt"] == -4.0

    total_fees = 1.0 + 0.4 + 1.6
    assert metrics["total_fees_usdt"] == 3.0
    assert metrics["fees_as_pct_of_profit"] == round((3.0 / 22.0) * 100, 2)

    # Strategy checks
    assert metrics["by_strategy"]["ScalpV1"]["trades"] == 2
    assert metrics["by_strategy"]["ScalpV1"]["wins"] == 2
    assert metrics["by_strategy"]["ScalpV1"]["profit"] == 26.0
    assert metrics["by_strategy"]["ScalpV1"]["win_rate"] == 100.0

    assert metrics["by_strategy"]["MeanReversionV1"]["trades"] == 1
    assert metrics["by_strategy"]["MeanReversionV1"]["wins"] == 0
    assert metrics["by_strategy"]["MeanReversionV1"]["profit"] == -4.0
    assert metrics["by_strategy"]["MeanReversionV1"]["win_rate"] == 0.0


def test_calculate_metrics_zero_profit_edge_case():
    trades = [
        {
            "pair": "BTC/USDT",
            "profit_ratio": 0.05,
            "profit_abs": 10.0,
            "fee_open": 0.5,
            "fee_close": 0.5,
            "strategy": "ScalpV1",
        },
        {
            "pair": "ETH/USDT",
            "profit_ratio": -0.05,
            "profit_abs": -10.0,
            "fee_open": 0.5,
            "fee_close": 0.5,
            "strategy": "ScalpV1",
        },
    ]
    metrics = calculate_metrics(trades)

    assert metrics["total_profit_usdt"] == 0.0
    # The code sets fees_as_pct_of_profit to 0 if total_profit == 0 to avoid division by zero
    assert metrics["fees_as_pct_of_profit"] == 0.0
