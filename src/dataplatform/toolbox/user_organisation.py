"""User-Organisation relationship management section for the Data Platform Toolbox."""

import streamlit as st
from dp_sdk.ocf import dp
from grpclib.exceptions import GRPCError


async def user_organisation_section(admin_client):
    """User + Organisation relationship management."""

    # Add User to Organisation
    st.markdown(
        '<h2 style="color:#ffd053;font-size:32px;">Add User to Organisation</h2>',
        unsafe_allow_html=True,
    )
    add_org = st.text_input("Organisation Name", key="add_user_org")
    add_user_oauth = st.text_input("User OAuth ID", key="add_user_oauth")
    if st.button("Add User to Organisation", key="add_user_to_org_button"):
        if not admin_client:
            st.error("❌ Could not connect to Data Platform")
        elif not add_org.strip() or not add_user_oauth.strip():
            st.warning("⚠️ Please fill in all fields")
        else:
            try:
                await admin_client.add_user_to_organisation(
                    dp.AddUserToOrganisationRequest(
                        org_name=add_org, user_oauth_id=add_user_oauth
                    )
                )
                st.success(
                    f"✅ User '{add_user_oauth}' added to organisation '{add_org}'!"
                )

            except GRPCError as e:
                st.error(
                    f"❌ gRPC Error: {e.message}"
                )
            except Exception as e:
                st.error(f"❌ Error adding user to organisation: {str(e)}")

    # Remove User from Organisation
    st.markdown(
        '<h2 style="color:#E63946;font-size:32px;">Remove User from Organisation</h2>',
        unsafe_allow_html=True,
    )
    remove_org = st.text_input("Organisation Name", key="remove_user_org")
    remove_user_oauth = st.text_input("User OAuth ID", key="remove_user_oauth")
    if st.button("Remove User from Organisation", key="remove_user_from_org_button"):
        if not admin_client:
            st.error("❌ Could not connect to Data Platform")
        elif not remove_org.strip() or not remove_user_oauth.strip():
            st.warning("⚠️ Please fill in all fields")
        else:
            try:
                await admin_client.remove_user_from_organisation(
                    dp.RemoveUserFromOrganisationRequest(
                        org_name=remove_org, user_oauth_id=remove_user_oauth
                    )
                )
                st.success(
                    f"✅ User '{remove_user_oauth}' removed from organisation '{remove_org}'!"
                )

            except GRPCError as e:
                st.error(
                    f"❌ gRPC Error: {e.message}"
                )
            except Exception as e:
                st.error(f"❌ Error removing user from organisation: {str(e)}")
