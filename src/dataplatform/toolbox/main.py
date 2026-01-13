"""This module contains the data platform toolbox for the OCF dashboard"""
import os
import json
import streamlit as st
from datetime import datetime
import pandas as pd
from dp_sdk.ocf import dp
from betterproto.lib.google.protobuf import Struct, Value

import grpc
from grpc_requests import Client

# Color scheme (matching existing toolbox)
# teal:  #63BCAF (Get operations)
# blue: #7bcdf3 (Create operations)  
# yellow: #ffd053 (Update operations)
# red: #E63946 (Delete operations)
# orange: #FF9736 (Info sections)


def get_data_platform_url():
    """
    Get the gRPC endpoint for the Data Platform server from
    environment variables DATA_PLATFORM_HOST and DATA_PLATFORM_PORT.
    """
    host = os.environ.get("DATA_PLATFORM_HOST", "localhost")
    port = os.environ.get("DATA_PLATFORM_PORT", "50051")
    return f"{host}:{port}"


def get_admin_client():
    """Get or create the gRPC admin client."""
    dp_url = get_data_platform_url()
    try:
        client = Client.get_by_endpoint(dp_url)
        return client.service("ocf.dp.DataPlatformAdministrationService")
    except Exception as e:
        st.error(f"Failed to connect to Data Platform at {dp_url}: {e}")
        return None


def get_data_client():
    """Get or create the gRPC data client."""
    dp_url = get_data_platform_url()
    try:
        client = Client.get_by_endpoint(dp_url)
        return client.service("ocf.dp.DataPlatformDataService")
    except Exception as e:
        st.error(f"Failed to connect to Data Platform at {dp_url}: {e}")
        return None


def dataplatform_toolbox_page():
    st.markdown(
        '<h1 style="color:#63BCAF;font-size:48px;">Data Platform Toolbox</h1>',
        unsafe_allow_html=True,
    )

    # Create tabs for different sections
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🏢 Organisations", 
        "👤 Users", 
        "🔗 User + Organisation",
        "📍 Locations",
        "📋 Policies"
    ])

    with tab1:
        organisation_section()
    
    with tab2:
        users_section()
    
    with tab3:
        user_organisation_section()
    
    with tab4:
        locations_section()
    
    with tab5:
        policies_section()


def organisation_section():
    """Organisation management section."""
    
    admin_client = get_admin_client()
    
    # Get Organisation Details
    st.markdown(
        '<h2 style="color:#63BCAF;font-size: 32px;">Get Organisation Details</h2>',
        unsafe_allow_html=True,
    )
    org_name = st.text_input("Organisation Name", key="get_org_name")
    if st.button("Get Organisation Details"):
        if not admin_client:
            st.error("❌ Could not connect to Data Platform")
        elif not org_name.strip():
            st.warning("⚠️ Please enter an organisation name")
        else:
            try:
                response = admin_client.GetOrganisation({"org_name": org_name})
                # Handle case where response is a string (JSON) instead of dict
                if isinstance(response, str):
                    response = json.loads(response)
                st.success(f"✅ Found organisation: {org_name}")
                st.write(response)
                    
            except grpc.RpcError as e:
                st.error(f"❌ gRPC Error: {e.details() if hasattr(e, 'details') else str(e)}")
            except Exception as e:
                st.error(f"❌ Error fetching organisation: {str(e)}")
        


    # Create Organisation
    st.markdown(
        '<h2 style="color:#7bcdf3;font-size: 32px;">Create Organisation</h2>',
        unsafe_allow_html=True,
    )
    with st.expander("Create new organisation"):
        new_org_name = st.text_input("New Organisation Name", key="create_org_name")
        metadata_json = st.text_area(
            "Metadata (JSON)", 
            value="{}", 
            key="create_org_metadata",
            help="Enter valid JSON for organisation metadata"
        )

        # lot of if statements earlier

        if st.button("Create Organisation") and admin_client:
            if not admin_client:
                st.error("❌ Could not connect to Data Platform")
            elif not new_org_name.strip():
                st.warning("⚠️ Please enter an organisation name")
            else:
                try:
                    # Parse metadata JSON
                    metadata = json.loads(metadata_json) if metadata_json.strip() else {}
                    # s = Struct()
                    # s.update({"key": "value"})

                    # s.update(metadata)
                    # metadata=Struct().from_pydict(metadata),
                    
                    
                    ## tried this but throwing error: ❌ gRPC Error: Exception serializing request!
                    # request = dp.CreateOrganisationRequest(
                    #     org_name=new_org_name,
                    #     metadata=metadata
                    # )
                    # print("----request object----")
                    # print(request)
                    # print("----------------------")
                    # response = admin_client.CreateOrganisation(request)                    


                    response = admin_client.CreateOrganisation({
                        "org_name": new_org_name,
                        "metadata": metadata
                    })

                    st.success(f"✅ Organisation '{new_org_name}' created successfully!")
                    st.write("**Organisation ID:**", response.get("org_id", "N/A"))
                    st.write("**Organisation Name:**", response.get("org_name", "N/A"))

                    st.write(response)
                    
                except json.JSONDecodeError:
                    st.error("❌ Invalid JSON in metadata field")
                except grpc.RpcError as e:
                    st.error(f"❌ gRPC Error: {e.details() if hasattr(e, 'details') else str(e)}")
                    raise e
                except Exception as e:
                    st.error(f"❌ Error creating organisation: {str(e)}")



    # Delete Organisation
    st.markdown(
        '<h2 style="color:#E63946;font-size:32px;">Delete Organisation</h2>',
        unsafe_allow_html=True,
    )
    with st.expander("Delete organisation"):
        del_org_name = st.text_input("Organisation Name to Delete", key="delete_org_name")
        st.warning("⚠️ This action cannot be undone!")
        confirm_delete = st.checkbox("I understand this will permanently delete the organisation", key="confirm_delete_org")
        if st.button("Delete Organisation"):
            if not admin_client:
                st.error("❌ Could not connect to Data Platform")
            elif not del_org_name.strip():
                st.warning("⚠️ Please enter an organisation name")
            elif not confirm_delete:
                st.warning("⚠️ Please confirm deletion by checking the box above")
            else:
                try:
                    admin_client.DeleteOrganisation({"org_name": del_org_name})
                    st.success(f"✅ Organisation '{del_org_name}' deleted successfully!")
                    
                except grpc.RpcError as e:
                    st.error(f"❌ gRPC Error: {e.details() if hasattr(e, 'details') else str(e)}")
                except Exception as e:
                    st.error(f"❌ Error deleting organisation: {str(e)}")
                        
                    


def users_section():
    """User management section."""
    
    admin_client = get_admin_client()
    
    # Get User Details
    st.markdown(
        '<h2 style="color:#63BCAF;font-size: 32px;">Get User Details</h2>',
        unsafe_allow_html=True,
    )
    oauth_id = st.text_input("User OAuth ID", key="get_user_oauth")
    if st.button("Get User Details"):
        if not admin_client:
            st.error("❌ Could not connect to Data Platform")
        elif not oauth_id.strip():
            st.warning("⚠️ Please enter an OAuth ID")
        else:
            try:
                response = admin_client.GetUser({"oauth_id": oauth_id})
                st.success(f"✅ Found user: {oauth_id}")
                
                # Display user details
                col1, col2 = st.columns(2)
                with col1:
                    st.write("**User ID:**", response.get("user_id", "N/A"))
                    st.write("**OAuth ID:**", response.get("oauth_id", "N/A"))
                    st.write("**Organisation:**", response.get("organisation", "N/A"))
                    created_at = response.get("created_at", {})
                    if created_at:
                        # Handle both ISO string and dict with seconds
                        if isinstance(created_at, str):
                            st.write("**Created At:**", created_at)
                        elif isinstance(created_at, dict):
                            st.write("**Created At:**", datetime.fromtimestamp(
                                created_at.get("seconds", 0)
                            ).strftime("%Y-%m-%d %H:%M:%S"))
                with col2:
                    st.write("**Location Policy Groups:**")
                    policy_groups = response.get("location_policy_groups", [])
                    if policy_groups:
                        for pg in policy_groups:
                            st.write(f"  - {pg}")
                    else:
                        st.write("  None")
                
                # Display metadata
                metadata = response.get("metadata", {})
                if metadata:
                    st.write("**Metadata:**")
                    st.json(metadata)
                    
            except grpc.RpcError as e:
                st.error(f"❌ gRPC Error: {e.details() if hasattr(e, 'details') else str(e)}")
            except Exception as e:
                st.error(f"❌ Error fetching user: {str(e)}")
                

    # Create User
    st.markdown(
        '<h2 style="color:#7bcdf3;font-size:32px;">Create User</h2>',
        unsafe_allow_html=True,
    )
    with st.expander("Create new user"):
        new_oauth_id = st.text_input("OAuth ID", key="create_user_oauth")
        user_org = st.text_input("Organisation Name", key="create_user_org", 
                                  help="User must be associated with an existing organisation")
        user_metadata = st.text_area(
            "Metadata (JSON)", 
            value="{}", 
            key="create_user_metadata",
            help="Enter valid JSON for user metadata"
        )
        if st.button("Create User"):
            if not admin_client:
                st.error("❌ Could not connect to Data Platform")
            elif not new_oauth_id.strip() or not user_org.strip():
                st.warning("⚠️ Please fill in all required fields")
            else:
                try:
                    # Parse metadata JSON
                    metadata = json.loads(user_metadata) if user_metadata.strip() else {}
                    #pass the object rather than dictionary
                    response = admin_client.CreateUser({
                        "oauth_id": new_oauth_id,
                        "organisation": user_org,
                        "metadata": metadata
                    })
                    
                    st.success(f"✅ User '{new_oauth_id}' created in organisation '{user_org}'!")
                    st.write("**User ID:**", response.get("user_id", "N/A"))
                    st.write("**OAuth ID:**", response.get("oauth_id", "N/A"))
                    st.write(response)
                    
                except json.JSONDecodeError:
                    st.error("❌ Invalid JSON in metadata field")
                except grpc.RpcError as e:
                    st.error(f"❌ gRPC Error: {e.details() if hasattr(e, 'details') else str(e)}")
                except Exception as e:
                    st.error(f"❌ Error creating user: {str(e)}")

                

    # Delete User
    st.markdown(
        '<h2 style="color:#E63946;font-size:32px;">Delete User</h2>',
        unsafe_allow_html=True,
    )
    with st.expander("Delete user"):
        del_user_id = st.text_input("User UUID to Delete", key="delete_user_id",
                                    help="Enter the UUID of the user (not OAuth ID)")
        st.warning("⚠️ This action cannot be undone!")
        confirm_delete_user = st.checkbox("I understand this will permanently delete the user", key="confirm_delete_user")
        if st.button("Delete User"):
            if not admin_client:
                st.error("❌ Could not connect to Data Platform")
            elif not del_user_id.strip():
                st.warning("⚠️ Please enter a user ID")
            elif not confirm_delete_user:
                st.warning("⚠️ Please confirm deletion by checking the box above")
            else:
                try:
                    admin_client.DeleteUser({"user_id": del_user_id})
                    st.success(f"✅ User '{del_user_id}' deleted successfully!")
                    
                except grpc.RpcError as e:
                    st.error(f"❌ gRPC Error: {e.details() if hasattr(e, 'details') else str(e)}")
                except Exception as e:
                    st.error(f"❌ Error deleting user: {str(e)}")
                        
                    
                
def user_organisation_section():
    """User + Organisation relationship management."""
    
    admin_client = get_admin_client()
    
    # Add User to Organisation
    st.markdown(
        '<h2 style="color:#ffd053;font-size:32px;">Add User to Organisation</h2>',
        unsafe_allow_html=True,
    )
    add_org = st.text_input("Organisation Name", key="add_user_org")
    add_user_oauth = st.text_input("User OAuth ID", key="add_user_oauth")
    if st.button("Add User to Organisation"):
        if not admin_client:
            st.error("❌ Could not connect to Data Platform")
        elif not add_org.strip() or not add_user_oauth.strip():
            st.warning("⚠️ Please fill in all fields")
        else:
            try:
                admin_client.AddUserToOrganisation({
                    "org_name": add_org,
                    "user_oauth_id": add_user_oauth
                })
                st.success(f"✅ User '{add_user_oauth}' added to organisation '{add_org}'!")
                
            except grpc.RpcError as e:
                st.error(f"❌ gRPC Error: {e.details() if hasattr(e, 'details') else str(e)}")
            except Exception as e:
                st.error(f"❌ Error adding user to organisation: {str(e)}")


    # Remove User from Organisation
    st.markdown(
        '<h2 style="color:#E63946;font-size:32px;">Remove User from Organisation</h2>',
        unsafe_allow_html=True,
    )
    rem_org = st.text_input("Organisation Name", key="rem_user_org")
    rem_user_oauth = st.text_input("User OAuth ID", key="rem_user_oauth")
    if st.button("Remove User from Organisation"):
        if not admin_client:
            st.error("❌ Could not connect to Data Platform")
        elif not rem_org.strip() or not rem_user_oauth.strip():
            st.warning("⚠️ Please fill in all fields")
        else:
            try:
                admin_client.RemoveUserFromOrganisation({
                    "org_name": rem_org,
                    "user_oauth_id": rem_user_oauth
                })
                st.success(f"✅ User '{rem_user_oauth}' removed from organisation '{rem_org}'!")
                
            except grpc.RpcError as e:
                st.error(f"❌ gRPC Error: {e.details() if hasattr(e, 'details') else str(e)}")
            except Exception as e:
                st.error(f"❌ Error removing user from organisation: {str(e)}")



def locations_section():
    """Location management section."""
    
    data_client = get_data_client()
    
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
    if st.button("List Locations"):
        if not data_client:
            st.error("❌ Could not connect to Data Platform")
        else:
            try:
                request = {}
                if energy_source_filter != "All":
                    request["energy_source_filter"] = ENERGY_SOURCES[energy_source_filter]
                if location_type_filter != "All":
                    request["location_type_filter"] = LOCATION_TYPES[location_type_filter]
                if user_filter:
                    request["user_oauth_id_filter"] = user_filter
                
                response = data_client.ListLocations(request)
                locations = response.get("locations", [])
                
                if locations:
                    st.success(f"✅ Found {len(locations)} location(s)")
                    
                    # Display as a table
                    location_data = []
                    location_type_names = ["Unknown", "SITE", "GSP", "REGION", "COUNTRY"]
                    for loc in locations:
                        latlng = loc.get("latlng", {})
                        # Handle energy_source that might be string or int
                        energy = loc.get("energy_source", 0)
                        if isinstance(energy, str):
                            energy_display = "SOLAR" if energy in ("1", "SOLAR") else "WIND" if energy in ("2", "WIND") else energy
                        else:
                            energy_display = "SOLAR" if energy == 1 else "WIND" if energy == 2 else "Unknown"
                        
                        # Handle location_type that might be string or int
                        loc_type = loc.get("location_type", 0)
                        if isinstance(loc_type, str):
                            # Could be "1" or "SITE" etc.
                            if loc_type.isdigit():
                                loc_type_display = location_type_names[int(loc_type)] if int(loc_type) < len(location_type_names) else loc_type
                            else:
                                loc_type_display = loc_type
                        else:
                            loc_type_display = location_type_names[loc_type] if loc_type < len(location_type_names) else "Unknown"
                        
                        location_data.append({
                            "UUID": loc.get("location_uuid", "N/A"),
                            "Name": loc.get("location_name", "N/A"),
                            "Energy Source": energy_display,
                            "Type": loc_type_display,
                            "Capacity (W)": loc.get("effective_capacity_watts", 0),
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
    if st.button("Get Location Details"):
        if not loc_uuid.strip():
            st.warning("⚠️ Please enter a location UUID")
        elif not data_client:
            st.error("❌ Could not connect to Data Platform")
        else:
            try:
                response = data_client.GetLocation({
                    "location_uuid": loc_uuid,
                    "energy_source": ENERGY_SOURCES.get(loc_energy, 1),
                    "include_geometry": include_geometry
                })
                st.success(f"✅ Found location: {loc_uuid}")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.write("**Location UUID:**", response.get("location_uuid", "N/A"))
                    st.write("**Location Name:**", response.get("location_name", "N/A"))
                    energy = response.get("energy_source", 0)
                    st.write("**Energy Source:**", "SOLAR" if energy == 1 else "WIND" if energy == 2 else "Unknown")
                    loc_type = response.get("location_type", 0)
                    st.write("**Location Type:**", ["Unknown", "SITE", "GSP", "REGION", "COUNTRY"][loc_type])
                
                with col2:
                    capacity = response.get('effective_capacity_watts', 0)
                    # Handle case where capacity might be a string
                    if isinstance(capacity, str):
                        try:
                            capacity = int(capacity)
                        except ValueError:
                            capacity = 0
                    st.write("**Effective Capacity:**", f"{capacity:,} W")
                    latlng = response.get("latlng", {})
                    st.write("**Latitude:**", latlng.get("latitude", "N/A"))
                    st.write("**Longitude:**", latlng.get("longitude", "N/A"))
                
                if include_geometry:
                    geometry = response.get("geometry_wkt", "")
                    if geometry:
                        st.write("**Geometry (WKT):**")
                        st.code(geometry)
                
                # Display metadata
                metadata = response.get("metadata", {})
                if metadata:
                    st.write("**Metadata:**")
                    st.json(metadata)
                    
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
        
        if st.button("Create Location"):
            if not data_client:
                st.error("❌ Could not connect to Data Platform")
            elif not loc_name.strip() or not geometry_wkt.strip() or capacity_watts <= 0:
                st.warning("⚠️ Please fill in all required fields (*)")
            else:
                try:
                    # Parse metadata JSON
                    metadata = json.loads(loc_metadata) if loc_metadata.strip() else {}
                    
                    response = data_client.CreateLocation({
                        "location_name": loc_name,
                        "energy_source": ENERGY_SOURCES.get(loc_energy_src, 1),
                        "location_type": LOCATION_TYPES.get(loc_type, 1),
                        "geometry_wkt": geometry_wkt,
                        "effective_capacity_watts": int(capacity_watts),
                        "metadata": metadata
                    })
                    st.success(f"✅ Location '{loc_name}' created successfully!")
                    st.write("**Location UUID:**", response.get("location_uuid", "N/A"))
                    st.write(response)
                    
                except json.JSONDecodeError:
                    st.error("❌ Invalid JSON in metadata field")
                except grpc.RpcError as e:
                    st.error(f"❌ gRPC Error: {e.details() if hasattr(e, 'details') else str(e)}")
                except Exception as e:
                    st.error(f"❌ Error creating location: {str(e)}")



def policies_section():
    """Policy management section."""
    
    admin_client = get_admin_client()
    
    # Permission mappings
    PERMISSIONS = {
        "READ": 1,   # PERMISSION_READ
        "WRITE": 2,  # PERMISSION_WRITE
    }
    
    ENERGY_SOURCES = {
        "SOLAR": 1,  # ENERGY_SOURCE_SOLAR
        "WIND": 2,   # ENERGY_SOURCE_WIND
    }
    
    # Create Location Policy Group
    st.markdown(
        '<h2 style="color:#7bcdf3;font-size: 32px;">Create Location Policy Group</h2>',
        unsafe_allow_html=True,
    )
    with st.expander("Create new policy group"):
        new_policy_group_name = st.text_input("Policy Group Name", key="create_policy_group_name")
        if st.button("Create Policy Group"):
            if not admin_client:
                st.error("❌ Could not connect to Data Platform")
            elif not new_policy_group_name.strip():
                st.warning("⚠️ Please enter a policy group name")
            else:
                try:
                    response = admin_client.CreateLocationPolicyGroup({
                        "name": new_policy_group_name
                    })
                    st.success(f"✅ Policy Group '{new_policy_group_name}' created!")
                    st.write("**Policy Group ID:**", response.get("location_policy_group_id", "N/A"))
                    st.write("**Name:**", response.get("name", "N/A"))
                except grpc.RpcError as e:
                    st.error(f"❌ gRPC Error: {e.details() if hasattr(e, 'details') else str(e)}")
                except Exception as e:
                    st.error(f"❌ Error creating policy group: {str(e)}")

    
    # Get Location Policy Group Details
    st.markdown(
        '<h2 style="color:#63BCAF;font-size: 32px;">Get Policy Group Details</h2>',
        unsafe_allow_html=True,
    )
    policy_group_name = st.text_input("Policy Group Name", key="get_policy_group_name")
    if st.button("Get Policy Group Details"):
        if not admin_client:
            st.error("❌ Could not connect to Data Platform")
        elif not policy_group_name.strip():
            st.warning("⚠️ Please enter a policy group name")
        else:
            try:
                response = admin_client.GetLocationPolicyGroup({
                    "location_policy_group_name": policy_group_name
                })
                st.success(f"✅ Found policy group: {policy_group_name}")
                
                st.write("**Policy Group ID:**", response.get("location_policy_group_id", "N/A"))
                st.write("**Name:**", response.get("name", "N/A"))
                
                # Display location policies
                policies = response.get("location_policies", [])
                if policies:
                    st.write("**Location Policies:**")
                    policy_data = []
                    for policy in policies:
                        policy_data.append({
                            "Location ID": policy.get("location_id", "N/A"),
                            "Energy Source": "SOLAR" if policy.get("energy_source") == 1 else "WIND",
                            "Permission": "READ" if policy.get("permission") == 1 else "WRITE",
                        })
                    df = pd.DataFrame(policy_data)
                    st.dataframe(df, use_container_width=True)
                else:
                    st.write("**Location Policies:** None")
                    
            except grpc.RpcError as e:
                st.error(f"❌ gRPC Error: {e.details() if hasattr(e, 'details') else str(e)}")
            except Exception as e:
                st.error(f"❌ Error fetching policy group: {str(e)}")
            
    
    # Add Location Policies to Group
    st.markdown(
        '<h2 style="color:#ffd053;font-size:32px;">Add Location Policies to Group</h2>',
        unsafe_allow_html=True,
    )
    with st.expander("Add policies to group"):
        add_policy_group = st.text_input("Policy Group Name", key="add_policy_group")
        add_location_id = st.text_input("Location UUID", key="add_policy_location")
        add_energy_source = st.selectbox("Energy Source", ["SOLAR", "WIND"], key="add_policy_energy")
        add_permission = st.selectbox("Permission", ["READ", "WRITE"], key="add_policy_permission")
        
        if st.button("Add Policy to Group"):
            if not admin_client:
                st.error("❌ Could not connect to Data Platform")
            elif not add_policy_group.strip() or not add_location_id.strip():
                st.warning("⚠️ Please fill in all required fields")
            else:
                try:
                    admin_client.AddLocationPoliciesToGroup({
                        "location_policy_group_name": add_policy_group,
                        "location_policies": [{
                            "location_id": add_location_id,
                            "energy_source": ENERGY_SOURCES[add_energy_source],
                            "permission": PERMISSIONS[add_permission]
                        }]
                    })
                    st.success(f"✅ Policy added to group '{add_policy_group}'!")
                except grpc.RpcError as e:
                    st.error(f"❌ gRPC Error: {e.details() if hasattr(e, 'details') else str(e)}")
                except Exception as e:
                    st.error(f"❌ Error adding policy: {str(e)}")
        
    
    # Remove Location Policies from Group
    st.markdown(
        '<h2 style="color:#E63946;font-size:32px;">Remove Location Policies from Group</h2>',
        unsafe_allow_html=True,
    )
    with st.expander("Remove policies from group"):
        rem_policy_group = st.text_input("Policy Group Name", key="rem_policy_group")
        rem_location_id = st.text_input("Location UUID", key="rem_policy_location")
        rem_energy_source = st.selectbox("Energy Source", ["SOLAR", "WIND"], key="rem_policy_energy")
        rem_permission = st.selectbox("Permission", ["READ", "WRITE"], key="rem_policy_permission")
        
        if st.button("Remove Policy from Group"):
            if not admin_client:
                st.error("❌ Could not connect to Data Platform")
            elif not rem_policy_group.strip() or not rem_location_id.strip():
                st.warning("⚠️ Please fill in all required fields")
            else:
                try:
                    admin_client.RemoveLocationPoliciesFromGroup({
                        "location_policy_group_name": rem_policy_group,
                        "location_policies": [{
                            "location_id": rem_location_id,
                            "energy_source": ENERGY_SOURCES[rem_energy_source],
                            "permission": PERMISSIONS[rem_permission]
                        }]
                    })
                    st.success(f"✅ Policy removed from group '{rem_policy_group}'!")
                except grpc.RpcError as e:
                    st.error(f"❌ gRPC Error: {e.details() if hasattr(e, 'details') else str(e)}")
                except Exception as e:
                    st.error(f"❌ Error removing policy: {str(e)}")

                
    
    # Add Policy Group to Organisation
    st.markdown(
        '<h2 style="color:#ffd053;font-size:32px;">Add Policy Group to Organisation</h2>',
        unsafe_allow_html=True,
    )
    add_pg_org = st.text_input("Organisation Name", key="add_pg_org")
    add_pg_name = st.text_input("Policy Group Name", key="add_pg_name")
    if st.button("Add Policy Group to Organisation"):
        if not admin_client:
            st.error("❌ Could not connect to Data Platform")
        elif not add_pg_org.strip() or not add_pg_name.strip():
            st.warning("⚠️ Please fill in all fields")
        else:
            try:
                admin_client.AddLocationPolicyGroupToOrganisation({
                    "org_name": add_pg_org,
                    "location_policy_group_name": add_pg_name
                })
                st.success(f"✅ Policy group '{add_pg_name}' added to organisation '{add_pg_org}'!")
            except grpc.RpcError as e:
                st.error(f"❌ gRPC Error: {e.details() if hasattr(e, 'details') else str(e)}")
            except Exception as e:
                st.error(f"❌ Error adding policy group to organisation: {str(e)}")

    
    # Remove Policy Group from Organisation
    st.markdown(
        '<h2 style="color:#E63946;font-size:32px;">Remove Policy Group from Organisation</h2>',
        unsafe_allow_html=True,
    )
    rem_pg_org = st.text_input("Organisation Name", key="rem_pg_org")
    rem_pg_name = st.text_input("Policy Group Name", key="rem_pg_name")
    if st.button("Remove Policy Group from Organisation"):
        if not rem_pg_org.strip() or not rem_pg_name.strip():
            st.warning("⚠️ Please fill in all fields")
        elif not admin_client:
            st.error("❌ Could not connect to Data Platform")
        else:
            try:
                admin_client.RemoveLocationPolicyGroupFromOrganisation({
                    "org_name": rem_pg_org,
                    "location_policy_group_name": rem_pg_name
                })
                st.success(f"✅ Policy group '{rem_pg_name}' removed from organisation '{rem_pg_org}'!")
            except grpc.RpcError as e:
                st.error(f"❌ gRPC Error: {e.details() if hasattr(e, 'details') else str(e)}")
            except Exception as e:
                st.error(f"❌ Error removing policy group from organisation: {str(e)}")