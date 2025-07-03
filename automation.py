import geopandas as gpd
import sys
import os
import pandas as pd

__all__ = ['check_osc_duplicates', 'check_invalid_cable_refs', 'report_splice_counts_by_closure', 'process_shapefiles', 'check_gistool_id', 'check_cluster_overlaps', 
           'check_granularity_fields', 'validate_non_virtual_closures', 'validate_feeder_primdistribution_locations']
#########################################################################
#######################check_invalid_cable_refs##########################
#########################################################################

def check_invalid_cable_refs(workspace):
    """
    Checks all cable piece shapefiles against their corresponding cable shapefiles
    for invalid or missing CableID references.

    Parameters:
    workspace (str): Path to the Comsof output folder

    Returns:
    None - prints the validation result per cable type
    """
    # Define cable types and file naming
    cable_types = [
        "Feeder", 
        "Drop", 
        "PrimDistribution", 
        "Distribution"
    ]

    print(f"🔍 Checking CableID references in workspace:\n{workspace}\n")

    for layer in cable_types:
        cable_file = f"OUT_{layer}Cables.shp"
        piece_file = f"OUT_{layer}CablePieces.shp"

        cable_path = os.path.join(workspace, cable_file)
        piece_path = os.path.join(workspace, piece_file)

        if not os.path.exists(cable_path):
            print(f"⚠️ Cable file missing: {cable_file}")
            continue
        if not os.path.exists(piece_path):
            print(f"⚠️ Cable piece file missing: {piece_file}")
            continue

        # Load shapefiles
        cables = gpd.read_file(cable_path)
        pieces = gpd.read_file(piece_path)

        # Check for invalid CableID references
        valid_ids = set(cables["CABLE_ID"])
        invalid_pieces = pieces[~pieces["CABLE_ID"].isin(valid_ids)]

        if invalid_pieces.empty:
            print(f"✅ {layer}CablePieces: All CABLE_IDs are valid.")
        else:
            print(f"❌ {layer}CablePieces: Found {len(invalid_pieces)} invalid CableID references.")
            print(invalid_pieces[["CABLE_ID"]].drop_duplicates().to_string(index=False))
        print("-" * 60)

#########################################################################
###########################check_osc_duplicates##########################
#########################################################################

def check_osc_duplicates(workspace):
    """
    Checks for duplicated OSC values in the OUT_Closures.shp's LINKED_AGG column.
    
    Args:
        workspace (str): Path to the directory containing OUT_Closures.shp
    
    Returns:
        bool: True if duplicates found, False if no duplicates, None if errors occurred
    """
    # Construct full path to shapefile
    shapefile_path = os.path.join(workspace, "OUT_Closures.shp")
    
    # Verify file exists
    if not os.path.isfile(shapefile_path):
        print(f"⛔ Error: OUT_Closures.shp not found in workspace: {workspace}")
        return None

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
    
#########################################################################
###########################check_splice_overload##########################
#########################################################################

def report_splice_counts_by_closure(workspace):
    """
    Reports the number of splices per closure in the Comsof export directory,
    grouped by closure type (IDENTIFIER).

    Parameters:
    workspace (str): Path to the Comsof output folder

    Returns:
    None – prints a formatted table
    """
    closure_file = os.path.join(workspace, "OUT_Closures.shp")
    splice_file = os.path.join(workspace, "OUT_Splices.shp")

    print(f"\n🔍 Reporting splices per closure type in:\n{workspace}\n")

    if not os.path.exists(closure_file):
        print("❌ Missing file: OUT_Closures.shp")
        return
    if not os.path.exists(splice_file):
        print("❌ Missing file: OUT_Splices.shp")
        return

    # Load shapefiles
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

    # Sort and print
    report_df.sort_values(by="SpliceCount", ascending=False, inplace=True)

    print(f"{'Closure Type (IDENTIFIER)':<30} {'Closure ID (ID)':<20} {'# Splices':<10}")
    print("-" * 65)

    for _, row in report_df.iterrows():
        identifier = row['IDENTIFIER'] if pd.notnull(row['IDENTIFIER']) else 'N/A'
        closure_id = str(row['ID']) if pd.notnull(row['ID']) else 'N/A'
        splice_count = row['SpliceCount']
        print(f"{identifier:<30} {closure_id:<20} {splice_count:<10}")

    print("\n✅ Report complete.\n")


#########################################################################
#######################check_invalid_identifiers##########################
#########################################################################

def process_shapefiles(workspace):
    """
    Processes OUT_FeederCables.shp and OUT_Closures.shp in the given workspace:
    1. For FeederCables: Ensures IDENTIFIER column exists and is filled with "Breakout"
    2. For Closures: Checks for non-virtual closures (VIRTUAL=0) with empty IDENTIFIER
    
    Args:
        workspace (str): Path to the directory containing shapefiles
    
    Returns:
        bool: True if errors found in closures, False if no errors, None if critical errors
    """
    try:
        # ==================================================================
        # Process OUT_FeederCables.shp
        # ==================================================================
        feeder_path = os.path.join(workspace, "OUT_FeederCables.shp")
        
        if not os.path.exists(feeder_path):
            print(f"⛔ Error: OUT_FeederCables.shp not found in {workspace}")
            return None
        
        feeder_gdf = gpd.read_file(feeder_path)
        
        # Create IDENTIFIER column if missing
        if 'IDENTIFIER' not in feeder_gdf.columns:
            feeder_gdf['IDENTIFIER'] = "Breakout"
            modified = True
        else:
            # Fill empty values in existing IDENTIFIER column
            mask = feeder_gdf['IDENTIFIER'].isna() | (feeder_gdf['IDENTIFIER'] == '')
            if mask.any():
                feeder_gdf.loc[mask, 'IDENTIFIER'] = "Breakout"
                modified = True
            else:
                modified = False
        
        # Save changes if any modifications were made
        if modified:
            feeder_gdf.to_file(feeder_path, driver='ESRI Shapefile')
            print("✅ Feeder cables: IDENTIFIER column has been updated with 'Breakout' values")
        else:
            print("✅ Feeder cables: IDENTIFIER column was already populated")

        # ==================================================================
        # Process OUT_Closures.shp
        # ==================================================================
        closures_path = os.path.join(workspace, "OUT_Closures.shp")
        
        if not os.path.exists(closures_path):
            print(f"⛔ Error: OUT_Closures.shp not found in {workspace}")
            return None
        
        closures_gdf = gpd.read_file(closures_path)
        errors_found = False
        
        # Check for required columns
        if 'IDENTIFIER' not in closures_gdf.columns:
            print("⛔ Error: 'IDENTIFIER' column not found in OUT_Closures.shp")
            return None
            
        if 'VIRTUAL' not in closures_gdf.columns:
            print("⛔ Error: 'VIRTUAL' column not found in OUT_Closures.shp")
            return None
        
        # Find problematic closures (non-virtual with empty identifier)
        mask = (closures_gdf['VIRTUAL'] == 0) & (closures_gdf['IDENTIFIER'].isna() | (closures_gdf['IDENTIFIER'] == ''))
        problem_closures = closures_gdf[mask]
        
        if not problem_closures.empty:
            print("\n⚠️  Problem found in closures:")
            print(f"Found {len(problem_closures)} non-virtual closures with empty IDENTIFIER")
            print("These require manual attention:\n")
            print(problem_closures[['IDENTIFIER', 'VIRTUAL']].to_string(index=False))
            errors_found = True
        else:
            print("\n✅ All non-virtual closures have valid IDENTIFIER values")
        
        return errors_found
        
    except Exception as e:
        print(f"⛔ Unexpected error: {e}")
        return None


#########################################################################
########################## check_gistool_id #############################
#########################################################################


def check_gistool_id(workspace):
    """
    Checks for non-empty GISTOOL_ID values in aerial or buried segments of OUT_UsedSegments.shp
    
    Args:
        workspace (str): Path to the directory containing shapefiles
    
    Returns:
        bool: True if issues found (non-empty GISTOOL_ID), False if no issues, None if errors
    """
    try:
        # Construct path to UsedSegments shapefile
        seg_path = os.path.join(workspace, "OUT_UsedSegments.shp")
        
        # Verify file exists
        if not os.path.isfile(seg_path):
            print(f"⛔ Error: OUT_UsedSegments.shp not found in {workspace}")
            return None
        
        # Read shapefile
        seg_gdf = gpd.read_file(seg_path)
        
        # Check for required columns
        required_cols = ['TYPE', 'GISTOOL_ID', 'ID']
        missing_cols = [col for col in required_cols if col not in seg_gdf.columns]
        if missing_cols:
            print(f"⛔ Error: Missing required columns: {', '.join(missing_cols)}")
            return None
        
        # Filter aerial and buried segments with non-empty GISTOOL_ID
        aerial_buried_mask = seg_gdf['TYPE'].isin(['AERIAL', 'BURIED'])
        non_empty_mask = ~seg_gdf['GISTOOL_ID'].isna() & (seg_gdf['GISTOOL_ID'] != '')
        
        # Combine masks
        problem_mask = aerial_buried_mask & non_empty_mask
        problem_segments = seg_gdf[problem_mask]
        
        if not problem_segments.empty:
            print("\n⚠️  Issues found in UsedSegments:")
            print(f"Found {len(problem_segments)} aerial/buried segments with non-empty GISTOOL_ID")
            print("GISTOOL_ID should be empty for aerial/buried segments:")
            print("Showing first 5 problematic segments:\n")
            
            # Create simplified report with ID column
            report = problem_segments[['TYPE', 'GISTOOL_ID', 'ID']].copy().head(5)
            report['GISTOOL_ID'] = report['GISTOOL_ID'].apply(lambda x: f"'{x}'" if pd.notna(x) else '')
            
            # Format as table with aligned columns
            print(report[['TYPE', 'GISTOOL_ID', 'ID']].to_string(index=False))
            
            return True
        else:
            print("\n✅ All aerial and buried segments have empty GISTOOL_ID values")
            return False
            
    except Exception as e:
        print(f"⛔ Unexpected error: {e}")
        return None
    
#########################################################################
########################## check_cluster_overlaps #############################
#########################################################################

def check_cluster_overlaps(workspace, cluster_files=None):
    """
    Detects overlapping features within each cluster layer shapefile.
    This is essential for YAML generation in Comsof.

    Args:
        workspace (str): Path to Comsof output directory containing .shp files.
        cluster_files (list, optional): List of filenames to check. 
            Defaults to standard Comsof cluster layers.

    Returns:
        None – prints the overlap check results.
    """
    import geopandas as gpd
    import os

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

    print("\n🔍 Running cluster self-overlap checks...\n")

    for file in cluster_files:
        path = os.path.join(workspace, file)

        if not os.path.isfile(path):
            print(f"⚠️ File not found: {file}")
            continue

        try:
            gdf = gpd.read_file(path)
            gdf = gdf[gdf.geometry.notnull()].reset_index(drop=True)

            # Use spatial index to efficiently detect intersections
            overlaps = []
            for idx, geom in gdf.geometry.items():
                candidates = gdf.sindex.query(geom, predicate="intersects")
                for j in candidates:
                    if idx < j and geom.intersects(gdf.geometry[j]):
                        overlaps.append((idx, j))

            if overlaps:
                print(f"❌ {file}: {len(overlaps)} overlaps found:")
                for a, b in overlaps[:5]:  # show only first 5
                    if "CableClusters" in file:
                        id_a = gdf.loc[a].get("CAB_GROUP", a)
                        id_b = gdf.loc[b].get("CAB_GROUP", b)
                        print(f"   • Cluster CAB_GROUP {id_a} overlaps with CAB_GROUP {id_b}")
                    else:
                        id_a = gdf.loc[a].get("AGG_ID", a)
                        id_b = gdf.loc[b].get("AGG_ID", b)
                        print(f"   • Cluster AGG_ID {id_a} overlaps with Cluster AGG_ID {id_b}")
            else:
                print(f"✅ {file}: No overlaps detected.")

        except Exception as e:
            print(f"⛔ Error processing {file}: {e}")

#################################################################################
########################## check_granularity_fields #############################
#################################################################################

def check_granularity_fields(workspace):
    """
    Validates that CABLEGRAN and BUNDLEGRAN fields are not set to -1 
    in all OUT_<Layer>Cables.shp files (Feeder, Drop, Distribution, PrimDistribution).

    Args:
        workspace (str): Path to Comsof export folder.

    Returns:
        None - Prints validation results.
    """
    import geopandas as gpd
    import os

    cable_layers = ["Feeder", "Drop", "Distribution", "PrimDistribution"]

    print("\n🔍 Checking CABLEGRAN and BUNDLEGRAN values in cable layers...\n")

    for layer in cable_layers:
        file_path = os.path.join(workspace, f"OUT_{layer}Cables.shp")

        if not os.path.exists(file_path):
            print(f"⚠️ Missing: OUT_{layer}Cables.shp")
            continue

        try:
            gdf = gpd.read_file(file_path)
            if 'CABLEGRAN' not in gdf.columns or 'BUNDLEGRAN' not in gdf.columns:
                print(f"❌ {file_path} is missing required fields CABLEGRAN or BUNDLEGRAN.")
                continue

            invalid_rows = gdf[(gdf['CABLEGRAN'] == -1) | (gdf['BUNDLEGRAN'] == -1)]

            if not invalid_rows.empty:
                print(f"❌ Found {len(invalid_rows)} invalid rows in OUT_{layer}Cables.shp")
                print(invalid_rows[['CABLE_ID', 'CABLEGRAN', 'BUNDLEGRAN']].head(5).to_string(index=False))
            else:
                print(f"✅ OUT_{layer}Cables.shp: All granularity values are valid.")

        except Exception as e:
            print(f"⛔ Error reading {file_path}: {e}")



#################################################################################
######################## validate_non_virtual_closures ##########################
#################################################################################

def validate_non_virtual_closures(workspace):
    """
    Validates that PrimDistribution, Distribution, and Drop closures are not virtual.
    
    Args:
        workspace (str): Path to Comsof output directory
    """
    print("\n🔍 Validating non-virtual closures...")

    closure_path = os.path.join(workspace, "OUT_Closures.shp")
    
    if not os.path.exists(closure_path):
        print("⛔ Error: OUT_Closures.shp not found in the workspace")
        return

    try:
        closures = gpd.read_file(closure_path)

        # Check required columns
        required_cols = ['LAYER', 'VIRTUAL']
        missing_cols = [col for col in required_cols if col not in closures.columns]
        if missing_cols:
            print(f"⛔ Error: Missing required columns: {', '.join(missing_cols)}")
            return

        # Identify closures that should not be virtual
        invalid_mask = (
            closures['LAYER'].isin(['PrimDistribution', 'Distribution', 'Drop']) &
            (closures['VIRTUAL'] == 1)
        )
        invalid_closures = closures[invalid_mask]

        if not invalid_closures.empty:
            print("\n⚠️  PROBLEM: Found non-virtual closures marked as virtual!")
            print(f"Total invalid closures: {len(invalid_closures)}")
            print("The following closure types should NEVER be virtual:")
            print("  - PrimDistribution")
            print("  - Distribution")
            print("  - Drop")
            print("\nInvalid closures:")
            print("  ID      LAYER              VIRTUAL")
            print("  ----    ----------------    -------")
            for _, row in invalid_closures.iterrows():
                closure_id = str(row.get('ID', 'N/A'))
                layer = row['LAYER']
                virtual = row['VIRTUAL']
                print(f"  {closure_id:<8} {layer:<18} {virtual}")
        else:
            print("\n✅ Everything is okay - all non-virtual closure types are properly marked!")
            print("Validated closure types:")
            print("  - PrimDistribution")
            print("  - Distribution")
            print("  - Drop")

    except Exception as e:
        print(f"⛔ Unexpected error: {e}")




#################################################################################
################ validate_feeder_primdistribution_locations #####################
#################################################################################


def validate_feeder_primdistribution_locations(workspace, tolerance=0.01):
    """
    Validates that Feeder Points and Primary Distribution Points are not co-located.
    
    Args:
        workspace (str): Path to Comsof output directory
        tolerance (float): Maximum allowed distance between points (in CRS units)
    """
    print("\n🔍 Validating Feeder and Primary Distribution Point locations...")

    feeder_path = os.path.join(workspace, "OUT_FeederPoints.shp")
    prim_path = os.path.join(workspace, "OUT_PrimDistributionPoints.shp")

    # Check if files exist
    if not os.path.exists(feeder_path):
        print("⛔ Error: OUT_FeederPoints.shp not found")
        return
    if not os.path.exists(prim_path):
        print("⛔ Error: OUT_PrimDistributionPoints.shp not found")
        return
    try:
        # Load shapefiles
        feeder_points = gpd.read_file(feeder_path)
        prim_points = gpd.read_file(prim_path)

        # Check if each file has exactly one point
        if len(feeder_points) != 1:
            print(f"⚠️ Warning: OUT_FeederPoints.shp has {len(feeder_points)} features (expected 1)")
        if len(prim_points) != 1:
            print(f"⚠️ Warning: OUT_PrimDistributionPoints.shp has {len(prim_points)} features (expected 1)")

        if len(feeder_points) > 0 and len(prim_points) > 0:
            # Get the first point from each file
            feeder_geom = feeder_points.geometry.iloc[0]
            prim_geom = prim_points.geometry.iloc[0]

            # Calculate distance between points
            distance = feeder_geom.distance(prim_geom)

            if distance < tolerance:
                feeder_coords = (feeder_geom.x, feeder_geom.y)
                prim_coords = (prim_geom.x, prim_geom.y)

                print("\n⚠️  CRITICAL ISSUE: Feeder and Primary Distribution Points are too close!")
                print(f"Distance between points: {distance:.6f} units (tolerance: {tolerance} units)")
                print(f"Feeder Point location: X={feeder_coords[0]:.6f}, Y={feeder_coords[1]:.6f}")
                print(f"Primary Distribution Point location: X={prim_coords[0]:.6f}, Y={prim_coords[1]:.6f}")
                print("\n❌ These points should not be co-located. Please verify in GIS software.")
            else:
                print("\n✅ Validation passed - points are sufficiently separated")
                print(f"Distance between points: {distance:.6f} units (minimum required: {tolerance} units)")
        else:
            print("\n⛔ Cannot perform validation - one or both files are empty")

    except Exception as e:
        print(f"⛔ Unexpected error: {e}")



#################################################################################
########################### validate_cable_diameters ############################
#################################################################################


import os
import geopandas as gpd

def validate_cable_diameters(workspace):
    """
    Validates that DIAMETER column is not empty or zero in cable shapefiles.
    
    Args:
        workspace (str): Path to Comsof output directory
    """
    print("\n🔍 Validating cable diameters...")

    cable_files = [
        "OUT_DistributionCables.shp",
        "OUT_FeederCables.shp",
        "OUT_PrimDistributionCables.shp"
    ]

    try:
        any_errors = False

        for file in cable_files:
            file_path = os.path.join(workspace, file)

            if not os.path.exists(file_path):
                print(f"⛔ Error: {file} not found in workspace")
                any_errors = True
                continue

            gdf = gpd.read_file(file_path)

            if 'DIAMETER' not in gdf.columns:
                print(f"⛔ Error: {file} is missing DIAMETER column")
                any_errors = True
                continue

            # Find invalid diameters (missing or zero)
            invalid_mask = gdf['DIAMETER'].isna() | (gdf['DIAMETER'] == 0)
            invalid_cables = gdf[invalid_mask]

            if not invalid_cables.empty:
                any_errors = True
                print(f"\n❌ PROBLEM: Found {len(invalid_cables)} cables with invalid diameters in {file}")
                print("Cables must have non-zero diameter values")

                # Show sample of problematic cables
                sample = invalid_cables[['CABLE_ID', 'DIAMETER']].head(5)
                print("\nSample of problematic cables:")
                print(sample.to_string(index=False))
            else:
                print(f"\n✅ {file}: All cables have valid diameters")

        if not any_errors:
            print("\n✅ All cable files have valid diameter values")

    except Exception as e:
        print(f"⛔ Unexpected error: {e}")
