from preswald import connect, get_df, query, table, text, plotly, matplotlib
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
text("# GitHub Programming Languages Analytics")
text("---")

try:
    connect()
    issues_df = get_df("issues_csv")
    prs_df = get_df("prs_csv")
    repos_df = get_df("repos_csv")
    text("**System Status**: All datasets loaded successfully")

    total_records = sum(len(df) for df in [issues_df, prs_df, repos_df])
    text(f" **Data Overview**: {total_records:,} total records processed")

except Exception as e:
    text(f"❌ **System Error**: {str(e)}")
    text("Please ensure all CSV files are properly uploaded and data source aliases match `preswald.toml`")
    import sys
    sys.exit(1)

def preprocess_datasets():
    global issues_df, prs_df, repos_df
    if issues_df is None or prs_df is None or repos_df is None:
        raise ValueError("One or more dataframes did not load correctly.")
    issues_df['count'] = pd.to_numeric(issues_df['count'], errors='coerce').fillna(0)
    issues_df = issues_df[issues_df['count'] > 0]
    prs_df['count'] = pd.to_numeric(prs_df['count'], errors='coerce').fillna(0)
    prs_df = prs_df[prs_df['count'] > 0]
    repos_df['num_repos'] = pd.to_numeric(repos_df['num_repos'], errors='coerce').fillna(0)
    repos_df = repos_df[repos_df['num_repos'] > 0]
    issues_summary = (
        issues_df.groupby('name')['count']
        .sum()
        .reset_index()
        .rename(columns={'count': 'total_issues'})
    )

    prs_summary = (
        prs_df.groupby('name')['count']
        .sum()
        .reset_index()
        .rename(columns={'count': 'total_prs'})
    )

    activity_summary = pd.merge(
        issues_summary,
        prs_summary,
        on='name',
        how='outer'
    ).fillna(0)

    complete_df = pd.merge(
        activity_summary,
        repos_df,
        left_on='name',
        right_on='language',
        how='outer'
    ).fillna(0)

    complete_df['language'] = complete_df['language'].fillna(complete_df['name'])

    complete_df['development_velocity'] = (
        complete_df['total_prs'] / (complete_df['num_repos'] + 1)
    )
    complete_df['issue_density'] = (
        complete_df['total_issues'] / (complete_df['num_repos'] + 1)
    )
    complete_df['activity_ratio'] = (
        complete_df['total_prs'] / (complete_df['total_issues'] + 1)
    )
    complete_df['ecosystem_health'] = (
        (complete_df['total_prs'] * 2 + complete_df['num_repos']) /
        (complete_df['total_issues'] + 1)
    )
    return complete_df

comprehensive_df = preprocess_datasets()
text("## ● Dashboard")

total_languages = len(comprehensive_df)
total_repositories = int(comprehensive_df['num_repos'].sum())
total_issues = int(comprehensive_df['total_issues'].sum())
total_prs = int(comprehensive_df['total_prs'].sum())
development_efficiency_pct = (total_prs / (total_issues + 1)) * 100

kpi_metrics = f"""
**● Performance Indicators**
- **Languages Analyzed**: {total_languages:,}
- **Total Repositories**: {total_repositories:,}
- **Issues Tracked**: {total_issues:,}
- **Pull Requests**: {total_prs:,}
- **Development Efficiency**: {development_efficiency_pct:.1f}% PR-to-Issue Ratio
"""
text(kpi_metrics)
text("##  1. Language Analysis")
text("### ● Programming Language Market Leaders")
market_leaders_query = """
SELECT
    language,
    num_repos,
    ROUND(
        CAST(num_repos AS FLOAT) /
        CAST((SELECT SUM(CAST(num_repos AS FLOAT)) FROM repos_csv) AS FLOAT)
        * 100, 2
    ) as market_share_pct
FROM repos_csv
WHERE CAST(num_repos AS INTEGER) > 0
ORDER BY market_share_pct DESC
"""

market_leaders = query(market_leaders_query, "repos_csv")

if market_leaders is not None and not market_leaders.empty:

    table(market_leaders, title="Top Languages by Market Share")
    page_size = 10
    page_number = 1
    start_idx = (page_number - 1) * page_size
    end_idx = page_number * page_size

    current_page_data = market_leaders[start_idx:end_idx]

    current_page_data_sorted_by_repos = current_page_data.sort_values(
        by="num_repos", ascending=False
    )

    fig1 = go.Figure()
    fig1.add_trace(
        go.Bar(
            x=current_page_data_sorted_by_repos['language'],
            y=current_page_data_sorted_by_repos['num_repos'],
            name="Repositories",
            text=current_page_data_sorted_by_repos['num_repos'],
            textposition='outside'
        )
    )

    fig1.update_layout(
        title="Repository Count Distribution",
        height=400,
        width=800,
        showlegend=False,
        margin=dict(t=50, b=50, l=50, r=50),
    )

    text("#### Repository Count Distribution")
    plotly(fig1)

    current_page_data_sorted_by_share = current_page_data.sort_values(
        by="market_share_pct", ascending=False
    )

    fig2 = go.Figure()
    fig2.add_trace(
        go.Pie(
            labels=current_page_data_sorted_by_share['language'],
            values=current_page_data_sorted_by_share['market_share_pct'],
            name="Market Share"
        )
    )

    fig2.update_layout(
        title="Programming Language Market Share",
        height=400,
        width=800,
        showlegend=True,
        margin=dict(t=50, b=50, l=50, r=50),
    )

    text("#### Market Share Analysis")
    plotly(fig2)

else:
    text("No data available for market leaders.")

text("## 2. Language Evolution & Growth Patterns")
issues_data = """
SELECT * FROM issues_csv
"""
all_data = query(issues_data, "issues_csv")
table(all_data, title="Data in issues_csv")
yearly_issues = query(
    """
    SELECT
      TRIM(LOWER(name)) AS language_normalized,
      year,
      SUM(CAST(count AS INTEGER)) AS issues_count
    FROM (
      SELECT DISTINCT
        TRIM(LOWER(name)) AS name,
        year,
        count
      FROM issues_csv
      WHERE name IS NOT NULL AND year IS NOT NULL AND count IS NOT NULL
    )
    GROUP BY language_normalized, year
    ORDER BY language_normalized, year
    """,
    "issues_csv"
)

yearly_issues["year"] = yearly_issues["year"].astype(int)
yearly_issues = yearly_issues.sort_values(["language_normalized", "year"])
yearly_issues["prev_year_issues"] = yearly_issues.groupby("language_normalized")["issues_count"].shift(1)
yearly_issues["growth_rate_pct"] = (
    (yearly_issues["issues_count"] - yearly_issues["prev_year_issues"])
    / yearly_issues["prev_year_issues"] * 100
)
yearly_issues = yearly_issues.dropna(subset=["growth_rate_pct"])

latest_year = int(yearly_issues["year"].max())
text(f"- Latest year analyzed: **{latest_year}**")

growth_latest = yearly_issues[yearly_issues["year"] == latest_year].copy()
growth_latest["absolute_change"] = growth_latest["issues_count"] - growth_latest["prev_year_issues"]

combined_top = growth_latest.copy()
combined_top = combined_top.sort_values("growth_rate_pct", ascending=False).head(100)
combined_top["growth_rank"] = combined_top["growth_rate_pct"].rank(ascending=False, method='min')

abs_top = (
    growth_latest.sort_values("absolute_change", ascending=False).head(100)
    .assign(rank_by="Absolute Increase")
)
abs_top["absolute_rank"] = abs_top["absolute_change"].rank(ascending=False, method='min')

combined_final = (
    pd.concat([combined_top, abs_top])
    .drop_duplicates(subset=["language_normalized"])
    .sort_values("growth_rate_pct", ascending=False)
)

combined_final['rank'] = combined_final.apply(
    lambda row: f"Growth Rank: {int(row['growth_rank'])}" if pd.notnull(row['growth_rank']) else 
                f"Absolute Rank: {int(row['absolute_rank'])}",
    axis=1
)

table(
    combined_final[[
        "language_normalized", 
        "issues_count", 
        "prev_year_issues", 
        "growth_rate_pct", 
        "absolute_change", 
        "rank"
    ]],
    title=f" Top Languages by Growth and Volume ({latest_year})"
)


fig = px.line(
    yearly_issues,
    x="year",
    y="issues_count",
    color="language_normalized",
    markers=True,
    line_group="language_normalized",
    hover_name="language_normalized",
    title=" Language Issue Trends Over Time",
    labels={
        "issues_count": "Total Issues",
        "year": "Year",
        "language_normalized": "Language"
    },
)

fig.update_layout(
    height=650,
    width=1000,
    plot_bgcolor='white',
    paper_bgcolor='white',
    font=dict(size=13),
    legend_title_text="Language",
    margin=dict(t=60, b=60, l=60, r=60)
)

fig.update_xaxes(showgrid=True, gridcolor='lightgrey')
fig.update_yaxes(showgrid=True, gridcolor='lightgrey', title_text="Total Issues")

plotly(fig)


text(f"### ● Growth Profile: Absolute vs % Growth — {latest_year}")

combo_data = combined_final.copy()
combo_data["language"] = combo_data["language_normalized"].str.title()
combo_data = combo_data.sort_values("absolute_change", ascending=False)

import plotly.graph_objects as go

fig = go.Figure()

fig.add_trace(go.Bar(
    x=combo_data["language"],
    y=combo_data["absolute_change"],
    name="Absolute Change in Issues",
    marker_color="#636EFA",
    yaxis='y1',
    hovertemplate="%{y} issue increase<extra></extra>"
))

fig.add_trace(go.Scatter(
    x=combo_data["language"],
    y=combo_data["growth_rate_pct"],
    name="Growth Rate (%)",
    mode="markers+lines",
    yaxis='y2',
    line=dict(color="#EF553B", width=2),
    marker=dict(size=8),
    hovertemplate="%{y:.1f}% growth<extra></extra>"
))

fig.update_layout(
    xaxis=dict(title="Language"),
    yaxis=dict(
        title="Absolute Change in Issues",
        titlefont=dict(color="#636EFA"),
        tickfont=dict(color="#636EFA")
    ),
    yaxis2=dict(
        title="Growth Rate (%)",
        titlefont=dict(color="#EF553B"),
        tickfont=dict(color="#EF553B"),
        overlaying="y",
        side="right"
    ),
    legend=dict(x=0.01, y=1.15, orientation="h"),
    plot_bgcolor="white",
    paper_bgcolor="white",
    font=dict(size=13),
    height=600,
    width=1000,
    margin=dict(t=70, b=60, l=60, r=60)
)

plotly(fig)

prs_clean = query("""
    SELECT 
        TRIM(LOWER(name)) AS language,
        year,
        quarter,
        CAST(count AS INTEGER) AS pr_count
    FROM prs_csv
    WHERE name IS NOT NULL 
    AND year IS NOT NULL 
    AND quarter IS NOT NULL 
    AND count IS NOT NULL
    ORDER BY language, year, quarter
""", "prs_csv")

text("## 3. Momentum Analysis of Languages")
text("### **Question**: Which languages show accelerating vs decelerating development momentum?")

momentum_data = []
languages = prs_clean['language'].unique()

for lang in languages:
    lang_data = prs_clean[prs_clean['language'] == lang].sort_values(['year', 'quarter'])
    
    if len(lang_data) >= 4:
        lang_data['prev_count'] = lang_data['pr_count'].shift(1)
        lang_data['qoq_change'] = lang_data['pr_count'] - lang_data['prev_count']
        lang_data['qoq_pct'] = (lang_data['qoq_change'] / lang_data['prev_count'] * 100).fillna(0)
        
        recent_quarters = lang_data.tail(3)
        early_quarters = lang_data.head(3)
        
        recent_avg_growth = recent_quarters['qoq_pct'].mean()
        early_avg_growth = early_quarters['qoq_pct'].mean()
        
        momentum_acceleration = recent_avg_growth - early_avg_growth
        
        growth_consistency = 100 - min(100, lang_data['qoq_pct'].std())
        
        total_prs = lang_data['pr_count'].sum()
        peak_quarter = lang_data['pr_count'].max()
        latest_quarter = lang_data['pr_count'].iloc[-1]
        
        momentum_data.append({
            'language': lang.title(),
            'momentum_acceleration': round(momentum_acceleration, 2),
            'growth_consistency_score': round(growth_consistency, 2),
            'recent_avg_growth_pct': round(recent_avg_growth, 2),
            'total_prs': total_prs,
            'peak_to_current_ratio': round(peak_quarter / latest_quarter, 2) if latest_quarter > 0 else 0,
            'momentum_category': 'Accelerating' if momentum_acceleration > 5 else 'Stable' if momentum_acceleration > -5 else 'Decelerating'
        })

momentum_df = pd.DataFrame(momentum_data).sort_values('momentum_acceleration', ascending=False)
table(momentum_df, title=" Language Momentum Report")

text(f"**Debug Info**: Found {len(momentum_df)} languages for momentum analysis")
table(momentum_df, title="Momentum Data for Debugging")

if len(momentum_df) > 0:
   if len(momentum_df) > 15:
       plot_data = momentum_df
       text(f"Displaying the top 20 languages out of a total of {len(momentum_df)} for clarity. Additional data is available.")
   else:
       plot_data = momentum_df
   text(f"Categories found: {plot_data['momentum_category'].value_counts().to_dict()}")
   
   fig = go.Figure()
   
   colors = {'Accelerating': '#2E8B57', 'Stable': '#f3ff33', 'Decelerating': '#DC143C'}
   
   all_categories = ['Accelerating', 'Stable', 'Decelerating']
   
   for category in all_categories:
       category_data = plot_data[plot_data['momentum_category'] == category]
       
       if len(category_data) > 0:
           fig.add_trace(go.Scatter(
               x=category_data['growth_consistency_score'],
               y=category_data['momentum_acceleration'],
               mode='markers',
               marker=dict(
                   size=category_data['total_prs'] / 100,
                   color=colors.get(category, '#888888'),
                   opacity=0.7,
                   line=dict(width=2, color='black')
               ),
               name=f'{category} ({len(category_data)})',
               text=category_data['language'],
               hovertemplate='<b>%{text}</b><br>' +
                            'Growth Consistency: %{x}<br>' +
                            'Momentum Acceleration: %{y}%<br>' +
                            f'Category: {category}<br>' +
                            '<extra></extra>'
           ))
       else:
           fig.add_trace(go.Scatter(
               x=[None],
               y=[None],
               mode='markers',
               marker=dict(color=colors.get(category, '#888888')),
               name=f'{category} (0)',
               showlegend=True
           ))
   
   fig.add_hline(y=0, line_dash="dash", line_color="gray", line_width=1)
   fig.add_vline(x=50, line_dash="dash", line_color="gray", line_width=1)
   
   fig.update_layout(
       title='Language Developing Momentum',
       xaxis_title='Growth Consistency Score',
       yaxis_title='Momentum Acceleration (%)',
       height=600,
       width=1000,
       plot_bgcolor='white',
       paper_bgcolor='white',
       showlegend=True
   )
   
   plotly(fig)
else:
   text("No momentum data available for visualization")

text("### ● Competitive Market Share ")
text("### **Question**: How is market share shifting between competing languages in the same domain?")

quarterly_totals = prs_clean.groupby(['year', 'quarter'])['pr_count'].sum().reset_index()
quarterly_totals['period'] = quarterly_totals['year'].astype(str) + '-Q' + quarterly_totals['quarter'].astype(str)

prs_with_share = prs_clean.merge(quarterly_totals[['year', 'quarter', 'pr_count']], 
                                on=['year', 'quarter'], suffixes=('', '_total'))
prs_with_share['market_share_pct'] = (prs_with_share['pr_count'] / prs_with_share['pr_count_total'] * 100)

web_languages = ['javascript', 'php', 'ruby', 'html', 'css', 'typescript', 'nodejs', 'angular', 'react', 'vue', 'asp.net', 'go', 'dart', 'elixir', 'svelte', 'jquery', 'graphql']
systems_languages = ['c', 'c++', 'java', 'c#', 'rust', 'assembly', 'fortran', 'pascal', 'ada', 'delphi', 'objective-c', 'scala', 'lua']
data_science_languages = ['r', 'matlab', 'julia', 'sas', 'sql', 'octave', 'haskell']
mobile_languages = ['swift', 'kotlin', 'dart', 'objective-c', 'react-native', 'flutter', 'xamarin']
game_dev_languages = ['lua', 'unreal script', 'gml', 'swift']
embedded_languages = ['ada', 'arduino', 'vhdl', 'verilog']
functional_languages = ['haskell', 'elixir', 'ocaml', 'f#', 'clojure', 'scheme', 'lisp', 'erl']
scripting_languages = ['bash', 'perl', 'ruby', 'lua', 'groovy', 'powershell', 'tcl']
enterprise_languages = ['delphi', 'vb.net', 'swift', 'kotlin']
markup_query_languages = ['html', 'xml', 'json', 'yaml', 'graphql', 'xslt', 'css', 'xpath']
cloud_devops_languages = ['bash', 'golang', 'yaml', 'terraform', 'dockerfile', 'groovy', 'powershell']
oop_languages = ['python', 'java', 'c++', 'ruby', 'c#', 'swift', 'scala', 'objective-c', 'perl', 'typescript', 'php']


def analyze_competitive_cluster(languages, cluster_name):
    cluster_data = prs_with_share[prs_with_share['language'].isin(languages)].copy()
    
    competition_analysis = []
    for lang in languages:
        lang_data = cluster_data[cluster_data['language'] == lang].sort_values(['year', 'quarter'])
        
        if len(lang_data) >= 3:
            early_share = lang_data['market_share_pct'].head(2).mean()
            recent_share = lang_data['market_share_pct'].tail(2).mean()
            share_change = recent_share - early_share
            
            avg_share = lang_data['market_share_pct'].mean()
            max_share = lang_data['market_share_pct'].max()
            current_share = lang_data['market_share_pct'].iloc[-1]
            
            share_volatility = lang_data['market_share_pct'].std()
            
            competition_analysis.append({
                'language': lang.title(),
                'cluster': cluster_name,
                'avg_market_share_pct': round(avg_share, 2),
                'share_change_pct': round(share_change, 2),
                'current_share_pct': round(current_share, 2),
                'peak_share_pct': round(max_share, 2),
                'share_volatility': round(share_volatility, 2),
                'competitive_status': 'Gaining' if share_change > 0.5 else 'Stable' if share_change > -0.5 else 'Losing'
            })
    
    return competition_analysis

web_competition = analyze_competitive_cluster(web_languages, 'Web Technologies')
systems_competition = analyze_competitive_cluster(systems_languages, 'Systems Programming')
data_science_competition = analyze_competitive_cluster(data_science_languages, 'Data Science & Machine Learning')
mobile_competition = analyze_competitive_cluster(mobile_languages, 'Mobile Development')
game_dev_competition = analyze_competitive_cluster(game_dev_languages, 'Game Development')
embedded_competition = analyze_competitive_cluster(embedded_languages, 'Embedded Systems')
functional_competition = analyze_competitive_cluster(functional_languages, 'Functional Programming')
scripting_competition = analyze_competitive_cluster(scripting_languages, 'Scripting Languages')
enterprise_competition = analyze_competitive_cluster(enterprise_languages, 'Enterprise Software')
markup_query_competition = analyze_competitive_cluster(markup_query_languages, 'Markup and Query Languages')
cloud_devops_competition = analyze_competitive_cluster(cloud_devops_languages, 'Cloud and DevOps')
oop_competition = analyze_competitive_cluster(oop_languages, 'Object-Oriented Programming')

all_competition = pd.DataFrame(web_competition + systems_competition + data_science_competition + mobile_competition +
                               game_dev_competition + embedded_competition + functional_competition + scripting_competition +
                               enterprise_competition + markup_query_competition + cloud_devops_competition + oop_competition)

table(all_competition, title=" Competitive Market Share Analysis")

fig = go.Figure()

colors = px.colors.qualitative.Set3

all_languages = web_languages + systems_languages + data_science_languages + mobile_languages + game_dev_languages + \
                embedded_languages + functional_languages + scripting_languages + enterprise_languages + \
                markup_query_languages + cloud_devops_languages + oop_languages

for i, lang in enumerate(all_languages):
    lang_data = prs_with_share[prs_with_share['language'] == lang].sort_values(['year', 'quarter'])
    if not lang_data.empty:
        periods = lang_data['year'].astype(str) + '-Q' + lang_data['quarter'].astype(str)
        fig.add_trace(go.Scatter(
            x=periods,
            y=lang_data['market_share_pct'],
            mode='lines+markers',
            name=lang.title(),
            line=dict(color=colors[i % len(colors)], width=2),
            marker=dict(size=6),
            visible=True
        ))

fig.update_layout(
    title='Programming Languages Market Share Evolution',
    xaxis_title='Time Period',
    yaxis_title='Market Share (%)',
    height=500,
    plot_bgcolor='white',
    paper_bgcolor='white',
    updatemenus=[
        {
            'buttons': [
                {
                    'label': 'All',
                    'method': 'update',
                    'args': [{'visible': [True] * len(all_languages)}, {'title': 'All Languages Market Share Evolution'}]
                },
                {
                    'label': 'Web',
                    'method': 'update',
                    'args': [{'visible': [True if lang in web_languages else False for lang in all_languages]}, {'title': 'Web Technologies Market Share Evolution'}]
                },
                {
                    'label': 'Systems',
                    'method': 'update',
                    'args': [{'visible': [True if lang in systems_languages else False for lang in all_languages]}, {'title': 'Systems Programming Market Share Evolution'}]
                },
                {
                    'label': 'Data Science',
                    'method': 'update',
                    'args': [{'visible': [True if lang in data_science_languages else False for lang in all_languages]}, {'title': 'Data Science Market Share Evolution'}]
                },
                {
                    'label': 'Mobile',
                    'method': 'update',
                    'args': [{'visible': [True if lang in mobile_languages else False for lang in all_languages]}, {'title': 'Mobile Development Market Share Evolution'}]
                },
                {
                    'label': 'Game Dev',
                    'method': 'update',
                    'args': [{'visible': [True if lang in game_dev_languages else False for lang in all_languages]}, {'title': 'Game Development Market Share Evolution'}]
                },
                {
                    'label': 'Embedded',
                    'method': 'update',
                    'args': [{'visible': [True if lang in embedded_languages else False for lang in all_languages]}, {'title': 'Embedded Systems Market Share Evolution'}]
                },
                {
                    'label': 'Functional',
                    'method': 'update',
                    'args': [{'visible': [True if lang in functional_languages else False for lang in all_languages]}, {'title': 'Functional Programming Market Share Evolution'}]
                },
                {
                    'label': 'Scripting',
                    'method': 'update',
                    'args': [{'visible': [True if lang in scripting_languages else False for lang in all_languages]}, {'title': 'Scripting Languages Market Share Evolution'}]
                },
                {
                    'label': 'Enterprise',
                    'method': 'update',
                    'args': [{'visible': [True if lang in enterprise_languages else False for lang in all_languages]}, {'title': 'Enterprise Software Market Share Evolution'}]
                },
                {
                    'label': 'Markup/Query',
                    'method': 'update',
                    'args': [{'visible': [True if lang in markup_query_languages else False for lang in all_languages]}, {'title': 'Markup and Query Languages Market Share Evolution'}]
                },
                {
                    'label': 'Cloud/DevOps',
                    'method': 'update',
                    'args': [{'visible': [True if lang in cloud_devops_languages else False for lang in all_languages]}, {'title': 'Cloud and DevOps Market Share Evolution'}]
                },
                {
                    'label': 'OOP',
                    'method': 'update',
                    'args': [{'visible': [True if lang in oop_languages else False for lang in all_languages]}, {'title': 'Object-Oriented Programming Market Share Evolution'}]
                }
            ],
            'direction': 'down',
            'showactive': True,
            'active': 0,
            'x': 0.75,
            'xanchor': 'left',
            'y': 1.15,
            'yanchor': 'top'
        }
    ]
)

plotly(fig)


text("## ● Language Performance ")
text("### **Question**: Can we identify performance patterns and cluster similar languages?")

performance_data = []

for lang in languages:
    lang_data = prs_clean[prs_clean['language'] == lang].sort_values(['year', 'quarter'])
    
    if len(lang_data) >= 2:
        total_prs = lang_data['pr_count'].sum()
        avg_prs = lang_data['pr_count'].mean()
        max_prs = lang_data['pr_count'].max()
        min_prs = lang_data['pr_count'].min()
        
        pr_std = lang_data['pr_count'].std()
        coefficient_variation = (pr_std / avg_prs * 100) if avg_prs > 0 else 0
        
        first_quarter = lang_data['pr_count'].iloc[0]
        last_quarter = lang_data['pr_count'].iloc[-1]
        overall_growth = ((last_quarter - first_quarter) / first_quarter * 100) if first_quarter > 0 else 0
        
        if total_prs > 50000:
            size_category = 'High Volume'
        elif total_prs > 10000:
            size_category = 'Medium Volume'
        else:
            size_category = 'Low Volume'
            
        stability_category = 'Stable' if coefficient_variation < 50 else 'Variable' if coefficient_variation < 100 else 'Highly Variable'
        
        performance_data.append({
            'language': lang.title(),
            'total_prs': total_prs,
            'avg_quarterly_prs': round(avg_prs, 1),
            'peak_quarter_prs': max_prs,
            'coefficient_of_variation': round(coefficient_variation, 1),
            'overall_growth_pct': round(overall_growth, 1),
            'size_category': size_category,
            'stability_category': stability_category,
            'quarters_active': len(lang_data)
        })

performance_df = pd.DataFrame(performance_data).sort_values('total_prs', ascending=False)
table(performance_df, title=" Language Performance  Analysis")

performance_df_filtered = performance_df

fig4 = px.scatter(
    performance_df, 
    x='avg_quarterly_prs',
    y='overall_growth_pct',
    color='stability_category',
    size='total_prs',
    hover_name='language',
    title="Language Performance Clustering Analysis",
    labels={
        'avg_quarterly_prs': 'Average Quarterly PRs',
        'overall_growth_pct': 'Overall Growth (%)',
        'stability_category': 'Stability Category',
        'total_prs': 'Total PRs',
        'language': 'Language'
    },
    color_discrete_map={
        'Stable': 'green',
        'Variable': 'yellow',
        'Highly Variable': 'red'
    },
    opacity=0.7,
)

fig4.update_layout(
    xaxis=dict(
        title='Average Quarterly PRs',
        range=[performance_df['avg_quarterly_prs'].min(), performance_df['avg_quarterly_prs'].max()],
        showgrid=True,
    ),
    yaxis=dict(
        title='Overall Growth (%)',
        range=[performance_df['overall_growth_pct'].min(), performance_df['overall_growth_pct'].max()],
        showgrid=True,
    ),
    autosize=True,
    showlegend=True,
    plot_bgcolor='white',
    paper_bgcolor='white',
    hovermode='closest',
)

fig4.update_traces(
    marker=dict(
        line=dict(width=1, color='black'),
        size=10,
    ),
    textfont=dict(color='black'),
)

plotly(fig4)


text("### ● Results")

if len(momentum_df) > 0:
    top_momentum = momentum_df.head(3)['language'].tolist()
    text(f"**Highest Momentum Languages**: {', '.join(top_momentum)}")
else:
    text("**Highest Momentum Languages**: Insufficient data")

if len(all_competition) > 0:
    top_competitive = all_competition.nlargest(3, 'share_change_pct')['language'].tolist()
    text(f"**Most Competitive Gainers**: {', '.join(top_competitive)}")
else:
    text("**Most Competitive Gainers**: No competitive data available")

top_performers = performance_df.head(3)['language'].tolist()
text(f"**Top Volume Languages**: {', '.join(top_performers)}")

text("### ● Validation")
if len(momentum_df) > 0:
    momentum_stats = momentum_df['momentum_acceleration']
    text(f"**Momentum Distribution**: Mean = {momentum_stats.mean():.2f}%, Std = {momentum_stats.std():.2f}%")
    significant_langs = len(momentum_df[momentum_df['momentum_acceleration'] > momentum_stats.mean() + momentum_stats.std()])
    text(f"**Languages with Significant Acceleration**: {significant_langs} out of {len(momentum_df)}")

perf_stats = performance_df['coefficient_of_variation']
text(f"**Performance Variability**: Mean = {perf_stats.mean():.1f}%, Languages with high stability: {len(performance_df[performance_df['coefficient_of_variation'] < 50])}")








