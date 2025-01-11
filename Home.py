# app.py

import streamlit as st
import plotly.express as px
import pandas as pd
from database import UKHousingDB
from fred_integration import FredAPI, UKEconomicData

# Initialize database and FRED API
@st.cache_resource
def init_services():
    db = UKHousingDB()
    fred_api = FredAPI()
    _econ_data = UKEconomicData(fred_api)
    return db, _econ_data

# Cache data loading functions
@st.cache_data
def load_regional_prices(_db, regions, start_year, end_year):
    return _db.get_regional_prices(regions, start_year, end_year)

@st.cache_data
def load_economic_data(_econ_data, start_year, end_year):
    """Load CPI, RPI and FX data"""
    return {
        'cpi': _econ_data.get_uk_cpi(start_year, end_year),
        'rpi': _econ_data.get_uk_rpi(start_year, end_year),
        'fx': _econ_data.get_gbp_usd(start_year, end_year),
    }

def process_price_data(df_prices, _econ_data=None, analysis_type="Nominal", index_to_first_year=True):
    """Process price data according to selected options"""
    df_pivot = df_prices.pivot(index='year', columns='region', values='median_price')
    
    if _econ_data and analysis_type != "Nominal":
        if analysis_type == "Real (CPI Adjusted)":
            df_pivot = df_pivot.mul(_econ_data['cpi'], axis=0)
        elif analysis_type == "Real (RPI Adjusted)":
            df_pivot = df_pivot.mul(_econ_data['rpi'], axis=0)
        elif analysis_type == "USD (Nominal)":
            df_pivot = df_pivot.mul(_econ_data['fx'], axis=0)
    
    if index_to_first_year:
        df_pivot = df_pivot.apply(lambda x: x/x.iloc[0])
    
    return df_pivot

def get_price_label(analysis_type, index_to_first_year):
    """Get appropriate y-axis label based on analysis type"""
    if index_to_first_year:
        return "Price Index (First Year = 1)"
    
    base_labels = {
        "Nominal": "Price (GBP)",
        "Real (CPI Adjusted)": "Price (Real GBP, CPI Adjusted)",
        "Real (RPI Adjusted)": "Price (Real GBP, RPI Adjusted)",
        "USD (Nominal)": "Price (USD)"
    }
    return base_labels.get(analysis_type, "Price")

def main():
    st.set_page_config(
        page_title="UK Housing Market Dashboard",
        page_icon="🏠",
        layout="wide"
    )

    st.title("UK Housing Market Dashboard")

    # Initialize services
    try:
        db, _econ_data = init_services()
    except ValueError as e:
        st.error(f"Error initializing services: {str(e)}")
        return
    
    # Sidebar controls
    st.sidebar.header("Controls")
    
    # Get available regions and years
    available_regions = db.get_available_regions()
    min_year, max_year = db.get_year_range()
    
    # Region selection
    default_regions = ['London', 'South East', 'East Midlands', 'North West', 'North East']
    selected_regions = st.sidebar.multiselect(
        "Select Regions",
        options=available_regions,
        default=[r for r in default_regions if r in available_regions]
    )
    
    # Year range selection
    year_range = st.sidebar.slider(
        "Select Year Range",
        min_value=min_year,
        max_value=max_year,
        value=(min_year, max_year)
    )
    
    # Analysis type selection
    analysis_type = st.sidebar.selectbox(
        "Price Analysis Type",
        ["Nominal", "Real (CPI Adjusted)", "Real (RPI Adjusted)", "USD (Nominal)"]
    )
    
    # Index option
    index_to_first = st.sidebar.checkbox(
        "Index to First Year",
        value=True,
        help="Show prices relative to first year in selection"
    )

    if not selected_regions:
        st.warning("Please select at least one region to analyze.")
        return

    # Load price data
    df_prices = load_regional_prices(db, selected_regions, year_range[0], year_range[1])
    
    # Load economic data if needed
    _econ_data_dict = None
    if analysis_type != "Nominal":
        with st.spinner("Loading economic data..."):
            try:
                _econ_data_dict = load_economic_data(_econ_data, year_range[0], year_range[1])
            except Exception as e:
                st.error(f"Error loading economic data: {str(e)}")
                return
    
    # Process data
    df_processed = process_price_data(
        df_prices, 
        _econ_data_dict, 
        analysis_type,
        index_to_first
    )
    
    # Create tabs for different views
    tab1, tab2 = st.tabs(["Price Trends", "Data Analysis"])
    
    with tab1:
        # Main price trend visualization
        fig = px.line(
            df_processed,
            labels={
                'index': 'Year',
                'value': get_price_label(analysis_type, index_to_first),
                'variable': 'Region'
            },
            title=f'Regional House Prices - {analysis_type}',
            width=800,
            height=600
        )
        
        # Update x-axis to show every year
        fig.update_layout(
            legend=dict(
                yanchor="top",
                y=0.99,
                xanchor="left",
                x=0.01
            ),
            hovermode='x unified',
            xaxis=dict(
                dtick=1,  # Show every year
                tickangle=45  # Angle the year labels for better readability
            )
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Add exchange rate context if showing USD prices
        if analysis_type in ["USD (Nominal)"]:
            st.subheader("Exchange Rate Context")
            fx_data = _econ_data_dict['fx']
            fx_df = pd.DataFrame({'Year': fx_data.index, 'GBP/USD': fx_data.values})
            
            fig_fx = px.line(
                fx_df,
                x='Year',
                y='GBP/USD',
                title='GBP/USD Exchange Rate',
                width=800,
                height=300
            )
            st.plotly_chart(fig_fx, use_container_width=True)
    
    with tab2:
        # Data tables and statistics
        st.subheader("Price Data")
        st.dataframe(df_processed.round(2), use_container_width=True)
        
        # Calculate and display growth rates
        if not index_to_first:
            st.subheader("Total Price Changes")
            total_change = (df_processed.iloc[-1] / df_processed.iloc[0] - 1) * 100
            st.dataframe(pd.DataFrame({
                'Region': total_change.index,
                'Total Change (%)': total_change.values.round(1)
            }).set_index('Region'), use_container_width=True)

if __name__ == "__main__":
    main()
