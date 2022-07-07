from argparse import ArgumentParser
import calendar
from datetime import datetime
import json
from pathlib import Path

import pandas as pd
import plotly
import plotly.graph_objects as go


def calculate_daily_balance(transactions_by_date, year, month, daysinmonth):
    daily_index = pd.date_range(
        pd.Timestamp(year, month, 1), pd.Timestamp(year, month, daysinmonth)
    )
    df_daily = pd.DataFrame(transactions_by_date["Running Balance"])
    return df_daily.reindex(daily_index, method="pad")


def format_df(df, year, month):
    df["Date"] = [pd.Timestamp(year, month, int(day)) for day in df["Date"]]
    return df


def format_transactions(df_credits, df_debits):
    transactions = pd.concat([df_credits, df_debits]).reset_index(drop=True)
    transactions = transactions.set_index("Date").sort_index()
    transactions["Balance"] = transactions["Amount"].cumsum()
    return transactions


def format_transactions_by_date(transactions):
    transactions_by_date = (
        transactions.groupby("Date")
        .agg({"Amount": "sum"})
        .rename(columns={"Amount": "Net Change"})
    )
    transactions_by_date["Running Balance"] = transactions_by_date[
        "Net Change"
    ].cumsum()
    return transactions_by_date


def get_date_info():
    now = datetime.now()
    month = now.month
    year = now.year
    daysinmonth = calendar.monthrange(now.year, now.month)[1]
    return year, month, daysinmonth


def load_data(path, year, month):
    if not isinstance(path, Path):
        path = Path(path)
    colnames = ["Item", "Date", "Amount"]

    df_credits = pd.read_excel(
        path, header=1, usecols="A:C", names=colnames
    ).dropna()
    df_debits = pd.read_excel(
        path, header=1, usecols="D:F", names=colnames
    ).dropna()

    df_credits = format_df(df_credits, year, month)
    df_debits = format_df(df_debits, year, month)
    df_debits["Amount"] = -df_debits["Amount"]

    return df_credits, df_debits


def plot_projection(df_daily, df_credits, df_debits, month, year, jsonflag=False):

    fig = go.Figure()

    fig.add_traces(
        [
            go.Scatter(
                x=df_daily.index,
                y=df_daily["Running Balance"],
                mode="lines+markers",
                name="Daily Balance",
            ),
            go.Scatter(
                x=df_credits["Date"],
                y=df_credits["Amount"],
                mode="markers",
                error_y={
                    "type": "data",
                    "symmetric": False,
                    "arrayminus": df_credits["Amount"],
                    "array": [0] * len(df_credits["Amount"]),
                    "width": 0,
                },
                marker={"size": 16, "symbol": "triangle-up", "color": "green"},
                name="Credits",
                hovertemplate="%{x}: %{y:$.2f}",
            ),
            go.Scatter(
                x=df_debits["Date"],
                y=df_debits["Amount"],
                mode="markers",
                error_y={
                    "type": "data",
                    "symmetric": False,
                    "arrayminus": df_debits["Amount"],
                    "array": [0] * len(df_debits["Amount"]),
                    "width": 0,
                },
                marker={"size": 16, "symbol": "triangle-down", "color": "red"},
                name="Debits",
                hovertemplate="%{x}: %{y:$.2f}",
            ),
        ]
    )

    fig.add_vline(datetime.now())
    fig.add_hline(0)

    fig.update_yaxes(hoverformat="d")
    fig.update_layout(
        title=f"Cash Flow & Projected Daily Balance for {month:02d}/{year}",
        xaxis_title="Date",
        yaxis_title="Projected Balance",
        yaxis_tickprefix="$",
        width=900,
    )

    if jsonflag:
        return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    else:
        fig.show()
        return fig


def cashflow(path, jsonflag=True):
    year, month, daysinmonth = get_date_info()
    df_credits, df_debits = load_data(path, year, month)
    transactions = format_transactions(df_credits, df_debits)
    transactions_by_date = format_transactions_by_date(transactions)
    df_daily = calculate_daily_balance(transactions_by_date, year, month, daysinmonth)
    fig = plot_projection(
        df_daily, df_credits, df_debits, month, year, jsonflag=jsonflag
    )
    return fig, transactions.reset_index().to_html(
        classes="table table-striped table-hover table-sm", index=False, justify="left"
    )


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("path")
    args = parser.parse_args()
    fig = cashflow(args["path"])
