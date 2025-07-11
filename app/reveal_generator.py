import os
import base64
from jinja2 import Environment, FileSystemLoader
from app.chart_generator import generate_chart_image


def encode_image_to_base64(image_path):
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def format_slide_content(content):
    if isinstance(content, list):
        return "<br>".join(
            line if line.strip().startswith("•") else f"• {line}"
            for line in content
        )
    elif isinstance(content, str) and "- " in content:
        lines = [line.strip("- ") for line in content.split("- ") if line.strip()]
        return "<br>".join(f"• {line}" for line in lines)
    return content


def generate_reveal_html(slides_json, df, output_path="output/report.html", return_html=False):


    rendered_slides = []

    for slide in slides_json:
        chart_column = slide.get("chart_column")
        chart_value = slide.get("chart_value")
        chart_type = slide.get("chart_type")
        has_chart = chart_column and chart_column.lower() != "null"

        # Slide 1: content
        rendered_slides.append({
            "title": slide.get("title", ""),
            "content": format_slide_content(slide.get("content", "")),
            "image_base64": None
        })

        # Slide 2: chart (if needed and valid columns)
        if has_chart and df is not None:
            if chart_column in df.columns and (not chart_value or chart_value in df.columns):
                try:
                    image_path = generate_chart_image(
                        df=df,
                        group_column=chart_column,
                        chart_type=chart_type,
                        value_column=chart_value
                    )
                    if image_path:
                        image_base64 = encode_image_to_base64(image_path)
                        rendered_slides.append({
                            "title": f"{slide.get('title')} (Chart)",
                            "content": "",
                            "image_base64": image_base64
                        })
                except Exception as e:
                    print(f"[Chart Error] Could not render chart: {e}")
            else:
                print(f"[Warning] Skipping chart - invalid column: {chart_column} or {chart_value}")

    # Render HTML using Jinja2
    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template("reveal_template.html")
    html_content = template.render(slides=rendered_slides)

    if return_html:
        return html_content
    else:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        return output_path
