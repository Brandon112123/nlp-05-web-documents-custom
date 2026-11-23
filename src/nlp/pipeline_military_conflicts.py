"""Extract Wikipedia war infobox data and build an interactive conflict dashboard."""

import json
from pathlib import Path
import re

from bs4 import BeautifulSoup
import pandas as pd
import plotly.express as px
import requests

CONFLICTS = {
    "Korean War": {
        "url": "https://en.wikipedia.org/wiki/Korean_War",
        "latitude": 38.0,
        "longitude": 127.0,
        "start_date": "1950-06-25",
        "end_date": "1953-07-27",
    },
    "Vietnam War": {
        "url": "https://en.wikipedia.org/wiki/Vietnam_War",
        "latitude": 16.0,
        "longitude": 107.0,
        "start_date": "1955-11-01",
        "end_date": "1975-04-30",
    },
    "Gulf War": {
        "url": "https://en.wikipedia.org/wiki/Gulf_War",
        "latitude": 29.3,
        "longitude": 47.5,
        "start_date": "1990-08-02",
        "end_date": "1991-02-28",
    },
}


def clean_text(element):
    """Remove citations and normalize whitespace from an HTML element."""
    if element is None:
        return "Not found"
    element = BeautifulSoup(str(element), "html.parser")
    for tag in element.select("sup.reference, .mw-editsection, style, script"):
        tag.decompose()
    text = element.get_text(" ", strip=True)
    text = re.sub(r"\[\s*(?:\d+|citation needed)[^\]]*\]", "", text)
    return re.sub(r"\s+", " ", text).strip() or "Not found"


def extract_conflict_data(name, details):
    """Extract Wikipedia title and military infobox fields."""
    response = requests.get(
        details["url"],
        headers={
            "User-Agent": "MilitaryConflictResearch/1.0 (educational data analysis)"
        },
        timeout=30,
    )
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    heading = soup.find("h1")
    infobox = soup.select_one("table.infobox")

    def field(*labels):
        if infobox is None:
            return "Not found"
        for row in infobox.select("tr"):
            header = row.find("th", recursive=False)
            value = row.find("td", recursive=False)
            if not header or not value:
                continue
            label = clean_text(header).lower().rstrip(":")
            if any(label == candidate.lower() for candidate in labels):
                return clean_text(value)
        return "Not found"

    return {
        "conflict": name,
        "title": clean_text(heading) if heading else name,
        "dates": field("Date"),
        "location": field("Location"),
        "outcome": field("Result", "Outcome"),
        "latitude": details["latitude"],
        "longitude": details["longitude"],
        "source": details["url"],
        "start_date": details["start_date"],
        "end_date": details["end_date"],
    }


def build_dashboard(df, destination):
    """Build a responsive dashboard with clickable map and charts."""
    map_fig = px.scatter_geo(
        df,
        lat="latitude",
        lon="longitude",
        color="conflict",
        hover_name="conflict",
        custom_data=["conflict"],
        projection="natural earth",
        title="Select a conflict on the map",
    )
    map_fig.update_traces(
        marker={"size": 17, "opacity": 0.9},
        hovertemplate="<b>%{customdata[0]}</b><extra></extra>",
    )
    map_fig.update_geos(showcountries=True, showcoastlines=True, fitbounds="locations")
    map_fig.update_layout(
        margin={"l": 10, "r": 10, "t": 55, "b": 10},
        height=480,
        legend_title_text="Conflict",
    )

    duration_fig = px.bar(
        df,
        x="conflict",
        y="duration_years",
        color="conflict",
        text="duration_years",
        title="Duration comparison (years)",
        labels={"conflict": "Conflict", "duration_years": "Years"},
    )
    duration_fig.update_traces(textposition="outside")
    duration_fig.update_layout(
        showlegend=False, height=380, margin={"l": 40, "r": 20, "t": 60, "b": 40}
    )

    timeline_fig = px.timeline(
        df,
        x_start="start_date",
        x_end="end_date",
        y="conflict",
        color="conflict",
        title="Historical timeline",
    )
    timeline_fig.update_yaxes(autorange="reversed")
    timeline_fig.update_layout(
        showlegend=False, height=330, margin={"l": 40, "r": 20, "t": 60, "b": 30}
    )

    map_html = map_fig.to_html(
        full_html=False,
        include_plotlyjs=True,
        div_id="military-map",
        config={"responsive": True},
    )
    bar_html = duration_fig.to_html(
        full_html=False, include_plotlyjs=False, config={"responsive": True}
    )
    timeline_html = timeline_fig.to_html(
        full_html=False, include_plotlyjs=False, config={"responsive": True}
    )

    # Escape JSON so Wikipedia text cannot accidentally terminate the script element.
    data_json = json.dumps(
        df.assign(
            start_date=df["start_date"].dt.strftime("%Y-%m-%d"),
            end_date=df["end_date"].dt.strftime("%Y-%m-%d"),
        ).to_dict(orient="records"),
        ensure_ascii=False,
    ).replace("<", "\\u003c")
    template_path = Path("templates/dashboard.html")
    if not template_path.exists():
        raise FileNotFoundError(f"Missing dashboard template: {template_path}")
    html = template_path.read_text(encoding="utf-8")
    html = (
        html.replace("__MAP__", map_html)
        .replace("__BAR__", bar_html)
        .replace("__TIMELINE__", timeline_html)
        .replace("__DATA__", data_json)
    )
    destination.write_text(html, encoding="utf-8")


def main():
    """Run the military conflict comparison pipeline."""
    records = []
    for name, details in CONFLICTS.items():
        print(f"Extracting {name}...")
        records.append(extract_conflict_data(name, details))

    df = pd.DataFrame(records)
    df["start_date"] = pd.to_datetime(df["start_date"])
    df["end_date"] = pd.to_datetime(df["end_date"])
    df["duration_days"] = (df["end_date"] - df["start_date"]).dt.days
    df["duration_years"] = (df["duration_days"] / 365.25).round(2)

    output_dir = Path("data/processed")
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "military_conflicts.csv"
    df.to_csv(csv_path, index=False)
    build_dashboard(df, Path("military_conflicts_dashboard.html"))

    print(df[["conflict", "duration_days", "duration_years"]].to_string(index=False))
    print(f"CSV saved: {csv_path}")
    print("Dashboard saved: military_conflicts_dashboard.html")


if __name__ == "__main__":
    main()
