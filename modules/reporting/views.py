from modules.reporting.models import AssetSummary


class ReportingView:
    @staticmethod
    def render_asset_summary(summary: AssetSummary) -> str:
        sections = []
        for title, values in (
            ("Theo loại", summary.by_category),
            ("Theo tình trạng", summary.by_status),
            ("Theo vị trí", summary.by_location),
        ):
            sections.append(f"{title}:")
            sections.extend(f"  {name}: {count}" for name, count in sorted(values.items()))
        return "\n".join(sections)
