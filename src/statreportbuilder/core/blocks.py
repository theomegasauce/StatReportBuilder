from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar

import pandas as pd
from scipy import stats


@dataclass
class ParamSpec:
    name: str
    label: str
    kind: str
    default: Any = None
    choices: list[str] | None = None
    source: str | None = None


@dataclass
class PortSpec:
    name: str
    kind: str


class Block:
    type_id: ClassVar[str] = ""
    title: ClassVar[str] = ""
    inputs: ClassVar[list[PortSpec]] = []
    outputs: ClassVar[list[PortSpec]] = []
    params_spec: ClassVar[list[ParamSpec]] = []

    def __init__(self, node_id: str, params: dict | None = None) -> None:
        self.node_id = node_id
        defaults = {p.name: p.default for p in self.params_spec}
        if params:
            defaults.update(params)
        self.params: dict = defaults

    def execute(self, inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError


class CSVLoaderBlock(Block):
    type_id = "csv_loader"
    title = "CSV Loader"
    inputs: ClassVar[list[PortSpec]] = []
    outputs: ClassVar[list[PortSpec]] = [PortSpec("dataframe", "dataframe")]
    params_spec: ClassVar[list[ParamSpec]] = [
        ParamSpec("csv_name", "CSV file", "file_ref", default=""),
    ]

    def execute(self, inputs, context):
        csv_name = self.params.get("csv_name") or ""
        if not csv_name:
            return {"dataframe": None}
        project = context.get("project")
        if project is None:
            return {"dataframe": None}
        path = project.csv_path(csv_name)
        if not path.exists():
            return {"dataframe": None}
        return {"dataframe": pd.read_csv(path)}


class TwoSampleTTestBlock(Block):
    type_id = "two_sample_ttest"
    title = "Two-Sample T-Test"
    inputs: ClassVar[list[PortSpec]] = [PortSpec("dataframe", "dataframe")]
    outputs: ClassVar[list[PortSpec]] = [PortSpec("result", "result")]
    params_spec: ClassVar[list[ParamSpec]] = [
        ParamSpec("group_column", "Group column", "column_ref", source="dataframe"),
        ParamSpec("value_column", "Value column", "column_ref", source="dataframe"),
        ParamSpec("equal_var", "Assume equal variance", "boolean", default=False),
    ]

    def execute(self, inputs, context):
        df = inputs.get("dataframe")
        if df is None:
            return {"result": None}

        gcol = self.params.get("group_column") or ""
        vcol = self.params.get("value_column") or ""
        if not gcol or not vcol or gcol not in df.columns or vcol not in df.columns:
            return {"result": None}

        groups = sorted(df[gcol].dropna().unique().tolist(), key=str)
        if len(groups) < 2:
            return {"result": None}

        g1, g2 = groups[0], groups[1]
        x1 = pd.to_numeric(df.loc[df[gcol] == g1, vcol], errors="coerce").dropna().to_numpy()
        x2 = pd.to_numeric(df.loc[df[gcol] == g2, vcol], errors="coerce").dropna().to_numpy()

        if len(x1) < 2 or len(x2) < 2:
            return {"result": None}

        equal_var = bool(self.params.get("equal_var", False))
        test = stats.ttest_ind(x1, x2, equal_var=equal_var)

        return {
            "result": {
                "t_statistic": float(test.statistic),
                "p_value": float(test.pvalue),
                "df": float(getattr(test, "df", float("nan"))),
                "n1": int(len(x1)),
                "n2": int(len(x2)),
                "mean1": float(x1.mean()),
                "mean2": float(x2.mean()),
                "std1": float(x1.std(ddof=1)),
                "std2": float(x2.std(ddof=1)),
                "group1": str(g1),
                "group2": str(g2),
                "value_column": vcol,
                "group_column": gcol,
                "equal_var": equal_var,
            }
        }


class ReportBlock(Block):
    type_id = "report"
    title = "Report"
    inputs: ClassVar[list[PortSpec]] = [PortSpec("result", "result")]
    outputs: ClassVar[list[PortSpec]] = [PortSpec("report_html", "html")]
    params_spec: ClassVar[list[ParamSpec]] = [
        ParamSpec("title", "Report title", "string", default="Two-Sample T-Test Report"),
        ParamSpec("alpha", "Significance level (α)", "number", default=0.05),
        ParamSpec("notes", "Notes", "text", default=""),
    ]

    def execute(self, inputs, context):
        result = inputs.get("result")
        title = str(self.params.get("title") or "Report")
        try:
            alpha = float(self.params.get("alpha", 0.05))
        except (TypeError, ValueError):
            alpha = 0.05
        notes = str(self.params.get("notes") or "")
        return {"report_html": self._render(title, alpha, notes, result)}

    @staticmethod
    def _render(title: str, alpha: float, notes: str, result: dict | None) -> str:
        head = (
            "<html><head><style>"
            "body { font-family: Arial, sans-serif; color: #222; margin: 24px; }"
            "h1 { border-bottom: 2px solid #444; padding-bottom: 6px; }"
            "h2 { margin-top: 24px; color: #333; }"
            "table { border-collapse: collapse; margin-top: 8px; }"
            "th, td { border: 1px solid #888; padding: 6px 12px; text-align: left; }"
            "th { background: #eee; }"
            ".verdict { font-weight: bold; }"
            ".sig { color: #1a7a1a; } .nonsig { color: #883333; }"
            "</style></head><body>"
        )

        if result is None:
            return (
                f"{head}<h1>{title}</h1>"
                "<p><em>Awaiting upstream result. "
                "Configure the CSV Loader and T-Test blocks.</em></p></body></html>"
            )

        sig = result["p_value"] < alpha
        verdict_class = "sig" if sig else "nonsig"
        verdict_text = "statistically significant" if sig else "not statistically significant"
        var_note = "equal variances assumed" if result["equal_var"] else "Welch's correction (unequal variances)"

        body = f"""
        <h1>{title}</h1>
        <h2>Summary</h2>
        <p>An independent two-sample t-test was conducted to compare
        <b>{result['value_column']}</b> between groups
        <b>{result['group1']}</b> and <b>{result['group2']}</b>
        (defined by <b>{result['group_column']}</b>).</p>

        <h2>Descriptive statistics</h2>
        <table>
          <tr><th>Group</th><th>n</th><th>Mean</th><th>SD</th></tr>
          <tr><td>{result['group1']}</td><td>{result['n1']}</td>
              <td>{result['mean1']:.4f}</td><td>{result['std1']:.4f}</td></tr>
          <tr><td>{result['group2']}</td><td>{result['n2']}</td>
              <td>{result['mean2']:.4f}</td><td>{result['std2']:.4f}</td></tr>
        </table>

        <h2>Test results</h2>
        <table>
          <tr><th>Statistic</th><th>Value</th></tr>
          <tr><td>t</td><td>{result['t_statistic']:.4f}</td></tr>
          <tr><td>df</td><td>{result['df']:.2f}</td></tr>
          <tr><td>p-value</td><td>{result['p_value']:.4g}</td></tr>
          <tr><td>α</td><td>{alpha}</td></tr>
          <tr><td>Variance</td><td>{var_note}</td></tr>
        </table>

        <h2>Conclusion</h2>
        <p>The difference in <b>{result['value_column']}</b> between
        <b>{result['group1']}</b> and <b>{result['group2']}</b> is
        <span class="verdict {verdict_class}">{verdict_text}</span>
        at α = {alpha}.</p>
        """
        if notes.strip():
            body += f"<h2>Notes</h2><p>{notes}</p>"

        return head + body + "</body></html>"


BLOCK_REGISTRY: dict[str, type[Block]] = {
    cls.type_id: cls for cls in (CSVLoaderBlock, TwoSampleTTestBlock, ReportBlock)
}
