import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from ..data_ingestion.models import Campaign, Keyword, Product


@dataclass
class BudgetRecommendation:
    campaign_id: str
    campaign_name: str
    current_budget: float
    recommended_budget: float
    budget_change: float
    budget_change_percentage: float
    action: str  # 'increase', 'decrease', 'maintain', 'pause'
    rationale: str
    expected_impact: Dict[str, float]
    priority: int  # 1-5, 1 being highest


class BudgetAllocationOptimizer:
    def __init__(self, total_budget_constraint: Optional[float] = None, 
                 min_budget: float = 10.0, max_budget: float = 1000.0):
        self.total_budget_constraint = total_budget_constraint
        self.min_budget = min_budget
        self.max_budget = max_budget
        self.min_roas_threshold = 1.5
        self.target_roas = 3.0
        self.budget_utilization_threshold = 0.8
        
    def optimize_budgets(self, campaigns: List[Campaign], keywords: List[Keyword],
                        historical_days: int = 30) -> List[BudgetRecommendation]:
        camp_df = pd.DataFrame([vars(c) for c in campaigns])
        kw_df = pd.DataFrame([vars(k) for k in keywords])
        
        campaign_metrics = self._calculate_campaign_metrics(camp_df, kw_df, historical_days)
        
        recommendations = []
        
        high_performers = campaign_metrics[
            (campaign_metrics['roas'] >= self.target_roas) &
            (campaign_metrics['budget_utilization'] >= self.budget_utilization_threshold)
        ]
        for _, campaign in high_performers.iterrows():
            rec = self._create_increase_recommendation(campaign, campaign_metrics)
            if rec:
                recommendations.append(rec)
        
        opportunity_campaigns = campaign_metrics[
            (campaign_metrics['roas'] >= self.min_roas_threshold) &
            (campaign_metrics['roas'] < self.target_roas) &
            (campaign_metrics['impression_share_lost'] > 20)
        ]
        for _, campaign in opportunity_campaigns.iterrows():
            rec = self._create_moderate_increase_recommendation(campaign, campaign_metrics)
            if rec:
                recommendations.append(rec)
        
        poor_performers = campaign_metrics[
            campaign_metrics['roas'] < self.min_roas_threshold
        ]
        for _, campaign in poor_performers.iterrows():
            rec = self._create_decrease_recommendation(campaign, campaign_metrics)
            if rec:
                recommendations.append(rec)
        
        if self.total_budget_constraint:
            recommendations = self._apply_budget_constraint(recommendations, campaign_metrics)
        
        recommendations.sort(key=lambda x: x.priority)
        
        return recommendations
    
    def _calculate_campaign_metrics(self, campaigns: pd.DataFrame, keywords: pd.DataFrame, 
                                  historical_days: int) -> pd.DataFrame:
        keyword_agg = keywords.groupby('campaign_id').agg({
            'impressions': 'sum',
            'clicks': 'sum',
            'conversions': 'sum',
            'spend': 'sum',
            'revenue': 'sum'
        }).reset_index()
        
        metrics = pd.merge(campaigns, keyword_agg, on='campaign_id', how='left', suffixes=('', '_kw'))
        
        metrics['daily_spend'] = metrics['total_spend'] / historical_days
        metrics['budget_utilization'] = metrics['daily_spend'] / metrics['daily_budget']
        metrics['budget_utilization'] = metrics['budget_utilization'].clip(upper=1.0)
        
        metrics['impression_share'] = metrics.apply(
            lambda x: min(x['impressions'] / (x['impressions'] / x['budget_utilization']) 
                         if x['budget_utilization'] > 0 else 0, 100), axis=1
        )
        metrics['impression_share_lost'] = 100 - metrics['impression_share']
        
        metrics['efficiency_score'] = (
            metrics['roas'] * 0.4 +
            metrics['conversion_rate'] * 0.3 +
            metrics['ctr'] * 0.3
        )
        
        metrics['scalability_score'] = (
            metrics['impression_share_lost'] * 0.5 +
            (metrics['roas'] / self.target_roas).clip(upper=2) * 25
        )
        
        return metrics
    
    def _create_increase_recommendation(self, campaign: pd.Series, 
                                      all_campaigns: pd.DataFrame) -> Optional[BudgetRecommendation]:
        current_budget = campaign['daily_budget']
        
        if campaign['budget_utilization'] >= 0.95:
            increase_factor = 1.5
        elif campaign['budget_utilization'] >= 0.85:
            increase_factor = 1.3
        else:
            increase_factor = 1.2
        
        if campaign['roas'] > self.target_roas * 1.5:
            increase_factor *= 1.2
        
        recommended_budget = min(current_budget * increase_factor, self.max_budget)
        recommended_budget = round(recommended_budget, 2)
        
        if recommended_budget <= current_budget * 1.05:
            return None
        
        budget_change = recommended_budget - current_budget
        expected_impact = self._calculate_expected_impact(campaign, current_budget, recommended_budget)
        
        rationale = self._generate_increase_rationale(campaign)
        
        return BudgetRecommendation(
            campaign_id=campaign['campaign_id'],
            campaign_name=campaign['campaign_name'],
            current_budget=current_budget,
            recommended_budget=recommended_budget,
            budget_change=budget_change,
            budget_change_percentage=round((budget_change / current_budget) * 100, 1),
            action='increase',
            rationale=rationale,
            expected_impact=expected_impact,
            priority=1 if campaign['roas'] > self.target_roas * 1.5 else 2
        )
    
    def _create_moderate_increase_recommendation(self, campaign: pd.Series,
                                               all_campaigns: pd.DataFrame) -> Optional[BudgetRecommendation]:
        current_budget = campaign['daily_budget']
        
        increase_factor = 1.1 + (campaign['scalability_score'] / 100) * 0.2
        
        recommended_budget = min(current_budget * increase_factor, self.max_budget)
        recommended_budget = round(recommended_budget, 2)
        
        if recommended_budget <= current_budget * 1.05:
            return None
        
        budget_change = recommended_budget - current_budget
        expected_impact = self._calculate_expected_impact(campaign, current_budget, recommended_budget)
        
        rationale = f"Testing scale: ROAS {campaign['roas']:.1f}x, {campaign['impression_share_lost']:.0f}% impression share opportunity"
        
        return BudgetRecommendation(
            campaign_id=campaign['campaign_id'],
            campaign_name=campaign['campaign_name'],
            current_budget=current_budget,
            recommended_budget=recommended_budget,
            budget_change=budget_change,
            budget_change_percentage=round((budget_change / current_budget) * 100, 1),
            action='increase',
            rationale=rationale,
            expected_impact=expected_impact,
            priority=3
        )
    
    def _create_decrease_recommendation(self, campaign: pd.Series,
                                      all_campaigns: pd.DataFrame) -> BudgetRecommendation:
        current_budget = campaign['daily_budget']
        
        if campaign['roas'] < 1.0:
            decrease_factor = 0.5
            action = 'decrease'
        elif campaign['roas'] < self.min_roas_threshold:
            decrease_factor = 0.7
            action = 'decrease'
        else:
            decrease_factor = 0.85
            action = 'decrease'
        
        if campaign['conversions'] == 0 and campaign['clicks'] > 50:
            decrease_factor = 0.3
            action = 'pause' if campaign['clicks'] > 100 else 'decrease'
        
        recommended_budget = max(current_budget * decrease_factor, self.min_budget)
        if action == 'pause':
            recommended_budget = 0
        
        recommended_budget = round(recommended_budget, 2)
        
        budget_change = recommended_budget - current_budget
        expected_impact = self._calculate_expected_impact(campaign, current_budget, recommended_budget)
        
        rationale = self._generate_decrease_rationale(campaign)
        
        return BudgetRecommendation(
            campaign_id=campaign['campaign_id'],
            campaign_name=campaign['campaign_name'],
            current_budget=current_budget,
            recommended_budget=recommended_budget,
            budget_change=budget_change,
            budget_change_percentage=round((budget_change / current_budget) * 100, 1),
            action=action,
            rationale=rationale,
            expected_impact=expected_impact,
            priority=4 if action == 'decrease' else 5
        )
    
    def _apply_budget_constraint(self, recommendations: List[BudgetRecommendation],
                               campaign_metrics: pd.DataFrame) -> List[BudgetRecommendation]:
        current_total = campaign_metrics['daily_budget'].sum()
        recommended_total = sum(r.recommended_budget for r in recommendations)
        
        if recommended_total <= self.total_budget_constraint:
            return recommendations
        
        scaling_factor = self.total_budget_constraint / recommended_total
        
        for rec in recommendations:
            if rec.action == 'increase':
                old_recommended = rec.recommended_budget
                rec.recommended_budget = round(rec.current_budget + 
                                             (old_recommended - rec.current_budget) * scaling_factor, 2)
                rec.budget_change = rec.recommended_budget - rec.current_budget
                rec.budget_change_percentage = round((rec.budget_change / rec.current_budget) * 100, 1)
        
        return recommendations
    
    def _calculate_expected_impact(self, campaign: pd.Series, current_budget: float,
                                 new_budget: float) -> Dict[str, float]:
        budget_ratio = new_budget / current_budget if current_budget > 0 else 0
        
        utilization_adjusted_ratio = min(budget_ratio, 1 / campaign['budget_utilization'] 
                                       if campaign['budget_utilization'] > 0 else budget_ratio)
        
        expected_spend_change = (new_budget * campaign['budget_utilization'] - 
                               current_budget * campaign['budget_utilization'])
        expected_impression_change = campaign['impressions'] * (utilization_adjusted_ratio - 1)
        expected_click_change = campaign['clicks'] * (utilization_adjusted_ratio - 1)
        expected_revenue_change = campaign['revenue'] * (utilization_adjusted_ratio - 1)
        
        return {
            'daily_spend_change': expected_spend_change,
            'monthly_spend_change': expected_spend_change * 30,
            'impression_change': expected_impression_change,
            'click_change': expected_click_change,
            'revenue_change': expected_revenue_change,
            'monthly_revenue_change': expected_revenue_change * 30,
            'roas_impact': campaign['roas']  # ROAS should remain stable
        }
    
    def _generate_increase_rationale(self, campaign: pd.Series) -> str:
        reasons = []
        
        if campaign['roas'] >= self.target_roas:
            reasons.append(f"Strong ROAS {campaign['roas']:.1f}x")
        
        if campaign['budget_utilization'] >= 0.9:
            reasons.append(f"Hitting budget cap ({campaign['budget_utilization']:.0%} utilization)")
        
        if campaign['impression_share_lost'] > 30:
            reasons.append(f"{campaign['impression_share_lost']:.0f}% impression share opportunity")
        
        if campaign['conversion_rate'] > 2.0:
            reasons.append(f"High conversion rate {campaign['conversion_rate']:.1f}%")
        
        return "; ".join(reasons)
    
    def _generate_decrease_rationale(self, campaign: pd.Series) -> str:
        reasons = []
        
        if campaign['roas'] < self.min_roas_threshold:
            reasons.append(f"Low ROAS {campaign['roas']:.1f}x")
        
        if campaign['conversions'] == 0:
            reasons.append(f"No conversions from {campaign['clicks']} clicks")
        
        if campaign['budget_utilization'] < 0.5:
            reasons.append(f"Low budget utilization {campaign['budget_utilization']:.0%}")
        
        if campaign['ctr'] < 0.5:
            reasons.append(f"Poor CTR {campaign['ctr']:.2f}%")
        
        return "; ".join(reasons)