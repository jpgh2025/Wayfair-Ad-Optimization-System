import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
from typing import Dict, List, Any
from datetime import datetime
import os


class DashboardBuilder:
    def __init__(self, output_dir: str = "reports/dashboards"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
    def create_executive_dashboard(self, data: Dict[str, Any], recommendations: Dict[str, List]) -> str:
        # Create figure with subplots
        fig = make_subplots(
            rows=3, cols=2,
            subplot_titles=(
                'Overall Performance Metrics',
                'Campaign ROAS Distribution',
                'Keyword Coverage Analysis',
                'Product Performance Tiers',
                'Optimization Impact Forecast',
                'Top Opportunities'
            ),
            specs=[[{"type": "indicator"}, {"type": "bar"}],
                   [{"type": "pie"}, {"type": "bar"}],
                   [{"type": "scatter"}, {"type": "table"}]]
        )
        
        # 1. Overall Performance Metrics
        self._add_performance_metrics(fig, data, row=1, col=1)
        
        # 2. Campaign ROAS Distribution
        self._add_campaign_roas_distribution(fig, data, row=1, col=2)
        
        # 3. Keyword Coverage Analysis
        self._add_keyword_coverage(fig, data, row=2, col=1)
        
        # 4. Product Performance Tiers
        self._add_product_tiers(fig, data, row=2, col=2)
        
        # 5. Optimization Impact Forecast
        self._add_impact_forecast(fig, recommendations, row=3, col=1)
        
        # 6. Top Opportunities Table
        self._add_opportunities_table(fig, recommendations, row=3, col=2)
        
        # Update layout
        fig.update_layout(
            height=1200,
            showlegend=True,
            title_text=f"WSP Performance Dashboard - {datetime.now().strftime('%Y-%m-%d')}",
            title_font_size=24
        )
        
        # Save dashboard
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{self.output_dir}/executive_dashboard_{timestamp}.html"
        fig.write_html(filename)
        
        return filename
    
    def _add_performance_metrics(self, fig, data, row, col):
        current_roas = data.get('current_state', {}).get('overall_roas', 0)
        target_roas = 3.0
        
        fig.add_trace(
            go.Indicator(
                mode="number+gauge+delta",
                value=current_roas,
                delta={'reference': target_roas, 'relative': True},
                title={'text': "Overall ROAS"},
                gauge={
                    'axis': {'range': [0, 6]},
                    'bar': {'color': "darkblue"},
                    'steps': [
                        {'range': [0, 2], 'color': "lightgray"},
                        {'range': [2, 3], 'color': "gray"},
                        {'range': [3, 6], 'color': "lightgreen"}
                    ],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': target_roas
                    }
                }
            ),
            row=row, col=col
        )
    
    def _add_campaign_roas_distribution(self, fig, data, row, col):
        if 'campaigns' in data:
            campaigns_df = pd.DataFrame(data['campaigns'])
            
            fig.add_trace(
                go.Bar(
                    x=campaigns_df['campaign_name'][:10],
                    y=campaigns_df['roas'][:10],
                    name='Campaign ROAS',
                    marker_color='indianred'
                ),
                row=row, col=col
            )
            
            fig.add_hline(y=3.0, line_dash="dash", line_color="green", 
                         annotation_text="Target ROAS", row=row, col=col)
    
    def _add_keyword_coverage(self, fig, data, row, col):
        coverage_data = data.get('search_term_coverage', {})
        
        labels = ['Targeted', 'Untargeted']
        values = [
            coverage_data.get('targeted_search_terms', 0),
            coverage_data.get('untargeted_search_terms', 0)
        ]
        
        fig.add_trace(
            go.Pie(
                labels=labels,
                values=values,
                hole=.3,
                marker_colors=['lightblue', 'lightgray']
            ),
            row=row, col=col
        )
    
    def _add_product_tiers(self, fig, data, row, col):
        if 'product_tiers' in data:
            tiers_df = pd.DataFrame(data['product_tiers'])
            
            fig.add_trace(
                go.Bar(
                    x=tiers_df.index,
                    y=tiers_df['revenue'],
                    name='Revenue by Tier',
                    marker_color=['gold', 'silver', 'bronze', 'gray']
                ),
                row=row, col=col
            )
    
    def _add_impact_forecast(self, fig, recommendations, row, col):
        # Calculate cumulative impact over time
        weeks = list(range(1, 13))
        revenue_impact = []
        cumulative = 0
        
        if 'expected_impact' in recommendations:
            weekly_impact = recommendations['expected_impact'].get('revenue_increase', 0) / 4
            for week in weeks:
                cumulative += weekly_impact * (1.1 ** (week/4))  # Compound growth
                revenue_impact.append(cumulative)
        
        fig.add_trace(
            go.Scatter(
                x=weeks,
                y=revenue_impact,
                mode='lines+markers',
                name='Revenue Impact Forecast',
                line=dict(color='green', width=3)
            ),
            row=row, col=col
        )
        
        fig.update_xaxes(title_text="Weeks", row=row, col=col)
        fig.update_yaxes(title_text="Cumulative Revenue ($)", row=row, col=col)
    
    def _add_opportunities_table(self, fig, recommendations, row, col):
        opportunities = []
        
        if 'keywords' in recommendations and recommendations['keywords']:
            for kw in recommendations['keywords'][:5]:
                opportunities.append({
                    'Type': 'New Keyword',
                    'Opportunity': kw.keyword_text,
                    'Impact': f"Score: {kw.opportunity_score:.1f}",
                    'Action': f"Add as {kw.match_type}"
                })
        
        if 'products' in recommendations and recommendations['products']:
            for prod in recommendations['products'][:3]:
                opportunities.append({
                    'Type': 'Product',
                    'Opportunity': prod.product_name[:30],
                    'Impact': f"Tier: {prod.current_tier.value}",
                    'Action': prod.recommended_action[:30]
                })
        
        if opportunities:
            df = pd.DataFrame(opportunities)
            
            fig.add_trace(
                go.Table(
                    header=dict(
                        values=list(df.columns),
                        fill_color='paleturquoise',
                        align='left'
                    ),
                    cells=dict(
                        values=[df[col] for col in df.columns],
                        fill_color='lavender',
                        align='left'
                    )
                ),
                row=row, col=col
            )
    
    def create_detailed_report(self, data: Dict[str, Any], recommendations: Dict[str, List]) -> str:
        # Create HTML report with multiple sections
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>WSP Optimization Report - {datetime.now().strftime('%Y-%m-%d')}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1 {{ color: #333; }}
                h2 {{ color: #666; }}
                table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #4CAF50; color: white; }}
                tr:nth-child(even) {{ background-color: #f2f2f2; }}
                .metric {{ font-size: 24px; font-weight: bold; color: #2196F3; }}
                .section {{ margin-bottom: 40px; }}
            </style>
        </head>
        <body>
            <h1>Wayfair Sponsored Products Optimization Report</h1>
            <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            
            <div class="section">
                <h2>Executive Summary</h2>
                <p>Current ROAS: <span class="metric">{data.get('current_state', {}).get('overall_roas', 0):.2f}x</span></p>
                <p>Total Spend: <span class="metric">${data.get('current_state', {}).get('total_spend', 0):,.2f}</span></p>
                <p>Total Revenue: <span class="metric">${data.get('current_state', {}).get('total_revenue', 0):,.2f}</span></p>
            </div>
            
            <div class="section">
                <h2>Optimization Recommendations Summary</h2>
                <ul>
                    <li>New Keywords to Add: {len(recommendations.get('keywords', []))}</li>
                    <li>Bid Adjustments: {len(recommendations.get('bids', []))}</li>
                    <li>Budget Reallocations: {len(recommendations.get('budgets', []))}</li>
                    <li>Negative Keywords: {len(recommendations.get('negative_keywords', []))}</li>
                </ul>
            </div>
            
            {self._generate_keyword_section(recommendations.get('keywords', []))}
            {self._generate_bid_section(recommendations.get('bids', []))}
            {self._generate_budget_section(recommendations.get('budgets', []))}
            {self._generate_negative_section(recommendations.get('negative_keywords', []))}
            
        </body>
        </html>
        """
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{self.output_dir}/detailed_report_{timestamp}.html"
        
        with open(filename, 'w') as f:
            f.write(html_content)
        
        return filename
    
    def _generate_keyword_section(self, keywords):
        if not keywords:
            return ""
        
        rows = ""
        for kw in keywords[:20]:
            rows += f"""
            <tr>
                <td>{kw.keyword_text}</td>
                <td>{kw.match_type}</td>
                <td>${kw.suggested_bid:.2f}</td>
                <td>{kw.expected_roas:.2f}x</td>
                <td>{kw.opportunity_score:.1f}</td>
                <td>{kw.rationale}</td>
            </tr>
            """
        
        return f"""
        <div class="section">
            <h2>Top Keyword Opportunities</h2>
            <table>
                <tr>
                    <th>Keyword</th>
                    <th>Match Type</th>
                    <th>Suggested Bid</th>
                    <th>Expected ROAS</th>
                    <th>Opportunity Score</th>
                    <th>Rationale</th>
                </tr>
                {rows}
            </table>
        </div>
        """
    
    def _generate_bid_section(self, bids):
        if not bids:
            return ""
        
        rows = ""
        for bid in bids[:20]:
            rows += f"""
            <tr>
                <td>{bid.keyword_text}</td>
                <td>${bid.current_bid:.2f}</td>
                <td>${bid.recommended_bid:.2f}</td>
                <td>{bid.bid_change_percentage:+.1f}%</td>
                <td>{bid.action}</td>
                <td>{bid.rationale}</td>
            </tr>
            """
        
        return f"""
        <div class="section">
            <h2>Bid Optimization Recommendations</h2>
            <table>
                <tr>
                    <th>Keyword</th>
                    <th>Current Bid</th>
                    <th>Recommended Bid</th>
                    <th>Change %</th>
                    <th>Action</th>
                    <th>Rationale</th>
                </tr>
                {rows}
            </table>
        </div>
        """
    
    def _generate_budget_section(self, budgets):
        if not budgets:
            return ""
        
        rows = ""
        for budget in budgets[:15]:
            rows += f"""
            <tr>
                <td>{budget.campaign_name}</td>
                <td>${budget.current_budget:.2f}</td>
                <td>${budget.recommended_budget:.2f}</td>
                <td>{budget.budget_change_percentage:+.1f}%</td>
                <td>{budget.action}</td>
                <td>{budget.rationale}</td>
            </tr>
            """
        
        return f"""
        <div class="section">
            <h2>Budget Reallocation Recommendations</h2>
            <table>
                <tr>
                    <th>Campaign</th>
                    <th>Current Budget</th>
                    <th>Recommended Budget</th>
                    <th>Change %</th>
                    <th>Action</th>
                    <th>Rationale</th>
                </tr>
                {rows}
            </table>
        </div>
        """
    
    def _generate_negative_section(self, negatives):
        if not negatives:
            return ""
        
        rows = ""
        for neg in negatives[:20]:
            rows += f"""
            <tr>
                <td>{neg.negative_keyword}</td>
                <td>{neg.match_type}</td>
                <td>{neg.application_level}</td>
                <td>${neg.wasted_spend:.2f}</td>
                <td>{neg.wasted_clicks}</td>
                <td>{neg.confidence_score:.2f}</td>
            </tr>
            """
        
        return f"""
        <div class="section">
            <h2>Negative Keyword Recommendations</h2>
            <table>
                <tr>
                    <th>Negative Keyword</th>
                    <th>Match Type</th>
                    <th>Level</th>
                    <th>Wasted Spend</th>
                    <th>Wasted Clicks</th>
                    <th>Confidence</th>
                </tr>
                {rows}
            </table>
        </div>
        """