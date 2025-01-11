# database.py

import os
from typing import List, Dict, Any, Optional
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine

class UKHousingDB:
    def __init__(self, config: Optional[Dict[str, str]] = None):
        """
        Initialize database connection with either config dict or environment variables.
        
        Args:
            config (dict, optional): Database configuration with host, database, user, password
        """
        load_dotenv()
        
        self.db_config = config or {
            'host': os.getenv('DB_HOST', 'localhost'),
            'database': os.getenv('DB_NAME', 'LandRegData'),
            'port': os.getenv('DB_PORT', 'port'),
            'user': os.getenv('DB_USER', 'root'),
            'password': os.getenv('DB_PASSWORD', 'password')
        }

        self.sql_alchemy_config = f"postgresql://{self.db_config['user']}:{self.db_config['password']}@{self.db_config['host']}:{self.db_config['port']}/{self.db_config['database']}"
        
    def get_connection(self):
        """Create and return a database connection."""
        return create_engine(self.sql_alchemy_config)
    
    def execute_query(self, query: str, params: Optional[tuple] = None) -> pd.DataFrame:
        """
        Execute SQL query and return results as pandas DataFrame.
        
        Args:
            query (str): SQL query to execute
            params (tuple, optional): Query parameters for parameterized queries
            
        Returns:
            pd.DataFrame: Query results
        """
        try:
            return pd.read_sql_query(query, con=self.get_connection(), params=params)
        except Exception as e:
            print(f"Error executing query: {e}")
            raise

    def get_regional_price_quantiles(self, start_year: int, end_year: int) -> pd.DataFrame:
        """
        Get regional house price quantiles for specified year range.
        
        Args:
            start_year (int): Start year for analysis
            end_year (int): End year for analysis
            
        Returns:
            pd.DataFrame: Regional price quantiles
        """
        query = """
        SELECT 
            EXTRACT(YEAR FROM date) as year,
            region,
            percentile_disc(0.25) WITHIN GROUP (order by price_gbp) as q25,
            percentile_disc(0.50) WITHIN GROUP (order by price_gbp) as median,
            percentile_disc(0.75) WITHIN GROUP (order by price_gbp) as q75
        FROM nov24pricepaidcomplete 
        INNER JOIN county_region 
            ON nov24pricepaidcomplete.county = county_region.county 
        WHERE EXTRACT(YEAR FROM date) BETWEEN %s AND %s
        GROUP BY 
            EXTRACT(YEAR FROM date),
            region
        ORDER BY 
            year, region
        """
        return self.execute_query(query, (start_year, end_year))

    def get_regional_prices(self, regions: List[str], start_year: int, end_year: int) -> pd.DataFrame:
        """
        Get median house prices for specified regions and year range.
        
        Args:
            regions (List[str]): List of regions to analyze
            start_year (int): Start year for analysis
            end_year (int): End year for analysis
            
        Returns:
            pd.DataFrame: Regional median prices
        """
        query = """
        SELECT 
            EXTRACT(YEAR FROM date) as year,
            region,
            percentile_disc(0.50) WITHIN GROUP (order by price_gbp) as median_price
        FROM nov24pricepaidcomplete 
        INNER JOIN county_region 
            ON nov24pricepaidcomplete.county = county_region.county 
        WHERE 
            EXTRACT(YEAR FROM date) BETWEEN %s AND %s
            AND region = ANY(%s)
        GROUP BY 
            EXTRACT(YEAR FROM date),
            region
        ORDER BY 
            year, region
        """
        return self.execute_query(query, (start_year, end_year, regions))

    def get_regional_iqr(self, regions: List[str], start_year: int, end_year: int) -> pd.DataFrame:
        """
        Get interquartile range for house prices by region.
        
        Args:
            regions (List[str]): List of regions to analyze
            start_year (int): Start year for analysis
            end_year (int): End year for analysis
            
        Returns:
            pd.DataFrame: Regional IQR values
        """
        query = """
        SELECT 
            EXTRACT(YEAR FROM date) as year,
            region,
            percentile_disc(0.75) WITHIN GROUP (order by price_gbp) - 
            percentile_disc(0.25) WITHIN GROUP (order by price_gbp) as iqr
        FROM nov24pricepaidcomplete 
        INNER JOIN county_region 
            ON nov24pricepaidcomplete.county = county_region.county 
        WHERE 
            EXTRACT(YEAR FROM date) BETWEEN %s AND %s
            AND region = ANY(%s)
        GROUP BY 
            EXTRACT(YEAR FROM date),
            region
        ORDER BY 
            year, region
        """
        return self.execute_query(query, (start_year, end_year, regions))

    def get_available_regions(self) -> List[str]:
        """Get list of all available regions in the database."""
        query = """
        SELECT DISTINCT region 
        FROM county_region 
        ORDER BY region
        """
        df = self.execute_query(query)
        return df['region'].tolist()

    def get_year_range(self) -> tuple:
        """Get the minimum and maximum years available in the database."""
        query = """
        SELECT 
            EXTRACT(YEAR FROM MIN(date)) as min_year,
            EXTRACT(YEAR FROM MAX(date)) as max_year
        FROM nov24pricepaidcomplete
        """
        df = self.execute_query(query)
        return int(df['min_year'].iloc[0]), int(df['max_year'].iloc[0])
    
    def get_year_range(self) -> tuple:
        """Get the minimum and maximum years available in the database."""
        query = """
        SELECT 
            EXTRACT(YEAR FROM MIN(date)) as min_year,
            EXTRACT(YEAR FROM MAX(date)) as max_year
        FROM nov24pricepaidcomplete
        """
        df = self.execute_query(query)
        return int(df['min_year'].iloc[0]), int(df['max_year'].iloc[0])
        
    def get_transaction_volumes(
        self,
        start_year: int,
        end_year: int,
        regions: Optional[List[str]] = None,
        by_quarter: bool = False,
        is_leasehold_flat: bool = False
    ) -> pd.DataFrame:
        """
        Get transaction volumes by region for specified year range, optionally broken down by quarter.
        
        Args:
            start_year (int): Start year for analysis
            end_year (int): End year for analysis
            regions (List[str], optional): List of regions to filter by. If None, includes all regions.
            by_quarter (bool): If True, break down volumes by quarter
            is_leasehold_flat (bool): If True, filter for leasehold flats only
            
        Returns:
            pd.DataFrame: DataFrame with columns for year, [quarter if by_quarter], region, and transaction_count
        """
        # Build WHERE clause conditions and parameters
        conditions = ["EXTRACT(YEAR FROM date) BETWEEN %s AND %s"]
        params = [start_year, end_year]
        
        if regions:
            conditions.append("region = ANY(%s)")
            params.append(regions)
            
        if is_leasehold_flat:
            conditions.extend([
                "property_type = 'F'",
                "tenure = 'L'"
            ])
            
        where_clause = " AND ".join(conditions)
        
        if by_quarter:
            query = f"""
            SELECT 
                EXTRACT(YEAR FROM date) as year,
                EXTRACT(QUARTER FROM date) as quarter,
                region,
                COUNT(*) as transaction_count
            FROM nov24pricepaidcomplete 
            INNER JOIN county_region 
                ON nov24pricepaidcomplete.county = county_region.county 
            WHERE {where_clause}
            GROUP BY 
                EXTRACT(YEAR FROM date),
                EXTRACT(QUARTER FROM date),
                region
            ORDER BY 
                year, quarter, region
            """
        else:
            query = f"""
            SELECT 
                EXTRACT(YEAR FROM date) as year,
                region,
                COUNT(*) as transaction_count
            FROM nov24pricepaidcomplete 
            INNER JOIN county_region 
                ON nov24pricepaidcomplete.county = county_region.county 
            WHERE {where_clause}
            GROUP BY 
                EXTRACT(YEAR FROM date),
                region
            ORDER BY 
                year, region
            """
            
        return self.execute_query(query, tuple(params))
    
    def compare_monthly_releases(self, year: int) -> pd.DataFrame:
        """
        Compare transaction counts between consecutive monthly data releases for a specific year.
        Compares current release (nov24pricepaidcomplete) with previous release (oct24pricepaidcomplete).
        
        Args:
            year (int): Year to analyze
            
        Returns:
            pd.DataFrame: DataFrame with columns for region, month, current_count, previous_count, and count_difference
        """
        query = """
        WITH current_counts AS (
            SELECT 
                EXTRACT(MONTH FROM date) as month,
                COUNT(*) as current_count
            FROM nov24pricepaidcomplete n
            INNER JOIN county_region c
                ON n.county = c.county
            WHERE EXTRACT(YEAR FROM date) = %s
            GROUP BY EXTRACT(MONTH FROM date)
        ),
        previous_counts AS (
            SELECT 
                EXTRACT(MONTH FROM date) as month,
                COUNT(*) as previous_count
            FROM oct24pricepaidcomplete o
            INNER JOIN county_region c
                ON o.county = c.county
            WHERE EXTRACT(YEAR FROM date) = %s
            GROUP BY EXTRACT(MONTH FROM date)
        )
        SELECT
            c.month,
            c.current_count,
            COALESCE(p.previous_count, 0) as previous_count,
            c.current_count - COALESCE(p.previous_count, 0) as count_difference,
            CASE 
                WHEN p.previous_count > 0 
                THEN ROUND(((c.current_count - p.previous_count)::float / p.previous_count * 100)::numeric, 1)
                ELSE NULL 
            END as percentage_change
        FROM current_counts c
        LEFT JOIN previous_counts p
            ON c.month = p.month 
        ORDER BY c.month
        """
        return self.execute_query(query, (year, year))

    def volume_by_price(
        self, 
        interval: int, 
        price_limit: int, 
        start_year: int, 
        end_year: int,
        regions: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        Get transaction volumes by price band for specified year range and regions.
        
        Args:
            interval (int): Price band interval
            price_limit (int): Price band limit    
            start_year (int): Start year for analysis
            end_year (int): End year for analysis
            regions (List[str], optional): List of regions to filter by. If None, includes all regions.
            
        Returns:
            pd.DataFrame: DataFrame with columns for year, quarter, region, price_band, and transaction_count
        """
        price_range = range(0, price_limit, interval)
        bound = lambda x: f"{x}K" if x < 1000 else f"{x/1000}M"
        bands = '\n'.join([f"WHEN price_gbp <= {(j+interval)*1000} THEN '{bound(j)}-{bound(j+interval)}'" for j in price_range])
        bands = bands + '\n' + f"ELSE 'Over {bound(price_range[-1]+interval)}'"

        # Build WHERE clause conditions and parameters
        conditions = ["EXTRACT(YEAR FROM date) BETWEEN %s AND %s"]
        params = [start_year, end_year]
        
        if regions:
            conditions.append("region = ANY(%s)")
            params.append(regions)
            
        where_clause = " AND ".join(conditions)

        query = f"""
            WITH price_bands AS (
            SELECT 
                CASE 
                {bands}
                END AS price_band,
                EXTRACT(YEAR FROM date) as year,
                EXTRACT(QUARTER FROM date) as quarter,
                region
            FROM nov24pricepaidcomplete 
            INNER JOIN county_region 
                ON nov24pricepaidcomplete.county = county_region.county
            WHERE {where_clause}
            )
            SELECT 
            year,
            quarter,
            region,
            price_band,
            COUNT(*) as transaction_count
            FROM price_bands
            GROUP BY 
            year,
            quarter,
            region,
            price_band
            ORDER BY 
            year, 
            quarter, 
            region,
            price_band
            """

        return self.execute_query(query, tuple(params))