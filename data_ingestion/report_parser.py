import pandas as pd
from typing import Dict, List, Optional, Union
from pathlib import Path
import re
from datetime import datetime
from .models import Campaign, Keyword, SearchTerm, Product


class WayfairReportParser:
    def __init__(self):
        self.date_formats = [
            '%Y-%m-%d',
            '%m/%d/%Y',
            '%d/%m/%Y',
            '%Y/%m/%d'
        ]
    
    def parse_date(self, date_str: str) -> Optional[datetime]:
        for date_format in self.date_formats:
            try:
                return datetime.strptime(str(date_str).strip(), date_format)
            except ValueError:
                continue
        return None
    
    def clean_currency(self, value: Union[str, float]) -> float:
        if pd.isna(value):
            return 0.0
        if isinstance(value, str):
            value = re.sub(r'[\$,]', '', value)
        try:
            return float(value)
        except:
            return 0.0
    
    def clean_percentage(self, value: Union[str, float]) -> float:
        if pd.isna(value):
            return 0.0
        if isinstance(value, str):
            value = re.sub(r'%', '', value)
        try:
            return float(value)
        except:
            return 0.0
    
    def parse_campaign_performance_report(self, file_path: str) -> List[Campaign]:
        df = pd.read_csv(file_path)
        
        df.columns = df.columns.str.lower().str.replace(' ', '_')
        
        campaigns = []
        for _, row in df.iterrows():
            campaign = Campaign(
                campaign_id=str(row.get('campaign_id', row.get('id', ''))),
                campaign_name=str(row.get('campaign_name', row.get('name', ''))),
                status=str(row.get('status', 'active')),
                daily_budget=self.clean_currency(row.get('daily_budget', 0)),
                total_spend=self.clean_currency(row.get('spend', row.get('cost', 0))),
                impressions=int(row.get('impressions', 0)),
                clicks=int(row.get('clicks', 0)),
                conversions=int(row.get('conversions', row.get('orders', 0))),
                revenue=self.clean_currency(row.get('revenue', row.get('sales', 0))),
                roas=float(row.get('roas', 0)) if row.get('roas') else 0.0
            )
            
            if campaign.roas == 0 and campaign.total_spend > 0:
                campaign.roas = campaign.revenue / campaign.total_spend
            
            campaigns.append(campaign)
        
        return campaigns
    
    def parse_keyword_optimization_report(self, file_path: str) -> List[Keyword]:
        df = pd.read_csv(file_path)
        
        df.columns = df.columns.str.lower().str.replace(' ', '_')
        
        keywords = []
        for _, row in df.iterrows():
            keyword = Keyword(
                keyword_id=str(row.get('keyword_id', row.get('id', ''))),
                keyword_text=str(row.get('keyword', row.get('keyword_text', ''))),
                match_type=str(row.get('match_type', 'broad')),
                campaign_id=str(row.get('campaign_id', '')),
                current_bid=self.clean_currency(row.get('bid', row.get('max_cpc', 0))),
                impressions=int(row.get('impressions', 0)),
                clicks=int(row.get('clicks', 0)),
                conversions=int(row.get('conversions', row.get('orders', 0))),
                spend=self.clean_currency(row.get('spend', row.get('cost', 0))),
                revenue=self.clean_currency(row.get('revenue', row.get('sales', 0)))
            )
            keywords.append(keyword)
        
        return keywords
    
    def parse_search_term_research_report(self, file_path: str) -> List[SearchTerm]:
        df = pd.read_csv(file_path)
        
        df.columns = df.columns.str.lower().str.replace(' ', '_')
        
        search_terms = []
        for _, row in df.iterrows():
            search_term = SearchTerm(
                search_term=str(row.get('search_term', row.get('query', ''))),
                keyword_id=str(row.get('keyword_id')) if pd.notna(row.get('keyword_id')) else None,
                campaign_id=str(row.get('campaign_id', '')),
                impressions=int(row.get('impressions', 0)),
                clicks=int(row.get('clicks', 0)),
                conversions=int(row.get('conversions', row.get('orders', 0))),
                spend=self.clean_currency(row.get('spend', row.get('cost', 0))),
                revenue=self.clean_currency(row.get('revenue', row.get('sales', 0))),
                supplier_share=self.clean_percentage(row.get('supplier_share', row.get('share', 0)))
            )
            search_terms.append(search_term)
        
        return search_terms
    
    def parse_product_performance_report(self, file_path: str) -> List[Product]:
        df = pd.read_csv(file_path)
        
        df.columns = df.columns.str.lower().str.replace(' ', '_')
        
        products = []
        for _, row in df.iterrows():
            product = Product(
                sku=str(row.get('sku', row.get('product_id', ''))),
                product_name=str(row.get('product_name', row.get('name', ''))),
                wholesale_cost=self.clean_currency(row.get('wholesale_cost', row.get('cost', 0))),
                retail_price=self.clean_currency(row.get('retail_price', row.get('price', 0))),
                impressions=int(row.get('impressions', 0)),
                clicks=int(row.get('clicks', 0)),
                conversions=int(row.get('conversions', row.get('orders', 0))),
                spend=self.clean_currency(row.get('spend', row.get('ad_spend', 0))),
                revenue=self.clean_currency(row.get('revenue', row.get('sales', 0))),
                inventory_level=int(row.get('inventory', 0)) if pd.notna(row.get('inventory')) else None
            )
            products.append(product)
        
        return products