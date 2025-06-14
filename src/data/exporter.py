"""
Export Facebook Ads data to various formats.
"""

import json
import os
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any, BinaryIO, Dict, List, Optional, Tuple, Union

import pandas as pd

from src.data.processor import DataProcessor
from src.utils.logger import get_logger

logger = get_logger(__name__)


class DataExporter:
    """
    Export data in various formats.
    """

    @staticmethod
    def export_to_csv(
        data: Union[List[Dict], pd.DataFrame], filename: Optional[str] = None
    ) -> Tuple[BytesIO, str]:
        """
        Export data to CSV format.

        Args:
            data: The data to export (list of dictionaries or DataFrame).
            filename: Optional filename (without extension).

        Returns:
            A tuple of (file buffer, filename).
        """
        # Convert to DataFrame if it's a list
        if isinstance(data, list):
            df = DataProcessor.convert_to_dataframe(data)
        else:
            df = data

        # Generate filename if not provided
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"facebook_ads_export_{timestamp}.csv"
        elif not filename.endswith(".csv"):
            filename = f"{filename}.csv"

        # Create buffer
        buffer = BytesIO()

        # Export DataFrame to CSV
        df.to_csv(
            buffer, index=False, encoding="utf-8-sig"
        )  # utf-8-sig for Excel compatibility

        # Reset buffer position to start
        buffer.seek(0)

        return buffer, filename

    @staticmethod
    def export_to_json(
        data: Union[List[Dict], pd.DataFrame], filename: Optional[str] = None
    ) -> Tuple[BytesIO, str]:
        """
        Export data to JSON format.

        Args:
            data: The data to export (list of dictionaries or DataFrame).
            filename: Optional filename (without extension).

        Returns:
            A tuple of (file buffer, filename).
        """
        # Convert to list if it's a DataFrame
        if isinstance(data, pd.DataFrame):
            data_list = data.to_dict("records")
        else:
            data_list = data

        # Generate filename if not provided
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"facebook_ads_export_{timestamp}.json"
        elif not filename.endswith(".json"):
            filename = f"{filename}.json"

        # Create buffer
        buffer = BytesIO()

        # Export data to JSON
        json_data = json.dumps(data_list, ensure_ascii=False, indent=2)
        buffer.write(json_data.encode("utf-8"))

        # Reset buffer position to start
        buffer.seek(0)

        return buffer, filename

    @staticmethod
    def export_to_excel(
        data: Union[
            List[Dict], pd.DataFrame, Dict[str, Union[List[Dict], pd.DataFrame]]
        ],
        filename: Optional[str] = None,
    ) -> Tuple[BytesIO, str]:
        """
        Export data to Excel format.

        Args:
            data: The data to export (list of dictionaries, DataFrame, or dict of sheet_name -> data).
            filename: Optional filename (without extension).

        Returns:
            A tuple of (file buffer, filename).
        """
        # Generate filename if not provided
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"facebook_ads_export_{timestamp}.xlsx"
        elif not filename.endswith(".xlsx"):
            filename = f"{filename}.xlsx"

        # Create buffer
        buffer = BytesIO()

        # Create Excel writer
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            if isinstance(data, dict):
                # Multiple sheets
                for sheet_name, sheet_data in data.items():
                    # Convert to DataFrame if necessary
                    if isinstance(sheet_data, list):
                        df = DataProcessor.convert_to_dataframe(sheet_data)
                    else:
                        df = sheet_data

                    # Write sheet
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
            else:
                # Single sheet
                if isinstance(data, list):
                    df = DataProcessor.convert_to_dataframe(data)
                else:
                    df = data

                # Write sheet
                df.to_excel(writer, sheet_name="Data", index=False)

        # Reset buffer position to start
        buffer.seek(0)

        return buffer, filename

    @staticmethod
    def export_data(
        data: Union[
            List[Dict], pd.DataFrame, Dict[str, Union[List[Dict], pd.DataFrame]]
        ],
        format: str = "csv",
        filename: Optional[str] = None,
    ) -> Tuple[BytesIO, str]:
        """
        Export data to the specified format.

        Args:
            data: The data to export.
            format: The export format ('csv', 'json', or 'excel').
            filename: Optional filename (without extension).

        Returns:
            A tuple of (file buffer, filename).
        """
        format = format.lower()

        if format == "csv":
            return DataExporter.export_to_csv(data, filename)
        elif format == "json":
            return DataExporter.export_to_json(data, filename)
        elif format == "excel":
            return DataExporter.export_to_excel(data, filename)
        else:
            raise ValueError(f"Unsupported export format: {format}")

    @staticmethod
    def save_to_file(buffer: BytesIO, filename: str, directory: str = "exports") -> str:
        """
        Save a buffer to a file.

        Args:
            buffer: The file buffer.
            filename: The filename.
            directory: The directory to save to.

        Returns:
            The path to the saved file.
        """
        # Create directory if it doesn't exist
        os.makedirs(directory, exist_ok=True)

        # Create path
        path = os.path.join(directory, filename)

        # Save file
        with open(path, "wb") as f:
            f.write(buffer.getvalue())

        return path
