# Phase S3 stories

## S3-01 · SaaS · Could

**Role:** Platform owner  
**Story:** As a platform owner, I want updates rolled out to all tenants safely, so that one bad release does not hit everyone.

**Acceptance criteria**

1. Given a new release, when I roll it out, then canary tenants migrate first and the rest follow only if they pass.
