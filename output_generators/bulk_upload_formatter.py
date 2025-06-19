import pandas as pd
from typing import List, Dict, Optional
from datetime import datetime
import os
from ..analyzers.keyword_analyzer import KeywordRecommendation
from ..analyzers.bid_optimizer import BidRecommendation
from ..analyzers.negative_keyword_finder import NegativeKeywordRecommendation


class WayfairBulkUploadFormatter:
    def __init__(self, output_dir: str = "reports/bulk_uploads"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
    def format_keyword_upload(self, recommendations: List[KeywordRecommendation], 
                            campaign_mapping: Dict[str, str]) -> str:
        data = []
        
        for rec in recommendations:
            campaign_id = self._determine_campaign(rec.keyword_text, campaign_mapping)
            
            data.append({
                'Campaign ID': campaign_id,
                'Campaign Name': campaign_mapping.get(campaign_id, ''),
                'Ad Group ID': '',  # Wayfair may auto-generate
                'Ad Group Name': f"{rec.keyword_text[:20]}_adgroup",
                'Keyword': rec.keyword_text,
                'Match Type': rec.match_type.capitalize(),
                'Max CPC': rec.suggested_bid,
                'Status': 'Active',
                'Final URL': '',  # Usually set at ad group level
                'Custom Parameters': f"source=wsp_optimizer&score={rec.opportunity_score}"
            })
        
        df = pd.DataFrame(data)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{self.output_dir}/keyword_upload_{timestamp}.csv"
        df.to_csv(filename, index=False)
        
        return filename
    
    def format_bid_changes(self, recommendations: List[BidRecommendation]) -> str:
        data = []
        
        active_changes = [r for r in recommendations if r.action != 'pause']
        
        for rec in active_changes:
            data.append({
                'Keyword ID': rec.keyword_id,
                'Keyword': rec.keyword_text,
                'Current Bid': rec.current_bid,
                'New Bid': rec.recommended_bid,
                'Bid Change %': rec.bid_change_percentage,
                'Action': rec.action,
                'Rationale': rec.rationale
            })
        
        df = pd.DataFrame(data)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{self.output_dir}/bid_changes_{timestamp}.csv"
        df.to_csv(filename, index=False)
        
        return filename
    
    def format_negative_keywords(self, recommendations: List[NegativeKeywordRecommendation]) -> str:
        data = []
        
        for rec in recommendations:
            if rec.application_level == 'campaign':
                for campaign_id in rec.affected_campaigns:
                    data.append({
                        'Campaign ID': campaign_id,
                        'Campaign Name': '',  # Would need mapping
                        'Negative Keyword': rec.negative_keyword,
                        'Match Type': rec.match_type.capitalize(),
                        'Level': 'Campaign'
                    })
            else:
                data.append({
                    'Campaign ID': 'All',
                    'Campaign Name': 'Account Level',
                    'Negative Keyword': rec.negative_keyword,
                    'Match Type': rec.match_type.capitalize(),
                    'Level': 'Account'
                })
        
        df = pd.DataFrame(data)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{self.output_dir}/negative_keywords_{timestamp}.csv"
        df.to_csv(filename, index=False)
        
        return filename
    
    def format_budget_changes(self, recommendations: List) -> str:
        data = []
        
        for rec in recommendations:
            data.append({
                'Campaign ID': rec.campaign_id,
                'Campaign Name': rec.campaign_name,
                'Current Daily Budget': rec.current_budget,
                'Recommended Daily Budget': rec.recommended_budget,
                'Budget Change': rec.budget_change,
                'Change %': rec.budget_change_percentage,
                'Action': rec.action,
                'Priority': rec.priority,
                'Rationale': rec.rationale,
                'Expected Monthly Revenue Impact': rec.expected_impact.get('monthly_revenue_change', 0)
            })
        
        df = pd.DataFrame(data)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{self.output_dir}/budget_changes_{timestamp}.csv"
        df.to_csv(filename, index=False)
        
        return filename
    
    def create_master_upload_file(self, all_recommendations: Dict[str, List]) -> str:
        with pd.ExcelWriter(f"{self.output_dir}/wayfair_bulk_upload_{datetime.now().strftime('%Y%m%d')}.xlsx") as writer:
            
            if 'keywords' in all_recommendations and all_recommendations['keywords']:
                keyword_df = self._prepare_keyword_df(all_recommendations['keywords'])
                keyword_df.to_excel(writer, sheet_name='New Keywords', index=False)
            
            if 'bids' in all_recommendations and all_recommendations['bids']:
                bid_df = self._prepare_bid_df(all_recommendations['bids'])
                bid_df.to_excel(writer, sheet_name='Bid Changes', index=False)
            
            if 'negative_keywords' in all_recommendations and all_recommendations['negative_keywords']:
                neg_df = self._prepare_negative_df(all_recommendations['negative_keywords'])
                neg_df.to_excel(writer, sheet_name='Negative Keywords', index=False)
            
            if 'budgets' in all_recommendations and all_recommendations['budgets']:
                budget_df = self._prepare_budget_df(all_recommendations['budgets'])
                budget_df.to_excel(writer, sheet_name='Budget Changes', index=False)
            
            summary_df = self._create_summary_sheet(all_recommendations)
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
        
        return writer.path
    
    def _determine_campaign(self, keyword: str, campaign_mapping: Dict[str, str]) -> str:
        # Logic to determine best campaign for keyword
        # This is simplified - in reality would use more sophisticated matching
        return list(campaign_mapping.keys())[0] if campaign_mapping else 'default_campaign'
    
    def _prepare_keyword_df(self, recommendations: List[KeywordRecommendation]) -> pd.DataFrame:
        return pd.DataFrame([{
            'Keyword': r.keyword_text,
            'Match Type': r.match_type,
            'Suggested Bid': r.suggested_bid,
            'Expected ROAS': r.expected_roas,
            'Opportunity Score': r.opportunity_score,
            'Source Search Terms': ', '.join(r.source_search_terms[:3])
        } for r in recommendations])
    
    def _prepare_bid_df(self, recommendations: List[BidRecommendation]) -> pd.DataFrame:
        return pd.DataFrame([{
            'Keyword ID': r.keyword_id,
            'Keyword': r.keyword_text,
            'Current Bid': r.current_bid,
            'Recommended Bid': r.recommended_bid,
            'Change %': r.bid_change_percentage,
            'Action': r.action,
            'Expected Revenue Impact': r.expected_impact.get('revenue_change', 0)
        } for r in recommendations])
    
    def _prepare_negative_df(self, recommendations: List[NegativeKeywordRecommendation]) -> pd.DataFrame:
        return pd.DataFrame([{
            'Negative Keyword': r.negative_keyword,
            'Match Type': r.match_type,
            'Level': r.application_level,
            'Wasted Spend': r.wasted_spend,
            'Campaigns Affected': len(r.affected_campaigns),
            'Confidence': r.confidence_score
        } for r in recommendations])
    
    def _prepare_budget_df(self, recommendations: List) -> pd.DataFrame:
        return pd.DataFrame([{
            'Campaign': r.campaign_name,
            'Current Budget': r.current_budget,
            'Recommended Budget': r.recommended_budget,
            'Change %': r.budget_change_percentage,
            'Priority': r.priority,
            'Expected Impact': r.expected_impact.get('monthly_revenue_change', 0)
        } for r in recommendations])
    
    def _create_summary_sheet(self, all_recommendations: Dict[str, List]) -> pd.DataFrame:
        summary = {
            'Optimization Type': [],
            'Number of Recommendations': [],
            'Total Expected Impact': [],
            'Implementation Priority': []
        }
        
        if 'keywords' in all_recommendations:
            summary['Optimization Type'].append('New Keywords')
            summary['Number of Recommendations'].append(len(all_recommendations['keywords']))
            summary['Total Expected Impact'].append('Expand keyword coverage')
            summary['Implementation Priority'].append('High')
        
        if 'bids' in all_recommendations:
            revenue_impact = sum(r.expected_impact.get('revenue_change', 0) 
                               for r in all_recommendations['bids'])
            summary['Optimization Type'].append('Bid Adjustments')
            summary['Number of Recommendations'].append(len(all_recommendations['bids']))
            summary['Total Expected Impact'].append(f'${revenue_impact:,.2f} monthly revenue')
            summary['Implementation Priority'].append('High')
        
        if 'negative_keywords' in all_recommendations:
            wasted_spend = sum(r.wasted_spend for r in all_recommendations['negative_keywords'])
            summary['Optimization Type'].append('Negative Keywords')
            summary['Number of Recommendations'].append(len(all_recommendations['negative_keywords']))
            summary['Total Expected Impact'].append(f'${wasted_spend:,.2f} spend savings')
            summary['Implementation Priority'].append('Medium')
        
        if 'budgets' in all_recommendations:
            summary['Optimization Type'].append('Budget Reallocation')
            summary['Number of Recommendations'].append(len(all_recommendations['budgets']))
            summary['Total Expected Impact'].append('Optimize spend distribution')
            summary['Implementation Priority'].append('Medium')
        
        return pd.DataFrame(summary)