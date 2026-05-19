"""Organisation management section for the Data Platform Toolbox."""

import streamlit as st
import json
from ocf.dp.dp_admin import messages_pb2, service_pb2_grpc
from grpclib.exceptions import GRPCError
from google.protobuf.json_format import MessageToDict


async def organisation_section(admin_client):
    """Organisation management section."""

    # Get Organisation Details
    st.markdown(
        '<h2 style="color:#63BCAF;font-size: 32px;">Get Organisation Details</h2>',
        unsafe_allow_html=True,
    )
    org_name = st.text_input("Organisation Name", key="get_org_name")
    if st.button("Get Organisation Details", key="get_org_button"):
        if not admin_client:
            st.error("❌ Could not connect to Data Platform")
        elif not org_name.strip():
            st.warning("⚠️ Please enter an organisation name")
        else:
            try:
                response = await admin_client.GetOrganisation(
                    messages_pb2.GetOrganisationRequest(org_name=org_name)
                )
                response_dict = MessageToDict(response)
                st.success(f"✅ Found organisation: {org_name}")
                st.write(response_dict)

            except GRPCError as e:
                st.error(
                    f"❌ gRPC Error: {e.message}"
                )
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
            help="Enter valid JSON for organisation metadata",
        )

        if st.button("Create Organisation", key="create_org_button"):
            if not admin_client:
                st.error("❌ Could not connect to Data Platform")
            elif not new_org_name.strip():
                st.warning("⚠️ Please enter an organisation name")
            else:
                try:
                    # Parse metadata JSON
                    metadata = (
                        json.loads(metadata_json) if metadata_json.strip() else {}
                    )
                    response = await admin_client.CreateOrganisation(
                        messages_pb2.CreateOrganisationRequest(
                            org_name=new_org_name, metadata=metadata
                        )
                    )
                    response_dict = MessageToDict(response)
                    st.success(
                        f"✅ Organisation '{new_org_name}' created successfully!"
                    )
                    st.write(response_dict)

                except json.JSONDecodeError:
                    st.error("❌ Invalid JSON in metadata field")
                except GRPCError as e:
                    st.error(
                        f"❌ gRPC Error: {e.message}"
                    )
                except Exception as e:
                    st.error(f"❌ Error creating organisation: {str(e)}")

    # Delete Organisation
    st.markdown(
        '<h2 style="color:#E63946;font-size:32px;">Delete Organisation</h2>',
        unsafe_allow_html=True,
    )
    with st.expander("Delete organisation"):
        del_org_name = st.text_input(
            "Organisation Name to Delete", key="delete_org_name"
        )
        st.warning("⚠️ This action cannot be undone!")
        confirm_delete = st.checkbox(
            "I understand this will permanently delete the organisation",
            key="confirm_delete_org",
        )
        if st.button("Delete Organisation", key="delete_org_button"):
            if not admin_client:
                st.error("❌ Could not connect to Data Platform")
            elif not del_org_name.strip():
                st.warning("⚠️ Please enter an organisation name")
            elif not confirm_delete:
                st.warning("⚠️ Please confirm deletion by checking the box above")
            else:
                try:
                    await admin_client.DeleteOrganisation(
                        messages_pb2.DeleteOrganisationRequest(org_name=del_org_name)
                    )
                    st.success(
                        f"✅ Organisation '{del_org_name}' deleted successfully!"
                    )

                except GRPCError as e:
                    st.error(
                        f"❌ gRPC Error: {e.message}"
                    )
                except Exception as e:
                    st.error(f"❌ Error deleting organisation: {str(e)}")
