"""Policy management section for the Data Platform Toolbox."""

import streamlit as st
import grpc
from dp_sdk.ocf import dp


async def policies_section(admin_client, data_client):
    """Policy management section."""

    # Permission mappings
    PERMISSIONS = {
        "READ": dp.Permission.READ,
        "WRITE": dp.Permission.WRITE,
    }

    ENERGY_SOURCES = {
        "SOLAR": dp.EnergySource.SOLAR,
        "WIND": dp.EnergySource.WIND,
    }

    # Create Location Policy Group
    st.markdown(
        '<h2 style="color:#7bcdf3;font-size: 32px;">Create Location Policy Group</h2>',
        unsafe_allow_html=True,
    )
    with st.expander("Create new policy group"):
        new_policy_group_name = st.text_input(
            "Policy Group Name", key="create_policy_group_name"
        )
        if st.button("Create Policy Group", key="create_policy_group_button"):
            if not admin_client:
                st.error("❌ Could not connect to Data Platform")
            elif not new_policy_group_name.strip():
                st.warning("⚠️ Please enter a policy group name")
            else:
                try:
                    response = await admin_client.create_location_policy_group(
                        dp.CreateLocationPolicyGroupRequest(name=new_policy_group_name)
                    )
                    response_dict = response.to_dict()
                    st.success(f"✅ Policy Group '{new_policy_group_name}' created!")
                    st.write(response_dict)
                except grpc.RpcError as e:
                    st.error(
                        f"❌ gRPC Error: {e.details() if hasattr(e, 'details') else str(e)}"
                    )
                except Exception as e:
                    st.error(f"❌ Error creating policy group: {str(e)}")

    # Get Location Policy Group Details
    st.markdown(
        '<h2 style="color:#63BCAF;font-size: 32px;">Get Policy Group Details</h2>',
        unsafe_allow_html=True,
    )
    policy_group_name = st.text_input("Policy Group Name", key="get_policy_group_name")
    if st.button("Get Policy Group Details", key="get_policy_group_button"):
        if not admin_client:
            st.error("❌ Could not connect to Data Platform")
        elif not policy_group_name.strip():
            st.warning("⚠️ Please enter a policy group name")
        else:
            try:
                response = await admin_client.get_location_policy_group(
                    dp.GetLocationPolicyGroupRequest(
                        location_policy_group_name=policy_group_name
                    )
                )
                response_dict = response.to_dict()
                st.success(f"✅ Found policy group: {policy_group_name}")
                st.write(response_dict)

            except grpc.RpcError as e:
                st.error(
                    f"❌ gRPC Error: {e.details() if hasattr(e, 'details') else str(e)}"
                )
            except Exception as e:
                st.error(f"❌ Error fetching policy group: {str(e)}")

    # Add Location Policies to Group
    st.markdown(
        '<h2 style="color:#ffd053;font-size:32px;">Add Location Policies to Group</h2>',
        unsafe_allow_html=True,
    )
    with st.expander("Add policies to group"):
        add_policy_group = st.text_input("Policy Group Name", key="add_policy_group")
        locations = []

        if data_client:
            try:
                response = await data_client.list_locations(dp.ListLocationsRequest())
                response_dict = response.to_dict()
                locations = response_dict.get("locations", [])
            except Exception as e:
                st.error(f"❌ Failed to fetch locations: {e}")

        if not locations:
            st.info("ℹ️ No locations found. Please create a location first.")

        location_options = {
            f"{loc.get('locationName', 'N/A')} — {loc.get('locationUuid', '')}": loc.get(
                "locationUuid"
            )
            for loc in locations
        }

        selected_label = st.selectbox(
            "Location", options=list(location_options.keys()), key="add_policy_location"
        )

        add_location_id = location_options.get(selected_label)

        add_energy_source = st.selectbox(
            "Energy Source", ["SOLAR", "WIND"], key="add_policy_energy"
        )
        add_permission = st.selectbox(
            "Permission", ["READ", "WRITE"], key="add_policy_permission"
        )

        if st.button("Add Policy to Group", key="add_policy_button"):
            if not admin_client:
                st.error("❌ Could not connect to Data Platform")
            elif not add_policy_group.strip() or not add_location_id.strip():
                st.warning("⚠️ Please fill in all required fields")
            else:
                try:
                    await admin_client.add_location_policies_to_group(
                        dp.AddLocationPoliciesToGroupRequest(
                            location_policy_group_name=add_policy_group,
                            location_policies=[
                                dp.LocationPolicy(
                                    location_id=add_location_id,
                                    energy_source=ENERGY_SOURCES[add_energy_source],
                                    permission=PERMISSIONS[add_permission],
                                )
                            ],
                        )
                    )
                    st.success(f"✅ Policy added to group '{add_policy_group}'!")
                except grpc.RpcError as e:
                    st.error(
                        f"❌ gRPC Error: {e.details() if hasattr(e, 'details') else str(e)}"
                    )
                except Exception as e:
                    st.error(f"❌ Error adding policy: {str(e)}")

    # Remove Location Policies from Group
    st.markdown(
        '<h2 style="color:#E63946;font-size:32px;">Remove Location Policies from Group</h2>',
        unsafe_allow_html=True,
    )
    with st.expander("Remove policies from group"):
        remove_policy_group = st.text_input(
            "Policy Group Name", key="remove_policy_group"
        )
        locations = []

        if data_client:
            try:
                response = await data_client.list_locations(dp.ListLocationsRequest())
                response_dict = response.to_dict()
                locations = response_dict.get("locations", [])
            except Exception as e:
                st.error(f"❌ Failed to fetch locations: {e}")

        if not locations:
            st.info("ℹ️ No locations found. Please create a location first.")

        location_options = {
            f"{loc.get('locationName', 'N/A')} — {loc.get('locationUuid', '')}": loc.get(
                "locationUuid"
            )
            for loc in locations
        }

        selected_label = st.selectbox(
            "Location",
            options=list(location_options.keys()),
            key="remove_policy_location",
        )

        remove_location_id = location_options.get(selected_label)
        remove_energy_source = st.selectbox(
            "Energy Source", ["SOLAR", "WIND"], key="remove_policy_energy"
        )
        remove_permission = st.selectbox(
            "Permission", ["READ", "WRITE"], key="remove_policy_permission"
        )

        if st.button("Remove Policy from Group", key="remove_policy_button"):
            if not admin_client:
                st.error("❌ Could not connect to Data Platform")
            elif not remove_policy_group.strip() or not remove_location_id.strip():
                st.warning("⚠️ Please fill in all required fields")
            else:
                try:
                    await admin_client.remove_location_policies_from_group(
                        dp.RemoveLocationPoliciesFromGroupRequest(
                            location_policy_group_name=remove_policy_group,
                            location_policies=[
                                dp.LocationPolicy(
                                    location_id=remove_location_id,
                                    energy_source=ENERGY_SOURCES[remove_energy_source],
                                    permission=PERMISSIONS[remove_permission],
                                )
                            ],
                        )
                    )
                    st.success(f"✅ Policy removed from group '{remove_policy_group}'!")
                except grpc.RpcError as e:
                    st.error(
                        f"❌ gRPC Error: {e.details() if hasattr(e, 'details') else str(e)}"
                    )
                except Exception as e:
                    st.error(f"❌ Error removing policy: {str(e)}")

    # Add Policy Group to Organisation
    st.markdown(
        '<h2 style="color:#ffd053;font-size:32px;">Add Policy Group to Organisation</h2>',
        unsafe_allow_html=True,
    )
    add_pg_org = st.text_input("Organisation Name", key="add_pg_org")
    add_pg_name = st.text_input("Policy Group Name", key="add_pg_name")
    if st.button("Add Policy Group to Organisation", key="add_pg_to_org_button"):
        if not admin_client:
            st.error("❌ Could not connect to Data Platform")
        elif not add_pg_org.strip() or not add_pg_name.strip():
            st.warning("⚠️ Please fill in all fields")
        else:
            try:
                await admin_client.add_location_policy_group_to_organisation(
                    dp.AddLocationPolicyGroupToOrganisationRequest(
                        org_name=add_pg_org, location_policy_group_name=add_pg_name
                    )
                )
                st.success(
                    f"✅ Policy group '{add_pg_name}' added to organisation '{add_pg_org}'!"
                )
            except grpc.RpcError as e:
                st.error(
                    f"❌ gRPC Error: {e.details() if hasattr(e, 'details') else str(e)}"
                )
            except Exception as e:
                st.error(f"❌ Error adding policy group to organisation: {str(e)}")

    # Remove Policy Group from Organisation
    st.markdown(
        '<h2 style="color:#E63946;font-size:32px;">Remove Policy Group from Organisation</h2>',
        unsafe_allow_html=True,
    )
    remove_policy_group_org = st.text_input(
        "Organisation Name", key="remove_policy_group_org"
    )
    remove_policy_group_name = st.text_input(
        "Policy Group Name", key="remove_policy_group_name"
    )
    if st.button(
        "Remove Policy Group from Organisation",
        key="remove_policy_group_from_org_button",
    ):
        if not remove_policy_group_org.strip() or not remove_policy_group_name.strip():
            st.warning("⚠️ Please fill in all fields")
        elif not admin_client:
            st.error("❌ Could not connect to Data Platform")
        else:
            try:
                await admin_client.remove_location_policy_group_from_organisation(
                    dp.RemoveLocationPolicyGroupFromOrganisationRequest(
                        org_name=remove_policy_group_org,
                        location_policy_group_name=remove_policy_group_name,
                    )
                )
                st.success(
                    f"✅ Policy group '{remove_policy_group_name}' removed from organisation '{remove_policy_group_org}'!"
                )
            except grpc.RpcError as e:
                st.error(
                    f"❌ gRPC Error: {e.details() if hasattr(e, 'details') else str(e)}"
                )
            except Exception as e:
                st.error(f"❌ Error removing policy group from organisation: {str(e)}")
