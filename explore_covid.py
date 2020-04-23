import os
from itertools import chain

import pandas as pd
import matplotlib.pyplot as plt
plt.style.use('ggplot')

from liquidata import pipe, source

######### Get Covid and world population data #######################

covid_base_url = "https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/"

def fetch_deaths():
    url = os.path.join(covid_base_url, "time_series_covid19_deaths_global.csv")
    print('Downloading deaths data ...')
    df = pd.read_csv(url, index_col=1)
    df.name = 'deaths'
    return df


def fetch_cases():
    url = os.path.join(covid_base_url, "time_series_covid19_confirmed_global.csv")
    print('Downloading cases data ...')
    df = pd.read_csv(url, index_col=1).drop(columns='Province/State Lat Long'.split())
    df.columns =  pd.to_datetime(df.columns)
    df.name = 'cases'
    return df


def load_population(path='.'):
    csv_name = 'WPP2019_TotalPopulationBySex.csv'
    local_copy = os.path.join(path, csv_name)
    if not os.path.exists(local_copy):
        print('Downloading population data ...')
        from urllib.request import urlretrieve
        url = os.path.join('https://population.un.org/wpp/Download/Files/1_Indicators%20(Standard)/CSV_FILES/',
                           csv_name)
        urlretrieve(url, local_copy)
    p = pd.read_csv(local_copy)
    p = p[p.Time == 2020]
    p = p[p.Variant == 'Medium']
    p = p.set_index('Location')
    p['population'] = (p.PopTotal * 1000).astype(int)
    return p.population


def population_rename_countries(p):
    "Rename countries to match those in Covid dataset"
    return p.rename(
        index= {'United States of America'          : 'US',
                'Venezuela (Bolivarian Republic of)': 'Venezuela',
                'Bolivia (Plurinational State of)'  : 'Bolivia',
                'Viet Nam'                          : 'Vietnam',
                'Republic of Moldova'               : 'Moldova',
                'Russian Federation'                : 'Russia',
                'United Republic of Tanzania'       : 'Tanzania',
                'China, Taiwan Province of China'   : 'Taiwan*',
                'Syrian Arab Republic'              : 'Syria',
                'Brunei Darussalam'                 : 'Brunei',
                "Republic of Korea"                 : 'Korea, South',
                'Iran (Islamic Republic of)'        : 'Iran',
                'Myanmar'                           : 'Burma',
                "Côte d'Ivoire"                     : "Cote d'Ivoire",
                'Democratic Republic of the Congo'  : 'Congo (Kinshasa)',
                'Congo'                             : 'Congo (Brazzaville)',
                "Lao People's Democratic Republic"  : 'Laos',
        }
    )


# Ensure data are loaded, but avoid reloading in interactive sessions
if 'pop'    not in locals(): pop    = population_rename_countries(load_population())
if 'cases'  not in locals(): cases  = fetch_cases()
if 'deaths' not in locals(): deaths = fetch_deaths()

####### Utilities for use in pipeline ####################

def smooth(window=7, std=3, min_periods=1, win_type='gaussian', **kwds):
    def smooth(df):
        return df.rolling(window, min_periods=min_periods, win_type=win_type, **kwds).mean(std=std)
    return smooth


def norm(strategy):
    if strategy is max:
        # Normalize WRT the maximum in each column
        def normalize(df):
            return df / df.max()

    elif isinstance(strategy, pd.Series):
        # Normalize each column according to its corresponding value in the
        # Series
        def normalize(df):
            df = df.copy()
            for column in df:
                df[column] /= strategy[column]
            return df
    else:
        #raise ValueError(f'Unrecognized normalization strategy: {strategy}')
        def normalize(df):
            return df / strategy(df)

    return normalize


def merge_country_regions(df, countries=None):
    countries = countries or df.index.unique()
    columns = []
    for c in countries:
        data = df.loc[c]
        if len(data.shape) == 1: columns.append(data)
        else                   : columns.append(data.sum().rename(c))
    return pd.concat(columns, axis=1)


def select(splittable, *rest):
    def select(df):
        countries = chain(splittable.split(), rest)
        return merge_country_regions(df, countries)
    return select


diff = pd.DataFrame.diff
gain = pd.DataFrame.pct_change


def start(date):
    def start(df):
        return df[df.index >= date]
    return start


def plot(df=None, **kwds):
    def plot(df):
        df.plot(**kwds)
        return df
    if kwds:
        return plot
    return plot(df)


def show(_):
    plt.show()

########## Usage Example ####################

nordics            = 'Denmark Sweden Norway Finland Iceland'
western_europe_big = 'Germany France Italy Spain', 'United Kingdom'
eastern_europe     = 'Russia Poland Czechia Ukraine Belarus'
benelux            = 'Belgium Netherlands Luxembourg',
mixA               = 'Switzerland US Italy Singapore', 'Korea, South', 'United Kingdom'
mixB               = 'Spain Switzerland Netherlands Sweden Poland Australia', 'New Zealand'
asia               = 'Japan Vietnam Burma Thailand Singapore Taiwan*', 'Korea, South'
balkans            = 'Croatia Serbia Albania Greece Switzerland', 'Bosnia and Herzegovina'
xxx                = 'Switzerland Austria Hungary Romania Bulgaria Moldova',
africaS            = 'Namibia Angola Botswana Zimbabwe Eswatini Mozambique', 'South Africa'
amerSud            = 'Argentina Brazil Uruguay Paraguay Chile Ecuador Peru',
these              = 'Switzerland Italy Netherlands Poland Australia', 'United Kingdom'

pipe(
    source << [cases],
    select(*these),
    start('2020-03-15'),
    smooth(9, std=3),
    [ norm(pop),          plot(title='total renormalized on population')              ],
    [ diff, smooth(),
      [ norm(pop),        plot(title='growth rate normalized on population') ],
      [ norm(max),        plot(title='growth rate normalized on maximum')    ],
      gain, smooth(),     plot(title='growth factor of growth rate',   ylim=(-.2,.2)) ],
    [ gain, smooth(),     plot(title='growth factor',                  ylim=(  0,.2)),
      gain, smooth(),     plot(title='growth factor of growth factor', ylim=(-.2,.2)) ],
    show)

