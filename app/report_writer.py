import requests
import pandas as pd
import re
from io import StringIO

def remove_think_blocks(text):
    """Remove <think>...</think> blocks if present in LLM response."""
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


def summarize_dataframe(df: pd.DataFrame) -> str:
    """Deep summary and quality check for DataFrame."""

    lines = []
    lines.append(f"🔹 Dataset: {len(df)} rows × {len(df.columns)} columns")

    # 1. Column overview
    lines.append("\n🔸 Column Overview:")
    for col in df.columns:
        dtype = df[col].dtype
        null_count = df[col].isnull().sum()
        unique_count = df[col].nunique()
        lines.append(f"  - {col} ({dtype}) | nulls: {null_count}, unique: {unique_count}")

    # 2. Numeric columns
    numeric_cols = df.select_dtypes(include=["number"]).columns
    if len(numeric_cols) > 0:
        lines.append("\n📊 Numeric Summary:")
        desc = df[numeric_cols].describe().T
        desc["skew"] = df[numeric_cols].skew()
        for col in desc.index:
            row = desc.loc[col]
            lines.append(
                f"  - {col}: mean={row['mean']:.2f}, std={row['std']:.2f}, min={row['min']}, max={row['max']}, skew={row['skew']:.2f}"
            )

    lines.append("\n⚠️ Potential Outliers (IQR Method):")
    for col in numeric_cols:
        q1 = df[col].quantile(0.25)
        q3 = df[col].quantile(0.75)
        iqr = q3 - q1
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr

        outliers = df[(df[col] < lower) | (df[col] > upper)]

        if not outliers.empty:
            # Get top 3 outlier values
            top_outlier_vals = outliers[col].nlargest(3).round(2).tolist()

            lines.append(
                f"  - {col}: {len(outliers)} outliers | IQR=({q1:.2f}, {q3:.2f}) | Top values: {top_outlier_vals}"
            )
        else:
            lines.append(
                f"  - {col}: No outliers detected | IQR=({q1:.2f}, {q3:.2f})"
            )


    # 4. Object columns (categorical/text)
    object_cols = df.select_dtypes(include=["object"]).columns
    for col in object_cols:
        vc = df[col].value_counts().head(3)
        lines.append(f"\n🔠 Top values in '{col}':")
        for val, count in vc.items():
            lines.append(f"  - {val}: {count} rows")

    # 5. Datetime columns if any
    datetime_cols = df.select_dtypes(include=["datetime", "datetime64[ns]"]).columns
    for col in datetime_cols:
        lines.append(f"\n🗓️ Datetime column: {col}")
        lines.append(f"  - Range: {df[col].min()} → {df[col].max()}")

    return "\n".join(lines)



def generate_report(question: str, sql: str, data_frame: pd.DataFrame, llm_api_url: str, api_key: str | None = None) -> str:
    """
    Generate report from user question, SQL query, and DataFrame returned from the query.
    Includes deep summary, outlier detection, skew analysis, nulls,... to help LLM analyze more accurately.
    """
    # Detailed summary
    data_summary = summarize_dataframe(data_frame)
    # Advanced prompt suggestions for LLM
    content = f"""
User Question:
{question}

Generated SQL:
{sql}

📊 Data Summary:
{data_summary}

🎯 Report Objective:
Write an analytical report that helps a data consumer understand the insight behind this query result.

👉 Important Guidelines:
- Do NOT assume significance unless justified by the data
- If the data is too uniform (e.g., all tax = 1), say so
- Highlight any skewed distributions or potential outliers
- Point out if a column has many nulls or low uniqueness
- Use clear bullet points or short summary paragraphs
- If there's no significant insight, say so briefly

✍️ Please generate a concise and data-grounded report:
"""

    headers = {
        "Content-Type": "application/json",
    }
    
    # Add Authorization header if api_key is provided
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "You are a careful, detail-driven data analyst."},
            {"role": "user", "content": content}
        ],
        "temperature": 0.1
    }

    try:
        response = requests.post(
            f"{llm_api_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=200
        )
        
        # Check response status
        if response.status_code != 200:
            raise RuntimeError(f"HTTP {response.status_code}: {response.text}")
        
        # Check if response has content
        if not response.text.strip():
            raise RuntimeError("Empty response from API")
        
        result = response.json()

        if "choices" in result and result["choices"]:
            raw_text = result["choices"][0]["message"]["content"]
            clean_text = remove_think_blocks(raw_text)
            return clean_text

        elif "error" in result:
            raise RuntimeError(f"LLM API Error: {result['error']}")

        else:
            raise RuntimeError(f"Invalid LLM response: {result}")

    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"❌ Connection error: {e}")
    except Exception as e:
        raise RuntimeError(f"❌ Unexpected error: {e}")
