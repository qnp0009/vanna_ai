import os
import json
from jinja2 import Environment, FileSystemLoader
import pandas as pd


def format_slide_content(content):
    if isinstance(content, list):
        return content
    elif isinstance(content, str) and "- " in content:
        lines = [line.strip("- ") for line in content.split("- ") if line.strip()]
        return lines
    elif isinstance(content, str):
        return [content]
    return content


def generate_chart_data(df, chart_column, chart_value, chart_type):
    """Generate Chart.js compatible data from DataFrame"""
    if chart_column not in df.columns or (chart_value and chart_value not in df.columns):
        return None
    
    try:
        if chart_type == "bar" and chart_value:
            # Group by chart_column and sum chart_value
            chart_data = df.groupby(chart_column)[chart_value].sum().sort_values(ascending=False)
            return {
                "labels": chart_data.index.tolist(),
                "data": chart_data.values.tolist(),
                "label": f"{chart_value} by {chart_column}"
            }
        
        elif chart_type == "pie" and chart_value:
            # Group by chart_column and sum chart_value
            chart_data = df.groupby(chart_column)[chart_value].sum()
            return {
                "labels": chart_data.index.tolist(),
                "data": chart_data.values.tolist(),
                "label": f"{chart_value} by {chart_column}"
            }
        
        elif chart_type == "line" and chart_value:
            # Group by chart_column and sum chart_value, sort by index
            chart_data = df.groupby(chart_column)[chart_value].sum().sort_index()
            return {
                "labels": chart_data.index.tolist(),
                "data": chart_data.values.tolist(),
                "label": f"{chart_value} over {chart_column}"
            }
        
        elif chart_type == "histogram":
            # Create histogram data
            hist_data = df[chart_column].value_counts().sort_index()
            return {
                "labels": hist_data.index.tolist(),
                "data": hist_data.values.tolist(),
                "label": f"Distribution of {chart_column}"
            }
        
        else:
            return None
            
    except Exception as e:
        print(f"❌ Error generating chart data: {e}")
        return None


def prepare_slides_data(slides_json, df):
    """Prepare slides data with real chart data from DataFrame"""
    prepared_slides = []
    
    for slide in slides_json:
        prepared_slide = {
            "title": slide.get("title", ""),
            "content": format_slide_content(slide.get("content", ""))
        }
        
        # Add chart data if chart fields are present
        chart_column = slide.get("chart_column")
        chart_value = slide.get("chart_value")
        chart_type = slide.get("chart_type")
        
        if chart_column and chart_value and chart_type:
            chart_data = generate_chart_data(df, chart_column, chart_value, chart_type)
            if chart_data:
                prepared_slide.update({
                    "chart_column": chart_column,
                    "chart_value": chart_value,
                    "chart_type": chart_type,
                    "chart_data": chart_data
                })
            else:
                # Chart data generation failed, remove chart fields
                prepared_slide.update({
                    "chart_column": None,
                    "chart_value": None,
                    "chart_type": None
                })
        else:
            prepared_slide.update({
                "chart_column": None,
                "chart_value": None,
                "chart_type": None
            })
        
        prepared_slides.append(prepared_slide)
    
    return prepared_slides


def generate_reveal_html(slides_json, df, output_path="output/report.html", return_html=False):
    """Generate Reveal.js HTML with real chart data"""
    
    # Prepare slides data with real chart data
    prepared_slides = prepare_slides_data(slides_json, df)
    
    # Render HTML using Jinja2
    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template("reveal_template.html")
    
    html_content = template.render(slides=prepared_slides)

    if return_html:
        return html_content
    else:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        return output_path
