import gpsoauth

# Configuration
email = 'ramtasquer@gmail.com'
password = 'rsuaxuokxbaujvlm '  # Use the App Password here
android_id = '1234567890abcdef'        # Any 16-hex string works for most APIs


def diagnose_login():
    print(f"Attempting login for {email}...")
    # Get the raw response from Google
    response = gpsoauth.perform_master_login(email, password, android_id)

    print("\n--- GOOGLE RESPONSE ---")
    print(response)
    print("-----------------------\n")

    if 'Token' in response:
        print("Success! Master Token retrieved.")
    else:
        error_type = response.get('Error', 'Unknown')
        print(f"Login Failed. Error Type: {error_type}")

        if error_type == 'NeedsBrowser':
            print("Action: Google wants you to log in via a browser first.")
            if 'Url' in response:
                print(f"Open this URL: {response['Url']}")
        elif error_type == 'BadAuthentication':
            print("Action: Double-check that there are no spaces in your App Password.")

diagnose_login()
#
# def get_google_auth():
#     try:
#         # Step 1: Get the Master Token
#         print("Authenticating with Google...")
#         master_response = gpsoauth.perform_master_login(email, password, android_id)
#
#         if 'Token' not in master_response:
#             print("Failed to get Master Token. Check credentials.")
#             return None
#
#         master_token = master_response['Token']
#
#         # Step 2: Get the OAuth Token
#         # 'sj' is for Samsung/Google Play Music; 'oauth2rt' is for general OAuth2
#         # 'audience' and 'service' depend on which API you are targeting
#         auth_response = gpsoauth.perform_oauth_login(
#             email,
#             master_token,
#             android_id,
#             service='sj',
#             app='com.google.android.music',
#             client_sig='38918a453d07199354f8b19af05ec6562ced5788'
#         )
#
#         return auth_response.get('Auth')
#
#     except Exception as e:
#         print(f"An error occurred: {e}")
#         return None
#
# token = get_google_auth()
# if token:
#     print(f"Success! Your OAuth Token is: {token}")
