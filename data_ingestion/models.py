from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, List
import pandas as pd


@dataclass
class Campaign:
    campaign_id: str
    campaign_name: str
    status: str
    daily_budget: float
    total_spend: float
    impressions: int
    clicks: int
    conversions: int
    revenue: float
    roas: float
    
    @property
    def ctr(self) -> float:
        return (self.clicks / self.impressions * 100) if self.impressions > 0 else 0.0
    
    @property
    def conversion_rate(self) -> float:
        return (self.conversions / self.clicks * 100) if self.clicks > 0 else 0.0
    
    @property
    def cpc(self) -> float:
        return (self.total_spend / self.clicks) if self.clicks > 0 else 0.0


@dataclass
class Keyword:
    keyword_id: str
    keyword_text: str
    match_type: str
    campaign_id: str
    current_bid: float
    impressions: int
    clicks: int
    conversions: int
    spend: float
    revenue: float
    
    @property
    def roas(self) -> float:
        return (self.revenue / self.spend) if self.spend > 0 else 0.0
    
    @property
    def ctr(self) -> float:
        return (self.clicks / self.impressions * 100) if self.impressions > 0 else 0.0
    
    @property
    def conversion_rate(self) -> float:
        return (self.conversions / self.clicks * 100) if self.clicks > 0 else 0.0


@dataclass
class SearchTerm:
    search_term: str
    keyword_id: Optional[str]
    campaign_id: str
    impressions: int
    clicks: int
    conversions: int
    spend: float
    revenue: float
    supplier_share: float
    
    @property
    def roas(self) -> float:
        return (self.revenue / self.spend) if self.spend > 0 else 0.0
    
    @property
    def is_targeted(self) -> bool:
        return self.keyword_id is not None


@dataclass
class Product:
    sku: str
    product_name: str
    wholesale_cost: float
    retail_price: float
    impressions: int
    clicks: int
    conversions: int
    spend: float
    revenue: float
    inventory_level: Optional[int] = None
    
    @property
    def roas(self) -> float:
        return (self.revenue / self.spend) if self.spend > 0 else 0.0
    
    @property
    def margin(self) -> float:
        return (self.retail_price - self.wholesale_cost) / self.retail_price if self.retail_price > 0 else 0.0
    
    @property
    def true_roas(self) -> float:
        profit = (self.revenue * self.margin)
        return (profit / self.spend) if self.spend > 0 else 0.0


@dataclass
class PerformanceMetrics:
    date_range: tuple[datetime, datetime]
    total_spend: float
    total_revenue: float
    total_impressions: int
    total_clicks: int
    total_conversions: int
    
    @property
    def roas(self) -> float:
        return (self.total_revenue / self.total_spend) if self.total_spend > 0 else 0.0
    
    @property
    def ctr(self) -> float:
        return (self.total_clicks / self.total_impressions * 100) if self.total_impressions > 0 else 0.0
    
    @property
    def conversion_rate(self) -> float:
        return (self.total_conversions / self.total_clicks * 100) if self.total_clicks > 0 else 0.0
    
    @property
    def acos(self) -> float:
        return (self.total_spend / self.total_revenue * 100) if self.total_revenue > 0 else 0.0