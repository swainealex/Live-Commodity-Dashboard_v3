#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Sep 11 18:51:59 2024

@author: alexswaine
"""

import pandas as pd
import dash
import logging
from dash import Dash, dcc, html, Input, Output, callback, ctx
from dash.exceptions import PreventUpdate
import plotly.express as px
import itertools
import requests
import plotly.graph_objects as go
from dash.dependencies import Input, Output, State

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Your API key
api_key = '0Xp45zCtf9hxMyS4jP5HLvJRvgIWLmsWy029sF5V'


def fetch_data():
    urls = {
        'Brent Oil': f'https://api.eia.gov/v2/seriesid/PET.RBRTE.D?api_key={api_key}',
        'Natural Gas': f'https://api.eia.gov/v2/seriesid/NG.RNGWHHD.D?api_key={api_key}',
        'Crude Oil': f'https://api.eia.gov/v2/seriesid/PET.RWTC.D?api_key={api_key}'
    }

    df_all = pd.DataFrame()
    for commodity, url in urls.items():
        response = requests.get(url)
        data = response.json()

        if 'response' in data and 'data' in data['response']:
            dates = [item['period'] for item in data['response']['data']]
            prices = [item['value'] for item in data['response']['data']]
            df = pd.DataFrame(list(zip(dates, prices)), columns=[
                              'Date', f'{commodity} Price'])
            df['Date'] = pd.to_datetime(df['Date'])
            df.set_index('Date', inplace=True)
            df_all = df_all.join(df, how='outer') if not df_all.empty else df

    return df_all.fillna(method='ffill')


def create_plotly_figure(df):
    fig = px.line(df, x=df.index, y=df.columns,
                  title="Historical Commodity Prices")
    fig.update_layout(xaxis_title="Date", yaxis_title="Price, $")
    return fig


# Instantiate Dash app
app = dash.Dash(__name__)
server = app.server

# Layout
app.layout = html.Div([
    html.H1("Live Commodity Price & Correlation Dashboard"),
    html.P("by Alexander Swaine"),
    html.P("Correlation between assets is useful for assuring portfolios are "
           "properly hedged and diversified. Correlation risk (how closely "
           "related different commodities' prices are) tends to go up when "
           "commodity prices rise overall. This means when commodity prices "
           "are increasing rapidly, the relationships between different "
           "commodities' prices become stronger. This correlation risk tends "
           "to decrease when the economy is doing well (in a boom phase) and "
           "increase when the economy is struggling (in a recession). "
           "There's evidence linking this correlation risk to how financially "
           "developed commodity markets are for instance with specified commodity "
           "index funds. More financially developed markets tend to have "
           "stronger correlations between commodities."),
    html.P("The core aim of this resource is to investigate these claims."
           "The following dashboard presents various visuals and indicators of "
           "the correlation between the three commodities: "
           "Brent Crude Oil, Natural Gas (Henry Hub Spot Price), and Crude Oil "
           "(West Texas Intermediate). Live data is obtained through an API "
           "from the Energy Information Administration (EIA) - an open source"
           " creditied below. As more information is collected "
           "and published open-source the goal is to extend the body of data "
           "beyond these three commodities towards a more complete picture of "
           "correlation risk. Though this is also intended to aide commodity "
           "market traders in order to test the previously discussed claims. "
           "As such, multiple time periods must be available for analysis"
           "in conjuction other live market data."
           ),

    # Data refresh button
    html.Button('Refresh Data', id='refresh-button', n_clicks=0),

    # Live Chart
    dcc.Graph(id='live-chart'),
    dcc.Interval(
        id='interval-component',
        interval=60*60*1000,  # Update every hour
        n_intervals=0
    ),
    html.P("Alongside contextual historical price data, there are two main "
           "indicators: the correlation matrix, and the rolling correlation "
           "time series. The correlation matrix simply displays the calculate correlation "
           "coefficients between all three commodities over the time period in question. "
           "The rolling correlation time series displays how correlation between "
           "two assets has varied over time. This 'rolling window' is proportional "
           "towards the specific time period in question. Both depict several "
           "time periods each to gain a fuller perspective. "
           ),
    # Heatmap Row
    html.H2("Correlation Heatmaps"),
    dcc.Graph(id='correlation-heatmap-total'),
    html.Div([
        dcc.Graph(id='correlation-heatmap-last-5-days'),
        dcc.Graph(id='correlation-heatmap-last-30-days'),

    ], style={'display': 'flex', 'justify-content': 'space-between'}),
    html.Div([
        dcc.Graph(id='correlation-heatmap-year-to-date'),
        dcc.Graph(id='correlation-heatmap-last-5-years'),
    ], style={'display': 'flex', 'justify-content': 'space-between'}),

    # Rolling Correlations
    html.H2("Rolling Correlation Time Series"),

    dcc.Graph(id='rolling-correlation-last-30-days'),
    dcc.Graph(id='rolling-correlation-year-to-date'),
    dcc.Graph(id='rolling-correlation-last-5-years'),


    # Status message
    html.Div(id='status-message')
])


@app.callback(
    [
        Output('live-chart', 'figure'),
        Output('correlation-heatmap-total', 'figure'),
        Output('correlation-heatmap-last-5-days', 'figure'),
        Output('correlation-heatmap-last-30-days', 'figure'),
        Output('correlation-heatmap-year-to-date', 'figure'),
        Output('correlation-heatmap-last-5-years', 'figure'),
        Output('rolling-correlation-last-30-days', 'figure'),
        Output('rolling-correlation-year-to-date', 'figure'),
        Output('rolling-correlation-last-5-years', 'figure'),
        Output('status-message', 'children')
    ],
    [
        Input('interval-component', 'n_intervals'),
        Input('refresh-button', 'n_clicks')
    ],
    prevent_initial_call=True,
    suppress_callback_exceptions=True
)
def update_all_visualizations(n, n_refresh):
    logger.debug("Callback triggered")

    # Initialize all output variables
    fig_live = None
    fig_total = None
    fig_last_5_days = None
    fig_last_30_days = None
    fig_year_to_date = None
    fig_last_5_years = None
    fig_rolling_30_days = None
    fig_rolling_ytd = None
    fig_rolling_5_years = None
    status_message = ""

    try:
        ctx = dash.callback_context

        if ctx.triggered:
            trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]

            # Fetch data
            df = fetch_data()
            logger.debug("Data fetched successfully")

            # Create live chart figure
            fig_live = create_plotly_figure(df)
            logger.debug("Live chart figure created")

            # Calculate correlations
            total_corr = df.corr()
            last_5_days = df.tail(5).corr()
            last_30_days = df.tail(30).corr()
            year_to_date = df.tail(max(365, len(df))).corr()
            last_5_years = df.tail(max(1826, len(df))).corr()

            vmin = -1
            vmax = 1

            def create_heatmap(corr_matrix, title):
                fig = px.imshow(corr_matrix, text_auto=True, aspect="auto",
                                labels=dict(
                                    x='', y='', color='Correlation Coefficient'),
                                title=title,
                                color_continuous_scale="Spectral",
                                zmin=vmin, zmax=vmax)
                return fig

            fig_total = create_heatmap(total_corr, "Total Correlation")
            fig_last_5_days = create_heatmap(
                last_5_days, "Correlation (Last 5 Days)")
            fig_last_30_days = create_heatmap(
                last_30_days, "Correlation (Last 30 Days)")
            fig_year_to_date = create_heatmap(
                year_to_date, "Correlation (Year to Date)")
            fig_last_5_years = create_heatmap(
                last_5_years, "Correlation (Last 5 Years)")

            # Create rolling correlation figures
            timeframes = {
                'Last 5 Days': 1,
                'Last 30 Days': 5,
                'Year to Date (YTD)': 30,
                'Last 5 Years': 60
            }

            commodities = ['Brent Oil Price',
                           'Natural Gas Price', 'Crude Oil Price']

            def plot_rolling_corr(df, timeframe, window):
                fig = go.Figure()
                for commodity1, commodity2 in itertools.combinations(commodities, 2):
                    rolling_corr = df[commodity1].rolling(
                        window=window).corr(df[commodity2])
                    fig.add_trace(go.Scatter(x=df.index, y=rolling_corr,
                                             mode='lines', name=f'{commodity1} vs {commodity2}'))

                fig.update_layout(
                    title=f'Rolling {window}-Day Correlation - {timeframe}',
                    xaxis_title='Date',
                    yaxis_title='Correlation',
                    yaxis_range=[-1, 1],
                    hovermode='x unified'
                )

                fig.update_xaxes(showgrid=True, gridwidth=1,
                                 gridcolor='#E2E2EA')
                fig.update_yaxes(showgrid=True, gridwidth=1,
                                 gridcolor='#E2E2EA')
                fig.add_hline(y=0, line_dash="dash", line_color="#000")

                return fig

            # Loop through each timeframe and plot the corresponding rolling correlations
            for timeframe, window in timeframes.items():
                df_timeframe = df if timeframe == 'Total Correlation' else df.tail({
                    'Last 5 Days': 5, 'Last 30 Days': 30, 'Year to Date (YTD)': 365, 'Last 5 Years': 1826}[timeframe])
                fig_rolling = plot_rolling_corr(
                    df_timeframe, timeframe, window)

                if timeframe == 'Last 30 Days':
                    fig_rolling_30_days = fig_rolling
                elif timeframe == 'Year to Date (YTD)':
                    fig_rolling_ytd = fig_rolling
                elif timeframe == 'Last 5 Years':
                    fig_rolling_5_years = fig_rolling

            status_message = "Data updated successfully"

        else:
            logger.debug("No trigger detected")
            raise PreventUpdate

    except Exception as e:
        logger.error(f"Error updating visualizations: {str(e)}", exc_info=True)
        status_message = f"An error occurred while updating visualizations: {str(e)}"

    return [
        fig_live,
        fig_total,
        fig_last_5_days,
        fig_last_30_days,
        fig_year_to_date,
        fig_last_5_years,
        fig_rolling_30_days,
        fig_rolling_ytd,
        fig_rolling_5_years,
        status_message
    ]


if __name__ == '__main__':
    app.run_server(debug=True)
