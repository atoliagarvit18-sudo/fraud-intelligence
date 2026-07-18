import torch  # Warm up PyTorch DLLs right at boot to prevent WinError 1114 on Windows
import asyncio
from app.collectors.reddit import RedditCollector
from app.scheduler import analysis_job
from app.database.mongo import get_collection
from app.config.constants import RAW_POSTS, PROCESSED_POSTS, CLUSTERS, EVENTS

async def main():
    print("--- 1. Running RedditCollector.collect_once() ---")
    collector = RedditCollector()
    inserted = collector.collect_once()
    print(f"-> Inserted {inserted} new raw posts into MongoDB!")

    print("\n--- 2. Running AI Analysis Pipeline (Preprocessing -> Groq LLM -> Embeddings -> Clustering -> Threat Engine) ---")
    analysis_job()

    print("\n==========================================================================")
    print("              LIVE OUTPUT STORED IN MONGODB DATABASE")
    print("==========================================================================")

    raw_col = get_collection(RAW_POSTS)
    proc_col = get_collection(PROCESSED_POSTS)
    clus_col = get_collection(CLUSTERS)
    ev_col = get_collection(EVENTS)

    print(f"\n[1] Total Raw Posts (`{RAW_POSTS}`): {raw_col.count_documents({})}")
    for p in raw_col.find().limit(3):
        title = (p.get("title") or "")[:75]
        print(f"  * [{p.get('source')} | ID: {p.get('source_id')}] {title}...")

    print(f"\n[2] Total Processed & Classified Posts (`{PROCESSED_POSTS}`): {proc_col.count_documents({})}")
    for p in proc_col.find().limit(4):
        st = p.get("scam_type")
        fraud = p.get("is_fraud")
        conf = p.get("confidence")
        summary = (p.get("summary") or "")[:75]
        entities = p.get("entities")
        print(f"  * Scam Type: {st} (Fraud?: {fraud}, Conf: {conf})")
        print(f"    Summary: {summary}...")
        print(f"    Entities: {entities}")

    print(f"\n[3] Total Fraud Campaigns (`{CLUSTERS}`): {clus_col.count_documents({})}")
    for c in clus_col.find().limit(3):
        cid = c.get("cluster_id")
        posts = c.get("post_count")
        sev = c.get("severity")
        score = c.get("campaign_score")
        platforms = c.get("platforms")
        print(f"  * Cluster {cid} | Severity: {sev} | Posts: {posts} | Score: {score}")
        print(f"    Targeted Platforms: {platforms}")

    print(f"\n[4] Total Threat Events (`{EVENTS}`): {ev_col.count_documents({})}")
    for e in ev_col.find().limit(3):
        etype = e.get("event_type")
        sev = e.get("severity")
        st = e.get("scam_type")
        posts = e.get("post_count")
        print(f"  * Event: {etype} | Severity: {str(sev).upper()} | Scam: {st} | Affected Posts: {posts}")

if __name__ == "__main__":
    asyncio.run(main())
