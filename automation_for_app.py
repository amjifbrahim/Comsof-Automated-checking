import geopandas as gpd
import sys
import os
import pandas as pd

__all__ = ['check_osc_duplicates', 'check_invalid_cable_refs', 'report_splice_counts_by_closure', 'process_shapefiles', 'check_gistool_id', 
           'check_cluster_overlaps', 'check_granularity_fields', 'validate_non_virtual_closures', 'validate_feeder_primdistribution_locations']



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
            output.append("⛔ Feeder cables: IDENTIFIER column needs to be updated with 'Breakout' values")
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
    


#################################################################################################

def check_cluster_overlaps(workspace, cluster_files=None):
    """
    Detects overlapping features within each cluster layer shapefile.
    Returns: (has_issues: bool, message: str)
    """
    import geopandas as gpd
    import os

    output = ["🔍 Running cluster self-overlap checks...\n"]
    try:
        if cluster_files is None:
            cluster_files = [
                "OUT_DropClusters.shp",
                "OUT_DistributionClusters.shp",
                "OUT_DistributionCableClusters.shp",
                "OUT_PrimDistributionClusters.shp",
                "OUT_PrimDistributionCableClusters.shp",
                "OUT_FeederClusters.shp",
                "OUT_FeederCableClusters.shp"
            ]

        issues_found = False
        for file in cluster_files:
            path = os.path.join(workspace, file)
            if not os.path.isfile(path):
                output.append(f"⚠️ File not found: {file}")
                continue

            gdf = gpd.read_file(path)
            gdf = gdf[gdf.geometry.notnull()].reset_index(drop=True)

            overlaps = []
            # spatial index for performance
            sindex = gdf.sindex
            for idx, geom in gdf.geometry.items():
                candidates = sindex.query(geom, predicate="intersects")
                for j in candidates:
                    if idx < j and geom.intersects(gdf.geometry[j]):
                        overlaps.append((idx, j))

            if overlaps:
                issues_found = True
                output.append(f"❌ {file}: {len(overlaps)} overlaps found:")
                for a, b in overlaps[:5]:
                    if "CableClusters" in file:
                        id_a = gdf.loc[a].get("CAB_GROUP", a)
                        id_b = gdf.loc[b].get("CAB_GROUP", b)
                        output.append(f"   • Cluster CAB_GROUP {id_a} overlaps with CAB_GROUP {id_b}")
                    else:
                        id_a = gdf.loc[a].get("AGG_ID", a)
                        id_b = gdf.loc[b].get("AGG_ID", b)
                        output.append(f"   • Cluster AGG_ID {id_a} overlaps with Cluster AGG_ID {id_b}")
            else:
                output.append(f"✅ {file}: No overlaps detected.")

            output.append("-" * 60)

        return issues_found, "\n".join(output)

    except Exception as e:
        output.append(f"⛔ Error running cluster overlap checks: {e}")
        return None, "\n".join(output)


#################################################################################################

def check_granularity_fields(workspace):
    """
    Validates that CABLEGRAN and BUNDLEGRAN fields are not set to -1 
    in all OUT_<Layer>Cables.shp files.
    Returns: (has_issues: bool, message: str)
    """
    import geopandas as gpd
    import os

    output = ["🔍 Checking CABLEGRAN and BUNDLEGRAN values in cable layers...\n"]
    try:
        cable_layers = ["Feeder", "Drop", "Distribution", "PrimDistribution"]
        issues_found = False

        for layer in cable_layers:
            file_name = f"OUT_{layer}Cables.shp"
            path = os.path.join(workspace, file_name)
            if not os.path.isfile(path):
                output.append(f"⚠️ Missing: {file_name}")
                continue

            gdf = gpd.read_file(path)
            if 'CABLEGRAN' not in gdf.columns or 'BUNDLEGRAN' not in gdf.columns:
                output.append(f"❌ {file_name} is missing CABLEGRAN or BUNDLEGRAN fields.")
                issues_found = True
                continue

            invalid = gdf[(gdf['CABLEGRAN'] == -1) | (gdf['BUNDLEGRAN'] == -1)]
            if not invalid.empty:
                issues_found = True
                count = len(invalid)
                output.append(f"❌ {file_name}: {count} invalid rows:")
                # show up to 5 rows
                preview = invalid[['CABLE_ID', 'CABLEGRAN', 'BUNDLEGRAN']].head(5)
                output.append(preview.to_string(index=False))
            else:
                output.append(f"✅ {file_name}: All granularity values are valid.")

            output.append("-" * 60)

        return issues_found, "\n".join(output)

    except Exception as e:
        output.append(f"⛔ Error checking granularity fields: {e}")
        return None, "\n".join(output)





######################################################################################################

def validate_non_virtual_closures(workspace):
    """
    Validates that PrimDistribution, Distribution, and Drop closures are not virtual.
    
    Args:
        workspace (str): Path to Comsof output directory
        
    Returns:
        tuple: (has_issues, message) where:
            has_issues: True if problems found, False otherwise
            message: Detailed validation results
    """


    output = ["🔍 Validating non-virtual closures..."]
    try:
        closure_path = os.path.join(workspace, "OUT_Closures.shp")
        if not os.path.isfile(closure_path):
            output.append(f"⛔ Error: OUT_Closures.shp not found in {workspace}")
            return None, "\n".join(output)

        closures = gpd.read_file(closure_path)

        # Check required columns
        required_cols = ['LAYER', 'VIRTUAL', 'EQ_ID']
        missing = [c for c in required_cols if c not in closures.columns]
        if missing:
            output.append(f"⛔ Error: Missing required columns: {', '.join(missing)}")
            return None, "\n".join(output)

        # Find closures of the given types that are marked virtual (VIRTUAL == 1)
        mask = (
            closures['LAYER'].isin(['PrimDistribution', 'Distribution', 'Drop']) &
            (closures['VIRTUAL'] == 1)
        )
        bad = closures[mask]

        if not bad.empty:
            output.append(f"❌ Found {len(bad)} closures incorrectly marked as virtual:")
            output.append("These closure types should never be virtual:")
            output.append("- PrimDistribution")
            output.append("- Distribution")
            output.append("- Drop\n")

            # Report using EQ_ID
            report = bad[['EQ_ID', 'LAYER', 'VIRTUAL']].copy()
            report['VIRTUAL'] = report['VIRTUAL'].astype(int)
            output.append(report.to_string(index=False))
            has_issues = True
        else:
            output.append("✅ All PrimDistribution, Distribution, and Drop closures are non-virtual as expected.")
            has_issues = False

        return has_issues, "\n".join(output)

    except Exception as e:
        output.append(f"⛔ Unexpected error: {e}")
        return None, "\n".join(output)

#######################################################################################################


def validate_feeder_primdistribution_locations(workspace, tolerance=0.01):
    """
    Validates that Feeder Points and Primary Distribution Points are not co-located.
    
    Args:
        workspace (str): Path to Comsof output directory
        tolerance (float): Maximum allowed distance between points (in CRS units)
        
    Returns:
        tuple: (has_issues, message) where:
            has_issues: True if points are too close, False otherwise
            message: Detailed validation results
    """
    output = []
    has_issues = False
    
    try:
        feeder_path = os.path.join(workspace, "OUT_FeederPoints.shp")
        prim_path = os.path.join(workspace, "OUT_PrimDistributionPoints.shp")
        
        output.append("\n🔍 Validating Feeder and Primary Distribution Point locations...")
        
        # Check if files exist
        if not os.path.exists(feeder_path):
            output.append("⛔ Error: OUT_FeederPoints.shp not found")
            return None, "\n".join(output)
        if not os.path.exists(prim_path):
            output.append("⛔ Error: OUT_PrimDistributionPoints.shp not found")
            return None, "\n".join(output)
        
        # Load shapefiles
        feeder_points = gpd.read_file(feeder_path)
        prim_points = gpd.read_file(prim_path)
        
        # Check if each file has exactly one point
        if len(feeder_points) != 1:
            output.append(f"⚠️ Warning: OUT_FeederPoints.shp has {len(feeder_points)} features (expected 1)")
        if len(prim_points) != 1:
            output.append(f"⚠️ Warning: OUT_PrimDistributionPoints.shp has {len(prim_points)} features (expected 1)")
        
        if len(feeder_points) > 0 and len(prim_points) > 0:
            # Get the first point from each file
            feeder_geom = feeder_points.geometry.iloc[0]
            prim_geom = prim_points.geometry.iloc[0]
            
            # Calculate distance between points
            distance = feeder_geom.distance(prim_geom)
            
            if distance < tolerance:
                has_issues = True
                # Get coordinates for reporting
                feeder_coords = (feeder_geom.x, feeder_geom.y)
                prim_coords = (prim_geom.x, prim_geom.y)
                
                output.append("\n⚠️  CRITICAL ISSUE: Feeder and Primary Distribution Points are too close!")
                output.append(f"Distance between points: {distance:.6f} units (tolerance: {tolerance} units)")
                output.append(f"Feeder Point location: X={feeder_coords[0]:.6f}, Y={feeder_coords[1]:.6f}")
                output.append(f"Primary Distribution Point location: X={prim_coords[0]:.6f}, Y={prim_coords[1]:.6f}")
                output.append("\n❌ These points should not be co-located. Please verify in GIS software.")
            else:
                output.append("\n✅ Validation passed - points are sufficiently separated")
                output.append(f"Distance between points: {distance:.6f} units (minimum required: {tolerance} units)")
        else:
            output.append("\n⛔ Cannot perform validation - one or both files are empty")
            return None, "\n".join(output)
        
        return has_issues, "\n".join(output)
        
    except Exception as e:
        output.append(f"⛔ Unexpected error: {e}")
        return None, "\n".join(output)

