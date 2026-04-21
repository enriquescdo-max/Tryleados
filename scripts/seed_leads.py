"""
Seed LeadOS with 20 realistic sample leads across different tiers.
Run: python scripts/seed_leads.py
"""

import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../config/.env"))
DB_URL = os.environ["LEADOS_DB_URL"]

LEADS = [
    # Tier 1 — strong ICP matches
    dict(email="sarah.chen@growthloop.io", first_name="Sarah", last_name="Chen",
         title="VP of Sales", company="GrowthLoop", company_revenue=8_000_000,
         employee_count=45, industry="SaaS", timezone="America/New_York", intent_score=0.85,
         linkedin_url="https://linkedin.com/in/sarahchen-growthloop"),

    dict(email="marcus.obi@revstack.ai", first_name="Marcus", last_name="Obi",
         title="CRO", company="RevStack AI", company_revenue=15_000_000,
         employee_count=120, industry="AI/ML", timezone="America/Chicago", intent_score=0.90,
         linkedin_url="https://linkedin.com/in/marcusobi"),

    dict(email="priya.sharma@fintrek.com", first_name="Priya", last_name="Sharma",
         title="Head of Growth", company="FinTrek", company_revenue=22_000_000,
         employee_count=200, industry="FinTech", timezone="America/Los_Angeles", intent_score=0.78,
         linkedin_url="https://linkedin.com/in/priyasharma-fintrek"),

    dict(email="james.wu@pipelineai.co", first_name="James", last_name="Wu",
         title="Co-Founder", company="Pipeline AI", company_revenue=3_500_000,
         employee_count=28, industry="SaaS", timezone="America/New_York", intent_score=0.88,
         linkedin_url="https://linkedin.com/in/jameswu-pipeline"),

    dict(email="elena.volkov@salescraft.io", first_name="Elena", last_name="Volkov",
         title="VP Sales", company="SalesCraft", company_revenue=12_000_000,
         employee_count=95, industry="GTM/RevOps tools", timezone="Europe/London", intent_score=0.82,
         linkedin_url="https://linkedin.com/in/elenavolkov"),

    dict(email="david.park@nexuscrm.com", first_name="David", last_name="Park",
         title="Head of Sales", company="NexusCRM", company_revenue=9_000_000,
         employee_count=60, industry="SaaS", timezone="America/Chicago", intent_score=0.75,
         linkedin_url="https://linkedin.com/in/davidpark-nexus"),

    dict(email="nina.foster@converta.io", first_name="Nina", last_name="Foster",
         title="Founder", company="Converta", company_revenue=2_000_000,
         employee_count=15, industry="AI/ML", timezone="America/New_York", intent_score=0.91,
         linkedin_url="https://linkedin.com/in/ninafoster"),

    dict(email="tom.harris@dealdesk.com", first_name="Tom", last_name="Harris",
         title="Revenue Operations Lead", company="DealDesk", company_revenue=18_000_000,
         employee_count=150, industry="GTM/RevOps tools", timezone="America/Denver", intent_score=0.80,
         linkedin_url="https://linkedin.com/in/tomharris-dealdesk"),

    # Tier 2 — moderate ICP matches
    dict(email="lisa.morgan@cloudpulse.io", first_name="Lisa", last_name="Morgan",
         title="Director of Sales", company="CloudPulse", company_revenue=5_000_000,
         employee_count=40, industry="SaaS", timezone="America/Los_Angeles", intent_score=0.55,
         linkedin_url="https://linkedin.com/in/lisamorgan"),

    dict(email="raj.patel@databridge.co", first_name="Raj", last_name="Patel",
         title="Sales Manager", company="DataBridge", company_revenue=4_000_000,
         employee_count=35, industry="FinTech", timezone="America/New_York", intent_score=0.60,
         linkedin_url="https://linkedin.com/in/rajpatel-databridge"),

    dict(email="kate.brooks@smartlead.ai", first_name="Kate", last_name="Brooks",
         title="CEO", company="SmartLead AI", company_revenue=1_200_000,
         employee_count=12, industry="AI/ML", timezone="Europe/London", intent_score=0.65,
         linkedin_url="https://linkedin.com/in/katebrooks-smartlead"),

    dict(email="alex.turner@boostgrowth.com", first_name="Alex", last_name="Turner",
         title="Director of Sales", company="BoostGrowth", company_revenue=7_000_000,
         employee_count=55, industry="SaaS", timezone="America/Chicago", intent_score=0.58,
         linkedin_url="https://linkedin.com/in/alexturner"),

    dict(email="jessica.lee@metricly.io", first_name="Jessica", last_name="Lee",
         title="Head of Revenue", company="Metricly", company_revenue=6_500_000,
         employee_count=48, industry="GTM/RevOps tools", timezone="America/New_York", intent_score=0.62,
         linkedin_url="https://linkedin.com/in/jessicalee-metricly"),

    dict(email="omar.hassan@scalepath.co", first_name="Omar", last_name="Hassan",
         title="VP of Growth", company="ScalePath", company_revenue=10_000_000,
         employee_count=80, industry="SaaS", timezone="America/Los_Angeles", intent_score=0.50,
         linkedin_url="https://linkedin.com/in/omarhassan"),

    # Lower tier — outside ICP
    dict(email="ben.carter@localretail.com", first_name="Ben", last_name="Carter",
         title="Sales Rep", company="LocalRetail", company_revenue=500_000,
         employee_count=8, industry="Retail", timezone="America/New_York", intent_score=0.20,
         linkedin_url="https://linkedin.com/in/bencarter"),

    dict(email="amy.wilson@bigcorp.com", first_name="Amy", last_name="Wilson",
         title="Account Executive", company="BigCorp", company_revenue=500_000_000,
         employee_count=5000, industry="Manufacturing", timezone="America/Chicago", intent_score=0.15,
         linkedin_url="https://linkedin.com/in/amywilson"),

    dict(email="chris.ng@startup.io", first_name="Chris", last_name="Ng",
         title="Sales Development Rep", company="Early Startup", company_revenue=100_000,
         employee_count=4, industry="SaaS", timezone="America/Los_Angeles", intent_score=0.30,
         linkedin_url="https://linkedin.com/in/chrisng"),

    dict(email="diana.ross@mediaco.com", first_name="Diana", last_name="Ross",
         title="Marketing Manager", company="MediaCo", company_revenue=3_000_000,
         employee_count=30, industry="Media", timezone="Europe/London", intent_score=0.25,
         linkedin_url="https://linkedin.com/in/dianaross"),

    dict(email="frank.miller@legacytech.com", first_name="Frank", last_name="Miller",
         title="IT Manager", company="LegacyTech", company_revenue=8_000_000,
         employee_count=70, industry="IT Services", timezone="America/New_York", intent_score=0.10,
         linkedin_url="https://linkedin.com/in/frankmiller"),

    dict(email="grace.kim@foodtech.co", first_name="Grace", last_name="Kim",
         title="Operations Lead", company="FoodTech", company_revenue=2_000_000,
         employee_count=20, industry="Food & Beverage", timezone="America/Los_Angeles", intent_score=0.18,
         linkedin_url="https://linkedin.com/in/gracekim"),
]

async def seed():
    conn = await asyncpg.connect(DB_URL)
    try:
        inserted = 0
        skipped  = 0
        for lead in LEADS:
            existing = await conn.fetchval(
                "SELECT id FROM leads WHERE email = $1", lead["email"]
            )
            if existing:
                skipped += 1
                continue
            await conn.execute(
                """
                INSERT INTO leads
                  (email, first_name, last_name, title, company, company_revenue,
                   employee_count, industry, timezone, intent_score, linkedin_url)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
                """,
                lead["email"], lead["first_name"], lead["last_name"], lead["title"],
                lead["company"], lead["company_revenue"], lead["employee_count"],
                lead["industry"], lead["timezone"], lead["intent_score"], lead["linkedin_url"],
            )
            inserted += 1

        print(f"[Seed] {inserted} leads inserted, {skipped} already existed")
        print(f"[Seed] Total leads in DB: {await conn.fetchval('SELECT COUNT(*) FROM leads')}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(seed())
