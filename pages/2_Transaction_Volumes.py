# pages/2_Transaction_Volumes.py

import streamlit as st
import plotly.express as px
import pandas as pd
from database import UKHousingDB

# Initialize database
@st.cache_resource
def init_database():
    return UKHousingDB()

# Cache data loading functions
@st.cache_data
def load_transaction_volumes(_db, regions, start_year, end_year, by_quarter=False, is_leasehold_flat=False):
    return _db.get_transaction_volumes(
        start_year=start_year,
        end_year=end_year,
        regions=regions if regions else None,
        by_quarter=by_quarter,
        is_leasehold_flat=is_leasehold_flat
    )

@st.cache_data
def load_monthly_comparison(_db, year):
    return _db.compare_monthly_releases(year)

@st.cache_data
def load_price_bands(_db, interval, price_limit, start_year, end_year, regions=None):
    return _db.volume_by_price(
        interval=interval,
        price_limit=price_limit,
        start_year=start_year,
        end_year=end_year,
        regions=regions
    )

def main():
    st.title("Transaction Volume Analysis")
    
    # Initialize database
    try:
        db = init_database()
    except ValueError as e:
        st.error(f"Error initializing database: {str(e)}")
        return
    
    # Sidebar controls
    st.sidebar.header("Controls")
    
    # Get available regions and years
    available_regions = db.get_available_regions()
    min_year, max_year = db.get_year_range()
    
    # Global region selection in sidebar
    selected_regions = st.sidebar.multiselect(
        "Select Regions",
        options=available_regions,
        default=['London', 'South East'] if 'London' in available_regions else available_regions[:2]
    )
    
    if not selected_regions:
        st.warning("Please select at least one region to analyze.")
        return
    
    # Create tabs for different analyses
    tab1, tab2, tab3 = st.tabs(["Historical Volumes", "By Price", "Monthly Updates"])
    
    with tab1:
        # Year range selection
        year_range = st.slider(
            "Select Year Range",
            min_value=min_year,
            max_value=max_year,
            value=(max_year-5, max_year)
        )
        
        # Property type filter
        is_leasehold_flat = st.checkbox(
            "Show Leasehold Flats Only",
            value=False,
            help="Filter for leasehold flat transactions only"
        )
            
        # Load and process data
        df_volumes = load_transaction_volumes(
            db, 
            selected_regions, 
            year_range[0], 
            year_range[1],
            is_leasehold_flat=is_leasehold_flat
        )
        
        # Create visualization
        fig = px.line(
            df_volumes,
            x='year',
            y='transaction_count',
            color='region',
            title='Annual Transaction Volumes by Region',
            labels={
                'year': 'Year',
                'transaction_count': 'Number of Transactions',
                'region': 'Region'
            }
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Show data table
        with st.expander("View Data"):
            st.dataframe(df_volumes, use_container_width=True)
    
    with tab2:
        # Price band analysis
        st.subheader("Transaction Volumes by Price Band")
        
        # Price band controls
        col1, col2 = st.columns(2)
        with col1:
            interval = st.number_input(
                "Price Band Interval (£'000s)",
                min_value=50,
                max_value=500,
                value=100,
                step=50,
                help="Size of each price bracket in thousands of pounds"
            )
        
        with col2:
            price_limit = st.number_input(
                "Maximum Price (£'000s)",
                min_value=interval,
                max_value=5000,
                value=1000,
                step=100,
                help="Maximum price to analyze in thousands of pounds"
            )
        
        # Year selection for price analysis
        selected_year = st.slider(
            "Select Year for Price Analysis",
            min_value=min_year + 2,  # Need 2 previous years
            max_value=max_year,
            value=max_year,
            key="price_year"
        )
        # Calculate the year range to include two previous years
        start_year = selected_year - 2
        end_year = selected_year
        
        # Load price band data
        df_price_bands = load_price_bands(
            db,
            interval,
            price_limit,
            start_year,
            end_year,
            regions=selected_regions
        )
        
        # Calculate total transactions by year and price band for the bar chart
        df_yearly = df_price_bands.groupby(['year', 'price_band', 'region'])['transaction_count'].sum().reset_index()
        
        # Create price band visualization (yearly)
        fig_price = px.bar(
            df_yearly,
            x='price_band',
            y='transaction_count',
            color='region',
            facet_row='year',
            title='Transaction Volumes by Price Band and Year',
            labels={
                'price_band': 'Price Band',
                'transaction_count': 'Number of Transactions',
                'region': 'Region'
            }
        )
        
        # Update layout for better readability
        fig_price.update_xaxes(tickangle=45)
        
        st.plotly_chart(fig_price, use_container_width=True)
        
        # Calculate total transactions by price band and year (summed across regions)
        df_total = df_yearly.groupby(['year', 'price_band'])['transaction_count'].sum().reset_index()
        
        # Calculate year-over-year changes for the selected year only
        df_yoy = df_total.copy()
        df_yoy['year'] = df_yoy['year'].astype(int)
        
        # Filter for selected year and previous year only
        df_yoy = df_yoy[df_yoy['year'].isin([selected_year, selected_year - 1])]
        
        # Pivot the data to get current and previous year columns
        df_yoy_pivot = df_yoy.pivot(index='price_band', 
                                   columns='year', 
                                   values='transaction_count').reset_index()
        
        # Calculate percentage change
        df_yoy_pivot['yoy_change'] = ((df_yoy_pivot[selected_year] - df_yoy_pivot[selected_year - 1]) / 
                                     df_yoy_pivot[selected_year - 1] * 100).round(1)
        
        # Prepare final dataframe for plotting
        df_yoy = df_yoy_pivot[['price_band', 'yoy_change']].copy()
        
        # Create year-over-year changes visualization
        fig_yoy = px.bar(
            df_yoy,
            x='price_band',
            y='yoy_change',
            title=f'Year-over-Year Changes in Total Transaction Volumes by Price Band for {selected_year} (%)',
            labels={
                'price_band': 'Price Band',
                'yoy_change': 'Year-over-Year Change (%)'
            }
        )
        
        fig_yoy.update_xaxes(tickangle=45)
        fig_yoy.add_hline(y=0, line_dash="dash", line_color="gray")
        
        st.plotly_chart(fig_yoy, use_container_width=True)
        
        with st.expander("View Price Band Data"):
            st.dataframe(df_yearly, use_container_width=True)
    
    with tab3:
        # Monthly updates analysis
        st.subheader("Monthly Data Updates")
        
        df_monthly = load_monthly_comparison(db, max_year)
        
        # Create monthly comparison visualization
        fig_monthly = px.bar(
            df_monthly,
            x='month',
            y='count_difference',
            color='percentage_change',
            title=f'Transaction Count Changes in Latest Update ({max_year})',
            labels={
                'count_difference': 'Change in Transaction Count',
                'percentage_change': 'Percentage Change (%)'
            },
            barmode='group'
        )
        
        st.plotly_chart(fig_monthly, use_container_width=True)
        
        with st.expander("View Monthly Comparison Data"):
            st.dataframe(
                df_monthly.sort_values(['month']),
                use_container_width=True
            )

if __name__ == "__main__":
    main()