from typing import List, Dict, Any, Tuple
import pandas as pd
from data_ingestion.models import Campaign, Keyword, SearchTerm, Product


class DataValidator:
    def __init__(self):
        self.validation_errors = []
        self.validation_warnings = []
    
    def validate_campaigns(self, campaigns: List[Campaign]) -> Tuple[bool, List[str]]:
        errors = []
        warnings = []
        
        campaign_ids = set()
        for campaign in campaigns:
            if not campaign.campaign_id:
                errors.append(f"Campaign missing ID: {campaign.campaign_name}")
            
            if campaign.campaign_id in campaign_ids:
                errors.append(f"Duplicate campaign ID: {campaign.campaign_id}")
            campaign_ids.add(campaign.campaign_id)
            
            if campaign.total_spend > 0 and campaign.revenue == 0:
                warnings.append(f"Campaign {campaign.campaign_name} has spend but no revenue")
            
            if campaign.clicks > campaign.impressions:
                errors.append(f"Campaign {campaign.campaign_name} has more clicks than impressions")
            
            if campaign.conversions > campaign.clicks:
                errors.append(f"Campaign {campaign.campaign_name} has more conversions than clicks")
        
        return len(errors) == 0, errors + warnings
    
    def validate_keywords(self, keywords: List[Keyword]) -> Tuple[bool, List[str]]:
        errors = []
        warnings = []
        
        keyword_ids = set()
        for keyword in keywords:
            if not keyword.keyword_id:
                errors.append(f"Keyword missing ID: {keyword.keyword_text}")
            
            if keyword.keyword_id in keyword_ids:
                errors.append(f"Duplicate keyword ID: {keyword.keyword_id}")
            keyword_ids.add(keyword.keyword_id)
            
            if keyword.current_bid <= 0:
                warnings.append(f"Keyword {keyword.keyword_text} has invalid bid: ${keyword.current_bid}")
            
            if keyword.match_type not in ['exact', 'phrase', 'broad']:
                warnings.append(f"Keyword {keyword.keyword_text} has invalid match type: {keyword.match_type}")
            
            if keyword.impressions > 0 and keyword.clicks == 0 and keyword.impressions > 1000:
                warnings.append(f"Keyword {keyword.keyword_text} has {keyword.impressions} impressions but no clicks")
        
        return len(errors) == 0, errors + warnings
    
    def validate_search_terms(self, search_terms: List[SearchTerm]) -> Tuple[bool, List[str]]:
        errors = []
        warnings = []
        
        for st in search_terms:
            if not st.search_term:
                errors.append("Empty search term found")
            
            if st.supplier_share > 100:
                errors.append(f"Search term '{st.search_term}' has invalid supplier share: {st.supplier_share}%")
            
            if st.clicks > 0 and st.impressions == 0:
                errors.append(f"Search term '{st.search_term}' has clicks but no impressions")
            
            if st.impressions > 100 and st.clicks == 0:
                warnings.append(f"High impression search term with no clicks: '{st.search_term}' ({st.impressions} impr)")
        
        return len(errors) == 0, errors + warnings
    
    def validate_products(self, products: List[Product]) -> Tuple[bool, List[str]]:
        errors = []
        warnings = []
        
        skus = set()
        for product in products:
            if not product.sku:
                errors.append(f"Product missing SKU: {product.product_name}")
            
            if product.sku in skus:
                errors.append(f"Duplicate SKU: {product.sku}")
            skus.add(product.sku)
            
            if product.wholesale_cost >= product.retail_price and product.retail_price > 0:
                errors.append(f"Product {product.sku} has wholesale cost >= retail price")
            
            if product.margin < 0:
                errors.append(f"Product {product.sku} has negative margin")
            
            if product.inventory_level is not None and product.inventory_level == 0:
                warnings.append(f"Product {product.sku} is out of stock")
        
        return len(errors) == 0, errors + warnings
    
    def validate_cross_references(self, campaigns: List[Campaign], keywords: List[Keyword], 
                                search_terms: List[SearchTerm]) -> Tuple[bool, List[str]]:
        errors = []
        warnings = []
        
        campaign_ids = {c.campaign_id for c in campaigns}
        keyword_ids = {k.keyword_id for k in keywords}
        
        # Make cross-reference validation warnings instead of errors
        for keyword in keywords:
            if keyword.campaign_id and keyword.campaign_id not in campaign_ids:
                warnings.append(f"Keyword {keyword.keyword_text} references campaign ID not in report: {keyword.campaign_id}")
        
        for st in search_terms:
            if st.campaign_id and st.campaign_id not in campaign_ids:
                warnings.append(f"Search term '{st.search_term}' references campaign ID not in report: {st.campaign_id}")
            
            if st.keyword_id and st.keyword_id not in keyword_ids:
                warnings.append(f"Search term '{st.search_term}' references keyword ID not in report: {st.keyword_id}")
        
        # Only return errors for critical issues
        return True, warnings