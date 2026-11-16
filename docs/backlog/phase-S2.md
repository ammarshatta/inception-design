# Phase S2 stories

## S2-01 · SaaS · Could

**Role:** Platform owner  
**Story:** As a platform owner, I want plans by feature flags and limits with monthly billing, so that I earn recurring revenue.

**Acceptance criteria**

1. Given a tenant on a plan without online payments, when its admin opens settings, then online payments cannot be switched on.
2. Given an unpaid invoice past grace, when the billing job runs, then the tenant is suspended with a notice.
