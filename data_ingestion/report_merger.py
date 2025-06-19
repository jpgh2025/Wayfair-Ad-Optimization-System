import pandas as pd
from typing import Dict, List, Optional
from .models import Campaign, Keyword, SearchTerm, Product


class ReportMerger:
    def __init__(self):
        self.campaigns_df = None
        self.keywords_df = None
        self.search_terms_df = None
        self.products_df = None
    
    def load_data(self, campaigns: List[Campaign], keywords: List[Keyword], 
                  search_terms: List[SearchTerm], products: List[Product]):
        self.campaigns_df = pd.DataFrame([vars(c) for c in campaigns])
        self.keywords_df = pd.DataFrame([vars(k) for k in keywords])
        self.search_terms_df = pd.DataFrame([vars(st) for st in search_terms])
        self.products_df = pd.DataFrame([vars(p) for p in products])
    
    def get_campaign_keyword_performance(self) -> pd.DataFrame:
        if self.keywords_df is None or self.campaigns_df is None:
            return pd.DataFrame()
        
        merged = pd.merge(
            self.keywords_df,
            self.campaigns_df[['campaign_id', 'campaign_name', 'daily_budget']],
            on='campaign_id',
            how='left'
        )
        
        merged['budget_utilization'] = merged.groupby('campaign_id')['spend'].transform('sum') / merged['daily_budget']
        merged['keyword_share_of_campaign'] = merged['spend'] / merged.groupby('campaign_id')['spend'].transform('sum')
        
        return merged
    
    def get_search_term_opportunities(self, min_impressions: int = 100) -> pd.DataFrame:
        if self.search_terms_df is None:
            return pd.DataFrame()
        
        untargeted = self.search_terms_df[self.search_terms_df['keyword_id'].isna()].copy()
        
        untargeted = untargeted[untargeted['impressions'] >= min_impressions]
        
        untargeted['opportunity_score'] = (
            untargeted['impressions'] * 0.3 +
            untargeted['roas'] * 1000 * 0.4 +
            untargeted['supplier_share'] * 10 * 0.3
        )
        
        return untargeted.sort_values('opportunity_score', ascending=False)
    
    def get_product_campaign_matrix(self) -> pd.DataFrame:
        if self.products_df is None or self.keywords_df is None:
            return pd.DataFrame()
        
        product_keyword_agg = self.keywords_df.groupby('campaign_id').agg({
            'spend': 'sum',
            'revenue': 'sum',
            'clicks': 'sum',
            'conversions': 'sum'
        }).reset_index()
        
        product_campaign_performance = pd.merge(
            self.products_df,
            product_keyword_agg,
            left_on='sku',
            right_on='campaign_id',
            how='left',
            suffixes=('_product', '_campaign')
        )
        
        return product_campaign_performance
    
    def get_holistic_performance_view(self) -> Dict[str, pd.DataFrame]:
        views = {}
        
        if self.campaigns_df is not None:
            views['campaign_summary'] = self.campaigns_df.agg({
                'total_spend': 'sum',
                'revenue': 'sum',
                'impressions': 'sum',
                'clicks': 'sum',
                'conversions': 'sum'
            })
        
        if self.keywords_df is not None:
            keyword_perf = self.keywords_df.copy()
            keyword_perf['efficiency_score'] = keyword_perf['roas'] * keyword_perf['conversion_rate']
            views['top_keywords'] = keyword_perf.nlargest(20, 'efficiency_score')
            views['bottom_keywords'] = keyword_perf.nsmallest(20, 'efficiency_score')
        
        if self.search_terms_df is not None:
            views['search_term_coverage'] = {
                'total_search_terms': len(self.search_terms_df),
                'targeted_search_terms': len(self.search_terms_df[self.search_terms_df['keyword_id'].notna()]),
                'untargeted_search_terms': len(self.search_terms_df[self.search_terms_df['keyword_id'].isna()]),
                'coverage_rate': len(self.search_terms_df[self.search_terms_df['keyword_id'].notna()]) / len(self.search_terms_df) * 100
            }
        
        if self.products_df is not None:
            product_tiers = self.products_df.copy()
            product_tiers['tier'] = pd.cut(
                product_tiers['roas'],
                bins=[-float('inf'), 1, 2, 3, float('inf')],
                labels=['Poor', 'Below Target', 'On Target', 'Star']
            )
            views['product_tiers'] = product_tiers.groupby('tier').agg({
                'sku': 'count',
                'spend': 'sum',
                'revenue': 'sum'
            })
        
        return views