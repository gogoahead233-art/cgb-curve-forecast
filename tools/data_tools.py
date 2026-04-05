"""
Unified Data Tools Entry Point
================================
Automatically selects Wind or AKShare data source based on config.DATA_SOURCE.
"""

import config


def get_data_tools():
    """Return the list of data tools for the current configuration."""
    if config.DATA_SOURCE == "wind":
        try:
            from tools.wind_tools import (
                get_macro_data, get_yield_curve, get_funding_data,
                get_futures_data, get_stock_index, get_us_treasury,
            )
        except ImportError:
            print("Warning: Wind unavailable, automatically switching to AKShare")
            from tools.akshare_tools import (
                get_macro_data, get_yield_curve, get_funding_data,
                get_futures_data, get_stock_index, get_us_treasury,
            )
    else:
        from tools.akshare_tools import (
            get_macro_data, get_yield_curve, get_funding_data,
            get_futures_data, get_stock_index, get_us_treasury,
        )

    return {
        "get_macro_data": get_macro_data,
        "get_yield_curve": get_yield_curve,
        "get_funding_data": get_funding_data,
        "get_futures_data": get_futures_data,
        "get_stock_index": get_stock_index,
        "get_us_treasury": get_us_treasury,
    }
