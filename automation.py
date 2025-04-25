import geopandas as gpd
import sys

def check_osc_duplicates(shapefile_path):
    """
    Checks for duplicated OSC values in a shapefile's LINKED_AGG column.
    
    Args:
        shapefile_path (str): Path to the shapefile (.shp)
    
    Returns:
        bool: True if duplicates found, False if no duplicates, None if errors occurred
    """
    try:
        # Read shapefile
        gdf = gpd.read_file(shapefile_path)
    except Exception as e:
        print(f"⛔ Error reading shapefile: {e}")
        return None

    # Check for required column
    if 'LINKED_AGG' not in gdf.columns:
        print("⛔ Error: 'LINKED_AGG' column not found in the shapefile")
        return None

    # Check for duplicates
    duplicates = gdf['LINKED_AGG'].duplicated(keep=False)
    
    if duplicates.any():
        print("\n⚠️  We have a problem of duplicated OSCs! ⚠️")
        print(f"Total duplicated entries: {duplicates.sum()}")
        
        duplicates_df = gdf[duplicates]['LINKED_AGG'].value_counts().reset_index()
        duplicates_df.columns = ['OSC Value', 'Duplicate Count']
        
        print("\nDuplicate occurrences:")
        print(duplicates_df.to_string(index=False))
        return True
    else:
        print("\n✅ Everything is okay - no duplicated OSCs found!")
        return False