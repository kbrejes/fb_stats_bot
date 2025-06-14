"""
Utility functions for exporting data in various formats.
"""

import csv
import json
import os
import tempfile
from typing import Any, Dict, List, Optional

import pandas as pd

from src.utils.logger import get_logger

logger = get_logger(__name__)


def export_data_to_csv(
    data: List[Dict[str, Any]], filename: Optional[str] = None
) -> str:
    """
    Export data to CSV format.

    Args:
        data: The data to export.
        filename: The filename (without extension).

    Returns:
        The path to the exported file.
    """
    if not filename:
        filename = "facebook_ads_export"

    # Create a temporary file
    fd, file_path = tempfile.mkstemp(suffix=".csv", prefix=f"{filename}_")
    os.close(fd)

    try:
        if not data:
            # Create an empty CSV file
            with open(file_path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["No data to export"])
            return file_path

        # Extract keys from all dictionaries to make sure we catch all possible columns
        all_keys = set()
        for item in data:
            all_keys.update(item.keys())

        # Sort keys for consistent column order
        fieldnames = sorted(all_keys)

        # Write to CSV
        with open(file_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)

        return file_path
    except Exception as e:
        logger.error(f"Error exporting to CSV: {str(e)}")
        # Delete the file if there was an error
        try:
            os.remove(file_path)
        except:
            pass
        raise


def export_data_to_json(
    data: List[Dict[str, Any]], filename: Optional[str] = None
) -> str:
    """
    Export data to JSON format.

    Args:
        data: The data to export.
        filename: The filename (without extension).

    Returns:
        The path to the exported file.
    """
    if not filename:
        filename = "facebook_ads_export"

    # Create a temporary file
    fd, file_path = tempfile.mkstemp(suffix=".json", prefix=f"{filename}_")
    os.close(fd)

    try:
        # Write to JSON
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return file_path
    except Exception as e:
        logger.error(f"Error exporting to JSON: {str(e)}")
        # Delete the file if there was an error
        try:
            os.remove(file_path)
        except:
            pass
        raise


def export_data_to_excel(
    data: List[Dict[str, Any]], filename: Optional[str] = None
) -> str:
    """
    Export data to Excel format.

    Args:
        data: The data to export.
        filename: The filename (without extension).

    Returns:
        The path to the exported file.
    """
    if not filename:
        filename = "facebook_ads_export"

    # Create a temporary file
    fd, file_path = tempfile.mkstemp(suffix=".xlsx", prefix=f"{filename}_")
    os.close(fd)

    try:
        if not data:
            # Create an empty DataFrame
            df = pd.DataFrame({"No data to export": []})
        else:
            # Convert to DataFrame
            df = pd.DataFrame(data)

        # Write to Excel
        with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Facebook Ads Data")

        return file_path
    except Exception as e:
        logger.error(f"Error exporting to Excel: {str(e)}")
        # Delete the file if there was an error
        try:
            os.remove(file_path)
        except:
            pass
        raise
