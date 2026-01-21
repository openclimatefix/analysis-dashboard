"""Location management section for the Data Platform Toolbox"""

import streamlit as st
import pandas as pd
import json
from dp_sdk.ocf import dp
import grpc

async def locations_section(data_client):
    """Location management section."""
    
    # Energy source and location type mappings
    ENERGY_SOURCES = {
        "All": None,
        "SOLAR": 1,  # ENERGY_SOURCE_SOLAR
        "WIND": 2,   # ENERGY_SOURCE_WIND
    }
    
    LOCATION_TYPES = {
        "All": None,
        "SITE": 1,     # LOCATION_TYPE_SITE
        "GSP": 2,      # LOCATION_TYPE_GSP
        "REGION": 3,   # LOCATION_TYPE_REGION
        "COUNTRY": 4,  # LOCATION_TYPE_COUNTRY
    }
    
    # List Locations
    st.markdown(
        '<h2 style="color:#63BCAF;font-size:32px;">List Locations</h2>',
        unsafe_allow_html=True,
    )
    with st.expander("Filter options"):
        energy_source_filter = st.selectbox(
            "Energy Source", 
            ["All", "SOLAR", "WIND"], 
            key="list_loc_energy"
        )
        location_type_filter = st.selectbox(
            "Location Type",
            ["All", "SITE", "GSP", "REGION", "COUNTRY"],
            key="list_loc_type"
        )
        user_filter = st.text_input(
            "Filter by User OAuth ID (optional)",
            key="list_loc_user",
            help="Leave empty to show all locations"
        )
    if st.button("List Locations", key="list_locations_button"):
        if not data_client:
            st.error("❌ Could not connect to Data Platform")
        else:
            try:
                request = dp.ListLocationsRequest()
                if energy_source_filter != "All":
                    request.energy_source_filter = ENERGY_SOURCES[energy_source_filter]
                if location_type_filter != "All":
                    request.location_type_filter = LOCATION_TYPES[location_type_filter]
                if user_filter:
                    request.user_oauth_id_filter = user_filter
                
                response = await data_client.list_locations(request)
                response_dict = response.to_dict()
                st.write(response_dict)
                locations = response_dict.get("locations", [])
                
                if locations:
                    st.success(f"✅ Found {len(locations)} location(s)")
                    
                    # Display as a table
                    location_data = []
                    location_type_names = ["Unknown", "SITE", "GSP", "REGION", "COUNTRY"]
                    for loc in locations:
                        latlng = loc.get("latlng", {})
                        # Handle energy_source that might be string or int
                        energy = loc.get("energySource", 0)
                        if isinstance(energy, str):
                            energy_display = "SOLAR" if energy in ("1", "SOLAR") else "WIND" if energy in ("2", "WIND") else energy
                        else:
                            energy_display = "SOLAR" if energy == 1 else "WIND" if energy == 2 else "Unknown"
                        
                        # Handle location_type that might be string or int
                        loc_type = loc.get("locationType", 0)
                        if isinstance(loc_type, str):
                            # Could be "1" or "SITE" etc.
                            if loc_type.isdigit():
                                loc_type_display = location_type_names[int(loc_type)] if int(loc_type) < len(location_type_names) else loc_type
                            else:
                                loc_type_display = loc_type
                        else:
                            loc_type_display = location_type_names[loc_type] if loc_type < len(location_type_names) else "Unknown"
                        
                        location_data.append({
                            "UUID": loc.get("locationUuid", "N/A"),
                            "Name": loc.get("locationName", "N/A"),
                            "Energy Source": energy_display,
                            "Type": loc_type_display,
                            "Capacity (W)": loc.get("effectiveCapacityWatts", 0),
                            "Latitude": latlng.get("latitude", "N/A"),
                            "Longitude": latlng.get("longitude", "N/A"),
                        })

                    df = pd.DataFrame(location_data)
                    st.dataframe(df, use_container_width=True)
                else:
                    st.info("No locations found with the specified filters")
                    
            except grpc.RpcError as e:
                st.error(f"❌ gRPC Error: {e.details() if hasattr(e, 'details') else str(e)}")
            except Exception as e:
                st.error(f"❌ Error listing locations: {str(e)}")

    # Get Location Details
    st.markdown(
        '<h2 style="color:#63BCAF;font-size: 32px;">Get Location Details</h2>',
        unsafe_allow_html=True,
    )
    loc_uuid = st.text_input("Location UUID", key="get_loc_uuid")
    loc_energy = st.selectbox("Energy Source", ["SOLAR", "WIND"], key="get_loc_energy")
    include_geometry = st.checkbox("Include Geometry", key="get_loc_geom")
    if st.button("Get Location Details", key="get_location_button"):
        if not loc_uuid.strip():
            st.warning("⚠️ Please enter a location UUID")
        elif not data_client:
            st.error("❌ Could not connect to Data Platform")
        else:
            try:
                response = await data_client.get_location(dp.GetLocationRequest(
                    location_uuid=loc_uuid,
                    energy_source=ENERGY_SOURCES.get(loc_energy, 1),
                    include_geometry=include_geometry
                ))
                response_dict = response.to_dict()
                st.success(f"✅ Found location: {loc_uuid}")
                st.write(response_dict)
            except grpc.RpcError as e:
                st.error(f"❌ gRPC Error: {e.details() if hasattr(e, 'details') else str(e)}")
            except Exception as e:
                st.error(f"❌ Error fetching location: {str(e)}")


    # Create Location
    st.markdown(
        '<h2 style="color:#7bcdf3;font-size:32px;">Create Location</h2>',
        unsafe_allow_html=True,
    )
    with st.expander("Create new location"):
        loc_name = st.text_input("Location Name *", key="create_loc_name")
        loc_energy_src = st.selectbox("Energy Source *", ["SOLAR", "WIND"], key="create_loc_energy")
        loc_type = st.selectbox("Location Type *", ["SITE", "GSP", "REGION", "COUNTRY"], key="create_loc_type")
        geometry_wkt = st.text_input(
            "Geometry (WKT) *", 
            placeholder="POINT(-0.127 51.507)",
            key="create_loc_geom",
            help="Enter location geometry in WKT format (e.g., POINT(lon lat))"
        )
        capacity_watts = st.number_input(
            "Effective Capacity (Watts) *", 
            min_value=0, 
            key="create_loc_cap",
            help="Enter the effective capacity in watts"
        )
        loc_metadata = st.text_area(
            "Metadata (JSON)", 
            value="{}", 
            key="create_loc_metadata",
            help="Enter valid JSON for location metadata"
        )
        
        if st.button("Create Location", key="create_location_button"):
            if not data_client:
                st.error("❌ Could not connect to Data Platform")
            elif not loc_name.strip() or not geometry_wkt.strip() or capacity_watts <= 0:
                st.warning("⚠️ Please fill in all required fields (*)")
            else:
                try:
                    # Parse metadata JSON
                    metadata = json.loads(loc_metadata) if loc_metadata.strip() else {}
                    response = await data_client.create_location(dp.CreateLocationRequest(
                        location_name=loc_name,
                        energy_source=ENERGY_SOURCES.get(loc_energy_src, 1),
                        location_type=LOCATION_TYPES.get(loc_type, 1),
                        geometry_wkt=geometry_wkt,
                        effective_capacity_watts=int(capacity_watts),
                        metadata=metadata
                    ))
                    response_dict = response.to_dict()
                    st.success(f"✅ Location '{loc_name}' created successfully!")
                    st.write(response_dict)
                    
                except json.JSONDecodeError:
                    st.error("❌ Invalid JSON in metadata field")
                except grpc.RpcError as e:
                    st.error(f"❌ gRPC Error: {e.details() if hasattr(e, 'details') else str(e)}")
                except Exception as e:
                    st.error(f"❌ Error creating location: {str(e)}")
