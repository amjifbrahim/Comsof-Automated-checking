import geopandas as gpd
import sys
import os
import pandas as pd

__all__ = ['check_osc_duplicates', 'check_invalid_cable_refs', 'report_splice_counts_by_closure', 'process_shapefiles', 'check_gistool_id']



###############################################################################################################


def check_osc_duplicates(workspace):
    output = []
    try:
        shapefile_path = os.path.join(workspace, "OUT_Closures.shp")
        
        if not os.path.isfile(shapefile_path):
            output.append(f"⛔ Error: OUT_Closures.shp not found in workspace: {workspace}")
            return None, "\n".join(output)

        gdf = gpd.read_file(shapefile_path)
        
        if 'LINKED_AGG' not in gdf.columns:
            output.append("⛔ Error: 'LINKED_AGG' column not found in the shapefile")
            return None, "\n".join(output)

        duplicates = gdf['LINKED_AGG'].duplicated(keep=False)
        
        if duplicates.any():
            output.append("\n⚠️  We have a problem of duplicated OSCs! ⚠️")
            output.append(f"Total duplicated entries: {duplicates.sum()}")
            
            duplicates_df = gdf[duplicates]['LINKED_AGG'].value_counts().reset_index()
            duplicates_df.columns = ['OSC Value', 'Duplicate Count']
            
            output.append("\nDuplicate occurrences:")
            output.append(duplicates_df.to_string(index=False))
            return True, "\n".join(output)
        else:
            output.append("\n✅ Everything is okay - no duplicated OSCs found!")
            return False, "\n".join(output)
            
    except Exception as e:
        output.append(f"⛔ Error reading shapefile: {e}")
        return None, "\n".join(output)


 ##############################################################################################################   

def process_shapefiles(workspace):
    output = []
    try:
        # Process FeederCables
        feeder_path = os.path.join(workspace, "OUT_FeederCables.shp")
        if not os.path.exists(feeder_path):
            output.append(f"⛔ Error: OUT_FeederCables.shp not found in {workspace}")
            return None, "\n".join(output)
        
        feeder_gdf = gpd.read_file(feeder_path)
        modified = False
        
        if 'IDENTIFIER' not in feeder_gdf.columns:
            feeder_gdf['IDENTIFIER'] = "Breakout"
            modified = True
        else:
            mask = feeder_gdf['IDENTIFIER'].isna() | (feeder_gdf['IDENTIFIER'] == '')
            if mask.any():
                feeder_gdf.loc[mask, 'IDENTIFIER'] = "Breakout"
                modified = True
        
        if modified:
            feeder_gdf.to_file(feeder_path, driver='ESRI Shapefile')
            output.append("✅ Feeder cables: IDENTIFIER column has been updated with 'Breakout' values")
        else:
            output.append("✅ Feeder cables: IDENTIFIER column was already populated")

        # Process Closures
        closures_path = os.path.join(workspace, "OUT_Closures.shp")
        if not os.path.exists(closures_path):
            output.append(f"⛔ Error: OUT_Closures.shp not found in {workspace}")
            return None, "\n".join(output)
        
        closures_gdf = gpd.read_file(closures_path)
        errors_found = False
        
        if 'IDENTIFIER' not in closures_gdf.columns:
            output.append("⛔ Error: 'IDENTIFIER' column not found in OUT_Closures.shp")
            return None, "\n".join(output)
            
        if 'VIRTUAL' not in closures_gdf.columns:
            output.append("⛔ Error: 'VIRTUAL' column not found in OUT_Closures.shp")
            return None, "\n".join(output)
        
        mask = ((closures_gdf['VIRTUAL'] == 0) & 
                (closures_gdf['IDENTIFIER'].isna() | (closures_gdf['IDENTIFIER'] == '')))
        problem_closures = closures_gdf[mask]
        
        if not problem_closures.empty:
            output.append("\n⚠️  Problem found in closures:")
            output.append(f"Found {len(problem_closures)} non-virtual closures with empty IDENTIFIER")
            output.append("These require manual attention:\n")
            output.append(problem_closures[['IDENTIFIER', 'VIRTUAL']].to_string(index=False))
            errors_found = True
        else:
            output.append("\n✅ All non-virtual closures have valid IDENTIFIER values")
            errors_found = False
        
        return errors_found, "\n".join(output)
        
    except Exception as e:
        output.append(f"⛔ Unexpected error: {e}")
        return None, "\n".join(output)
    


###########################################################################################################

def check_gistool_id(workspace):
    output = []
    try:
        seg_path = os.path.join(workspace, "OUT_UsedSegments.shp")
        if not os.path.isfile(seg_path):
            output.append(f"⛔ Error: OUT_UsedSegments.shp not found in {workspace}")
            return None, "\n".join(output)
        
        seg_gdf = gpd.read_file(seg_path)
        
        required_cols = ['TYPE', 'GISTOOL_ID', 'ID']
        missing_cols = [col for col in required_cols if col not in seg_gdf.columns]
        if missing_cols:
            output.append(f"⛔ Error: Missing required columns: {', '.join(missing_cols)}")
            return None, "\n".join(output)
        
        aerial_buried_mask = seg_gdf['TYPE'].isin(['AERIAL', 'BURIED'])
        non_empty_mask = ~seg_gdf['GISTOOL_ID'].isna() & (seg_gdf['GISTOOL_ID'] != '')
        
        problem_mask = aerial_buried_mask & non_empty_mask
        problem_segments = seg_gdf[problem_mask]
        
        if not problem_segments.empty:
            output.append("\n⚠️  Issues found in UsedSegments:")
            output.append(f"Found {len(problem_segments)} aerial/buried segments with non-empty GISTOOL_ID")
            output.append("GISTOOL_ID should be empty for aerial/buried segments:")
            output.append("Showing first 5 problematic segments:\n")
            
            report = problem_segments[['TYPE', 'GISTOOL_ID', 'ID']].copy().head(5)
            report['GISTOOL_ID'] = report['GISTOOL_ID'].apply(lambda x: f"'{x}'" if pd.notna(x) else '')
            output.append(report[['TYPE', 'GISTOOL_ID', 'ID']].to_string(index=False))
            
            return True, "\n".join(output)
        else:
            output.append("\n✅ All aerial and buried segments have empty GISTOOL_ID values")
            return False, "\n".join(output)
            
    except Exception as e:
        output.append(f"⛔ Unexpected error: {e}")
        return None, "\n".join(output)
    


############################################################################################################
def check_invalid_cable_refs(workspace):
    """
    Checks all cable piece shapefiles for invalid CableID references
    Returns: (has_issues, message) tuple
    """
    output = []
    has_issues = False
    
    try:
        cable_types = ["Feeder", "Drop", "PrimDistribution", "Distribution"]
        output.append("🔍 Checking CableID references for all cable types")

        for layer in cable_types:
            cable_file = f"OUT_{layer}Cables.shp"
            piece_file = f"OUT_{layer}CablePieces.shp"
            cable_path = os.path.join(workspace, cable_file)
            piece_path = os.path.join(workspace, piece_file)

            if not os.path.exists(cable_path):
                output.append(f"⚠️ Cable file missing: {cable_file}")
                continue
            if not os.path.exists(piece_path):
                output.append(f"⚠️ Cable piece file missing: {piece_file}")
                continue

            cables = gpd.read_file(cable_path)
            pieces = gpd.read_file(piece_path)

            # Check for invalid CableID references
            valid_ids = set(cables["CABLE_ID"])
            invalid_pieces = pieces[~pieces["CABLE_ID"].isin(valid_ids)]

            if invalid_pieces.empty:
                output.append(f"✅ {layer}CablePieces: All CABLE_IDs are valid.")
            else:
                has_issues = True
                invalid_count = len(invalid_pieces)
                invalid_ids = invalid_pieces["CABLE_ID"].unique()
                output.append(f"❌ {layer}CablePieces: Found {invalid_count} pieces with {len(invalid_ids)} invalid CableIDs")
                output.append("Invalid CableIDs: " + ", ".join(map(str, invalid_ids[:10])))
                if len(invalid_ids) > 10:
                    output.append(f"Showing first 10 of {len(invalid_ids)} invalid IDs")
            output.append("-" * 60)
        
        return has_issues, "\n".join(output)
        
    except Exception as e:
        output.append(f"⛔ Unexpected error: {str(e)}")
        return None, "\n".join(output)
    


#############################################################################################################

def report_splice_counts_by_closure(workspace):
    """
    Reports the number of splices per closure
    Returns: (is_report, message) tuple (status always False for reports)
    """
    output = []
    
    try:
        closure_file = os.path.join(workspace, "OUT_Closures.shp")
        splice_file = os.path.join(workspace, "OUT_Splices.shp")
        output.append("🔍 Reporting splices per closure type")

        if not os.path.exists(closure_file):
            output.append("❌ Missing file: OUT_Closures.shp")
            return None, "\n".join(output)
        if not os.path.exists(splice_file):
            output.append("❌ Missing file: OUT_Splices.shp")
            return None, "\n".join(output)

        closures = gpd.read_file(closure_file)
        splices = gpd.read_file(splice_file)

        # Count splices per closure ID
        splice_counts = splices["ID"].value_counts().reset_index()
        splice_counts.columns = ["ID", "SpliceCount"]

        # Merge counts into closures
        closures["ID"] = closures["ID"].astype(str)
        splice_counts["ID"] = splice_counts["ID"].astype(str)
        report_df = closures[["IDENTIFIER", "ID"]].copy()
        report_df = report_df.merge(splice_counts, on="ID", how="left")
        report_df["SpliceCount"] = report_df["SpliceCount"].fillna(0).astype(int)

        # Sort and format report
        report_df.sort_values(by="SpliceCount", ascending=False, inplace=True)
        output.append(f"{'Closure Type':<30} {'Closure ID':<20} {'# Splices':<10}")
        output.append("-" * 60)

        for _, row in report_df.iterrows():
            identifier = row['IDENTIFIER'] if pd.notnull(row['IDENTIFIER']) else 'N/A'
            closure_id = str(row['ID']) if pd.notnull(row['ID']) else 'N/A'
            splice_count = row['SpliceCount']
            output.append(f"{identifier:<30} {closure_id:<20} {splice_count:<10}")

        output.append("\n✅ Splice report complete.")
        return False, "\n".join(output)  # Always False status for reports
        
    except Exception as e:
        output.append(f"⛔ Unexpected error: {str(e)}")
        return None, "\n".join(output)
    


