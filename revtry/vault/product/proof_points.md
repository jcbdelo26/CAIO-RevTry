# Proof Points

**Valid Through**: 2026-06-30
**Last Updated**: 2026-03-07
**Updated By**: Phase 1 setup
**Applies To**: Campaign Craft Agent

## Purpose

Proof points provide credible, specific evidence that Campaign Craft uses to personalize email drafts. Each proof point is tagged by industry tier so the agent selects relevant evidence for the recipient's vertical.

## Proof Points Library

### Tier 1 Industries (Agencies, Staffing, Consulting, Law, CPA, Real Estate, E-commerce)

| ID | Proof Point | Metric | Industry Tags |
|----|------------|--------|---------------|
| PP-001 | AI-powered workflow automation reduced manual task time | 40% reduction in admin hours | agencies, consulting |
| PP-002 | Automated lead scoring and qualification pipeline | 3x increase in qualified pipeline | staffing, agencies |
| PP-003 | AI-driven contract review and risk flagging | 60% faster contract turnaround | law, consulting |
| PP-004 | Intelligent CRM automation with predictive follow-up | 2.5x improvement in response rates | real estate, e-commerce |
| PP-005 | AI-powered financial document processing | 50% reduction in data entry errors | cpa, consulting |
| PP-006 | Automated inventory forecasting and demand planning | 25% reduction in overstock costs | e-commerce |

### Tier 2 Industries (B2B SaaS, IT Services, Healthcare, Financial Services)

| ID | Proof Point | Metric | Industry Tags |
|----|------------|--------|---------------|
| PP-007 | AI customer success automation and churn prediction | 30% reduction in churn rate | saas, it services |
| PP-008 | Intelligent ticket routing and resolution automation | 45% faster resolution times | saas, it services |
| PP-009 | AI-powered patient scheduling and resource optimization | 35% improvement in scheduling efficiency | healthcare |
| PP-010 | Automated compliance monitoring and reporting | 70% reduction in manual compliance work | financial services, healthcare |

### Tier 3 Industries (Manufacturing, Logistics, Construction, Home Services)

| ID | Proof Point | Metric | Industry Tags |
|----|------------|--------|---------------|
| PP-011 | AI-powered quality inspection and defect detection | 80% faster defect identification | manufacturing |
| PP-012 | Route optimization and predictive maintenance | 20% reduction in fleet costs | logistics |
| PP-013 | Automated project estimation and resource allocation | 30% more accurate project bids | construction |
| PP-014 | AI-driven scheduling and dispatch optimization | 25% improvement in job completion rates | home services |

## Selection Rules

1. Campaign Craft selects proof points where `Industry Tags` overlap with the lead's `normalized_industry`
2. Maximum 2 proof points per draft
3. If no industry-specific match, use PP-001 or PP-002 (general operational efficiency)
4. Proof point text is woven into the email body, NOT appended as a list

## Anti-Fabrication Rule

> Only use proof points listed in this file. Do NOT invent statistics, case studies, or metrics. If no relevant proof point exists, omit the proof point from the draft entirely.

## Review Trigger

- When new case studies or client results are available
- When industry focus shifts
- Quarterly during vault freshness review
