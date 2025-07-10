import matplotlib.pyplot as plt
import os

def generate_chart_image(df, group_column, chart_type= str, value_column=None, output_path="output/chart.png"):
    if group_column not in df.columns or (value_column and value_column not in df.columns):
        print("❌ Invalid column name(s).")
        return None

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.figure(figsize=(10, 6.5))

    try:
        if chart_type == "bar" and value_column:
            chart_data = df.groupby(group_column)[value_column].sum().sort_values(ascending=False)
            chart_data.plot(kind="bar", color='skyblue', edgecolor='black')
            plt.ylabel(value_column)
            plt.title(f"{value_column} by {group_column}")

        elif chart_type == "pie" and value_column:
            chart_data = df.groupby(group_column)[value_column].sum()
            chart_data.plot(kind="pie", autopct="%1.1f%%", startangle=90)
            plt.ylabel("")
            plt.title(f"{value_column} by {group_column}")

        elif chart_type == "line" and value_column:
            chart_data = df.groupby(group_column)[value_column].sum().sort_index()
            chart_data.plot(kind="line", marker="o")
            plt.ylabel(value_column)
            plt.title(f"{value_column} over {group_column}")

        elif chart_type == "histogram":
            df[group_column].hist(bins=10, color='skyblue', edgecolor='black')
            plt.title(f"{group_column} (Histogram)")
            plt.xlabel(group_column)
            plt.ylabel("Frequency")

        else:
            print("❌ Unsupported chart type.")
            return None

        plt.tight_layout()
        plt.savefig(output_path)
        plt.close()
        return output_path

    except Exception as e:
        print(f"❌ Chart generation error: {e}")
        return None
