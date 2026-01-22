"""User management section for the Data Platform Toolbox."""

import streamlit as st
import json
from dp_sdk.ocf import dp
import grpc


async def users_section(admin_client):
    """User management section."""

    # Get User Details
    st.markdown(
        '<h2 style="color:#63BCAF;font-size: 32px;">Get User Details</h2>',
        unsafe_allow_html=True,
    )
    oauth_id = st.text_input("User OAuth ID", key="get_user_oauth")
    if st.button("Get User Details", key="get_user_button"):
        if not admin_client:
            st.error("❌ Could not connect to Data Platform")
        elif not oauth_id.strip():
            st.warning("⚠️ Please enter an OAuth ID")
        else:
            try:
                response = await admin_client.get_user(
                    dp.GetUserRequest(oauth_id=oauth_id)
                )
                response_dict = response.to_dict()
                st.success(f"✅ Found user: {oauth_id}")
                st.write(response_dict)

            except grpc.RpcError as e:
                st.error(
                    f"❌ gRPC Error: {e.details() if hasattr(e, 'details') else str(e)}"
                )
            except Exception as e:
                st.error(f"❌ Error fetching user: {str(e)}")

    # Create User
    st.markdown(
        '<h2 style="color:#7bcdf3;font-size:32px;">Create User</h2>',
        unsafe_allow_html=True,
    )
    with st.expander("Create new user"):
        new_oauth_id = st.text_input("OAuth ID", key="create_user_oauth")
        user_org = st.text_input(
            "Organisation Name",
            key="create_user_org",
            help="User must be associated with an existing organisation",
        )
        user_metadata = st.text_area(
            "Metadata (JSON)",
            value="{}",
            key="create_user_metadata",
            help="Enter valid JSON for user metadata",
        )
        if st.button("Create User", key="create_user_button"):
            if not admin_client:
                st.error("❌ Could not connect to Data Platform")
            elif not new_oauth_id.strip() or not user_org.strip():
                st.warning("⚠️ Please fill in all required fields")
            else:
                try:
                    # Parse metadata JSON
                    metadata = (
                        json.loads(user_metadata) if user_metadata.strip() else {}
                    )
                    response = await admin_client.create_user(
                        dp.CreateUserRequest(
                            oauth_id=new_oauth_id,
                            organisation=user_org,
                            metadata=metadata,
                        )
                    )
                    response_dict = response.to_dict()
                    st.success(
                        f"✅ User '{new_oauth_id}' created in organisation '{user_org}'!"
                    )
                    st.write(response_dict)

                except json.JSONDecodeError:
                    st.error("❌ Invalid JSON in metadata field")
                except grpc.RpcError as e:
                    st.error(
                        f"❌ gRPC Error: {e.details() if hasattr(e, 'details') else str(e)}"
                    )
                except Exception as e:
                    st.error(f"❌ Error creating user: {str(e)}")

    # Delete User
    st.markdown(
        '<h2 style="color:#E63946;font-size:32px;">Delete User</h2>',
        unsafe_allow_html=True,
    )
    with st.expander("Delete user"):
        del_user_id = st.text_input(
            "User UUID to Delete",
            key="delete_user_id",
            help="Enter the UUID of the user (not OAuth ID)",
        )
        st.warning("⚠️ This action cannot be undone!")
        confirm_delete_user = st.checkbox(
            "I understand this will permanently delete the user",
            key="confirm_delete_user",
        )
        if st.button("Delete User", key="delete_user_button"):
            if not admin_client:
                st.error("❌ Could not connect to Data Platform")
            elif not del_user_id.strip():
                st.warning("⚠️ Please enter a user ID")
            elif not confirm_delete_user:
                st.warning("⚠️ Please confirm deletion by checking the box above")
            else:
                try:
                    # admin_client.DeleteUser({"user_id": del_user_id})
                    await admin_client.delete_user(
                        dp.DeleteUserRequest(user_id=del_user_id)
                    )
                    st.success(f"✅ User '{del_user_id}' deleted successfully!")

                except grpc.RpcError as e:
                    st.error(
                        f"❌ gRPC Error: {e.details() if hasattr(e, 'details') else str(e)}"
                    )
                except Exception as e:
                    st.error(f"❌ Error deleting user: {str(e)}")
