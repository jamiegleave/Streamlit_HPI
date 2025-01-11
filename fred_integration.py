# fred_integration.py

import os
from typing import Optional
import pandas as pd
from datetime import datetime
from fredapi import Fred
from dotenv import load_dotenv
import requests
from io import StringIO

class FredAPI:
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize FRED API client using official fredapi package
        
        Args:
            api_key (str, optional): FRED API key. If not provided, will look for FRED_API_KEY in environment
        """
        load_dotenv()
        self.api_key = api_key or os.getenv('FRED_API_KEY')
        if not self.api_key:
            raise ValueError("FRED API key not found. Set FRED_API_KEY in environment or pass to constructor.")
        
        self.fred = Fred(api_key=self.api_key)
        
    def get_series(self, series_id: str, start_year: int, end_year: int) -> pd.Series:
        """
        Fetch data series from FRED
        
        Args:
            series_id (str): FRED series identifier
            start_year (int): Start year for data
            end_year (int): End year for data
            
        Returns:
            pd.Series: Time series data with year index
        """
        # Get series with annual frequency
        series = self.fred.get_series(
            series_id,
            observation_start=f"{start_year}-01-01",
            observation_end=f"{end_year}-12-31",
            frequency='m'
        )
        
        # Resample to annual frequency
        series = series.resample('YE').mean()

        # Convert DatetimeIndex to year
        series.index = series.index.year
        
        return series

    def get_series_info(self, series_id: str) -> dict:
        """
        Get metadata about a FRED series
        
        Args:
            series_id (str): FRED series identifier
            
        Returns:
            dict: Series metadata
        """
        return self.fred.get_series_info(series_id)

class UKEconomicData:
    """Handler for UK economic data from FRED and ONS"""
    
    SERIES = {
        'CPI': 'GBRCPIALLMINMEI',  # UK CPI All Items
        'GBP_USD': 'DEXUSUK',      # USD to GBP exchange rate
    }
    
    def __init__(self, fred_api: FredAPI):
        """
        Initialize with FRED API client
        
        Args:
            fred_api (FredAPI): Initialized FRED API client
        """
        self.fred_api = fred_api
        
    def get_uk_cpi(self, start_year: int, end_year: int, base_year: Optional[int] = None) -> pd.Series:
        """
        Get UK CPI data and calculate adjustment factors
        
        Args:
            start_year (int): Start year for data
            end_year (int): End year for data
            base_year (int, optional): Base year for adjustment (defaults to latest year)
            
        Returns:
            pd.Series: CPI adjustment factors indexed by year
        """
        cpi_data = self.fred_api.get_series(self.SERIES['CPI'], start_year, end_year)
        
        # Get base CPI value
        if base_year is None:
            base_cpi = cpi_data.iloc[-1]  # Use latest year
        else:
            if base_year not in cpi_data.index:
                raise ValueError(f"Base year {base_year} not found in CPI data")
            base_cpi = cpi_data[base_year]
        
        # Calculate adjustment factors
        adjustment_factors = 1 / (cpi_data / base_cpi)
        
        return adjustment_factors    
    def get_gbp_usd(self, start_year: int, end_year: int) -> pd.Series:
        """
        Get GBP/USD exchange rate data
        
        Args:
            start_year (int): Start year for data
            end_year (int): End year for data
            
        Returns:
            pd.Series: Exchange rates indexed by year
        """
        return self.fred_api.get_series(self.SERIES['GBP_USD'], start_year, end_year)

    def get_uk_rpi(self, start_year: int, end_year: int, base_year: Optional[int] = None) -> pd.Series:
        """
        Get UK RPI data and calculate adjustment factors by downloading ONS CSV data
        
        Args:
            start_year (int): Start year for data
            end_year (int): End year for data
            base_year (int, optional): Base year for adjustment (defaults to latest year)
            
        Returns:
            pd.Series: RPI adjustment factors indexed by year, matching CPI data structure
        """
        # Download CSV from ONS website
        url = "https://www.ons.gov.uk/generator?format=csv&uri=/economy/inflationandpriceindices/timeseries/chaw/mm23"
        response = requests.get(url)
        if response.status_code != 200:
            raise ValueError(f"Failed to download RPI data: HTTP {response.status_code}")
        
        # Read the CSV data
        df = pd.read_csv(StringIO(response.text), skiprows=7)  # Skip header rows
        
        # Convert data to numeric, handling the date column
        df.columns = ['date', 'value']
        df['value'] = pd.to_numeric(df['value'], errors='coerce')
        
        # Filter for monthly data using regex pattern "YYYY MMM"
        monthly_pattern = r'^\d{4}\s[A-Z]{3}$'
        df = df.loc[df['date'].str.match(monthly_pattern, na=False)].copy()
        
        # Extract year from date string
        df['year'] = df['date'].str.extract(r'(\d{4})').astype(int)
        
        # Group by year and take the average
        rpi_data = df.groupby('year')['value'].mean()
        
        # Ensure index is integer type to match CPI data
        rpi_data.index = rpi_data.index.astype(int)
        
        # Filter to requested year range
        rpi_data = rpi_data[(rpi_data.index >= start_year) & (rpi_data.index <= end_year)]
        
        if rpi_data.empty:
            raise ValueError(f"No RPI data found for year range {start_year}-{end_year}")
        
        # Get base RPI value
        if base_year is None:
            base_rpi = rpi_data.iloc[-1]  # Use latest year
        else:
            if base_year not in rpi_data.index:
                raise ValueError(f"Base year {base_year} not found in RPI data")
            base_rpi = rpi_data[base_year]
        
        # Calculate adjustment factors
        adjustment_factors = 1 / (rpi_data / base_rpi)
        
        # Ensure the output is a pandas Series with year index
        adjustment_factors = pd.Series(
            adjustment_factors.values,
            index=adjustment_factors.index,
            name='RPI_adjustment'
        )
        
        return adjustment_factors
