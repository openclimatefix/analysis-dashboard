"""User-Organisation relationship management section for the Data Platform Toolbox."""

import streamlit as st
from dataplatform.toolbox.clients import get_admin_client

import grpc

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
    if st.button("Add User to Organisation", key="add_user_to_org_button"):
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
    rem_org = st.text_input("Organisation Name", key="remove_user_org")
    rem_user_oauth = st.text_input("User OAuth ID", key="remove_user_oauth")
    if st.button("Remove User from Organisation", key="remove_user_from_org_button"):
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
