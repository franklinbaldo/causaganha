import ibis
import pandas as pd
import statistics

# Connect to local DB and query TJRO rows to calculate true average text length
db = ibis.duckdb.connect("data/causaganha.duckdb")
intim = db.table("intimations")

tjro_local = intim.filter(intim.sigla_tribunal == "TJRO").filter(intim.texto.notnull())

sample = tjro_local.select(intim.texto).limit(500).execute()
lengths = sample["texto"].str.len().tolist()
avg_chars = statistics.mean(lengths)
avg_tokens = avg_chars / 4

# Read sync-manifest to count how many TJRO 2025 daily parquet files are uploaded on Internet Archive
df_manifest = pd.read_csv("data/sync-manifest.csv")
df_manifest["date"] = pd.to_datetime(df_manifest["date"])
df_tjro_2025 = df_manifest[
    (df_manifest["tribunal"] == "TJRO")
    & (df_manifest["date"].dt.year == 2025)
    & (df_manifest["ia_status"] == "uploaded")
]
uploaded_days = len(df_tjro_2025)

# Calculate typical daily volume of intimations for TJRO from local database
daily_counts = (
    tjro_local.group_by(tjro_local.data_disponibilizacao)
    .aggregate(count=tjro_local.count())
    .execute()
)
avg_rows_per_day = daily_counts["count"].mean()

# Extrapolate for full TJRO 2025 dataset
total_docs_est = int(uploaded_days * avg_rows_per_day)
total_chars_est = total_docs_est * avg_chars
total_tokens_est = total_chars_est / 4
tokens_m = total_tokens_est / 1_000_000

# Compute costs
gemini_cost = tokens_m * 0.20
gemini_batch_cost = tokens_m * 0.10
pplx_cost = tokens_m * 0.004
nemotron_cost = 0.00

print("=== TJRO 2025 Dataset Metrics (Internet Archive) ===")
print(f"Uploaded Days in 2025:  {uploaded_days} days (out of 261 in manifest)")
print(f"Avg Intimations / Day:  {avg_rows_per_day:,.2f}")
print(f"Est. Total Documents:  {total_docs_est:,}")
print(f"Avg Chars per text:    {avg_chars:,.0f} (~{avg_tokens:.1f} tokens)")
print(f"Est. Total Tokens:     {total_tokens_est:,.0f} ({tokens_m:.2f}M tokens)")
print()
print("=================== Cost Estimate Table ===================")
print(f"1. OpenRouter Llama-Nemotron (2048-dim, free):  $0.00 USD (FREE!)")
print(f"2. OpenRouter Perplexity pplx ($0.004/1M):      ${pplx_cost:.4f} USD")
print(f"3. Gemini Batch API ($0.10/1M):                ${gemini_batch_cost:.4f} USD")
print(f"4. Gemini On-Demand ($0.20/1M):                ${gemini_cost:.4f} USD")
print()
print("Jina AI (jina-embeddings-v3, free 10M tokens/month):")
if tokens_m <= 10:
    print(f"  Fits entirely within the monthly 10M free budget!")
else:
    excess = tokens_m - 10
    print(f"  Exceeds monthly 10M free tier by {excess:.2f}M tokens.")
print("===========================================================")
