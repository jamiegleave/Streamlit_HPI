# UK Housing Market Dashboard

## 1. Application Concept
A Streamlit dashboard that analyzes UK house prices across regions, providing both nominal and real price trends, distribution analysis, and regional comparisons. The application will connect to a PostgreSQL database containing Land Registry Price Paid data.

## 2. UX/UI Requirements

### Main Dashboard Layout
- Sidebar:
  - Date range selector
  - Region selector (multi-select)
  - Price analysis type (Nominal/Real/USD)
  - Chart type selector

### Main Content Tabs
1. **Price Trends**
   - Median price evolution by region
   - Price indices (base year adjustable)
   - CPI-adjusted real prices
   - USD-adjusted prices

2. **Price Distribution**
   - Regional IQR analysis
   - Price quantiles (25th, 50th, 75th percentiles)
   - Distribution visualizations

3. **Regional Analysis**
   - Region-to-region comparisons
   - Regional price disparities
   - Time-series analysis

## 3. Key Features (Priority Order)

### Phase 1 - Core Analysis
1. PostgreSQL database connection
2. Basic price trend visualization
3. Regional filtering
4. Nominal price analysis

### Phase 2 - Advanced Analytics
5. CPI adjustment integration
6. USD conversion
7. Statistical analysis (IQR, quantiles)
8. Custom date range analysis

### Phase 3 - Enhanced Features
9. Data export capabilities
10. Custom chart configurations
11. Trend analysis and forecasting
12. Regional heat maps

## 4. Technical Stack

### Required Libraries
```python
requirements.txt:

streamlit>=1.28.0
pandas>=2.0.0
plotly>=5.18.0
numpy>=1.24.0
psycopg2-binary>=2.9.9
python-dotenv>=1.0.0
scipy>=1.11.0
```

### Core Components
- **Frontend**: Streamlit
- **Data Processing**: Pandas, NumPy
- **Database**: PostgreSQL, psycopg2
- **Visualization**: Plotly
- **Statistical Analysis**: SciPy

## 5. Data Structure & Implementation

### Database Schema
1. **Price Paid Table (nov24pricepaidcomplete)**
   ```sql
   - transaction_id (TEXT)
   - price_gbp (NUMERIC)
   - date (DATE)
   - postcode (TEXT)
   - property_type (CHAR)
   - new_build (CHAR)
   - tenure (CHAR)
   - county (TEXT)
   ```

2. **Region Mapping (county_region)**
   ```sql
   - county (TEXT)
   - region (TEXT)
   ```

### Key SQL Queries
```sql
# Regional Price Analysis
SELECT 
    EXTRACT(YEAR FROM date),
    region,
    percentile_disc(0.25) WITHIN GROUP (order by price_gbp),
    percentile_disc(0.50) WITHIN GROUP (order by price_gbp),
    percentile_disc(0.75) WITHIN GROUP (order by price_gbp)
FROM nov24pricepaidcomplete 
INNER JOIN county_region 
    ON nov24pricepaidcomplete.county=county_region.county 
GROUP BY 
    EXTRACT(YEAR FROM date), 
    region
```

### File Structure
```
uk_housing_dashboard/
├── app.py
├── requirements.txt
├── .env
├── src/
│   ├── database.py
│   ├── analysis.py
│   └── visualization.py
├── config/
│   └── db_config.py
└── utils/
    └── helpers.py
```

### External Data Integration
1. **FRED API Integration**
   - GBRCPIALLMINMEI (UK CPI)
   - DEXUSUK (GBP/USD Exchange Rate)
   - Handle API authentication via environment variables

### Key Visualizations
1. **Trend Lines**
   - Region-specific price trends
   - Indexed growth rates
   - Real vs nominal comparison

2. **Distribution Analysis**
   - IQR by region
   - Year-over-year changes
   - Regional price spreads
