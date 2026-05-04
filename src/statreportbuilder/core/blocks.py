from __future__ import annotations

import base64
import io
from dataclasses import dataclass
from typing import Any, ClassVar

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats


CATEGORY_EXAMINATION = "examination"
CATEGORY_VALIDITY = "validity"
CATEGORY_HYPOTHESIS = "hypothesis"
CATEGORY_POSTHOC = "posthoc"
CATEGORY_GRAPHICS = "graphics"
CATEGORY_TEXT = "text"

CATEGORY_LABELS: dict[str, str] = {
    CATEGORY_EXAMINATION: "Examination",
    CATEGORY_VALIDITY: "Validity",
    CATEGORY_HYPOTHESIS: "Hypothesis tests",
    CATEGORY_POSTHOC: "Post Hoc tests",
    CATEGORY_GRAPHICS: "Graphics",
    CATEGORY_TEXT: "Text blocks",
}

CATEGORY_ORDER: list[str] = [
    CATEGORY_EXAMINATION,
    CATEGORY_VALIDITY,
    CATEGORY_HYPOTHESIS,
    CATEGORY_POSTHOC,
    CATEGORY_GRAPHICS,
    CATEGORY_TEXT,
]


PLOT_SIZES: dict[str, tuple[float, float]] = {
    "small": (4.0, 3.0),
    "medium": (6.0, 4.0),
    "large": (8.5, 5.5),
}


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
    category: ClassVar[str] = CATEGORY_EXAMINATION
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

    def draft_summary(self) -> str:
        parts = []
        for spec in self.params_spec:
            value = self.params.get(spec.name)
            if value in (None, "", False):
                continue
            parts.append(f"{spec.label}: {value}")
        return "; ".join(parts) if parts else "(unconfigured)"


def _fig_to_base64(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=110)
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def _plot_size(params: dict) -> tuple[float, float]:
    return PLOT_SIZES.get(str(params.get("output_size") or "medium"), PLOT_SIZES["medium"])


def _numeric_groups(df: pd.DataFrame, gcol: str, vcol: str) -> dict[str, np.ndarray]:
    out: dict[str, np.ndarray] = {}
    for label in sorted(df[gcol].dropna().unique().tolist(), key=str):
        values = pd.to_numeric(df.loc[df[gcol] == label, vcol], errors="coerce").dropna().to_numpy()
        if len(values) > 0:
            out[str(label)] = values
    return out


# ============================================================================
# Loader (kept; not exposed in palette but still used internally + by presets)
# ============================================================================


class CSVLoaderBlock(Block):
    type_id = "csv_loader"
    title = "CSV Loader"
    category = CATEGORY_EXAMINATION
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

    def draft_summary(self) -> str:
        name = self.params.get("csv_name") or ""
        return f"Load CSV: {name}" if name else "Load CSV: (no file selected)"


# ============================================================================
# Examination
# ============================================================================


class DatasetVariableTableBlock(Block):
    type_id = "dataset_variable_table"
    title = "Variable Table"
    category = CATEGORY_EXAMINATION
    inputs: ClassVar[list[PortSpec]] = [PortSpec("dataframe", "dataframe")]
    outputs: ClassVar[list[PortSpec]] = [PortSpec("result", "result")]
    params_spec: ClassVar[list[ParamSpec]] = [
        ParamSpec("max_rows", "Max rows", "integer", default=50),
    ]

    def execute(self, inputs, context):
        df = inputs.get("dataframe")
        if df is None:
            return {"result": None}
        rows = []
        for col in df.columns:
            series = df[col]
            rows.append({
                "Variable": col,
                "Type": str(series.dtype),
                "n": int(series.notna().sum()),
                "Missing": int(series.isna().sum()),
                "Unique": int(series.nunique(dropna=True)),
            })
        table = pd.DataFrame(rows)
        max_rows = int(self.params.get("max_rows") or 50)
        return {
            "result": {
                "tables": [{"name": "Variable summary", "data": table.head(max_rows)}],
                "interpretation": (
                    f"The dataset contains {len(df.columns)} variables and {len(df):,} rows. "
                    "The table above lists each variable with its data type, observed count, "
                    "missing count, and number of unique values."
                ),
            }
        }


class DatasetFrequencyTableBlock(Block):
    type_id = "dataset_frequency_table"
    title = "Frequency Table"
    category = CATEGORY_EXAMINATION
    inputs: ClassVar[list[PortSpec]] = [PortSpec("dataframe", "dataframe")]
    outputs: ClassVar[list[PortSpec]] = [PortSpec("result", "result")]
    params_spec: ClassVar[list[ParamSpec]] = [
        ParamSpec("column", "Column", "column_ref", source="dataframe"),
        ParamSpec("max_rows", "Max rows", "integer", default=30),
    ]

    def execute(self, inputs, context):
        df = inputs.get("dataframe")
        col = self.params.get("column") or ""
        if df is None or not col or col not in df.columns:
            return {"result": None}
        counts = df[col].value_counts(dropna=False)
        total = int(counts.sum()) or 1
        table = pd.DataFrame({
            "Value": [str(v) for v in counts.index],
            "Count": counts.values,
            "Percent": [c / total * 100 for c in counts.values],
        })
        max_rows = int(self.params.get("max_rows") or 30)
        return {
            "result": {
                "tables": [{"name": f"Frequencies of {col}", "data": table.head(max_rows)}],
                "interpretation": (
                    f"Distribution of '{col}' across {total:,} observations. "
                    f"There are {len(counts)} distinct values."
                ),
            }
        }


class DatasetNumericalStatsBlock(Block):
    type_id = "dataset_numerical_stats"
    title = "Numerical Statistics"
    category = CATEGORY_EXAMINATION
    inputs: ClassVar[list[PortSpec]] = [PortSpec("dataframe", "dataframe")]
    outputs: ClassVar[list[PortSpec]] = [PortSpec("result", "result")]
    params_spec: ClassVar[list[ParamSpec]] = [
        ParamSpec("decimals", "Decimal places", "integer", default=4),
        ParamSpec("max_rows", "Max rows", "integer", default=50),
    ]

    def execute(self, inputs, context):
        df = inputs.get("dataframe")
        if df is None:
            return {"result": None}
        numeric = df.select_dtypes(include="number")
        if numeric.empty:
            return {
                "result": {
                    "tables": [],
                    "interpretation": "No numeric columns were found in the dataset.",
                }
            }
        decimals = int(self.params.get("decimals") or 4)
        rows = []
        for col in numeric.columns:
            series = numeric[col].dropna()
            if series.empty:
                continue
            rows.append({
                "Variable": col,
                "n": int(series.size),
                "Mean": round(float(series.mean()), decimals),
                "SD": round(float(series.std(ddof=1)) if series.size > 1 else 0.0, decimals),
                "Min": round(float(series.min()), decimals),
                "Q1": round(float(series.quantile(0.25)), decimals),
                "Median": round(float(series.median()), decimals),
                "Q3": round(float(series.quantile(0.75)), decimals),
                "Max": round(float(series.max()), decimals),
                "Missing": int(numeric[col].isna().sum()),
            })
        table = pd.DataFrame(rows)
        max_rows = int(self.params.get("max_rows") or 50)
        return {
            "result": {
                "tables": [{"name": "Numerical statistics", "data": table.head(max_rows)}],
                "interpretation": (
                    f"Descriptive statistics for {len(rows)} numeric variable(s). "
                    "Means, standard deviations, and quartiles summarise central tendency and spread."
                ),
            }
        }


# ============================================================================
# Validity
# ============================================================================


class NormalityTestBlock(Block):
    type_id = "normality_test"
    title = "Normality Tests"
    category = CATEGORY_VALIDITY
    inputs: ClassVar[list[PortSpec]] = [PortSpec("dataframe", "dataframe")]
    outputs: ClassVar[list[PortSpec]] = [PortSpec("result", "result")]
    params_spec: ClassVar[list[ParamSpec]] = [
        ParamSpec("group_column", "Group column", "column_ref", source="dataframe"),
        ParamSpec("value_column", "Value column", "column_ref", source="dataframe"),
        ParamSpec("alpha", "Significance level (α)", "number", default=0.05),
        ParamSpec("decimals", "Decimal places", "integer", default=4),
    ]

    def execute(self, inputs, context):
        df = inputs.get("dataframe")
        gcol = self.params.get("group_column") or ""
        vcol = self.params.get("value_column") or ""
        if df is None or not gcol or not vcol or gcol not in df.columns or vcol not in df.columns:
            return {"result": None}

        groups = _numeric_groups(df, gcol, vcol)
        if not groups:
            return {"result": None}

        try:
            alpha = float(self.params.get("alpha", 0.05))
        except (TypeError, ValueError):
            alpha = 0.05
        decimals = int(self.params.get("decimals") or 4)

        rows = []
        for label, x in groups.items():
            row = {"Group": label, "n": int(len(x))}

            if len(x) >= 3:
                w, p = stats.shapiro(x)
                row["Shapiro-Wilk W"] = round(float(w), decimals)
                row["Shapiro-Wilk p"] = round(float(p), decimals)
            else:
                row["Shapiro-Wilk W"] = float("nan")
                row["Shapiro-Wilk p"] = float("nan")

            if len(x) >= 2 and float(x.std(ddof=1)) > 0:
                ks = stats.kstest(x, "norm", args=(float(x.mean()), float(x.std(ddof=1))))
                row["K-S statistic"] = round(float(ks.statistic), decimals)
                row["K-S p"] = round(float(ks.pvalue), decimals)
            else:
                row["K-S statistic"] = float("nan")
                row["K-S p"] = float("nan")

            if len(x) >= 8:
                k2, p_ag = stats.normaltest(x)
                row["D'Agostino K²"] = round(float(k2), decimals)
                row["D'Agostino p"] = round(float(p_ag), decimals)
            else:
                row["D'Agostino K²"] = float("nan")
                row["D'Agostino p"] = float("nan")

            if len(x) >= 8:
                ad = stats.anderson(x, dist="norm")
                idx5 = list(ad.significance_level).index(5.0) if 5.0 in list(ad.significance_level) else 2
                row["Anderson-Darling A²"] = round(float(ad.statistic), decimals)
                row["AD crit (5%)"] = round(float(ad.critical_values[idx5]), decimals)
            else:
                row["Anderson-Darling A²"] = float("nan")
                row["AD crit (5%)"] = float("nan")

            rows.append(row)

        table = pd.DataFrame(rows)
        verdicts = []
        for r in rows:
            sw_p = r.get("Shapiro-Wilk p")
            if sw_p is not None and not pd.isna(sw_p):
                tag = "consistent with normality" if sw_p >= alpha else "departs from normality"
                verdicts.append(f"{r['Group']} ({tag}, Shapiro-Wilk p = {sw_p:.4f})")

        interp = (
            f"Normality of '{vcol}' was assessed within each level of '{gcol}' using "
            f"Shapiro-Wilk, Kolmogorov-Smirnov, D'Agostino K², and Anderson-Darling tests. "
            "p-values below α indicate evidence against the null hypothesis of normality. "
        )
        if verdicts:
            interp += "Per-group summary: " + "; ".join(verdicts) + "."

        return {
            "result": {
                "tables": [{"name": "Normality tests by group", "data": table}],
                "interpretation": interp,
                "value_column": vcol,
                "group_column": gcol,
                "alpha": alpha,
            }
        }


class QQPlotBlock(Block):
    type_id = "qq_plot"
    title = "Q-Q Plot"
    category = CATEGORY_VALIDITY
    inputs: ClassVar[list[PortSpec]] = [PortSpec("dataframe", "dataframe")]
    outputs: ClassVar[list[PortSpec]] = [PortSpec("result", "result")]
    params_spec: ClassVar[list[ParamSpec]] = [
        ParamSpec("group_column", "Group column", "column_ref", source="dataframe"),
        ParamSpec("value_column", "Value column", "column_ref", source="dataframe"),
        ParamSpec(
            "output_size", "Plot size", "choice",
            default="medium", choices=["small", "medium", "large"],
        ),
    ]

    def execute(self, inputs, context):
        df = inputs.get("dataframe")
        gcol = self.params.get("group_column") or ""
        vcol = self.params.get("value_column") or ""
        if df is None or not vcol or vcol not in df.columns:
            return {"result": None}

        if gcol and gcol in df.columns:
            groups = _numeric_groups(df, gcol, vcol)
        else:
            values = pd.to_numeric(df[vcol], errors="coerce").dropna().to_numpy()
            groups = {vcol: values} if len(values) > 0 else {}

        if not groups:
            return {"result": None}

        width, height = _plot_size(self.params)
        n = len(groups)
        cols = min(n, 3)
        rows = (n + cols - 1) // cols
        fig, axes = plt.subplots(rows, cols, figsize=(width * cols / max(cols, 1), height * rows / max(rows, 1)), squeeze=False)

        for idx, (label, x) in enumerate(groups.items()):
            ax = axes[idx // cols][idx % cols]
            if len(x) >= 3:
                stats.probplot(x, dist="norm", plot=ax)
                ax.set_title(f"{label}  (n={len(x)})")
            else:
                ax.text(0.5, 0.5, f"{label}: n<3", ha="center", va="center")
                ax.set_axis_off()

        for j in range(len(groups), rows * cols):
            axes[j // cols][j % cols].set_axis_off()

        fig.tight_layout()
        png_b64 = _fig_to_base64(fig)

        interp = (
            f"Q-Q plot of '{vcol}'"
            + (f" by '{gcol}'." if gcol else ".")
            + " Points lying close to the reference line are consistent with a normal distribution; "
            "systematic curvature suggests departure from normality."
        )
        return {
            "result": {
                "plots": [{"name": "Q-Q plot", "png_base64": png_b64}],
                "interpretation": interp,
            }
        }


class VarianceTestBlock(Block):
    type_id = "variance_test"
    title = "Variance Tests"
    category = CATEGORY_VALIDITY
    inputs: ClassVar[list[PortSpec]] = [PortSpec("dataframe", "dataframe")]
    outputs: ClassVar[list[PortSpec]] = [PortSpec("result", "result")]
    params_spec: ClassVar[list[ParamSpec]] = [
        ParamSpec("group_column", "Group column", "column_ref", source="dataframe"),
        ParamSpec("value_column", "Value column", "column_ref", source="dataframe"),
        ParamSpec("alpha", "Significance level (α)", "number", default=0.05),
        ParamSpec("decimals", "Decimal places", "integer", default=4),
    ]

    def execute(self, inputs, context):
        df = inputs.get("dataframe")
        gcol = self.params.get("group_column") or ""
        vcol = self.params.get("value_column") or ""
        if df is None or not gcol or not vcol or gcol not in df.columns or vcol not in df.columns:
            return {"result": None}

        groups = _numeric_groups(df, gcol, vcol)
        if len(groups) < 2:
            return {"result": None}

        try:
            alpha = float(self.params.get("alpha", 0.05))
        except (TypeError, ValueError):
            alpha = 0.05
        decimals = int(self.params.get("decimals") or 4)

        arrays = list(groups.values())
        labels = list(groups.keys())

        levene = stats.levene(*arrays, center="median")
        bartlett = stats.bartlett(*arrays)

        rows = [
            {
                "Test": "Levene (median-centered)",
                "Statistic": round(float(levene.statistic), decimals),
                "p-value": round(float(levene.pvalue), decimals),
            },
            {
                "Test": "Bartlett",
                "Statistic": round(float(bartlett.statistic), decimals),
                "p-value": round(float(bartlett.pvalue), decimals),
            },
        ]

        if len(arrays) == 2:
            x1, x2 = arrays
            v1, v2 = float(np.var(x1, ddof=1)), float(np.var(x2, ddof=1))
            if v1 > 0 and v2 > 0:
                f_stat = v1 / v2
                df1, df2 = len(x1) - 1, len(x2) - 1
                p_f = 2 * min(stats.f.cdf(f_stat, df1, df2), 1 - stats.f.cdf(f_stat, df1, df2))
                rows.append({
                    "Test": f"F-test ({labels[0]} vs {labels[1]})",
                    "Statistic": round(float(f_stat), decimals),
                    "p-value": round(float(p_f), decimals),
                })

        table = pd.DataFrame(rows)
        levene_p = float(levene.pvalue)
        equal_var = levene_p >= alpha
        verdict = "consistent with equal variances" if equal_var else "indicates unequal variances"
        interp = (
            f"Levene's test on '{vcol}' across '{gcol}' returned p = {levene_p:.4f}, which {verdict} "
            f"at α = {alpha}. "
            f"{'Pool the variance for downstream tests.' if equal_var else 'Use a Welch-style correction for downstream tests.'}"
        )

        return {
            "result": {
                "tables": [{"name": "Variance tests", "data": table}],
                "interpretation": interp,
                "equal_var": equal_var,
                "alpha": alpha,
            }
        }


# ============================================================================
# Hypothesis tests
# ============================================================================


class TwoMeanTTestBlock(Block):
    type_id = "two_mean_ttest"
    title = "Two-Mean T-Test"
    category = CATEGORY_HYPOTHESIS
    inputs: ClassVar[list[PortSpec]] = [PortSpec("dataframe", "dataframe")]
    outputs: ClassVar[list[PortSpec]] = [PortSpec("result", "result")]
    params_spec: ClassVar[list[ParamSpec]] = [
        ParamSpec("group_column", "Group column", "column_ref", source="dataframe"),
        ParamSpec("value_column", "Value column", "column_ref", source="dataframe"),
        ParamSpec("equal_var", "Assume equal variance", "boolean", default=False),
        ParamSpec("alpha", "Significance level (α)", "number", default=0.05),
        ParamSpec("decimals", "Decimal places", "integer", default=4),
    ]

    def execute(self, inputs, context):
        df = inputs.get("dataframe")
        gcol = self.params.get("group_column") or ""
        vcol = self.params.get("value_column") or ""
        if df is None or not gcol or not vcol or gcol not in df.columns or vcol not in df.columns:
            return {"result": None}

        groups = _numeric_groups(df, gcol, vcol)
        if len(groups) < 2:
            return {"result": None}

        labels = list(groups.keys())
        g1, g2 = labels[0], labels[1]
        x1, x2 = groups[g1], groups[g2]
        if len(x1) < 2 or len(x2) < 2:
            return {"result": None}

        equal_var = bool(self.params.get("equal_var", False))
        try:
            alpha = float(self.params.get("alpha", 0.05))
        except (TypeError, ValueError):
            alpha = 0.05
        decimals = int(self.params.get("decimals") or 4)

        test = stats.ttest_ind(x1, x2, equal_var=equal_var)
        t_stat = float(test.statistic)
        p_val = float(test.pvalue)
        df_val = float(getattr(test, "df", float("nan")))

        n1, n2 = len(x1), len(x2)
        m1, m2 = float(x1.mean()), float(x2.mean())
        s1, s2 = float(x1.std(ddof=1)), float(x2.std(ddof=1))

        desc = pd.DataFrame([
            {"Group": g1, "n": n1, "Mean": round(m1, decimals), "SD": round(s1, decimals),
             "SE": round(s1 / np.sqrt(n1), decimals)},
            {"Group": g2, "n": n2, "Mean": round(m2, decimals), "SD": round(s2, decimals),
             "SE": round(s2 / np.sqrt(n2), decimals)},
        ])

        var_note = "equal variances assumed (pooled)" if equal_var else "Welch's correction (unequal variances)"
        results = pd.DataFrame([
            {"Statistic": "t", "Value": round(t_stat, decimals)},
            {"Statistic": "df", "Value": round(df_val, 2)},
            {"Statistic": "p-value", "Value": round(p_val, decimals)},
            {"Statistic": "α", "Value": alpha},
            {"Statistic": "Variance assumption", "Value": var_note},
        ])

        sig = p_val < alpha
        verdict = "statistically significant" if sig else "not statistically significant"
        interp = (
            f"An independent two-sample t-test compared '{vcol}' between groups "
            f"'{g1}' (M = {m1:.{decimals}f}, SD = {s1:.{decimals}f}, n = {n1}) and "
            f"'{g2}' (M = {m2:.{decimals}f}, SD = {s2:.{decimals}f}, n = {n2}) using {var_note}. "
            f"The difference was {verdict}, t({df_val:.2f}) = {t_stat:.{decimals}f}, p = {p_val:.{decimals}f}, "
            f"at α = {alpha}."
        )

        return {
            "result": {
                "tables": [
                    {"name": "Descriptive statistics", "data": desc},
                    {"name": "Test results", "data": results},
                ],
                "interpretation": interp,
                "t_statistic": t_stat,
                "p_value": p_val,
                "df": df_val,
                "n1": n1, "n2": n2,
                "mean1": m1, "mean2": m2,
                "std1": s1, "std2": s2,
                "group1": g1, "group2": g2,
                "value_column": vcol,
                "group_column": gcol,
                "equal_var": equal_var,
                "alpha": alpha,
            }
        }


# ============================================================================
# Post Hoc
# ============================================================================


class ConfidenceIntervalBlock(Block):
    type_id = "confidence_interval"
    title = "Confidence Interval"
    category = CATEGORY_POSTHOC
    inputs: ClassVar[list[PortSpec]] = [PortSpec("dataframe", "dataframe")]
    outputs: ClassVar[list[PortSpec]] = [PortSpec("result", "result")]
    params_spec: ClassVar[list[ParamSpec]] = [
        ParamSpec("group_column", "Group column", "column_ref", source="dataframe"),
        ParamSpec("value_column", "Value column", "column_ref", source="dataframe"),
        ParamSpec("confidence", "Confidence level", "number", default=0.95),
        ParamSpec("equal_var", "Assume equal variance", "boolean", default=False),
        ParamSpec("decimals", "Decimal places", "integer", default=4),
    ]

    def execute(self, inputs, context):
        df = inputs.get("dataframe")
        gcol = self.params.get("group_column") or ""
        vcol = self.params.get("value_column") or ""
        if df is None or not gcol or not vcol or gcol not in df.columns or vcol not in df.columns:
            return {"result": None}

        groups = _numeric_groups(df, gcol, vcol)
        if len(groups) < 2:
            return {"result": None}

        try:
            conf = float(self.params.get("confidence", 0.95))
        except (TypeError, ValueError):
            conf = 0.95
        if not 0 < conf < 1:
            conf = 0.95
        decimals = int(self.params.get("decimals") or 4)
        equal_var = bool(self.params.get("equal_var", False))

        labels = list(groups.keys())
        g1, g2 = labels[0], labels[1]
        x1, x2 = groups[g1], groups[g2]
        n1, n2 = len(x1), len(x2)
        m1, m2 = float(x1.mean()), float(x2.mean())
        s1, s2 = float(x1.std(ddof=1)), float(x2.std(ddof=1))

        per_group_rows = []
        for label, x in groups.items():
            n = len(x)
            if n < 2:
                continue
            mean = float(x.mean())
            se = float(x.std(ddof=1)) / np.sqrt(n)
            tcrit = stats.t.ppf(0.5 + conf / 2, df=n - 1)
            per_group_rows.append({
                "Group": label,
                "n": n,
                "Mean": round(mean, decimals),
                "SE": round(se, decimals),
                "Lower": round(mean - tcrit * se, decimals),
                "Upper": round(mean + tcrit * se, decimals),
            })
        per_group_table = pd.DataFrame(per_group_rows)

        diff = m1 - m2
        if equal_var:
            sp_sq = ((n1 - 1) * s1 ** 2 + (n2 - 1) * s2 ** 2) / (n1 + n2 - 2)
            se_diff = float(np.sqrt(sp_sq * (1 / n1 + 1 / n2)))
            df_diff = n1 + n2 - 2
        else:
            se_diff = float(np.sqrt(s1 ** 2 / n1 + s2 ** 2 / n2))
            num = (s1 ** 2 / n1 + s2 ** 2 / n2) ** 2
            den = (s1 ** 2 / n1) ** 2 / (n1 - 1) + (s2 ** 2 / n2) ** 2 / (n2 - 1)
            df_diff = num / den if den > 0 else float(n1 + n2 - 2)

        tcrit = stats.t.ppf(0.5 + conf / 2, df=df_diff)
        lo = diff - tcrit * se_diff
        hi = diff + tcrit * se_diff

        diff_table = pd.DataFrame([{
            "Comparison": f"{g1} − {g2}",
            "Difference": round(diff, decimals),
            "SE": round(se_diff, decimals),
            "df": round(float(df_diff), 2),
            f"Lower {int(conf * 100)}%": round(lo, decimals),
            f"Upper {int(conf * 100)}%": round(hi, decimals),
        }])

        contains_zero = lo <= 0 <= hi
        verdict = "contains 0, consistent with no difference" if contains_zero \
            else "excludes 0, consistent with a real difference"
        interp = (
            f"The {int(conf * 100)}% confidence interval for the difference in mean '{vcol}' "
            f"between '{g1}' and '{g2}' is [{lo:.{decimals}f}, {hi:.{decimals}f}]. "
            f"This interval {verdict} between the groups."
        )

        return {
            "result": {
                "tables": [
                    {"name": "Per-group confidence intervals", "data": per_group_table},
                    {"name": "Difference of means", "data": diff_table},
                ],
                "interpretation": interp,
                "confidence": conf,
                "lower": lo,
                "upper": hi,
                "difference": diff,
            }
        }


# ============================================================================
# Graphics
# ============================================================================


class BoxplotBlock(Block):
    type_id = "boxplot"
    title = "Boxplot"
    category = CATEGORY_GRAPHICS
    inputs: ClassVar[list[PortSpec]] = [PortSpec("dataframe", "dataframe")]
    outputs: ClassVar[list[PortSpec]] = [PortSpec("result", "result")]
    params_spec: ClassVar[list[ParamSpec]] = [
        ParamSpec("group_column", "Group column", "column_ref", source="dataframe"),
        ParamSpec("value_column", "Value column", "column_ref", source="dataframe"),
        ParamSpec(
            "output_size", "Plot size", "choice",
            default="medium", choices=["small", "medium", "large"],
        ),
    ]

    def execute(self, inputs, context):
        df = inputs.get("dataframe")
        gcol = self.params.get("group_column") or ""
        vcol = self.params.get("value_column") or ""
        if df is None or not vcol or vcol not in df.columns:
            return {"result": None}

        if gcol and gcol in df.columns:
            groups = _numeric_groups(df, gcol, vcol)
        else:
            values = pd.to_numeric(df[vcol], errors="coerce").dropna().to_numpy()
            groups = {vcol: values} if len(values) > 0 else {}
        if not groups:
            return {"result": None}

        width, height = _plot_size(self.params)
        fig, ax = plt.subplots(figsize=(width, height))
        ax.boxplot(list(groups.values()), labels=list(groups.keys()))
        ax.set_ylabel(vcol)
        ax.set_xlabel(gcol or "")
        ax.set_title(f"Boxplot of {vcol}" + (f" by {gcol}" if gcol else ""))
        fig.tight_layout()
        png_b64 = _fig_to_base64(fig)

        interp = (
            f"Boxplot showing the distribution of '{vcol}'"
            + (f" across levels of '{gcol}'." if gcol else ".")
            + " Boxes span the interquartile range; the centre line marks the median."
        )
        return {
            "result": {
                "plots": [{"name": "Boxplot", "png_base64": png_b64}],
                "interpretation": interp,
            }
        }


class HistogramBlock(Block):
    type_id = "histogram"
    title = "Histogram"
    category = CATEGORY_GRAPHICS
    inputs: ClassVar[list[PortSpec]] = [PortSpec("dataframe", "dataframe")]
    outputs: ClassVar[list[PortSpec]] = [PortSpec("result", "result")]
    params_spec: ClassVar[list[ParamSpec]] = [
        ParamSpec("group_column", "Group column (optional)", "column_ref", source="dataframe"),
        ParamSpec("value_column", "Value column", "column_ref", source="dataframe"),
        ParamSpec("bins", "Number of bins", "integer", default=20),
        ParamSpec(
            "output_size", "Plot size", "choice",
            default="medium", choices=["small", "medium", "large"],
        ),
    ]

    def execute(self, inputs, context):
        df = inputs.get("dataframe")
        gcol = self.params.get("group_column") or ""
        vcol = self.params.get("value_column") or ""
        if df is None or not vcol or vcol not in df.columns:
            return {"result": None}

        bins = int(self.params.get("bins") or 20)
        width, height = _plot_size(self.params)
        fig, ax = plt.subplots(figsize=(width, height))

        if gcol and gcol in df.columns:
            groups = _numeric_groups(df, gcol, vcol)
            for label, x in groups.items():
                ax.hist(x, bins=bins, alpha=0.5, label=str(label))
            ax.legend(title=gcol)
        else:
            values = pd.to_numeric(df[vcol], errors="coerce").dropna().to_numpy()
            ax.hist(values, bins=bins)

        ax.set_xlabel(vcol)
        ax.set_ylabel("Frequency")
        ax.set_title(f"Histogram of {vcol}" + (f" by {gcol}" if gcol else ""))
        fig.tight_layout()
        png_b64 = _fig_to_base64(fig)

        interp = (
            f"Histogram of '{vcol}' with {bins} bins"
            + (f", overlaid by '{gcol}'." if gcol else ".")
            + " Use the shape to assess skewness, modality, and outliers."
        )
        return {
            "result": {
                "plots": [{"name": "Histogram", "png_base64": png_b64}],
                "interpretation": interp,
            }
        }


class ConfidenceIntervalPlotBlock(Block):
    type_id = "ci_plot"
    title = "CI Plot"
    category = CATEGORY_GRAPHICS
    inputs: ClassVar[list[PortSpec]] = [PortSpec("dataframe", "dataframe")]
    outputs: ClassVar[list[PortSpec]] = [PortSpec("result", "result")]
    params_spec: ClassVar[list[ParamSpec]] = [
        ParamSpec("group_column", "Group column", "column_ref", source="dataframe"),
        ParamSpec("value_column", "Value column", "column_ref", source="dataframe"),
        ParamSpec("confidence", "Confidence level", "number", default=0.95),
        ParamSpec(
            "output_size", "Plot size", "choice",
            default="medium", choices=["small", "medium", "large"],
        ),
    ]

    def execute(self, inputs, context):
        df = inputs.get("dataframe")
        gcol = self.params.get("group_column") or ""
        vcol = self.params.get("value_column") or ""
        if df is None or not gcol or not vcol or gcol not in df.columns or vcol not in df.columns:
            return {"result": None}
        groups = _numeric_groups(df, gcol, vcol)
        if not groups:
            return {"result": None}

        try:
            conf = float(self.params.get("confidence", 0.95))
        except (TypeError, ValueError):
            conf = 0.95
        if not 0 < conf < 1:
            conf = 0.95

        labels: list[str] = []
        means: list[float] = []
        errs: list[float] = []
        for label, x in groups.items():
            n = len(x)
            if n < 2:
                continue
            m = float(x.mean())
            se = float(x.std(ddof=1)) / np.sqrt(n)
            tcrit = stats.t.ppf(0.5 + conf / 2, df=n - 1)
            labels.append(str(label))
            means.append(m)
            errs.append(tcrit * se)

        if not labels:
            return {"result": None}

        width, height = _plot_size(self.params)
        fig, ax = plt.subplots(figsize=(width, height))
        positions = list(range(len(labels)))
        ax.errorbar(positions, means, yerr=errs, fmt="o", capsize=6, color="#1f5fa8")
        ax.set_xticks(positions)
        ax.set_xticklabels(labels)
        ax.set_xlabel(gcol)
        ax.set_ylabel(vcol)
        ax.set_title(f"{int(conf * 100)}% CI for mean {vcol} by {gcol}")
        ax.grid(True, axis="y", alpha=0.3)
        fig.tight_layout()
        png_b64 = _fig_to_base64(fig)

        interp = (
            f"Group means with {int(conf * 100)}% confidence intervals for '{vcol}' "
            f"by '{gcol}'. Non-overlapping intervals suggest different population means."
        )
        return {
            "result": {
                "plots": [{"name": "CI plot", "png_base64": png_b64}],
                "interpretation": interp,
            }
        }


# ============================================================================
# Text
# ============================================================================


class ActionImpactBlock(Block):
    type_id = "action_impact"
    title = "Action & Impact"
    category = CATEGORY_TEXT
    inputs: ClassVar[list[PortSpec]] = []
    outputs: ClassVar[list[PortSpec]] = [PortSpec("result", "result")]
    params_spec: ClassVar[list[ParamSpec]] = [
        ParamSpec("action", "Action", "text", default=""),
        ParamSpec("impact", "Impact", "text", default=""),
    ]

    def execute(self, inputs, context):
        action = str(self.params.get("action") or "").strip()
        impact = str(self.params.get("impact") or "").strip()
        if not action and not impact:
            return {
                "result": {
                    "text_sections": [],
                    "interpretation": "",
                }
            }
        sections = []
        if action:
            sections.append({"heading": "Action", "body": action})
        if impact:
            sections.append({"heading": "Impact", "body": impact})
        return {
            "result": {
                "text_sections": sections,
                "interpretation": "",
            }
        }


# ============================================================================
# Registry & legacy aliases
# ============================================================================


_BLOCK_CLASSES: list[type[Block]] = [
    CSVLoaderBlock,
    DatasetVariableTableBlock,
    DatasetFrequencyTableBlock,
    DatasetNumericalStatsBlock,
    NormalityTestBlock,
    QQPlotBlock,
    VarianceTestBlock,
    TwoMeanTTestBlock,
    ConfidenceIntervalBlock,
    BoxplotBlock,
    HistogramBlock,
    ConfidenceIntervalPlotBlock,
    ActionImpactBlock,
]


BLOCK_REGISTRY: dict[str, type[Block]] = {cls.type_id: cls for cls in _BLOCK_CLASSES}


# Legacy type_id aliases — old saved reports keep loading.
BLOCK_REGISTRY["two_sample_ttest"] = TwoMeanTTestBlock
BLOCK_REGISTRY["report"] = TwoMeanTTestBlock


# Aliases referenced elsewhere by old name.
TwoSampleTTestBlock = TwoMeanTTestBlock
ReportBlock = TwoMeanTTestBlock


PALETTE_BLOCK_TYPE_IDS: dict[str, list[str]] = {
    CATEGORY_EXAMINATION: [
        DatasetVariableTableBlock.type_id,
        DatasetFrequencyTableBlock.type_id,
        DatasetNumericalStatsBlock.type_id,
    ],
    CATEGORY_VALIDITY: [
        NormalityTestBlock.type_id,
        QQPlotBlock.type_id,
        VarianceTestBlock.type_id,
    ],
    CATEGORY_HYPOTHESIS: [
        TwoMeanTTestBlock.type_id,
    ],
    CATEGORY_POSTHOC: [
        ConfidenceIntervalBlock.type_id,
    ],
    CATEGORY_GRAPHICS: [
        BoxplotBlock.type_id,
        HistogramBlock.type_id,
        ConfidenceIntervalPlotBlock.type_id,
    ],
    CATEGORY_TEXT: [
        ActionImpactBlock.type_id,
    ],
}
