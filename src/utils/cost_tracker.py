#!/usr/bin/env python3
"""
OpenAI API cost tracker with daily budget enforcement and email alerts.

Tracks costs in-memory (resets on app restart), triggers alerts at
80% and 100% of daily budget.
"""

import time
from threading import Lock
from typing import Dict, Tuple
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os


class CostTracker:
    """Track OpenAI API costs with daily budget limit and email alerts."""
    
    # OpenAI pricing per 1M tokens (as of November 2025)
    # Source: https://openai.com/pricing
    # Note: Update these when OpenAI changes pricing
    PRICING = {
        'gpt-4o-mini': {
            'input': 0.15,   # $0.15 per 1M input tokens
            'output': 0.60   # $0.60 per 1M output tokens
        },
        'gpt-4o': {
            'input': 2.50,   # $2.50 per 1M input tokens
            'output': 10.00  # $10.00 per 1M output tokens
        },
        'gpt-4-turbo': {
            'input': 10.00,  # $10.00 per 1M input tokens
            'output': 30.00  # $30.00 per 1M output tokens
        },
        'gpt-4': {
            'input': 30.00,  # $30.00 per 1M input tokens
            'output': 60.00  # $60.00 per 1M output tokens
        },
        'gpt-3.5-turbo': {
            'input': 0.50,   # $0.50 per 1M input tokens
            'output': 1.50   # $1.50 per 1M output tokens
        }
    }
    
    def __init__(self, daily_budget_usd: float = 1.0, alert_email: str = None, model: str = 'gpt-4o-mini'):
        """
        Initialize cost tracker.
        
        Args:
            daily_budget_usd: Maximum daily spend in USD
            alert_email: Email address for alerts (from .env)
            model: OpenAI model name (for pricing lookup)
        """
        self.daily_budget = daily_budget_usd
        self.alert_email = alert_email
        self.model = model
        self.current_day = time.strftime('%Y-%m-%d')
        self.daily_cost = 0.0
        self.user_costs: Dict[str, float] = {}
        self.alert_80_sent = False
        self.lock = Lock()
        
        # Validate model pricing is available
        if model not in self.PRICING:
            available = ', '.join(self.PRICING.keys())
            raise ValueError(f"Unknown model '{model}'. Available: {available}")
    
    def record_query(self, user_id: str, prompt_tokens: int, completion_tokens: int) -> dict:
        """
        Record cost of a query.
        
        Args:
            user_id: User identifier
            prompt_tokens: Tokens used for prompt (input)
            completion_tokens: Tokens used for completion (output)
            
        Returns:
            dict with cost details and alert status
        """
        with self.lock:
            # Reset if new day
            today = time.strftime('%Y-%m-%d')
            if today != self.current_day:
                self.current_day = today
                self.daily_cost = 0.0
                self.user_costs = {}
                self.alert_80_sent = False
            
            # Get pricing for current model
            pricing = self.PRICING.get(self.model)
            if not pricing:
                # Fallback to gpt-4o-mini pricing if model not found
                pricing = self.PRICING['gpt-4o-mini']
                print(f"Warning: No pricing for model '{self.model}', using gpt-4o-mini rates")
            
            # Calculate cost using model-specific pricing
            # Note: prompt_tokens = input to GPT (context + question)
            #       completion_tokens = output from GPT (the answer)
            input_cost = (prompt_tokens / 1_000_000) * pricing['input']
            output_cost = (completion_tokens / 1_000_000) * pricing['output']
            query_cost = input_cost + output_cost
            
            # Update totals
            self.daily_cost += query_cost
            self.user_costs[user_id] = self.user_costs.get(user_id, 0.0) + query_cost
            
            # Check alert thresholds
            budget_percentage = (self.daily_cost / self.daily_budget) * 100
            
            result = {
                'query_cost': round(query_cost, 6),
                'daily_cost': round(self.daily_cost, 4),
                'daily_budget': self.daily_budget,
                'remaining': round(self.daily_budget - self.daily_cost, 4),
                'percentage': round(budget_percentage, 1)
            }
            
            # Send 80% warning (once per day)
            if budget_percentage >= 80 and not self.alert_80_sent:
                self._send_alert('warning', result)
                self.alert_80_sent = True
            
            # Send 100% critical alert (every time)
            if budget_percentage >= 100:
                self._send_alert('critical', result)
            
            return result
    
    def is_budget_exceeded(self) -> Tuple[bool, dict]:
        """Check if daily budget exceeded."""
        with self.lock:
            exceeded = self.daily_cost >= self.daily_budget
            return exceeded, {
                'daily_cost': round(self.daily_cost, 4),
                'daily_budget': self.daily_budget,
                'remaining': round(self.daily_budget - self.daily_cost, 4),
                'percentage': round((self.daily_cost / self.daily_budget) * 100, 1)
            }
    
    def _send_alert(self, alert_type: str, cost_info: dict):
        """Send email alert (internal method)."""
        if not self.alert_email:
            return
        
        # Get top users by cost
        top_users = sorted(self.user_costs.items(), key=lambda x: x[1], reverse=True)[:5]
        
        if alert_type == 'warning':
            subject = f"[D&D RAG] Warning: 80% Daily Budget Consumed"
            body = f"""Daily Budget Status Report
--------------------------
Date: {time.strftime('%Y-%m-%d')}
Time: {time.strftime('%H:%M:%S UTC')}

Budget Information:
- Daily limit: ${self.daily_budget:.2f}
- Current spend: ${cost_info['daily_cost']:.4f}
- Remaining: ${cost_info['remaining']:.4f}
- Percentage: {cost_info['percentage']:.1f}%

Top Users (by cost):
"""
            for i, (user_id, cost) in enumerate(top_users, 1):
                body += f"{i}. {user_id}: ${cost:.4f}\n"
            
            body += "\nAction Required: None (informational)\nService Status: Operational"
        
        else:  # critical
            subject = f"[D&D RAG] CRITICAL: Daily Budget Exceeded"
            body = f"""CRITICAL ALERT - Service Paused
--------------------------
Date: {time.strftime('%Y-%m-%d')}
Time: {time.strftime('%H:%M:%S UTC')}

Budget Information:
- Daily limit: ${self.daily_budget:.2f}
- Current spend: ${cost_info['daily_cost']:.4f}
- Overage: ${cost_info['daily_cost'] - self.daily_budget:.4f}
- Percentage: {cost_info['percentage']:.1f}%

Top Users (by cost):
"""
            for i, (user_id, cost) in enumerate(top_users, 1):
                body += f"{i}. {user_id}: ${cost:.4f}\n"
            
            body += "\nAction Required: Review usage patterns\nService Status: HTTP 503 (Service Unavailable)"
        
        try:
            self._send_email(subject, body)
        except Exception as e:
            # Don't crash app if email fails
            print(f"Warning: Failed to send alert email: {e}")
    
    def _send_email(self, subject: str, body: str):
        """Send email via SMTP (requires SMTP config in .env)."""
        smtp_host = os.getenv('SMTP_HOST', 'localhost')
        smtp_port = int(os.getenv('SMTP_PORT', '587'))
        smtp_user = os.getenv('SMTP_USER')
        smtp_pass = os.getenv('SMTP_PASS')
        from_email = os.getenv('SMTP_FROM', 'dnd-rag@yourdomain.com')
        
        msg = MIMEMultipart()
        msg['From'] = from_email
        msg['To'] = self.alert_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            if smtp_user and smtp_pass:
                server.login(smtp_user, smtp_pass)
            server.send_message(msg)
