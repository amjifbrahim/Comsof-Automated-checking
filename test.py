import geopandas as gpd
import os

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

