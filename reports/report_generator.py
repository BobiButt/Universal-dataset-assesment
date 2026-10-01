"""
Markdown Assessment Report Builder (Steps 1 - 14)
"""

import os
from typing import Dict, Any

class ReportGenerator:
    def __init__(self, inventory: Dict[str, Any], quality: Dict[str, Any], label_audit: Dict[str, Any], model_results: Dict[str, Any]):
        self.inventory = inventory
        self.quality = quality
        self.label_audit = label_audit
        self.model_results = model_results

    def generate_markdown_report(self, output_path: str = "reports/dataset_report.md") -> str:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        md_content = f"""# Universal Dataset Assessment & AI Model Recommendation Report

## 1. Dataset Inventory
- **Data Path:** `{self.inventory.get('source_path')}`
- **Structure Type:** `{self.inventory.get('structure_type').upper()}`
- **Total Files Scanned:** `{self.inventory.get('total_files')}`
- **Total Size:** `{self.inventory.get('total_size_mb')} MB`
- **Detected Modalities:** `{', '.join(self.inventory.get('detected_modalities', []))}`

## 2. Data Quality Summary
- **Total Rows:** `{self.quality.get('total_rows', 'N/A')}`
- **Total Columns:** `{self.quality.get('total_columns', 'N/A')}`
- **Empty Rows:** `{self.quality.get('empty_rows', 0)}`
- **Missing Value Profile:**
```json
{self.quality.get('missing_counts', {})}
```

## 3. Label Audit
- **Target Column:** `{self.label_audit.get('target_column', 'N/A')}`
- **Task Type:** `{self.label_audit.get('inferred_task_type', 'N/A')}`
- **Missing Labels:** `{self.label_audit.get('missing_labels', 'N/A')}`
- **Imbalanced:** `{self.label_audit.get('is_imbalanced', False)}`

## 4. Model Results
- **Model:** `{self.model_results.get('model', 'N/A')}`
- **Metric:** `{self.model_results.get('metric', 'N/A')}`
- **Score:** `{self.model_results.get('score', 'N/A')}`
"""

        with open(output_path, "w", encoding="utf-8") as report_file:
            report_file.write(md_content)

        return output_path